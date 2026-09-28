import os
import re
import json
import argparse
from pathlib import Path

def load_catalog(catalog_path):
    with open(catalog_path, 'r') as f:
        return json.load(f)

def clean_markdown_tables(text):
    """
    Finds markdown tables that have 'Questions' and 'Answers' (or similar) headers.
    Returns the table with the 'Questions' column removed or cleared out to prevent scaffolding matches.
    """
    lines = text.split('\n')
    cleaned_lines = []
    
    in_table = False
    col_idx_to_remove = -1
    
    for line in lines:
        if line.strip().startswith('|'):
            # Table row
            cols = [c.strip() for c in line.split('|')]
            # Header check
            if not in_table:
                if 'question' in line.lower() and 'answer' in line.lower():
                    in_table = True
                    for idx, c in enumerate(cols):
                        if 'question' in c.lower() or 'prompt' in c.lower():
                            col_idx_to_remove = idx
            
            if in_table and col_idx_to_remove != -1 and col_idx_to_remove < len(cols):
                # We are in a question/answer table. Clear out the question column contents.
                # Do not clear the separator line `|---|`
                if set(cols[col_idx_to_remove].replace('-', '').replace(':', '')) != set():
                    cols[col_idx_to_remove] = " "
                cleaned_lines.append('|'.join(cols))
            else:
                cleaned_lines.append(line)
        else:
            in_table = False
            col_idx_to_remove = -1
            cleaned_lines.append(line)
            
    return '\n'.join(cleaned_lines)

def clean_markdown_text(text, doc_type_code, catalog):
    original_len = len(text)
    
    # 0. Normalize escaping (e.g. \_ -> _)
    text = text.replace('\\_', '_').replace('\\*', '*')

    # 1. Clean markdown tables specifically targeted at Questions | Answers
    text = clean_markdown_tables(text)

    # 2. Universal boilerplates applied to all documents
    universal_patterns = [
        r'(?im)^.*cleantech\s+open\s+confidential\s*[\u2013\u2014-]\s*do\s+not\s+duplicate.*$',
        r'(?im)^.*©\s*(?:2022|2025)?\s*cleantech\s+open.*$',
        r'(?im)^.*do\s+not\s+duplicate.*$',
        r'(?im)^.*the\s+information\s+presented\s+above\s+is\s+confidential.*$',
        r'(?i)\(?\s*\d+[,\d]*\s*(?:total\s*)?characters?\s*(?:limit|max|maximum)[^\)\n]*\)?',
        
        # New requirements:
        r'(?im)^.*(?:instructions?|directions?):.*$',
        r'(?im)^[\s\d.]*essential\s+business\s+deliverable:?.*$',
        r'(?im)^.*upload\s+(?:this\s+document\s+)?as.*$',
        r'(?im)^.*teamname_.*$',
        r'(?is)if available, and relevant, provide written technology-related testimonials.*?\(one to three pages maximum\)\.?'
    ]
    for p in universal_patterns:
        text = re.sub(p, '', text, flags=re.MULTILINE)

    # 3. Known high-impact multi-line blocks (loose examples, archetype templates)
    text = re.sub(r"(?is)loose\s+example:\s*[\u201c\"'].*?[\u201d\"']\s*", '', text)
    text = re.sub(r"(?is)example:\s*[\u201c\"']blair\s+smith.*?\(source\s+with\s+more\s+examples\)\s*", '', text)
    text = re.sub(r'(?i)e\.g\.,\s*(?:add\s+multilingual|partner\s+with\s+hbcus|partner\s+with\s+local|reach\s+500|30%\s+increase|50%\s+increase)[^\n]*', '', text)
    
    # 4. Document-specific scaffolding from catalog
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

    # 5. Clean up empty markdown headers, stray list markers, and excessive whitespace
    text = re.sub(r'(?m)^#+\s*$', '', text)
    text = re.sub(r'(?m)^\s*[-*•\d\.]+\s*$', '', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    cleaned_text = text.strip()
    return cleaned_text, original_len, len(cleaned_text)

def classify_filename(fname):
    fname_lower = fname.lower()
    
    if re.search(r'(ebd[_\-\s]*2|impact[_\-\s]*deliverable|deliverable[_\-\s]*2)', fname_lower):
        return 'EBD2'
    if re.search(r'(ebd[_\-\s]*3|customer[_\-\s]*segmentation|deliverable[_\-\s]*3)', fname_lower):
        return 'EBD3'
    if re.search(r'(ebd[_\-\s]*4|technology[_\-\s]*validation|deliverable[_\-\s]*4)', fname_lower):
        return 'EBD4'
    if re.search(r'(ebd[_\-\s]*1|executive[_\-\s]*summary|deliverable[_\-\s]*1|ebd[_\-\s]*6|ebd[_\-\s]*9)', fname_lower):
        return 'EBD1_ExecSummary'
    if re.search(r'(business[_\-\s]*model[_\-\s]*canvas|strategyzer|bmc)', fname_lower):
        return 'BMC'
    if re.search(r'(financial[_\-\s]*projection|pro[_\-\s]*forma|ebd[_\-\s]*5|deliverable[_\-\s]*5)', fname_lower):
        return 'FinancialProjection'
    if re.search(r'(pitch[_\-\s]*deck|slide[_\-\s]*deck|investor[_\-\s]*deck|ebd[_\-\s]*8|deliverable[_\-\s]*8)', fname_lower):
        return 'IP_PitchDeck'
        
    return 'OTHER'

def process_directory(input_dir, output_dir, catalog_path):
    catalog = load_catalog(catalog_path)
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    
    total_files = 0
    total_orig_chars = 0
    total_clean_chars = 0
    
    for md_file in input_path.rglob('*.md'):
        fname = md_file.name
        doc_type = classify_filename(fname)
                
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
    parser = argparse.ArgumentParser(description="Clean competition scaffolding from markdown files v2.")
    parser.add_argument('--input-dir', required=True, help="Input directory of parsed markdowns")
    parser.add_argument('--output-dir', required=True, help="Output directory for clean markdowns")
    parser.add_argument('--catalog', default='data/scaffolding_master_catalog.json', help="Path to master scaffolding catalog JSON")
    args = parser.parse_args()
    
    process_directory(args.input_dir, args.output_dir, args.catalog)
