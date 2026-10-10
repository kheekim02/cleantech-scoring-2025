#!/usr/bin/env python3
"""Integrity check for ai_cache_v5_parsed (or any sibling cache dir).

Fails if company JSON / primary_map counts diverge, or if any primary_map is a
broken/circular symlink, unreadable, empty, or non-object JSON.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path


def _is_circular_or_broken_symlink(path: Path) -> str | None:
    if not path.is_symlink():
        return None
    try:
        # Resolve with strict following; loops raise OSError on Linux.
        path.resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        return f"symlink_unresolvable:{exc}"
    # Symlink that resolves to itself / same path repeatedly
    try:
        target = Path(os.readlink(path))
        if not target.is_absolute():
            target = (path.parent / target).resolve()
        if target.resolve() == path.resolve():
            return "symlink_self_loop"
    except OSError as exc:
        return f"symlink_readlink_fail:{exc}"
    return "symlink_not_allowed"


def check_cache(cache: Path) -> dict:
    findings: list[dict] = []
    company_files = sorted(
        p for p in cache.glob("*.json") if not p.name.endswith(".primary_map.json")
    )
    map_files = sorted(cache.glob("*.primary_map.json"))
    companies = {p.stem for p in company_files}
    maps = {p.name[: -len(".primary_map.json")] for p in map_files}

    if companies != maps:
        missing_maps = sorted(companies - maps)
        missing_json = sorted(maps - companies)
        if missing_maps:
            findings.append(
                {
                    "severity": "HARD",
                    "gate": "G0.0",
                    "detail": f"missing primary_map for {len(missing_maps)} companies",
                    "extra": {"companies": missing_maps[:20]},
                }
            )
        if missing_json:
            findings.append(
                {
                    "severity": "HARD",
                    "gate": "G0.0",
                    "detail": f"orphan primary_map without company json: {len(missing_json)}",
                    "extra": {"companies": missing_json[:20]},
                }
            )

    readable_maps = 0
    for path in map_files:
        company = path.name[: -len(".primary_map.json")]
        if path.is_symlink():
            reason = _is_circular_or_broken_symlink(path) or "symlink_not_allowed"
            findings.append(
                {
                    "severity": "HARD",
                    "gate": "G0.0",
                    "company": company,
                    "detail": f"primary_map must be a real file ({reason})",
                }
            )
            continue
        try:
            raw = path.read_text(encoding="utf-8")
        except OSError as exc:
            findings.append(
                {
                    "severity": "HARD",
                    "gate": "G0.0",
                    "company": company,
                    "detail": f"primary_map unreadable: {exc}",
                }
            )
            continue
        if not raw.strip():
            findings.append(
                {
                    "severity": "HARD",
                    "gate": "G0.0",
                    "company": company,
                    "detail": "primary_map empty",
                }
            )
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            findings.append(
                {
                    "severity": "HARD",
                    "gate": "G0.0",
                    "company": company,
                    "detail": f"primary_map invalid JSON: {exc}",
                }
            )
            continue
        if not isinstance(payload, dict) or not payload:
            findings.append(
                {
                    "severity": "HARD",
                    "gate": "G0.0",
                    "company": company,
                    "detail": "primary_map must be a non-empty object",
                }
            )
            continue
        readable_maps += 1

    for path in company_files:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            findings.append(
                {
                    "severity": "HARD",
                    "gate": "G0.0",
                    "company": path.stem,
                    "detail": f"company json unreadable: {exc}",
                }
            )
            continue
        if not isinstance(payload, list):
            findings.append(
                {
                    "severity": "HARD",
                    "gate": "G0.0",
                    "company": path.stem,
                    "detail": "company json is not a list",
                }
            )

    hard = [f for f in findings if f["severity"] == "HARD"]
    return {
        "cache_dir": str(cache),
        "companies": len(company_files),
        "primary_maps": len(map_files),
        "readable_primary_maps": readable_maps,
        "status": "GREEN" if not hard else "RED",
        "hard_count": len(hard),
        "findings": findings[:50],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Check AI cache primary_map integrity")
    ap.add_argument(
        "--cache-dir",
        default="/data/scraping/datasets/cto_accelerator/ai_cache_v5_parsed",
    )
    ap.add_argument(
        "--out",
        default="/data/scraping/datasets/cto_accelerator/cache_integrity_wave0.json",
    )
    args = ap.parse_args()
    cache = Path(args.cache_dir)
    if not cache.is_dir():
        print(json.dumps({"status": "RED", "detail": f"missing cache dir {cache}"}))
        return 1
    report = check_cache(cache)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))
    summary = {
        "cache_dir": report["cache_dir"],
        "companies": report["companies"],
        "primary_maps": report["primary_maps"],
        "readable_primary_maps": report["readable_primary_maps"],
        "status": report["status"],
        "hard_count": report["hard_count"],
        "out": str(out),
    }
    print(json.dumps(summary, indent=2))
    if report["findings"]:
        for f in report["findings"][:15]:
            print(f"HARD {f.get('gate')} {f.get('company', '*')}: {f['detail']}")
    return 0 if report["status"] == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
