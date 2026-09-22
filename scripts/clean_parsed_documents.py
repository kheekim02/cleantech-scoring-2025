import os
import re
import json
import argparse
from pathlib import Path

def load_catalog(catalog_path):
    with open(catalog_path, 'r') as f:
        return json.load(f)

def clean_markdown_text(text, doc_type_code, catalog):
    original_len = len(text)
    
    # 1. Universal boilerplates applied to all documents
    universal_patterns = [
        r'(?i)cleantech\s+open\s+confidential\s*[\u2013\u2014-]\s*do\s+not\s+duplicate[^\n]*',
        r'(?i)©\s*(?:2022|2025)?\s*cleantech\s+open[^\n]*',
        r'(?i)do\s+not\s+duplicate\s+or\s+distribute\s+without\s+written\s+permission[^\n]*',
        r'(?i)the\s+information\s+presented\s+above\s+is\s+confidential[^\n]*',
        r'(?i)\(?\s*\d+[,\d]*\s*(?:total\s*)?characters?\s*(?:limit|max|maximum)[^\)\n]*\)?',
        r'(?i)upload\s+this\s+document\s+as\s+teamname[^\n]*',
        r'(?i)^#+\s*(?:instructions?|directions?):?\s*$',
        r'(?i)^#+\s*essential\s+business\s+deliverable\s*#\d+.*$',
        r'(?i)^#+\s*module\s*\d+.*instructions:?.*$',
    ]
    for p in universal_patterns:
        text = re.sub(p, '', text, flags=re.MULTILINE)

    # 2. Known high-impact multi-line blocks (loose examples, archetype templates)
    # EBD2 loose example
    text = re.sub(r"(?is)loose\s+example:\s*[\u201c\"'].*?[\u201d\"']\s*", '', text)
    # EBD3 Blair Smith archetype
    text = re.sub(r"(?is)example:\s*[\u201c\"']blair\s+smith.*?\(source\s+with\s+more\s+examples\)\s*", '', text)
    # Inclusion e.g. bullet lists
    text = re.sub(r'(?i)e\.g\.,\s*(?:add\s+multilingual|partner\s+with\s+hbcus|partner\s+with\s+local|reach\s+500|30%\s+increase|50%\s+increase)[^\n]*', '', text)
    
    # 3. Document-specific scaffolding from catalog
    if doc_type_code in catalog:
        items = catalog[doc_type_code].get('items', [])
        for item in items:
            raw_target = item['text']
            words = raw_target.split()
            if len(words) < 4:
                continue
                
            # Build flexible regex allowing markdown characters, punctuation variants, and whitespace
            escaped_words = [re.escape(w) for w in words]
            pattern = r'(?i)' + r'[\s\\_*\-]+'.join(escaped_words)
            text = re.sub(pattern, '', text)

    # 4. Clean up empty markdown headers, stray list markers, and excessive whitespace
    text = re.sub(r'(?m)^#+\s*$', '', text)
    text = re.sub(r'(?m)^\s*[-*•\d\.]+\s*$', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    cleaned_text = text.strip()
    return cleaned_text, original_len, len(cleaned_text)

def process_directory(input_dir, output_dir, catalog_path):
    catalog = load_catalog(catalog_path)
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    total_files = 0
    total_orig_chars = 0
    total_clean_chars = 0
    
    for md_file in input_path.rglob('*.md'):
        fname = md_file.name
        doc_type = 'OTHER'
        for code, info in catalog.items():
            if re.search(info['pattern'], fname, re.IGNORECASE):
                doc_type = code
                break
                
        with open(md_file, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            
        cleaned, orig_len, clean_len = clean_markdown_text(content, doc_type, catalog)
        
        rel_path = md_file.relative_to(input_path)
        dest_file = output_path / rel_path
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(dest_file, 'w', encoding='utf-8') as f:
            f.write(cleaned)
            
        total_files += 1
        total_orig_chars += orig_len
        total_clean_chars += clean_len
        
    reduction = ((total_orig_chars - total_clean_chars) / total_orig_chars * 100) if total_orig_chars > 0 else 0
    print(f"Processed {total_files} files.")
    print(f"Original Characters: {total_orig_chars:,}")
    print(f"Cleaned Characters:  {total_clean_chars:,}")
    print(f"Boilerplate Stripped: {total_orig_chars - total_clean_chars:,} chars ({reduction:.1f}% reduction)")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Clean competition scaffolding from markdown files.")
    parser.add_argument('--input-dir', required=True, help="Input directory of parsed markdowns")
    parser.add_argument('--output-dir', required=True, help="Output directory for clean markdowns")
    parser.add_argument('--catalog', default='data/scaffolding_master_catalog.json', help="Path to master scaffolding catalog JSON")
    args = parser.parse_args()
    
    process_directory(args.input_dir, args.output_dir, args.catalog)
