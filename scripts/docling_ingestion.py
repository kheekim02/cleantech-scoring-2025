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

# Deliverable names outrank module numbers in the filename. Checked first so
# "Business_Model_Canvas_Module_1" stays EBD1 and "EBD_1_Team_Targets" stays M8.
# Bare tokens (Canvas, Team, Legal, Patent) and a blanket EBD9→executive-summary
# rule are intentionally absent: they pull the wrong file into a primary source.
DOC_TYPE_ALIASES = {
    # Content names are checked before EBD numbers. These are cohort-wide template
    # names, not one company's filename: interview sheets, archetype exercises,
    # financial models, and pitches stay in those groups even when the EBD number
    # is glued on, misspelled, or omitted.
    'M3': [r'Arch[ei]type', r'Product[_\-\s]*Market[_\-\s]*Fit', r'(?<![A-Za-z])PMF(?![A-Za-z])'],
    'M8': [r'Team[_\-\s]*Targets?', r'Management[_\-\s]*Team', r'Managemet[_\-\s]*Team', r'Target[_\-\s]*Goals?'],
    'M4': [r'Markets[_\-\s]*(?:and|&)[_\-\s]*Getting'],
    'M1': [
        r'Customer[_\-\s]*Interview',
        r'Customer[_\-\s]*Discover',
        r'Interview[_\-\s]*Capture',
        r'Module[_\-\s]*One\b',
    ],
    'M2': [r'GHG'],
    'M7': [r'Legal[_\-\s]*(?:Questions|Assignment)'],
    'EBD5': [
        r'Financial[_\-\s]*Projection',
        r'Financial[_\-\s]*Plan',
        r'Financial[_\-\s]*Model',
        r'Fian+cial[_\-\s]*(?:Projection|Model|Plan)',
        r'finincial[_\-\s]*proj',
        r'[0-9][_\-\s]*year[_\-\s]*projections?',
        r'Revenue[_\-\s]*(?:Projection|Forecast|Model)',
        r'revenue[_\-\s]*cost[_\-\s]*model',
        r'EBITDA[_\-\s]*Forecast',
        r'projec+t+ion',
        r'Pro[_\-\s]*Forma',
    ],
    'EBD8': [
        r'Pitch[_\-\s]*Deck',
        r'Slide[_\-\s]*Deck',
        r'Investor[_\-\s]*(?:Deck|Pitch)',
        r'PDeck',
        r'Pitch',
        r'Cleantech[_\-\s]*Open[_\-\s]*Deck',
        r'CTO[_\-\s]*Deck',
        # "Deck" names the investor deck. Technical_Deck and Strategy_Deck do not.
        r'(?<!Technical_)(?<!Technical-)(?<!Strategy_)(?<!Strategy-)Deck',
        r'EBD[_\-\s]*10(?![0-9])',
    ],
    'EBD1': [
        r'Business[_\-\s]*Model[_\-\s]*Canvas',
        r'Business[_\-\s]*Modle[_\-\s]*Canvas',
        r'Business[_\-\s]*Model[_\-\s]*Convass',
        r'Biz[_\-\s]*Model',
        r'BMC',
        r'Strategyzer',
    ],
    'EBD2': [r'Impact[_\-\s]*Statement'],
    'EBD3': [r'Customer[_\-\s]*Segment', r'Competitive[_\-\s]*Matrix'],
    'EBD4': [r'Technology[_\-\s]*Validation', r'Technology[_\-\s]*Testimonial', r'Tech[_\-\s]*Val'],
    'EBD6': [
        r'Executive[_\-\s]*Summary',
        r'Exec[_\-\s]*Summary',
        r'Executive[_\-\s]*Overview',
        r'One[_\-\s]*Page',
        r'1[_\-\s]*Pager',
    ],
}

