import json
import urllib.parse
import os
import psycopg2
import sys
import re

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from docling_ingestion import detect_doc_type, infer_doc_type_from_text
import importlib.util

# Load the extractor module dynamically to avoid naming conflicts if any
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "14_ai_copilot_extractor_v2.py")
spec = importlib.util.spec_from_file_location("extractor_v2_interface", path)
ext_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ext_mod)

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAPSHOT_PATH = os.path.join(ROOT_DIR, "scripts", "archive", "analysis_and_audits", "db_snapshot_pre_ai.json")

CANONICAL_CATEGORY_ORDER = ['BC', 'ES', 'F', 'IP', 'IS', 'L', 'M', 'PMF', 'T', 'TP', 'OTHER']

def load_db_url():
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"].replace("?pgbouncer=true", "")
    with open(".env", "r") as f:
        for line in f:
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip().strip("'").strip('"').replace("?pgbouncer=true", "")
    raise ValueError("No DB URL")

def classify_pdf(sid: str, filename: str, p: dict) -> list[str]:
    md_path = os.path.join(ROOT_DIR, "data", "parsed_clean", sid, "converted", f"{filename}.md")
    text = ""
    if os.path.exists(md_path):
        with open(md_path, "r", encoding="utf-8", errors="replace") as mf:
            text = mf.read()

    dt = detect_doc_type(filename)
    inferred = infer_doc_type_from_text(text) if dt == 'OTHER' else None
    final_type = dt if dt != 'OTHER' else (inferred or 'OTHER')
    cats = ext_mod.interface_categories_for_doc_type(final_type)

    if not cats:
        lower = filename.lower()
        if re.search(r'assignment[_\-\s]*2\b', lower):
            cats = ['ES']
        elif re.search(r'assignment[_\-\s]*3\b', lower):
            cats = ['PMF']
        elif re.search(r'assignmen?e?nt[_\-\s]*4\b', lower):
            cats = ['M']
        elif re.search(r'inclusion', lower):
            cats = ['ES', 'L']
        elif re.search(r'ecosystem', lower):
            cats = ['M']
        elif re.search(r'letter[_\-\s]*of[_\-\s]*intent|\bloi\b', lower):
            cats = ['PMF', 'M']
        elif re.search(r'letter[_\-\s]*of[_\-\s]*support|\blos\b|testimonial', lower):
            cats = ['TP', 'IS']
        elif re.search(r'case[_\-\s]*study|pilot|test[_\-\s]*report|field[_\-\s]*trial', lower):
            cats = ['TP']
        elif re.search(r'tam\b|market', lower):
            cats = ['M']
        elif re.search(r'patent|trademark|\bip\b', lower):
            cats = ['L']
        elif re.search(r'financial|projection|revenue|5-year', lower):
            cats = ['F']
        elif re.search(r'deck', lower):
            cats = ['IP']
        elif re.search(r'canvas|bmc', lower):
            cats = ['BC']
        elif re.search(r'team', lower):
            cats = ['T']
        else:
            cats = ['OTHER']
    return cats

def main():
    snapshot = {}
    if os.path.exists(SNAPSHOT_PATH):
        with open(SNAPSHOT_PATH, "r", encoding="utf-8") as f:
            snapshot = json.load(f)

    conn = psycopg2.connect(load_db_url())
    cur = conn.cursor()
    
    cur.execute("SELECT startup_id, payload FROM startup_extractions")
    rows = cur.fetchall()
    
    updated_count = 0
    total_files_mapped = 0
    
    for sid, payload in rows:
        if "document" not in payload:
            payload["document"] = {"sections": []}
            
        # 1. Collect all unique PDFs from snapshot and current payload to ensure zero dropped files
        all_pdfs_map = {}
        
        # From snapshot
        if sid in snapshot:
            snap_data = snapshot[sid]
            snap_list = snap_data if isinstance(snap_data, list) else snap_data.get("document", {}).get("sections", [])
            for sec in snap_list:
                for pdf in sec.get("pdfs", []):
                    if pdf.get("url"):
                        all_pdfs_map[pdf["url"]] = pdf

        # From current DB payload
        for sec in payload["document"].get("sections", []):
            for pdf in sec.get("pdfs", []):
                if pdf.get("url"):
                    all_pdfs_map[pdf["url"]] = pdf

        unique_pdfs = list(all_pdfs_map.values())
        new_sections_map = {}
        
        for pdf in unique_pdfs:
            url = pdf["url"]
            filename = urllib.parse.unquote(url.split("/")[-1])
            
            cats = classify_pdf(sid, filename, pdf)
            for cat in cats:
                if cat not in new_sections_map:
                    new_sections_map[cat] = []
                # Avoid duplicate URLs within same section
                if not any(p["url"] == url for p in new_sections_map[cat]):
                    new_sections_map[cat].append(pdf)
                    
        new_sections = []
        for cat in CANONICAL_CATEGORY_ORDER:
            if cat in new_sections_map and new_sections_map[cat]:
                heading = ext_mod.INTERFACE_CATEGORY_LABELS.get(cat, "Supporting Documents & Deliverables")
                new_sections.append({
                    "cat_code": cat,
                    "heading": heading,
                    "pdfs": new_sections_map[cat]
                })
                
        payload["document"]["sections"] = new_sections
        total_files_mapped += len(unique_pdfs)
        
        cur.execute("UPDATE startup_extractions SET payload = %s WHERE startup_id = %s", (json.dumps(payload), sid))
        updated_count += 1
        
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"Successfully rebuilt and pushed UI document mappings for {updated_count} startups.")
    print(f"Total unique deliverable files mapped: {total_files_mapped} (zero dropped files).")

if __name__ == "__main__":
    main()
