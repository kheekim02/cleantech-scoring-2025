import os
import glob
from pathlib import Path
import fitz  # PyMuPDF
from rapidocr import RapidOCR

def main():
    raw_dir = "/data/scraping/datasets/cto_accelerator/raw/"
    parsed_dir = "/data/scraping/datasets/cto_accelerator/parsed/"
    
    ocr_engine = RapidOCR()
    
    pdf_files = glob.glob(os.path.join(raw_dir, "**/*.pdf"), recursive=True)
    print(f"Found {len(pdf_files)} PDFs in raw/")
    
    ocr_count = 0
    for pdf_path in pdf_files:
        path_obj = Path(pdf_path)
        
        rel_path = path_obj.relative_to(raw_dir)
        company_name = rel_path.parts[0]
        filename = path_obj.name
        
        md_path = os.path.join(parsed_dir, company_name, "converted", f"{filename}.md")
        
        needs_ocr = False
        if not os.path.exists(md_path):
            needs_ocr = True
        else:
            size = os.path.getsize(md_path)
            if size < 100:
                needs_ocr = True
                
        if needs_ocr:
            print(f"Needs OCR: {pdf_path} (md size: {os.path.getsize(md_path) if os.path.exists(md_path) else 'Missing'})")
            
            try:
                doc = fitz.open(pdf_path)
                md_content = []
                for page_num in range(len(doc)):
                    page = doc[page_num]
                    pix = page.get_pixmap(dpi=150)
                    img_bytes = pix.tobytes("png")
                    result = ocr_engine(img_bytes)
                    
                    page_text = []
                    if result and hasattr(result, 'txts') and result.txts:
                        for text in result.txts:
                            page_text.append(text)
                            
                    md_content.append(f"<!-- Page {page_num + 1} -->\n" + "\n".join(page_text) + "\n")
                    
                final_md = "\n".join(md_content)
                
                os.makedirs(os.path.dirname(md_path), exist_ok=True)
                with open(md_path, "w", encoding="utf-8") as f:
                    f.write(final_md)
                
                print(f"  -> Successfully OCR'd to {md_path} ({len(final_md)} chars)")
                ocr_count += 1
            except Exception as e:
                print(f"  -> Failed to OCR {pdf_path}: {e}")

    print(f"Finished OCR. Processed {ocr_count} files.")

if __name__ == '__main__':
    main()
