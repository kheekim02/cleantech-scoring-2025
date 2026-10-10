# scripts/measure_visual_markers.py
"""Count structural visual markers in parsed markdown (EBD8 pitch decks)."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

PATTERNS = {
    "image_comment": re.compile(r"<!--\s*image\b[^>]*-->", re.IGNORECASE),
    "md_image": re.compile(r"!\[[^\]]*\]\([^)]*\)"),
    "diagram_heading": re.compile(r"^#{1,6}\s*diagram\b", re.IGNORECASE | re.MULTILINE),
    "figure_caption": re.compile(r"^\s*(?:figure|fig\.)\s*\d+\s*[:.]", re.IGNORECASE | re.MULTILINE),
}


def count_visual_markers(text: str) -> dict[str, int]:
    return {name: len(p.findall(text or "")) for name, p in PATTERNS.items()}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parsed-dir", required=True)
    ap.add_argument("--glob", default="**/*EBD8*.md")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    per_file = {}
    for p in sorted(Path(a.parsed_dir).glob(a.glob)):
        per_file[str(p.relative_to(a.parsed_dir))] = count_visual_markers(p.read_text(encoding="utf-8", errors="ignore"))
    files_with_any = sum(1 for c in per_file.values() if sum(c.values()) > 0)
    summary = {"files": len(per_file), "files_with_any_marker": files_with_any, "per_file": per_file}
    Path(a.out).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"{files_with_any}/{len(per_file)} files contain visual markers")


if __name__ == "__main__":
    main()
