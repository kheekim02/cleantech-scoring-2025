import argparse
import os
import sys
import glob

DEFAULT_PARSED_DIR = "/data/scraping/datasets/cto_accelerator/parsed_clean_v4/"

# Filename tokens for deliverables the scorer treats as primary sources.
PRIMARY_MARKERS = [
    "EBD",
    "Impact",
    "Customer",
    "Technology",
    "Executive",
    "BMC",
    "BusinessModel",
    "Strategyzer",
    "Financial",
    "ProForma",
    "Pitch",
    "InvestorDeck",
    "SlideDeck",
]

# Template phrases that must not survive in the cleaned tree.
SCAFFOLD_INDICATORS = [
    "instructions:",
    "upload this document as",
    "teamname_",
    "do not duplicate",
    "essential business deliverable",
]

FOREGGER_DECK = (
    "Foregger_Energy_Solutions",
    "converted",
    "11_FES_CTO_Slide_Deck.pdf.md",
)
FOREGGER_MIN_CHARS = 3000
PRIMARY_MIN_CHARS = 50


def audit(parsed_dir: str) -> list[str]:
    """Return one message per failed check. An empty list is a pass."""
    failures = []
    if not os.path.isdir(parsed_dir):
        return [f"parsed directory is missing: {parsed_dir}"]

    empty_primary = []
    scaffolded = []
    markdowns = glob.glob(os.path.join(parsed_dir, "**/*.md"), recursive=True)
    for path in markdowns:
        filename = os.path.basename(path)
        is_primary = any(marker.lower() in filename.lower() for marker in PRIMARY_MARKERS)
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            content = handle.read()
        if is_primary and len(content.strip()) < PRIMARY_MIN_CHARS:
            empty_primary.append((path, len(content.strip())))
        lowered = content.lower()
        for indicator in SCAFFOLD_INDICATORS:
            if indicator in lowered:
                scaffolded.append((path, indicator))

    if empty_primary:
        preview = ", ".join(f"{path} ({size} chars)" for path, size in empty_primary[:5])
        failures.append(
            f"{len(empty_primary)} primary deliverables are under {PRIMARY_MIN_CHARS} characters: {preview}"
        )
    if scaffolded:
        preview = ", ".join(f"{path} [{indicator}]" for path, indicator in scaffolded[:5])
        failures.append(f"{len(scaffolded)} files still contain template scaffolding: {preview}")

    deck = os.path.join(parsed_dir, *FOREGGER_DECK)
    if not os.path.exists(deck):
        failures.append(f"Foregger slide deck is missing: {deck}")
    else:
        with open(deck, "r", encoding="utf-8", errors="replace") as handle:
            size = len(handle.read())
        if size <= FOREGGER_MIN_CHARS:
            failures.append(
                f"Foregger slide deck OCR is too small ({size} chars, need more than {FOREGGER_MIN_CHARS})"
            )
    return failures


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Fail when cleaned founder markdown is incomplete or still contains template text.")
    parser.add_argument("--parsed-dir", default=DEFAULT_PARSED_DIR)
    args = parser.parse_args(argv)

    print("\n--- Integrity Audit ---")
    failures = audit(args.parsed_dir)
    if failures:
        for message in failures:
            print(f"FAIL: {message}")
        return 1
    print("PASS: primary deliverables have text, template lines are gone, and the Foregger deck is present.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
