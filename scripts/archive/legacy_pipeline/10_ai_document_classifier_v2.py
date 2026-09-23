import os
import json
import time
import requests
import sys

OLLAMA_URL = 'http://localhost:11434/api/generate'
MODEL = 'deepseek-coder-v2:16b'
RAW_BASE_DIR = '/data/scraping/datasets/cto_accelerator/parsed'
OUTPUT_FILE = '/tmp/ai_pdf_mapping_v2.json'

ALLOWED_CATS = ['BC', 'ES', 'F', 'IP', 'IS', 'L', 'M', 'PMF', 'T', 'TP']

CATEGORIES_DEF = """CATEGORIES (with definitions):
- BC: Business Model Canvas — Contains the Business Model Canvas framework (Key Partners, Key Activities, Value Propositions, Customer Segments, Revenue Streams, Cost Structure, Channels).
- ES: Environmental & Social Impact — GHG emission reduction potential, sustainability questions, impact/sustainability questionnaires, ERP self-assessments, carbon accounting.
- F:  Financials — Financial projections, 3-year pro formas, COGS analysis, revenue models, funding milestones, cap tables, profit/loss statements.
- IP: Investor Pitch — Pitch decks, investor presentations, demo day slides.
- IS: Executive Summary — One-page executive summaries, company overviews, elevator pitches in document form.
- L:  Legal & Inclusion — Inclusion assignments, diversity/equity strategies, legal structure documents, IP filings.
- M:  Market & Customers — Customer segmentation matrices, competitive analysis, TAM/SAM/SOM, market sizing.
- PMF: Product-Market Fit — Customer discovery interview capture sheets, customer validation, problem-solution fit evidence.
- T:  Team — Team target documents, org charts, founder bios, hiring plans, advisory board.
- TP: Tech / Product — Technology validation, TRL/MRL assessments, product development milestones, technical specifications, prototyping."""

def fallback_regex(filename):
    f = filename.lower()
    if 'inclusion' in f or 'm7' in f: return 'L'
    if 'impact' in f and 'statement' not in f: return 'ES'
    if 'statement' in f: return 'IS' 
    if 'ghg' in f or 'erp' in f or 'sustainab' in f or 'ebd2' in f or 'ebd9' in f: return 'ES'
    if 'canvas' in f or 'bmc' in f or ('ebd1' in f and 'ebd10' not in f): return 'BC'
    if 'segment' in f or 'matrix' in f or 'ebd3' in f: return 'M'
    if 'technology' in f or 'validation' in f or 'ebd4' in f or 'm4' in f: return 'TP'
    if 'financ' in f or 'projection' in f or 'pro_forma' in f or 'proforma' in f or 'profit' in f or 'loss' in f or 'ebd5' in f or 'm6' in f: return 'F'
    if 'team' in f or 'target' in f or 'ebd10' in f or 'm8' in f: return 'T'
    if 'pitch' in f or 'deck' in f or 'ebd8' in f: return 'IP'
    if 'discovery' in f or 'interview' in f or 'm1' in f or 'm3' in f or 'assignment' in f: return 'PMF'
    if 'executive' in f or 'summary' in f or '1pager' in f or 'one_page' in f or 'ebd6' in f: return 'IS'
    return 'IS'

def classify_doc(filename, text):
    if len(text.strip()) < 50:
        return fallback_regex(filename), 'REGEX_EMPTY_FILE'

    prompt = f"""You are a document classifier for the CTO Cleantech Accelerator.
Read the document text below and assign it to exactly ONE category.

{CATEGORIES_DEF}

Output ONLY the 2-3 letter category code. Nothing else.

<document>
{text[:4000]}
</document>"""

    for attempt in range(3):
        try:
            res = requests.post(OLLAMA_URL, json={
                'model': MODEL, 'prompt': prompt, 'stream': False,
                'options': {'temperature': 0.0, 'num_predict': 10}
            }, timeout=30).json()
            
            raw = res.get('response', '').strip().replace('"', '').replace("'", "").replace('.', '').upper()
            
            # Exact match
            if raw in ALLOWED_CATS:
                return raw, 'AI'
                
            # Token match
            tokens = raw.split()
            for t in tokens:
                clean_t = t.strip(':-_*`#')
                if clean_t in ALLOWED_CATS:
                    return clean_t, 'AI'
        except Exception:
            time.sleep(1)
            continue
            
    return fallback_regex(filename), 'REGEX_FALLBACK'

