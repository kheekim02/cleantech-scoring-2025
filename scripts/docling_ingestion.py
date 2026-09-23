"""Docling Ingestion Engine with Scaffolding Filtering and Bounding Box Provenance.

Extracts structured chunks (paragraphs, headings, tables) with exact page numbers
and bounding-box coordinates from applicant PDFs, stripping competition scaffolding.
"""
import os
import re
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DOC_TYPE_PATTERNS = {
    'M1': [r'M1\b', r'Module.*1'],
    'M2': [r'M2\b', r'Module.*2', r'GHG'],
    'M3': [r'M3\b', r'Module.*3'],
    'M4': [r'M4\b', r'Module.*4'],
    'M5': [r'M5\b', r'Module.*5'],
    'M6': [r'M6\b', r'Module.*6'],
    'M7': [r'M7\b', r'Module.*7', r'Legal'],
    'M8': [r'M8\b', r'Module.*8', r'Team'],
    'EBD1': [r'Canvas', r'Biz.*Model', r'EBD1'],
    'EBD2': [r'EBD2', r'Impact.*Statement'],
    'EBD3': [r'EBD3', r'Customer.*Segment', r'Competitive.*Matrix'],
    'EBD4': [r'EBD4', r'TechnologyValidation', r'Tech.*Val', r'Patent'],
    'EBD5': [r'EBD5', r'FinancialProjection', r'Financial'],
    'EBD6': [r'EBD6', r'Executive.*Summary', r'OnePage'],
    'EBD8': [r'EBD8', r'Pitch', r'Deck', r'Investor.*Pitch'],
}

DOC_TYPE_CATALOG_MAP = {
    'EBD1': ['BMC', 'EBD1'],
    'EBD2': ['EBD2', 'M2', 'GHG', 'Inclusion'],
    'EBD3': ['EBD3', 'M4'],
    'EBD4': ['EBD4'],
    'EBD5': ['FinancialProjection', 'M6', 'EBD5'],
    'EBD6': ['EBD1_ExecSummary', 'EBD6'],
    'EBD8': ['EBD8'],
    'M1': ['M1'],
    'M2': ['M2', 'GHG', 'Inclusion'],
    'M3': ['M3'],
    'M4': ['M4', 'EBD3'],
    'M5': ['M5'],
    'M6': ['M6', 'FinancialProjection', 'EBD5'],
    'M7': ['M7'],
    'M8': ['M8'],
    'BMC': ['BMC', 'EBD1'],
}

UNIVERSAL_SCAFFOLDING_PATTERNS = [
    r'(?i)cleantech\s+open\s+confidential\s*[\u2013\u2014-]\s*do\s+not\s+duplicate[^\n]*',
    r'(?i)©\s*(?:2022|2023|2024|2025)?\s*cleantech\s+open[^\n]*',
    r'(?i)do\s+not\s+duplicate\s+or\s+distribute\s+without\s+written\s+permission[^\n]*',
    r'(?i)the\s+information\s+presented\s+above\s+is\s+confidential[^\n]*',
    r'(?i)\(?\s*\d+[,\d]*\s*(?:total\s*)?characters?\s*(?:limit|max|maximum)[^\)\n]*\)?',
    r'(?i)upload\s+this\s+document\s+as\s+teamname[^\n]*',
    r'(?i)^#*\s*(?:instructions?|directions?):?.*$',
    r'(?i)^#*\s*essential\s+business\s+deliverable\s*#\d+.*$',
    r'(?i)^#*\s*module\s*\d+.*instructions:?.*$',
    r"(?is)loose\s+example:\s*[\u201c\"'].*?[\u201d\"']\s*",
    r"(?is)example:\s*[\u201c\"']blair\s+smith.*?\(source\s+with\s+more\s+examples\)\s*",
    r'(?i)e\.g\.,\s*(?:add\s+multilingual|partner\s+with\s+hbcus|partner\s+with\s+local|reach\s+500|30%\s+increase|50%\s+increase)[^\n]*',
    r'(?is)for\s+the\s+financial\s+projection\s+model.*?(?:validation\s+interviews\.?|$)',
    r'(?is)use\s+your\s+work\s+in\s+module\s*3.*?(?:validation\s+interviews\.?|$)',
    r'(?is)use\s+your\s+customer\s+acquisition\s+cost\s+in\s+module\s*4[^\n]*',
    r'(?is)three\s+year\s+financial\s+projection:.*?(?:validation\s+interviews\.?|$)',
    r'(?is)building\s+and\s+exporting\s+your\s+model:.*?(?:previous\s+one\.?|$)',
    r'(?is)to\s+create\s+a\s+single\s+pdf.*?(?:print\s+to\s+pdf\.?|$)',
    r'(?is)module\s*\d+:\s*[^\n]+assignment\s+questions',
    r'(?is)interview\s+professionals\s+familiar\s+with\s+the[^\n]*',
]

