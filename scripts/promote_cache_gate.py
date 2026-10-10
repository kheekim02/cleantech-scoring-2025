#!/usr/bin/env python3
"""Promote an AI cache directory only after integrity + audit gates pass.

Gate order (all required GREEN/PASS before --apply):
  1. check_cache_integrity  — refuse any *.primary_map.json symlink
  2. audit_citations_independent — HARD must be 0
  3. cohort audit_v5_parsed grounding — every company PASS

Atomic promote on --apply:
  live → live_pre_promote_<UTC>
  candidate → live
  optional: leave a symlink at candidate path pointing at live (real maps stay files)

Never pushes to Supabase. Interface remains human-only; ops SoR is the cache.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.audit_v5_parsed import audit_parsed_records  # noqa: E402
from scripts.check_cache_integrity import check_cache  # noqa: E402


DEFAULT_LIVE = "/data/scraping/datasets/cto_accelerator/ai_cache_v5_parsed"
DEFAULT_RUBRIC = "/data/scraping/datasets/cto_accelerator/master_282_rubric.json"
SCRIPTS = Path(__file__).resolve().parent


def _utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def count_symlink_maps(cache: Path) -> list[str]:
    bad: list[str] = []
    for path in sorted(cache.glob("*.primary_map.json")):
        if path.is_symlink():
            bad.append(path.name)
    return bad


def run_integrity(cache: Path) -> dict[str, Any]:
    report = check_cache(cache)
    symlink_maps = count_symlink_maps(cache)
    report["symlink_primary_maps"] = symlink_maps
    if symlink_maps:
        report["status"] = "RED"
        report["hard_count"] = int(report.get("hard_count") or 0) + len(symlink_maps)
        report.setdefault("findings", []).append(
            {
                "severity": "HARD",
                "gate": "G0.0",
                "detail": f"{len(symlink_maps)} primary_map symlinks (promote refuses)",
                "extra": {"files": symlink_maps[:20]},
            }
        )
    return report


def run_independent(
    cache: Path,
    rubric: Path,
    out: Path,
    python: str,
) -> dict[str, Any]:
    cmd = [
        python,
        str(SCRIPTS / "audit_citations_independent.py"),
        "--cache-dir",
        str(cache),
        "--rubric",
        str(rubric),
        "--out",
        str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(ROOT))
    summary: dict[str, Any] = {"returncode": proc.returncode, "stdout": proc.stdout[-2000:]}
    if out.is_file():
        payload = json.loads(out.read_text())
        summary["cohort_status"] = payload.get("cohort_status")
        summary["hard_count"] = payload.get("hard_count")
        summary["soft_count"] = payload.get("soft_count")
        summary["by_gate"] = payload.get("by_gate")
    else:
        summary["cohort_status"] = "RED"
        summary["hard_count"] = None
        summary["stderr"] = proc.stderr[-2000:]
    return summary


def run_v5_grounding(cache: Path, rubric: Path) -> dict[str, Any]:
    """Cohort wrapper around audit_parsed_records (same checks as audit_v5_parsed CLI).

    Rows with structured error_code withholds are skipped so operational withholds
    do not fail the grounding gate.
    """
    questions = json.loads(rubric.read_text()) if rubric.is_file() else []
    ok = 0
    fail = 0
    failures: list[dict[str, Any]] = []
    for path in sorted(cache.glob("*.json")):
        if path.name.endswith(".primary_map.json"):
            continue
        company = path.stem
        map_path = cache / f"{company}.primary_map.json"
        if not map_path.is_file() or map_path.is_symlink():
            fail += 1
            failures.append({"company": company, "detail": "missing_or_symlink_primary_map"})
            continue
        try:
            primary = json.loads(map_path.read_text())
            records = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError) as exc:
            fail += 1
            failures.append({"company": company, "detail": str(exc)})
            continue
        if not isinstance(records, list):
            fail += 1
            failures.append({"company": company, "detail": "extraction_not_list"})
            continue
        scored = [r for r in records if not r.get("error_code")]
        findings = audit_parsed_records(scored, primary, questions)
        if findings:
            fail += 1
            failures.append(
                {
                    "company": company,
                    "findings": [
                        f"{f.get('check')}:{(f.get('detail') or '')[:120]}" for f in findings[:5]
                    ],
                }
            )
        else:
            ok += 1
    return {
        "ok": ok,
        "fail": fail,
        "status": "PASS" if fail == 0 else "FAIL",
        "failures": failures[:20],
    }


def gates_green(integrity: dict, independent: dict, grounding: dict) -> bool:
    if integrity.get("status") != "GREEN":
        return False
    if integrity.get("symlink_primary_maps"):
        return False
    if independent.get("cohort_status") != "GREEN":
        return False
    if int(independent.get("hard_count") or 0) != 0:
        return False
    if grounding.get("status") != "PASS":
        return False
    return True


def atomic_promote(
    candidate: Path,
    live: Path,
    backup_root: Path,
    leave_candidate_symlink: bool = True,
) -> dict[str, Any]:
    """Rename live→backup, candidate→live. Maps must already be real files."""
    stamp = _utc_stamp()
    backup = backup_root / f"{live.name}_pre_promote_{stamp}"
    if backup.exists():
        raise FileExistsError(f"backup already exists: {backup}")
    if not candidate.is_dir():
        raise FileNotFoundError(f"candidate missing: {candidate}")
    # Final symlink refusal immediately before rename.
    bad = count_symlink_maps(candidate)
    if bad:
        raise RuntimeError(f"refuse promote: symlink primary_maps={bad[:5]}")

    live_existed = live.exists() or live.is_symlink()
    if live_existed:
        live.rename(backup)
    candidate.rename(live)
    if leave_candidate_symlink and not candidate.exists():
        os.symlink(live, candidate)

    return {
        "live": str(live),
        "backup": str(backup) if live_existed else None,
        "candidate_symlink": str(candidate) if leave_candidate_symlink else None,
        "promoted_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Promote AI cache only after gates pass")
    ap.add_argument(
        "--candidate",
        default="",
        help="Cache dir to validate/promote (default: --live for check-only)",
    )
    ap.add_argument("--live", default=DEFAULT_LIVE)
    ap.add_argument(
        "--backup-root",
        default="/data/scraping/datasets/cto_accelerator",
        help="Directory for live_pre_promote_<UTC> backups",
    )
    ap.add_argument("--rubric", default=DEFAULT_RUBRIC)
    ap.add_argument(
        "--out",
        default="/data/scraping/datasets/cto_accelerator/promote_gate_report.json",
    )
    ap.add_argument(
        "--apply",
        action="store_true",
        help="Atomically promote candidate→live after GREEN gates",
    )
    ap.add_argument(
        "--check-only",
        action="store_true",
        help="Run gates only (default when --apply not set)",
    )
    ap.add_argument(
        "--no-candidate-symlink",
        action="store_true",
        help="Do not recreate candidate path as symlink to live after promote",
    )
    ap.add_argument(
        "--allow-supabase",
        action="store_true",
        help="IGNORED/REFUSED — Supabase push is never performed by this gate",
    )
    ap.add_argument("--python", default=sys.executable)
    args = ap.parse_args()

    if args.allow_supabase:
        print(
            json.dumps(
                {
                    "status": "RED",
                    "detail": "Supabase push refused by promote_cache_gate (interface human-only)",
                }
            )
        )
        return 2

    live = Path(args.live)
    candidate = Path(args.candidate) if args.candidate else live
    rubric = Path(args.rubric)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    stamp = _utc_stamp()

    if not candidate.is_dir():
        print(json.dumps({"status": "RED", "detail": f"candidate missing: {candidate}"}))
        return 1

    integrity = run_integrity(candidate)
    indep_out = out.parent / f"citation_independent_audit_promote_{stamp}.json"
    independent = run_independent(candidate, rubric, indep_out, args.python)
    grounding = run_v5_grounding(candidate, rubric)
    green = gates_green(integrity, independent, grounding)

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": "apply" if args.apply else "check_only",
        "candidate": str(candidate),
        "live": str(live),
        "integrity": {
            "status": integrity.get("status"),
            "hard_count": integrity.get("hard_count"),
            "readable_primary_maps": integrity.get("readable_primary_maps"),
            "symlink_primary_maps": integrity.get("symlink_primary_maps"),
        },
        "independent": {
            "status": independent.get("cohort_status"),
            "hard_count": independent.get("hard_count"),
            "soft_count": independent.get("soft_count"),
            "out": str(indep_out),
        },
        "v5_grounding": grounding,
        "gates_green": green,
        "supabase_push": "REFUSED_not_in_interface",
        "promote": None,
    }

    if args.apply:
        if candidate.resolve() == live.resolve():
            report["status"] = "RED"
            report["detail"] = "refuse --apply when candidate == live (nothing to promote)"
            out.write_text(json.dumps(report, indent=2))
            print(json.dumps({"status": "RED", "detail": report["detail"], "out": str(out)}))
            return 1
        if not green:
            report["status"] = "RED"
            report["detail"] = "gates not GREEN; promote refused"
            out.write_text(json.dumps(report, indent=2))
            print(json.dumps({"status": "RED", "gates_green": False, "out": str(out)}))
            return 1
        try:
            report["promote"] = atomic_promote(
                candidate,
                live,
                Path(args.backup_root),
                leave_candidate_symlink=not args.no_candidate_symlink,
            )
            # Post-promote integrity on live
            post = run_integrity(live)
            report["post_promote_integrity"] = {
                "status": post.get("status"),
                "readable_primary_maps": post.get("readable_primary_maps"),
                "symlink_primary_maps": post.get("symlink_primary_maps"),
            }
            if post.get("status") != "GREEN" or post.get("symlink_primary_maps"):
                report["status"] = "RED"
                report["detail"] = "post-promote integrity failed"
                out.write_text(json.dumps(report, indent=2))
                print(json.dumps({"status": "RED", "detail": report["detail"], "out": str(out)}))
                return 1
            report["status"] = "GREEN"
        except Exception as exc:
            report["status"] = "RED"
            report["detail"] = f"promote failed: {exc}"
            out.write_text(json.dumps(report, indent=2))
            print(json.dumps({"status": "RED", "detail": report["detail"], "out": str(out)}))
            return 1
    else:
        report["status"] = "GREEN" if green else "RED"

    out.write_text(json.dumps(report, indent=2))
    print(
        json.dumps(
            {
                "status": report["status"],
                "gates_green": green,
                "integrity": report["integrity"]["status"],
                "independent_hard": report["independent"]["hard_count"],
                "v5_grounding": grounding.get("status"),
                "supabase_push": report["supabase_push"],
                "out": str(out),
            }
        )
    )
    return 0 if report["status"] == "GREEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
