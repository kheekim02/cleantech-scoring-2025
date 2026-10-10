#!/usr/bin/env python3
"""Wave 0: replace circular/broken primary_map symlinks with real file copies.

Default source is the pre-remediation backup. Never leaves a symlink in place.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser(description="Restore real primary_map.json files into cache")
    ap.add_argument(
        "--cache-dir",
        default="/data/scraping/datasets/cto_accelerator/ai_cache_v5_parsed",
    )
    ap.add_argument(
        "--backup-dir",
        default="/data/scraping/datasets/cto_accelerator/ai_cache_v5_parsed_pre_remediation_20261003T214821Z",
    )
    ap.add_argument(
        "--out",
        default="/data/scraping/datasets/cto_accelerator/wave0_primary_map_restore.json",
    )
    args = ap.parse_args()

    cache = Path(args.cache_dir)
    backup = Path(args.backup_dir)
    if not cache.is_dir() or not backup.is_dir():
        print(json.dumps({"status": "RED", "detail": "cache or backup missing"}))
        return 1

    company_files = sorted(
        p for p in cache.glob("*.json") if not p.name.endswith(".primary_map.json")
    )
    restored = 0
    missing_backup = []
    already_real = 0
    errors = []

    for company_path in company_files:
        company = company_path.stem
        dst = cache / f"{company}.primary_map.json"
        src = backup / f"{company}.primary_map.json"
        if not src.is_file() or src.is_symlink():
            # Only accept real backup files
            if src.is_symlink() or not src.exists():
                missing_backup.append(company)
                continue
        try:
            if dst.exists() or dst.is_symlink():
                if dst.is_symlink():
                    dst.unlink()
                elif dst.is_file():
                    # Real file already present — leave unless unreadable
                    try:
                        json.loads(dst.read_text(encoding="utf-8"))
                        already_real += 1
                        continue
                    except Exception:
                        dst.unlink()
            shutil.copy2(src, dst)
            # Verify
            payload = json.loads(dst.read_text(encoding="utf-8"))
            if not isinstance(payload, dict) or not payload:
                raise ValueError("copied map empty/non-object")
            if dst.is_symlink():
                raise ValueError("destination still a symlink after copy")
            restored += 1
        except Exception as exc:
            errors.append({"company": company, "error": str(exc)})

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cache_dir": str(cache),
        "backup_dir": str(backup),
        "companies": len(company_files),
        "restored": restored,
        "already_real": already_real,
        "missing_backup": missing_backup,
        "errors": errors,
        "status": "GREEN" if not missing_backup and not errors else "RED",
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