def run(dry_run=False):
    if dry_run:
        companies = ['AmpTrans', 'Averra', 'Bonhomme_&_Associates', 'Condor_Calibration_Services', 'Novagrid']
        print("=== RUNNING 5-STARTUP DRY-RUN ===")
    else:
        all_comps = os.listdir(RAW_BASE_DIR)
        companies = sorted([c for c in all_comps if not c.startswith('startup_test_') and c not in ('spark_inc', 'solarpure_inc')])
        print(f"=== RUNNING FULL BATCH ({len(companies)} startups) ===")

    mappings = {}
    dry_run_rows = []
    total_docs = 0
    ai_count = 0
    regex_count = 0
    matches_count = 0

    for company in companies:
        cat_dir = os.path.join(RAW_BASE_DIR, company, 'converted')
        if not os.path.exists(cat_dir):
            continue
            
        mappings[company] = {}
        files = sorted(os.listdir(cat_dir))
        
        for f in files:
            if not f.endswith('.pdf.md'):
                continue
                
            pdf_name = f[:-3] # 'filename.pdf.md' -> 'filename.pdf'
            file_path = os.path.join(cat_dir, f)
            with open(file_path, 'r', errors='ignore') as file_obj:
                text = file_obj.read()
                
            regex_cat = fallback_regex(pdf_name)
            ai_cat, source = classify_doc(pdf_name, text)
            
            mappings[company][pdf_name] = {'cat_code': ai_cat, 'source': source, 'regex_code': regex_cat}
            
            total_docs += 1
            if source == 'AI':
                ai_count += 1
            else:
                regex_count += 1
                
            is_match = (ai_cat == regex_cat)
            if is_match:
                matches_count += 1
                
            dry_run_rows.append({
                'company': company,
                'filename': pdf_name,
                'regex': regex_cat,
                'ai': ai_cat,
                'source': source,
                'match': is_match
            })
            
            print(f"[{company}] {pdf_name[:40]:40} | Regex: {regex_cat:3} | AI: {ai_cat:3} | Source: {source:10} | {'MATCH' if is_match else 'DIFF'}", flush=True)

    # Compute distribution
    cat_counts = {c: 0 for c in ALLOWED_CATS}
    for row in dry_run_rows:
        cat_counts[row['ai']] += 1

    print("\n=== SUMMARY STATISTICS ===")
    print(f"Total Documents: {total_docs}")
    print(f"AI Classified: {ai_count} ({ai_count/total_docs*100:.1f}%)" if total_docs else "0")
    print(f"Regex Fallback / Empty: {regex_count}")
    print(f"Agreement with Regex: {matches_count}/{total_docs} ({matches_count/total_docs*100:.1f}%)" if total_docs else "0")
    print("\nCategory Distribution:")
    for cat, cnt in sorted(cat_counts.items()):
        pct = (cnt / total_docs * 100) if total_docs else 0
        print(f"  {cat:4}: {cnt:3} ({pct:5.1f}%)")

    # Output to file
    out_path = '/tmp/dry_run_comparison.json' if dry_run else OUTPUT_FILE
    with open(out_path, 'w') as out_f:
        json.dump({
            'meta': {
                'total_documents': total_docs,
                'ai_classified': ai_count,
                'regex_count': regex_count,
                'matches_count': matches_count,
                'cat_counts': cat_counts,
                'dry_run': dry_run
            },
            'rows': dry_run_rows,
            'mappings': mappings
        }, out_f, indent=2)

    print(f"\nWrote results to {out_path}")

if __name__ == '__main__':
    is_dry = '--dry-run' in sys.argv
    run(dry_run=is_dry)
