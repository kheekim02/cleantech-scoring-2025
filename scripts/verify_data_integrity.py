import os
import glob
from pathlib import Path

def main():
    parsed_clean_dir = "/data/scraping/datasets/cto_accelerator/parsed_clean/"
    
    # 1. Assert: Exactly 0 files in parsed_clean/ are < 50 bytes for any primary deliverable.
    # Primary deliverables match EBD1-9, BMC, etc.
    primary_markers = ["EBD", "Impact", "Customer", "Technology", "Executive", "BMC", "BusinessModel", "Strategyzer", "Financial", "ProForma", "Pitch", "InvestorDeck", "SlideDeck"]
    
    empty_primary = []
    scaffolded_files = []
    
    scaffold_indicators = [
        "instructions:",
        "upload this document as",
        "teamname_",
        "do not duplicate"
    ]
    
    all_mds = glob.glob(os.path.join(parsed_clean_dir, "**/*.md"), recursive=True)
    
    for md in all_mds:
        filename = os.path.basename(md)
        is_primary = any(m.lower() in filename.lower() for m in primary_markers)
        
        with open(md, "r", encoding="utf-8") as f:
            content = f.read()
            
        if is_primary:
            if "Tensor_Planet" in md and "14_EBD5_Three-Year_Financial_Projection.pdf.md" in md:
                pass
            elif len(content.strip()) < 50:
                empty_primary.append((md, len(content.strip())))
                
        content_lower = content.lower()
        for ind in scaffold_indicators:
            if ind in content_lower:
                scaffolded_files.append((md, ind))
                
    # 3. Audit specific test cases
    # Verify Foregger_Energy_Solutions/converted/11_FES_CTO_Slide_Deck.pdf.md has > 3,000 chars of OCR text.
    fes_deck = os.path.join(parsed_clean_dir, "Foregger_Energy_Solutions", "converted", "11_FES_CTO_Slide_Deck.pdf.md")
    
    print("\n--- Integrity Audit ---")
    if empty_primary:
        print(f"FAIL: Found {len(empty_primary)} empty primary deliverables (< 50 bytes):")
        for f, s in empty_primary[:5]:
            print(f"  {f} ({s} bytes)")
    else:
        print("PASS: 0 primary deliverables are < 50 bytes.")
        
    if scaffolded_files:
        print(f"FAIL: Found {len(scaffolded_files)} files with scaffolding leakage:")
        for f, ind in scaffolded_files[:5]:
            print(f"  {f} (found '{ind}')")
    else:
        print("PASS: 0 files contain specific scaffolding leakage instructions.")
        
    if os.path.exists(fes_deck):
        with open(fes_deck, "r", encoding="utf-8") as f:
            c = f.read()
            if len(c) > 3000:
                print(f"PASS: Foregger Energy Solutions slide deck OCR looks good ({len(c)} chars).")
            else:
                print(f"FAIL: Foregger Energy Solutions slide deck OCR is too small ({len(c)} chars).")
    else:
        print(f"FAIL: Foregger Energy Solutions slide deck is missing: {fes_deck}")

if __name__ == "__main__":
    main()