DOC_TYPE_PATTERNS = {
    # Modules — match M1, Module_1, Module 1. The number is a whole token, so M10/Module 10 do not match M1.
    # Underscore is a word character, so \b does not split Module_1_Customer or M8Team.
    # (?![0-9]) still rejects Module_10 and M10.
    # Company names are often glued on: GreenSightTechnologiesM3Assignment.
    # M[_\-\s]*3 still rejects M10/M30 because the next character cannot be a digit.
    'M1': [r'M[_\-\s]*1(?![0-9])', r'Module[_\-\s]*1(?![0-9])'],
    'M2': [r'M[_\-\s]*2(?![0-9])', r'Module[_\-\s]*2(?![0-9])'],
    'M3': [r'M[_\-\s]*3(?![0-9])', r'Module[_\-\s]*3(?![0-9])'],
    'M4': [r'M[_\-\s]*4(?![0-9])', r'Module[_\-\s]*4(?![0-9])'],
    'M5': [r'M[_\-\s]*5(?![0-9])', r'Module[_\-\s]*5(?![0-9])'],
    'M6': [r'M[_\-\s]*6(?![0-9])', r'Module[_\-\s]*6(?![0-9])'],
    'M7': [r'M[_\-\s]*7(?![0-9])', r'Module[_\-\s]*7(?![0-9])'],
    'M8': [r'M[_\-\s]*8(?![0-9])', r'Module[_\-\s]*8(?![0-9])'],
    # EBDs require a separator after the number. EBD1CustomerInterview is not a canvas;
    # EBD_4_TechnologyValidation still matches, and the name alias catches the glued form.
    'EBD1': [r'EBD[_\-\s]*1(?![A-Za-z0-9])', r'Deliverable[_\-\s]*1(?![A-Za-z0-9])'],
    'EBD2': [r'EBD[_\-\s]*2(?![A-Za-z0-9])', r'Deliverable[_\-\s]*2(?![A-Za-z0-9])'],
    'EBD3': [r'EBD[_\-\s]*3(?![A-Za-z0-9])', r'Deliverable[_\-\s]*3(?![A-Za-z0-9])'],
    'EBD4': [r'EBD[_\-\s]*4(?![A-Za-z0-9])', r'Deliverable[_\-\s]*4(?![A-Za-z0-9])'],
    'EBD5': [r'EBD[_\-\s]*5(?![A-Za-z0-9])', r'Deliverable[_\-\s]*5(?![A-Za-z0-9])'],
    'EBD6': [r'EBD[_\-\s]*6(?![A-Za-z0-9])', r'Deliverable[_\-\s]*6(?![A-Za-z0-9])'],
    'EBD8': [r'EBD[_\-\s]*8(?![A-Za-z0-9])', r'Deliverable[_\-\s]*8(?![A-Za-z0-9])'],
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
    r'(?im)^.*essential\s+business\s+deliverable.*$',
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


def _first_doc_type_match(filename: str, table: dict[str, list[str]]) -> str | None:
    for code, patterns in table.items():
        for pat in patterns:
            if re.search(pat, filename, re.IGNORECASE):
                return code
    return None


def detect_doc_type(filename: str) -> str:
    """Detect deliverable type code (EBD1-EBD8, M1-M8) from PDF filename."""
    clean_name = os.path.basename(filename)
    alias = _first_doc_type_match(clean_name, DOC_TYPE_ALIASES)
    if alias:
        return alias
    explicit = _first_doc_type_match(clean_name, DOC_TYPE_PATTERNS)
    return explicit or 'OTHER'


# Opening headings that name the deliverable. The first match in the window wins.
# max_start keeps a later section (a pitch deck's finance slide, a canvas block
# inside a tech-validation form) from renaming the document.
TEXT_TITLE_RULES = [
    (r'customer interview capture sheet', 'M1', 500),
    (r'module\s*2.{0,80}?impact', 'M2', 400),
    (r'module\s*3\W{0,40}product\s*/?\s*market\s*f[il]t', 'M3', 500),
    (r'module\s*7\W{0,30}legal', 'M7', 500),
    (r'module\s*8\W{0,40}management\s*team', 'M8', 500),
    (r'team targets', 'M8', 180),
    (r'greenhouse gas emission reduction potential', 'M2', 600),
    (r'impact statement\s*:', 'EBD2', 600),
    (r'markets and getting to them', 'M4', 500),
    (r'finances and funding', 'M6', 500),
    (r'customer segmentation', 'EBD3', 250),
    (r'product technology validation', 'EBD4', 500),
    (r'investor pitch', 'EBD8', 280),
]

# Doc types that share one scoring-interface group. A filename and a title may
# disagree on M1 vs M3 and still be the same Product Market Fit dropdown.
DOC_TYPE_INTERFACE = {
    'EBD1': 'BC',
    'EBD2': 'ES', 'M2': 'ES',
    'EBD5': 'F', 'M6': 'F',
    'EBD8': 'IP',
    'EBD6': 'IS',
    'M7': 'L',
    'EBD3': 'M', 'M4': 'M',
    'M1': 'PMF', 'M3': 'PMF',
    'M8': 'T',
    'EBD4': 'TP',
}


def infer_doc_type_from_text(text: str, window: int = 1200) -> str | None:
    """Read the opening of an extracted PDF and return its deliverable type.

    Returns None when the opening does not contain a template title. Mentions
    deeper in the document are ignored.
    """
    if not text:
        return None
    head = text[:window].lower()
    best: tuple[int, str] | None = None
    for pattern, code, max_start in TEXT_TITLE_RULES:
        match = re.search(pattern, head)
        if match is None or match.start() > max_start:
            continue
        if best is None or match.start() < best[0]:
            best = (match.start(), code)
    return None if best is None else best[1]


def resolve_doc_type(filename: str, text: str | None = None) -> str:
    """Map a PDF using its filename, then its opening text when the name is weak.

    A clear template title overrides a filename only when the two would land in
    different interface groups. M1 and M3 both stay Product Market Fit.
    """
    named = detect_doc_type(filename)
    inferred = infer_doc_type_from_text(text or '')
    if inferred is None:
        return named
    if named == 'OTHER':
        return inferred
    named_group = DOC_TYPE_INTERFACE.get(named)
    inferred_group = DOC_TYPE_INTERFACE.get(inferred)
    if named_group != inferred_group:
        return inferred
    return named


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
    filename_type = detect_doc_type(filename)
    # A caller-supplied type that differs from the filename is kept.
    # The filename type is provisional until the opening text is read.
    forced = doc_type is not None and doc_type != filename_type
    if not doc_type:
        doc_type = filename_type

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

    if raw_chunks and not forced:
        opening = "\n".join(chunk["text"] for chunk in raw_chunks[:15])
        doc_type = resolve_doc_type(filename, opening)
        for chunk in raw_chunks:
            chunk["doc_type"] = doc_type

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
        try:
            chunks = extract_pdf_chunks(str(pdf), catalog_path=catalog_path)
            doc_type = chunks[0]["doc_type"] if chunks else detect_doc_type(fname)
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
