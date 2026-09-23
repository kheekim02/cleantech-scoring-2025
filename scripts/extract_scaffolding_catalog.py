import os
import glob
import re
import pymupdf
from collections import defaultdict, Counter

raw_base = '/Users/geoffrey/Global_Key_Advisors/Migrating_Automated_Startup_Scraper/data/raw'

# Define regex patterns for deliverable types
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

def clean_text(t):
    if not t: return ""
    # Normalize unicode bullets, zero width spaces, and whitespace
    t = re.sub(r'[•●○\u200b\xa0\r\n\t]+', ' ', t)
    return ' '.join(t.split()).strip()

all_pdfs = glob.glob(os.path.join(raw_base, '*', '**', '*.pdf'), recursive=True)

catalog = {}

for type_name, pattern in type_patterns.items():
    # Find all files matching this type
    matching_files = [f for f in all_pdfs if re.search(pattern, os.path.basename(f), re.IGNORECASE)]
    total_docs = len(matching_files)
    if total_docs < 3:
        continue
        
    block_doc_counts = Counter()
    block_samples = {}
    
    for f in matching_files:
        try:
            doc = pymupdf.open(f)
            seen_in_doc = set()
            for page in doc:
                blocks = page.get_text('blocks')
                for b in blocks:
                    raw_txt = b[4].strip()
                    cleaned = clean_text(raw_txt)
                    
                    # Filter out noise: very short phrases, pure numbers, headers, page numbers
                    if len(cleaned) < 30 or len(cleaned.split()) < 5:
                        continue
                    if re.match(r'^(page \d+|\d+|table of contents)$', cleaned.lower()):
                        continue
                        
                    # Use a normalized key for matching (ignore minor punctuation and casing)
                    norm_key = re.sub(r'[^a-zA-Z0-9]+', ' ', cleaned).lower().strip()
                    if norm_key and norm_key not in seen_in_doc:
                        seen_in_doc.add(norm_key)
                        block_doc_counts[norm_key] += 1
                        if norm_key not in block_samples:
                            block_samples[norm_key] = cleaned
        except Exception:
            pass
            
    # Threshold strictly > 50%
    threshold = total_docs * 0.50
    scaffolding_items = []
    
    for norm_key, count in block_doc_counts.most_common():
        if count > threshold:
            pct = (count / total_docs) * 100
            scaffolding_items.append({
                'text': block_samples[norm_key],
                'count': count,
                'total': total_docs,
                'pct': pct
            })
            
    if scaffolding_items:
        catalog[type_name] = {
            'total_files': total_docs,
            'threshold': f"> 50% (min {int(threshold) + 1}/{total_docs} files)",
            'items': scaffolding_items
        }

print(f"Catalog generated for {len(catalog)} deliverable types.")

# Print structured markdown output
out_file = "scaffolding_attribution_catalog.txt"
with open(out_file, "w") as out:
    for type_name, data in catalog.items():
        out.write(f"\n================================================================================\n")
        out.write(f"DOCUMENT TYPE: {type_name}\n")
        out.write(f"Files Evaluated: {data['total_files']} | Threshold: {data['threshold']}\n")
        out.write(f"Scaffolding Blocks Found: {len(data['items'])}\n")
        out.write(f"================================================================================\n")
        
        for idx, item in enumerate(data['items'], 1):
            out.write(f"\n--- Item {idx} [Appears in {item['count']}/{item['total']} files ({item['pct']:.1f}%)] ---\n")
            out.write(f"{item['text']}\n")

print(f"Full catalog written to {out_file}")
