import os
import json
import time
import requests
import sys

OLLAMA_URL = 'http://localhost:11434/api/generate'
MODEL = 'llama3.2:latest'
RAW_BASE_DIR = '/data/scraping/datasets/cto_accelerator/parsed'
OUTPUT_FILE = '/tmp/ai_pdf_mapping_hybrid.json'

ALLOWED_CATS = ['BC', 'ES', 'F', 'IP', 'IS', 'L', 'M', 'PMF', 'T', 'TP']

PROMPT_TEMPLATE = """You are a document classifier for the Cleantech Open (CTO) Accelerator.
Classify the following document into EXACTLY ONE category.

CATEGORIES & CTO DELIVERABLE DEFINITIONS:
- BC: Business Model Canvas — Business Model Canvas 9-box framework, CTO EBD 1, BMC worksheets.
- ES: Environmental & Social Impact — GHG emissions reduction (ERP), sustainability questions, CTO Module 2 questions, CTO EBD 2 (Impact Statement).
- F: Financials — 3-5 year financial projections, pro forma models, COGS, P&L, CTO Module 6 questions, CTO EBD 5.
- IP: Investor Pitch — Pitch decks, investor slide presentations, demo day slides (multi-slide overview of problem, solution, market, team, and ask).
- IS: Executive Summary — 1-page executive summary documents, company overview briefs, CTO EBD 6.
- L: Legal & Inclusion — Inclusion assignments, diversity/equity strategies, patents, corporate legal formation, CTO Module 7 questions.
- M: Market & Customers — Customer segmentation matrices, competitor analysis, TAM/SAM/SOM market sizing sheets, CTO EBD 3.
- PMF: Product-Market Fit — Customer discovery interview capture sheets, customer validation notes, CTO Module 1 and Module 3 questions.
- T: Team — Team targets, founder bios, organizational chart, hiring milestones, advisory board, CTO Module 8 questions.
- TP: Tech / Product — Technology validation, TRL/MRL technical assessment, engineering specifications, prototype testing, CTO Module 4 questions, CTO EBD 4.

Document Filename: {filename}
Document Text:
{text}

Output ONLY the 2-3 letter category code (BC, ES, F, IP, IS, L, M, PMF, T, TP). Nothing else:"""

def baseline_regex(filename):
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

def high_confidence_rule(filename):
    """
    Returns (category, True) if the filename matches an unmistakable deliverable pattern with 100% confidence.
    Otherwise returns (None, False).
    """
    f = filename.lower()
    # Presentations
    if 'pitch' in f or 'deck' in f or 'ebd8' in f:
        return 'IP', True
    # Business Canvas
    if 'canvas' in f or 'bmc' in f or ('ebd1' in f and 'ebd10' not in f):
        return 'BC', True
    # Financials
    if 'financialprojection' in f or 'financial_projection' in f or 'pro_forma' in f or 'proforma' in f or 'ebd5' in f or 'm6' in f:
        return 'F', True
    # Legal & Inclusion
    if 'inclusion' in f or 'm7' in f:
        return 'L', True
    # Team
    if 'teamtarget' in f or 'team_target' in f or 'ebd10' in f or 'm8' in f:
        return 'T', True
    # Technology
    if 'ebd4' in f:
        return 'TP', True
    # Market
    if 'ebd3' in f or 'm4questions' in f or 'm4_questions' in f or 'module_4' in f:
        return 'M', True
    # Customer Discovery
    if 'customerdiscovery' in f or 'customer_discovery' in f or 'interview_capture' in f or 'm1customer' in f or 'm3assignment' in f:
        return 'PMF', True
    # Executive Summary (strict, avoid EBD2 impact statement)
    if ('executive_summary' in f or 'exec_summary' in f or 'one_page' in f or '1pager' in f or 'one_pager' in f or 'ebd6' in f) and 'impact' not in f:
        return 'IS', True
    # Environmental / GHG
    if 'ghg' in f or 'erp' in f or 'sustainab' in f or 'ebd2' in f or 'ebd9' in f:
        return 'ES', True

    return None, False

def classify_ai(filename, text):
    if len(text.strip()) < 50:
        return baseline_regex(filename), 'REGEX_EMPTY_FILE'

    prompt = PROMPT_TEMPLATE.format(filename=filename, text=text[:4000])

    for attempt in range(3):
        try:
            res = requests.post(OLLAMA_URL, json={
                'model': MODEL,
                'prompt': prompt,
                'stream': False,
                'options': {'temperature': 0.0, 'num_predict': 10}
            }, timeout=30).json()

            raw = res.get('response', '').strip().replace('"', '').replace("'", "").replace('.', '').upper()
            if raw in ALLOWED_CATS:
                return raw, 'AI'

            tokens = raw.split()
            for t in tokens:
                clean_t = t.strip(':-_*`#')
                if clean_t in ALLOWED_CATS:
                    return clean_t, 'AI'
        except Exception:
            time.sleep(0.5)
            continue

    return baseline_regex(filename), 'REGEX_FALLBACK'

