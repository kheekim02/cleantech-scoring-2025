import os
import glob
import re
import json
import pymupdf
from collections import Counter

raw_base = '/Users/geoffrey/Global_Key_Advisors/Migrating_Automated_Startup_Scraper/data/raw'

type_patterns = {
    'EBD2': {
        'name': 'EBD #2: Impact/Sustainability Statement',
        'pattern': r'EBD2'
    },
    'EBD3': {
        'name': 'EBD #3: Customer Segmentation & Competitive Matrix',
        'pattern': r'EBD3'
    },
    'EBD4': {
        'name': 'EBD #4: Product Technology Validation',
        'pattern': r'EBD4'
    },
    'EBD1_ExecSummary': {
        'name': 'EBD #1 / Executive Summary',
        'pattern': r'(EBD1|Executive_Summary)'
    },
    'M1': {
        'name': 'Module 1: Customer Discovery Interviews',
        'pattern': r'(M1|CustomerDiscovery)'
    },
    'M2': {
        'name': 'Module 2: Impact Questions',
        'pattern': r'M2'
    },
    'M3': {
        'name': 'Module 3: Product-Market Fit Questions',
        'pattern': r'M3'
    },
    'M4': {
        'name': 'Module 4: Markets & Getting to Them',
        'pattern': r'M4'
    },
    'M6': {
        'name': 'Module 6: Finances & Funding',
        'pattern': r'M6'
    },
    'M7': {
        'name': 'Module 7: IP Strategy & Legal',
        'pattern': r'M7'
    },
    'M8': {
        'name': 'Module 8: Team & Operations',
        'pattern': r'M8'
    },
    'Inclusion': {
        'name': 'Inclusion Assignment',
        'pattern': r'Inclusion'
    },
    'GHG': {
        'name': 'GHG / Emissions Reduction Potential',
        'pattern': r'GHG'
    },
    'FinancialProjection': {
        'name': 'Financial Projections',
        'pattern': r'FinancialProjection'
    },
    'BMC': {
        'name': 'Business Model Canvas',
        'pattern': r'(Business_Model_Canvas|Strategyzer)'
    }
}

all_pdfs = glob.glob(os.path.join(raw_base, '*', '**', '*.pdf'), recursive=True)

def normalize_line(l):
    l = re.sub(r'[•●○\u200b\xa0\r\n\t]+', ' ', l)
    return ' '.join(l.split()).strip()

master_catalog = {}

for code, info in type_patterns.items():
    pattern = info['pattern']
    full_name = info['name']
    
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
                raw_text = page.get_text()
                lines = raw_text.split('\n')
                for l in lines:
                    cleaned = normalize_line(l)
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
            
    # Keep everything with frequency > 20%
    threshold = total_docs * 0.20
    scaffolding_lines = []
    
    for norm_key, count in line_counts.most_common():
        if count > threshold:
            pct = round((count / total_docs) * 100, 1)
            scaffolding_lines.append({
                'text': line_samples[norm_key],
                'count': count,
                'total_files': total_docs,
                'pct': pct
            })
            
    master_catalog[code] = {
        'name': full_name,
        'pattern': pattern,
        'total_files': total_docs,
        'threshold_pct': 20.0,
        'min_files': int(threshold) + 1,
        'total_scaffolding_items': len(scaffolding_lines),
        'items': scaffolding_lines
    }

# 1. Save JSON catalog
os.makedirs('data', exist_ok=True)
json_out = 'data/scaffolding_master_catalog.json'
with open(json_out, 'w') as f:
    json.dump(master_catalog, f, indent=2)

# 2. Save Markdown reference document
md_out = 'data/MASTER_SCAFFOLDING_CATALOG.md'
with open(md_out, 'w') as f:
    f.write("# Master CleanTech Open Template Scaffolding Catalog\n\n")
    f.write("This catalog documents all competition scaffolding, prompt questions, instructions, and dummy examples identified across the 92 startups using a **> 20% frequency filter** across 1,481 files.\n\n")
    f.write("| Deliverable Code | Deliverable Name | Total Files | Scaffolding Items (>20%) |\n")
    f.write("| :--- | :--- | :--- | :--- |\n")
    for code, info in master_catalog.items():
        f.write(f"| `{code}` | {info['name']} | {info['total_files']} | {info['total_scaffolding_items']} |\n")
    f.write("\n---\n\n")
    
    for code, info in master_catalog.items():
        f.write(f"## `{code}`: {info['name']}\n")
        f.write(f"- **Evaluated Files**: {info['total_files']}\n")
        f.write(f"- **Filter Threshold**: > 20% ({info['min_files']}+ files)\n")
        f.write(f"- **Scaffolding Blocks**: {info['total_scaffolding_items']}\n\n")
        
        for idx, item in enumerate(info['items'], 1):
            f.write(f"{idx}. `[{item['count']}/{item['total_files']} files ({item['pct']} %)]` {item['text']}\n")
        f.write("\n---\n\n")

print(f"Master catalogs generated:")
print(f"  - JSON: {json_out}")
print(f"  - Markdown: {md_out}")