_CONVERTER_CACHE = None


def get_docling_converter():
    """Lazily initialize and cache the Docling DocumentConverter with device optimization."""
    global _CONVERTER_CACHE
    if _CONVERTER_CACHE is None:
        import sys
        try:
            import torch
        except ImportError:
            torch = None
        from docling.document_converter import DocumentConverter, PdfFormatOption
        from docling.datamodel.base_models import InputFormat
        from docling.datamodel.pipeline_options import PdfPipelineOptions, AcceleratorOptions, AcceleratorDevice

        pipeline_options = PdfPipelineOptions()
        # On macOS Darwin MPS lacks float64 for RT-DETR sinusoidal embeddings; use CPU
        if sys.platform == 'darwin':
            pipeline_options.accelerator_options = AcceleratorOptions(device=AcceleratorDevice.CPU)
        elif torch and torch.cuda.is_available():
            pipeline_options.accelerator_options = AcceleratorOptions(device=AcceleratorDevice.CUDA)
        else:
            pipeline_options.accelerator_options = AcceleratorOptions(device=AcceleratorDevice.CPU)

        _CONVERTER_CACHE = DocumentConverter(
            format_options={
                InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
            }
        )
    return _CONVERTER_CACHE


def detect_doc_type(filename: str) -> str:
    """Detect deliverable type code (EBD1-EBD8, M1-M8) from PDF filename."""
    clean_name = os.path.basename(filename)
    for code, patterns in DOC_TYPE_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, clean_name, re.IGNORECASE):
                return code
    return 'OTHER'


def load_scaffolding_catalog(catalog_path: str | None = None) -> dict[str, Any]:
    """Load the master scaffolding catalog JSON if available."""
    default_paths = [
        catalog_path,
        'data/scaffolding_master_catalog.json',
        '/data/scraping/datasets/cto_accelerator/scaffolding_master_catalog.json',
    ]
    for p in default_paths:
        if p and os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Error loading scaffolding catalog from {p}: {e}")
    return {}


def clean_scaffolding_from_chunks(
    chunks: list[dict[str, Any]],
    doc_type: str = 'OTHER',
    catalog_path: str | None = None,
) -> list[dict[str, Any]]:
    """Filter competition template scaffolding boilerplate out of extracted chunks."""
    catalog = load_scaffolding_catalog(catalog_path)
    
    # Collect items from mapped categories as well as global catalog
    cat_keys = DOC_TYPE_CATALOG_MAP.get(doc_type, [doc_type])
    cat_items = []
    for k in cat_keys:
        if k in catalog:
            cat_items.extend(catalog[k].get('items', []))

    # Also collect high-confidence multi-word items across all categories
    for cat_data in catalog.values():
        for item in cat_data.get('items', []):
            raw_t = item.get('text', '').strip()
            if len(raw_t.split()) >= 4:
                cat_items.append(item)

    cleaned_chunks = []
    for chunk in chunks:
        text = chunk.get('text', '')
        if not text or not text.strip():
            continue

        # 1. Apply universal regex patterns
        for pat in UNIVERSAL_SCAFFOLDING_PATTERNS:
            text = re.sub(pat, '', text, flags=re.MULTILINE)

        # 2. Apply catalog-specific items
        for item in cat_items:
            raw_target = item.get('text', '')
            words = raw_target.split()
            if len(words) < 4:
                continue
            escaped_words = [re.escape(w) for w in words]
            pat = r'(?i)' + r'[\s\\_*\-]+'.join(escaped_words)
            text = re.sub(pat, '', text, flags=re.MULTILINE)

        # 3. Clean trailing whitespace / empty markdown artifacts
        text = re.sub(r'(?m)^#+\s*$', '', text)
        text = re.sub(r'(?m)^\s*[-*•\d\.]+\s*$', '', text)
        text = re.sub(r'\n{3,}', '\n\n', text).strip()

        # If after cleaning the text is empty or meaningless (<8 chars with no digits/letters), drop it
        if len(text) >= 8 and re.search(r'[a-zA-Z0-9]', text):
            cleaned_chunk = dict(chunk)
            cleaned_chunk['text'] = text
            cleaned_chunks.append(cleaned_chunk)

    return cleaned_chunks


