# src/scorer/visual_deck_inspector.py
from __future__ import annotations

from pathlib import Path
from typing import Any
import fitz  # PyMuPDF


def inspect_deck_visuals(pdf_path: str | Path) -> dict[str, Any]:
    """Inspect raw slide deck PDF for embedded images, vector paths, and diagram structures."""
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    doc = fitz.open(str(path))
    pages_data: list[dict[str, Any]] = []
    total_images = 0
    total_drawings = 0

    for page_num in range(len(doc)):
        page = doc[page_num]
        images = page.get_images(full=True)
        drawings = page.get_drawings()
        img_count = len(images)
        draw_count = len(drawings)
        total_images += img_count
        total_drawings += draw_count

        text = page.get_text().lower()

        # A diagram candidate has >= 5 vector drawing shapes or >= 1 image with structural text
        is_diagram_candidate = draw_count >= 5 or (
            img_count >= 1
            and any(
                w in text
                for w in [
                    "problem",
                    "model",
                    "process",
                    "workflow",
                    "system",
                    "architecture",
                    "diagram",
                ]
            )
        )

        # A logo candidate exists on page 1 or page 2 if bounded raster or prominent header vector
        has_logo_candidate = page_num <= 1 and (img_count >= 1 or draw_count >= 1)

        pages_data.append({
            "page_num": page_num + 1,
            "image_count": img_count,
            "drawing_count": draw_count,
            "is_diagram_candidate": is_diagram_candidate,
            "has_logo_candidate": has_logo_candidate,
            "text_preview": text[:200],
        })

    doc.close()

    has_diagram = any(p["is_diagram_candidate"] for p in pages_data)
    has_logo = any(p["has_logo_candidate"] for p in pages_data)

    return {
        "pdf_path": str(path),
        "page_count": len(pages_data),
        "total_images": total_images,
        "total_drawings": total_drawings,
        "has_images": total_images > 0,
        "has_vector_drawings": total_drawings > 0,
        "has_diagram": has_diagram,
        "has_logo": has_logo,
        "pages": pages_data,
    }
