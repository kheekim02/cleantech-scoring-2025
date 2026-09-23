import json
import os
from collections import defaultdict

CACHE_DIR = '/data/scraping/datasets/cto_accelerator/ai_cache_363'
RAW_BASE_DIR = '/data/scraping/datasets/cto_accelerator/parsed'
MAPPING_FILE = '/tmp/ai_pdf_mapping_hybrid.json'
OUTPUT_REPORT = '/tmp/363_ingestion_insights.json'

SUBJECTIVE_IDS = {
    'BC_Q1', 'BC_Q2', 'BC_Q3', 'BC_Q4', 'BC_Q5',
    'IS_Q7', 'IS_Q16',
    'PMF_Q15', 'PMF_Q17',
    'TP_Q13', 'TP_Q14', 'TP_Q15',
    'F_Q22', 'F_Q23', 'F_Q24',
    'IP_Q22', 'IP_Q50'
}

CATEGORIES = ['BC', 'ES', 'F', 'IP', 'IS', 'L', 'M', 'PMF', 'T', 'TP']

def main():
    mappings = json.load(open(MAPPING_FILE))['mappings']
    cache_files = [f for f in os.listdir(CACHE_DIR) if f.endswith('.json')]
    
    print(f"Analyzing {len(cache_files)} completed startups...")

    total_evals = 0
    total_yes = 0
    total_citations = 0
    in_section_citations = 0
    cross_section_citations = 0

    # Leakage matrix: [q_cat][doc_cat] -> count
    leakage_matrix = defaultdict(lambda: defaultdict(int))
    
    # Hub docs: [doc_cat] -> citation count
    hub_doc_citations = defaultdict(int)

    # Category stats: [q_cat] -> {total, yes, has_citation}
    cat_stats = defaultdict(lambda: {'total': 0, 'yes': 0, 'citations': 0})

    # Strictness comparison
    strict_stats = {'total': 0, 'yes': 0, 'citations': 0}
    clean_stats = {'total': 0, 'yes': 0, 'citations': 0}

    for idx, cfile in enumerate(sorted(cache_files)):
        company = cfile.replace('.json', '')
        cache_path = os.path.join(CACHE_DIR, cfile)
        try:
            cache = json.load(open(cache_path))
        except Exception:
            continue

        cat_dir = os.path.join(RAW_BASE_DIR, company, 'converted')
        if not os.path.exists(cat_dir):
            continue

        doc_texts = {}
        for f in os.listdir(cat_dir):
            if f.endswith('.md'):
                pdf_name = f[:-3] if f.endswith('.pdf.md') else f.replace('.md', '.pdf')
                try:
                    doc_texts[pdf_name] = open(os.path.join(cat_dir, f), errors='ignore').read()
                except Exception:
                    pass

        company_map = mappings.get(company, {})

        for item in cache:
            total_evals += 1
            qid = item.get('q_id', '')
            q_cat = qid.split('_')[0]
            val = item.get('predicted_val')
            cit = item.get('citation')

            if val == 1:
                total_yes += 1

            cat_stats[q_cat]['total'] += 1
            if val == 1:
                cat_stats[q_cat]['yes'] += 1

            # Check if this question is part of a subjective cluster
            orig_parent = qid.split('a')[0].split('b')[0].split('c')[0].split('d')[0].split('_val')[0]
            if orig_parent in SUBJECTIVE_IDS:
                strict_stats['total'] += 1
                if val == 1:
                    strict_stats['yes'] += 1
                if cit:
                    strict_stats['citations'] += 1
            else:
                clean_stats['total'] += 1
                if val == 1:
                    clean_stats['yes'] += 1
                if cit:
                    clean_stats['citations'] += 1

            if cit and len(cit.strip()) > 8:
                total_citations += 1
                cat_stats[q_cat]['citations'] += 1

                # Locate document
                found_doc_cat = None
                for pdf_name, text in doc_texts.items():
                    if cit in text:
                        found_doc_cat = company_map.get(pdf_name, {}).get('cat_code', 'UNKNOWN')
                        break

                if found_doc_cat:
                    leakage_matrix[q_cat][found_doc_cat] += 1
                    hub_doc_citations[found_doc_cat] += 1
                    if q_cat == found_doc_cat:
                        in_section_citations += 1
                    else:
                        cross_section_citations += 1

    report = {
        'total_startups_analyzed': len(cache_files),
        'total_evaluations': total_evals,
        'total_yes_rate': total_yes / total_evals if total_evals else 0,
        'total_citations_analyzed': total_citations,
        'in_section_citations': in_section_citations,
        'cross_section_citations': cross_section_citations,
        'cross_section_pct': cross_section_citations / (in_section_citations + cross_section_citations) if (in_section_citations + cross_section_citations) else 0,
        'leakage_matrix': {k: dict(v) for k, v in leakage_matrix.items()},
        'hub_doc_citations': dict(hub_doc_citations),
        'category_stats': dict(cat_stats),
        'strict_vs_clean': {
            'strict_clusters': {
                'total': strict_stats['total'],
                'yes_rate': strict_stats['yes'] / strict_stats['total'] if strict_stats['total'] else 0,
                'citation_rate': strict_stats['citations'] / strict_stats['total'] if strict_stats['total'] else 0
            },
            'clean_clusters': {
                'total': clean_stats['total'],
                'yes_rate': clean_stats['yes'] / clean_stats['total'] if clean_stats['total'] else 0,
                'citation_rate': clean_stats['citations'] / clean_stats['total'] if clean_stats['total'] else 0
            }
        }
    }

    with open(OUTPUT_REPORT, 'w') as f:
        json.dump(report, f, indent=2)

    print("Analysis complete. Saved to", OUTPUT_REPORT)

if __name__ == '__main__':
    main()