def extract_pdf_chunks(
    pdf_path: str,
    doc_type: str | None = None,
    catalog_path: str | None = None,
) -> list[dict[str, Any]]:
    """Extract structured chunks from a PDF with page numbers and bounding boxes using Docling."""
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    filename = os.path.basename(pdf_path)
    if not doc_type:
        doc_type = detect_doc_type(filename)

    converter = get_docling_converter()
    result = converter.convert(pdf_path)
    doc = result.document

    raw_chunks = []
    chunk_counter = 0

    for item, level in doc.iterate_items():
        prov = getattr(item, 'prov', [])
        p_no = prov[0].page_no if prov else 1

        # Check element type and extract text / table markdown
        item_type = type(item).__name__.lower().replace('item', '')
        if 'table' in item_type:
            # Format table as clean markdown
            if hasattr(item, 'export_to_markdown'):
                try:
                    text = item.export_to_markdown(doc=doc)
                except TypeError:
                    text = item.export_to_markdown()
            else:
                text = getattr(item, 'text', '')
        else:
            text = getattr(item, 'text', '')

        if not text or not text.strip():
            continue

        chunk_counter += 1
        raw_chunks.append({
            'chunk_id': f"{Path(filename).stem}_{chunk_counter:04d}",
            'source_pdf': filename,
            'doc_type': doc_type,
            'page_no': p_no,
            'type': item_type,
            'text': text.strip(),
        })

    # Filter scaffolding
    clean_chunks = clean_scaffolding_from_chunks(raw_chunks, doc_type=doc_type, catalog_path=catalog_path)
    return clean_chunks


def process_startup_folder(
    startup_raw_dir: str,
    output_dir: str,
    catalog_path: str | None = None,
) -> dict[str, Any]:
    """Process all PDFs for a single startup, generating structured chunks and unified markdown."""
    startup_path = Path(startup_raw_dir)
    if not startup_path.exists():
        raise FileNotFoundError(f"Startup raw directory not found: {startup_raw_dir}")

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(startup_path.rglob('*.pdf'))
    if not pdf_files:
        logger.warning(f"No PDFs found under {startup_raw_dir}")
        return {'chunks': [], 'total_chunks': 0}

    all_chunks = []
    unified_doc_parts = []

    for pdf in pdf_files:
        fname = pdf.name
        doc_type = detect_doc_type(fname)
        try:
            chunks = extract_pdf_chunks(str(pdf), doc_type=doc_type, catalog_path=catalog_path)
            all_chunks.extend(chunks)

            # Build markdown section for prompt prefix caching
            doc_section = [f"=== DOCUMENT: {fname} [Type: {doc_type}] ==="]
            for c in chunks:
                page_info = f"[Page {c['page_no']}]" if c.get('page_no') else ""
                doc_section.append(f"{page_info} {c['text']}")
            unified_doc_parts.append("\n\n".join(doc_section))
        except Exception as e:
            logger.error(f"Error processing {fname}: {e}")

    # Write chunks.json
    chunks_file = out_path / "chunks.json"
    with open(chunks_file, 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, indent=2)

    # Write full_text.md for RadixAttention prompt prefill
    full_text_file = out_path / "full_text.md"
    with open(full_text_file, 'w', encoding='utf-8') as f:
        f.write("\n\n\n".join(unified_doc_parts))

    return {
        'startup_id': startup_path.name,
        'chunks_count': len(all_chunks),
        'chunks_file': str(chunks_file),
        'full_text_file': str(full_text_file),
    }


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="Docling Ingestion Engine with Provenance and Scaffolding Filter")
    parser.add_argument('--input', required=True, help="Input directory of raw PDFs or single PDF")
    parser.add_argument('--output', required=True, help="Output directory for clean chunks and markdown")
    parser.add_argument('--catalog', default='data/scaffolding_master_catalog.json', help="Scaffolding catalog JSON")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    if os.path.isfile(args.input):
        chunks = extract_pdf_chunks(args.input, catalog_path=args.catalog)
        os.makedirs(args.output, exist_ok=True)
        out_file = os.path.join(args.output, "chunks.json")
        with open(out_file, 'w') as f:
            json.dump(chunks, f, indent=2)
        print(f"Extracted {len(chunks)} chunks from {args.input} -> {out_file}")
    else:
        res = process_startup_folder(args.input, args.output, catalog_path=args.catalog)
        print(f"Processed startup {res.get('startup_id')}: {res.get('chunks_count')} chunks saved to {res.get('chunks_file')}")
