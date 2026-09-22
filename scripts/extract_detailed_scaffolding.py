import os
import glob
import re
import pymupdf
from collections import defaultdict, Counter

raw_base = '/Users/geoffrey/Global_Key_Advisors/Migrating_Automated_Startup_Scraper/data/raw'

type_patterns = {
    'EBD #2: Impact/Sustainability Statement': r'EBD2',
    'EBD #3: Customer Segmentation & Competitive Matrix': r'EBD3',
    'EBD #4: Product Technology Validation': r'EBD4',
    'EBD #1 / Executive Summary': r'(EBD1|Executive_Summary)',
    'Module 1: Customer Discovery Interviews': r'(M1|CustomerDiscovery)',
    'Module 2: Impact Questions': r'M2',
    'Module 3: Product-Market Fit Questions': r'M3',
    'Module 4: Markets & Getting to Them': r'M4',
    'Module 6: Finances & Funding': r'M6',
    'Module 7: IP Strategy & Legal': r'M7',
    'Module 8: Team & Operations': r'M8',
    'Inclusion Assignment': r'Inclusion',
    'GHG / Emissions Reduction Potential': r'GHG',
    'Financial Projections': r'FinancialProjection',
    'Business Model Canvas': r'(Business_Model_Canvas|Strategyzer)'
}

all_pdfs = glob.glob(os.path.join(raw_base, '*', '**', '*.pdf'), recursive=True)

def normalize_line(l):
    l = re.sub(r'[•●○\u200b\xa0\r\n\t]+', ' ', l)
    return ' '.join(l.split()).strip()

catalog = {}

for type_name, pattern in type_patterns.items():
    matching_files = [f for f in all_pdfs if re.search(pattern, os.path.basename(f), re.IGNORECASE)]
    total_docs = len(matching_files)
    if total_docs < 3:
        continue
        
    line_counts = Counter()
    line_samples = {}
    
    for f in matching_files:
        try:
            doc = pymupdf.open(f)
            seen_in_doc = set()
            for page in doc:
                # Extract clean lines
                raw_text = page.get_text()
                # Split on newlines, but also look at paragraphs
                lines = raw_text.split('\n')
                for l in lines:
                    cleaned = normalize_line(l)
                    # Filter out short or trivial lines
                    if len(cleaned) < 20 or len(cleaned.split()) < 3:
                        continue
                    if re.match(r'^(page \d+|\d+|table of contents)$', cleaned.lower()):
                        continue
                    norm_key = re.sub(r'[^a-zA-Z0-9]+', ' ', cleaned).lower().strip()
                    if norm_key and norm_key not in seen_in_doc:
                        seen_in_doc.add(norm_key)
                        line_counts[norm_key] += 1
                        if norm_key not in line_samples:
                            line_samples[norm_key] = cleaned
        except Exception:
            pass
            
    # Filter lines > 50%
    threshold = total_docs * 0.50
    common_lines = []
    for norm_key, count in line_counts.most_common():
        if count > threshold:
            pct = (count / total_docs) * 100
            common_lines.append({
                'text': line_samples[norm_key],
                'count': count,
                'total': total_docs,
                'pct': pct
            })
            
    if common_lines:
        catalog[type_name] = {
            'total_files': total_docs,
            'threshold': f"> 50% ({int(threshold) + 1}/{total_docs} files)",
            'lines': common_lines
        }

out_file = "detailed_scaffolding_list.txt"
with open(out_file, "w") as out:
    for type_name, data in catalog.items():
        out.write(f"\n{'='*90}\n")
        out.write(f"DOCUMENT DELIVERABLE: {type_name}\n")
        out.write(f"Files Analyzed: {data['total_files']} | Scaffolding Filter: {data['threshold']}\n")
        out.write(f"{'='*90}\n")
        
        for idx, item in enumerate(data['lines'], 1):
            out.write(f"[{item['count']}/{item['total']} files ({item['pct']:.1f}%)] {item['text']}\n")

print(f"Detailed line catalog written to {out_file}")
