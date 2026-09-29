import json
import urllib.parse
import os
import psycopg2
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from docling_ingestion import detect_doc_type
import importlib.util

# Load the extractor module dynamically to avoid naming conflicts if any
path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "14_ai_copilot_extractor_v2.py")
spec = importlib.util.spec_from_file_location("extractor_v2_interface", path)
ext_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ext_mod)

def load_db_url():
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"].replace("?pgbouncer=true", "")
    with open(".env", "r") as f:
        for line in f:
            if line.startswith("DATABASE_URL="):
                return line.split("=", 1)[1].strip().strip("'").strip('"').replace("?pgbouncer=true", "")
    raise ValueError("No DB URL")

def main():
    conn = psycopg2.connect(load_db_url())
    cur = conn.cursor()
    
    cur.execute("SELECT startup_id, payload FROM startup_extractions")
    rows = cur.fetchall()
    
    updated_count = 0
    for sid, payload in rows:
        if "document" not in payload or "sections" not in payload["document"]:
            continue
            
        all_pdfs = []
        for sec in payload["document"]["sections"]:
            for pdf in sec.get("pdfs", []):
                all_pdfs.append(pdf)
                
        unique_pdfs = { p["url"]: p for p in all_pdfs }.values()
        new_sections_map = {} 
        
        for pdf in unique_pdfs:
            url = pdf["url"]
            filename = urllib.parse.unquote(url.split("/")[-1])
            
            doc_type = detect_doc_type(filename)
            cats = ext_mod.interface_categories_for_doc_type(doc_type)
            
            for cat in cats:
                if cat not in new_sections_map:
                    new_sections_map[cat] = []
                new_sections_map[cat].append(pdf)
                
        new_sections = []
        for cat, pdfs in new_sections_map.items():
            heading = ext_mod.INTERFACE_CATEGORY_LABELS.get(cat, cat)
            new_sections.append({
                "cat_code": cat,
                "heading": heading,
                "pdfs": pdfs
            })
            
        payload["document"]["sections"] = new_sections
        
        cur.execute("UPDATE startup_extractions SET payload = %s WHERE startup_id = %s", (json.dumps(payload), sid))
        updated_count += 1
        
    conn.commit()
    cur.close()
    conn.close()
    
    print(f"Successfully rebuilt and pushed UI document mappings for {updated_count} startups.")

if __name__ == "__main__":
    main()