def classify_hybrid(filename, text):
    cat, is_high_conf = high_confidence_rule(filename)
    if is_high_conf:
        return cat, 'RULE_HIGH_CONF'
    
    # Otherwise, use the tuned AI classifier
    ai_cat, source = classify_ai(filename, text)
    return ai_cat, f'HYBRID_{source}'

def run(dry_run=False):
    if dry_run:
        companies = ['AmpTrans', 'Averra', 'Bonhomme_&_Associates', 'Condor_Calibration_Services', 'Novagrid']
        print("=== RUNNING 5-STARTUP HYBRID & TUNED AI DRY-RUN ===")
    else:
        all_comps = os.listdir(RAW_BASE_DIR)
        companies = sorted([c for c in all_comps if not c.startswith('startup_test_') and c not in ('spark_inc', 'solarpure_inc')])
        print(f"=== RUNNING FULL BATCH ({len(companies)} startups) ===")

    mappings = {}
    dry_run_rows = []
    total_docs = 0

    ai_alone_matches = 0
    hybrid_matches_with_regex = 0
    rule_hits = 0
    ai_calls = 0

    for company in companies:
        cat_dir = os.path.join(RAW_BASE_DIR, company, 'converted')
        if not os.path.exists(cat_dir):
            continue

        mappings[company] = {}
        files = sorted(os.listdir(cat_dir))

        for f in files:
            if not f.endswith('.pdf.md'):
                continue

            pdf_name = f[:-3]
            file_path = os.path.join(cat_dir, f)
            with open(file_path, 'r', errors='ignore') as file_obj:
                text = file_obj.read()

            base_cat = baseline_regex(pdf_name)
            ai_alone_cat, ai_source = classify_ai(pdf_name, text)
            hybrid_cat, hybrid_source = classify_hybrid(pdf_name, text)

            total_docs += 1
            if 'RULE' in hybrid_source:
                rule_hits += 1
            else:
                ai_calls += 1

            ai_matches = (ai_alone_cat == base_cat)
            hybrid_matches = (hybrid_cat == base_cat)

            if ai_matches:
                ai_alone_matches += 1
            if hybrid_matches:
                hybrid_matches_with_regex += 1

            mappings[company][pdf_name] = {
                'cat_code': hybrid_cat,
                'source': hybrid_source,
                'ai_alone_code': ai_alone_cat,
                'regex_code': base_cat
            }

            dry_run_rows.append({
                'company': company,
                'filename': pdf_name,
                'regex': base_cat,
                'ai_alone': ai_alone_cat,
                'hybrid': hybrid_cat,
                'source': hybrid_source,
                'hybrid_vs_regex_match': hybrid_matches
            })

            print(f"[{company[:10]:10}] {pdf_name[:35]:35} | Regex: {base_cat:3} | AI-Alone: {ai_alone_cat:3} | Hybrid: {hybrid_cat:3} ({hybrid_source:15})", flush=True)

    # Compute distributions
    hybrid_counts = {c: 0 for c in ALLOWED_CATS}
    ai_counts = {c: 0 for c in ALLOWED_CATS}
    regex_counts = {c: 0 for c in ALLOWED_CATS}

    for row in dry_run_rows:
        hybrid_counts[row['hybrid']] += 1
        ai_counts[row['ai_alone']] += 1
        regex_counts[row['regex']] += 1

    print("\n=== SUMMARY STATISTICS ===")
    print(f"Total Documents: {total_docs}")
    print(f"High-Confidence Deliverable Rules Applied: {rule_hits} ({rule_hits/total_docs*100:.1f}%)")
    print(f"Dynamic AI Classifications Applied: {ai_calls} ({ai_calls/total_docs*100:.1f}%)")
    print(f"Tuned AI-Alone Agreement with Regex: {ai_alone_matches}/{total_docs} ({ai_alone_matches/total_docs*100:.1f}%)")
    print(f"Hybrid Agreement with Regex Baseline: {hybrid_matches_with_regex}/{total_docs} ({hybrid_matches_with_regex/total_docs*100:.1f}%)")

    print("\nHybrid Category Distribution:")
    for cat, cnt in sorted(hybrid_counts.items()):
        pct = (cnt / total_docs * 100) if total_docs else 0
        print(f"  {cat:4}: {cnt:3} ({pct:5.1f}%) [Regex: {regex_counts[cat]:2}, Tuned-AI: {ai_counts[cat]:2}]")

    out_path = '/tmp/dry_run_hybrid_comparison.json' if dry_run else OUTPUT_FILE
    with open(out_path, 'w') as out_f:
        json.dump({
            'meta': {
                'total_documents': total_docs,
                'rule_hits': rule_hits,
                'ai_calls': ai_calls,
                'ai_alone_agreement': ai_alone_matches / total_docs if total_docs else 0,
                'hybrid_agreement': hybrid_matches_with_regex / total_docs if total_docs else 0,
                'hybrid_counts': hybrid_counts,
                'ai_counts': ai_counts,
                'regex_counts': regex_counts,
                'dry_run': dry_run
            },
            'rows': dry_run_rows,
            'mappings': mappings
        }, out_f, indent=2)

    print(f"\nWrote results to {out_path}")

if __name__ == '__main__':
    is_dry = '--dry-run' in sys.argv
    run(dry_run=is_dry)
