import os
import glob
import re
from pathlib import Path
import fitz  # PyMuPDF

RAW_DIR = "/data/scraping/datasets/cto_accelerator/raw/"
PARSED_DIR = "/data/scraping/datasets/cto_accelerator/parsed/"
MIN_MARKDOWN_BYTES = 100
MIN_DIGITAL_CHARS = 50


def digital_markdown(pdf_path: str) -> str:
    """Read embedded PDF text. Returns an empty string when the pages are images."""
    doc = fitz.open(pdf_path)
    pages = []
    for page_num, page in enumerate(doc):
        pages.append(f"<!-- Page {page_num + 1} -->\n{page.get_text().strip()}")
    doc.close()
    return "\n\n".join(pages)


def digital_body_chars(markdown: str) -> int:
    body = re.sub(r"<!--.*?-->", "", markdown, flags=re.DOTALL)
    return len(body.strip())


def ocr_markdown(pdf_path: str, engine) -> str:
    doc = fitz.open(pdf_path)
    pages = []
    for page_num, page in enumerate(doc):
        pix = page.get_pixmap(dpi=150)
        result = engine(pix.tobytes("png"))
        lines = []
        if result and getattr(result, "txts", None):
            lines.extend(result.txts)
        pages.append(f"<!-- Page {page_num + 1} -->\n" + "\n".join(lines) + "\n")
    doc.close()
    return "\n".join(pages)


def markdown_needs_repair(md_path: str) -> bool:
    if not os.path.exists(md_path):
        return True
    return os.path.getsize(md_path) < MIN_MARKDOWN_BYTES


def repair_markdown(pdf_path: str, md_path: str, ocr_engine=None):
    """Write markdown from embedded text, or OCR when the PDF has no text layer.

    Returns ('digital'|'ocr', char_count). Does not delete the PDF.
    """
    digital = digital_markdown(pdf_path)
    if digital_body_chars(digital) >= MIN_DIGITAL_CHARS:
        final_md = digital
        method = "digital"
    else:
        if ocr_engine is None:
            from rapidocr import RapidOCR
            ocr_engine = RapidOCR()
        final_md = ocr_markdown(pdf_path, ocr_engine)
        method = "ocr"
    os.makedirs(os.path.dirname(md_path), exist_ok=True)
    with open(md_path, "w", encoding="utf-8") as handle:
        handle.write(final_md)
    return method, len(final_md), ocr_engine


def main():
    pdf_files = glob.glob(os.path.join(RAW_DIR, "**/*.pdf"), recursive=True)
    print(f"Found {len(pdf_files)} PDFs in raw/")

    repaired = 0
    ocr_engine = None
    for pdf_path in sorted(pdf_files):
        path_obj = Path(pdf_path)
        company_name = path_obj.relative_to(RAW_DIR).parts[0]
        md_path = os.path.join(PARSED_DIR, company_name, "converted", f"{path_obj.name}.md")
        if not markdown_needs_repair(md_path):
            continue
        current = os.path.getsize(md_path) if os.path.exists(md_path) else "Missing"
        print(f"Needs repair: {pdf_path} (md size: {current})")
        try:
            method, chars, ocr_engine = repair_markdown(pdf_path, md_path, ocr_engine)
            print(f"  -> Wrote {method} text to {md_path} ({chars} chars)")
            repaired += 1
        except Exception as exc:
            print(f"  -> Failed to repair {pdf_path}: {exc}")

    print(f"Finished. Repaired {repaired} files.")

if __name__ == '__main__':
    main()
