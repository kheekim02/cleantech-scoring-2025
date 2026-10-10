#!/usr/bin/env python3
"""Independent citation/rationale audit for ai_cache_v5_parsed.

Defines gates in docs/CITATION_RATIONALE_AUDIT_GATES.md, then scores the cohort
against them — including cross-company duplicate citation/rationale detection.

This is intentionally separate from scripts/audit_v5_parsed.py.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Allow running from repo root or scripts/
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.scorer.schemas import (  # noqa: E402
    is_engineered_rationale,
    is_entity_short_cite,
    is_junk_micro_citation,
    is_negative_citation,
    is_scaffolding_citation,
    match_citation_to_text,
    normalize_text,
)

CLAIM_RE = re.compile(r"\bSDG\s*\d+\b|\$\s?\d[\d,]*|\b\d+(?:\.\d+)?\s*%", re.IGNORECASE)
ABSENCE_RE = re.compile(
    r"(does\s+not\s+(?:state|mention|provide|include|contain|specify)|"
    r"no\s+(?:mention|evidence|information|discussion)|"
    r"not\s+(?:explicitly\s+)?(?:stated|mentioned|provided)|"
    r"absent|missing\s+from\s+the\s+document)",
    re.IGNORECASE,
)
GENERIC_RATIONALE_PHRASES = [
    "lacks concrete evidence",
    "insufficient information",
    "insufficient evidence",
    "the document provides a clear",
    "the document clearly articulates",
    "based on the provided information",
    "as stated in the document",
    "meets the criteria",
    "does not meet the criteria",
    "no relevant information was found",
    "unable to determine",
    "the startup demonstrates a strong",
]
COMPANY_HINT_RE = re.compile(
    r"\b(?:customer|segment|competitor|revenue|margin|tam|sam|som|pilot|"
    r"patent|partner|channel|cac|ltv|arr|mrr|sdg|kwh|mw|gw|ammonia|"
    r"battery|carbon|solar|grid)\b",
    re.IGNORECASE,
)


@dataclass
class Finding:
    severity: str  # HARD | SOFT
    gate: str
    company: str
    q_id: str
    detail: str
    extra: dict[str, Any] = field(default_factory=dict)


def word_count(text: str | None) -> int:
    if not text:
        return 0
    return len(re.findall(r"[A-Za-z0-9]+", text))


def tokenize(text: str | None) -> set[str]:
    return set(normalize_text(text).split()) if text else set()


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def allowed_scores(question: dict[str, Any] | None) -> set[float]:
    if question:
        vals = []
        for option in question.get("options") or []:
            raw = option.get("val") if isinstance(option, dict) else option
            if raw is not None:
                vals.append(round(float(raw), 2))
        if vals:
            return set(vals)
    return {0.0, 0.25, 0.5, 0.75, 1.0}


def load_questions(rubric: list[dict[str, Any]] | None) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for q in rubric or []:
        qid = q.get("new_q_id") or q.get("q_id")
        if qid:
            out[str(qid)] = q
    return out


def cat_for(qid: str, question: dict[str, Any] | None) -> str:
    if question and question.get("cat_code"):
        return str(question["cat_code"])
    return qid.split("_")[0] if qid else "?"


def is_zero(score: Any) -> bool:
    return score is not None and round(float(score), 2) == 0.0


def is_true_negative_record(record: dict[str, Any]) -> bool:
    """Null or zero-score with no citation — allowed soft uniqueness exemptions."""
    score = record.get("predicted_val")
    cite = record.get("citation")
    has_cite = bool(cite and str(cite).strip())
    if score is None and not has_cite:
        return True
    if is_zero(score) and not has_cite:
        return True
    return False


def is_absence_rationale(rationale: str | None) -> bool:
    if not rationale or not str(rationale).strip():
        return False
    return bool(ABSENCE_RE.search(str(rationale)))


def has_company_specific_content(rationale: str) -> bool:
    """True if rationale has a proper-ish noun, number, or domain hint beyond generics."""
    if not rationale.strip():
        return False
    if re.search(r"\d", rationale):
        return True
    if re.search(r"\b[A-Z][a-zA-Z]{2,}\b", rationale):  # capitalized token
        return True
    if COMPANY_HINT_RE.search(rationale):
        return True
    # quoted fragment
    if '"' in rationale or "'" in rationale or "“" in rationale:
        return True
    return False


def audit_record(
    company: str,
    record: dict[str, Any],
    primary_by_cat: dict[str, str],
    questions: dict[str, dict[str, Any]],
) -> list[Finding]:
    findings: list[Finding] = []
    qid = str(record.get("q_id") or "?")
    question = questions.get(qid)
    cat = cat_for(qid, question)
    score = record.get("predicted_val")
    confidence = record.get("confidence")
    citation = record.get("citation")
    rationale = record.get("rationale") or ""
    primary = primary_by_cat.get(cat) or ""

    # G0
    if score is not None and round(float(score), 2) not in allowed_scores(question):
        findings.append(Finding("HARD", "G0.1", company, qid, f"score {score} not in allowed options"))
    if confidence is None or not (0.0 <= float(confidence) <= 1.0):
        findings.append(Finding("HARD", "G0.2", company, qid, f"confidence {confidence} out of range"))
    if score is not None and not str(rationale).strip():
        findings.append(Finding("HARD", "G0.3", company, qid, "rationale missing"))
    if score is not None and not is_zero(score) and not (citation and str(citation).strip()):
        findings.append(Finding("HARD", "G0.4", company, qid, "non-zero score without citation"))

    # Engineered pipeline strings persisted as rationales are always HARD.
    if is_engineered_rationale(rationale):
        findings.append(
            Finding("HARD", "G2.5", company, qid, "engineered pipeline rationale string")
        )

    # G1 citation
    if citation and str(citation).strip():
        cite = str(citation)
        if is_scaffolding_citation(cite):
            findings.append(Finding("HARD", "G1.2", company, qid, "scaffolding citation"))
        if not match_citation_to_text(cite, primary):
            findings.append(Finding("HARD", "G1.1", company, qid, "citation not verbatim in primary markdown"))
        if not is_zero(score) and is_negative_citation(cite):
            findings.append(Finding("HARD", "G1.3", company, qid, "meta/negative citation on non-zero score"))
        wc = word_count(cite)
        # Short non-zero cites: SOFT only for grounded entity-like names; junk is HARD.
        if not is_zero(score) and wc < 3:
            if is_junk_micro_citation(cite):
                findings.append(
                    Finding("HARD", "G1.4", company, qid, f"junk micro-citation on non-zero ({cite!r})")
                )
            elif wc >= 1 and is_entity_short_cite(cite) and match_citation_to_text(cite, primary):
                findings.append(
                    Finding(
                        "SOFT",
                        "G1.4",
                        company,
                        qid,
                        f"short grounded proper-name cite ({wc} words)",
                    )
                )
            else:
                findings.append(Finding("HARD", "G1.4", company, qid, f"citation too short ({wc} words) for non-zero"))
        elif wc and (wc < 8 or wc > 80):
            findings.append(Finding("SOFT", "G1.4", company, qid, f"citation length suboptimal ({wc} words)"))
        if wc > 120:
            findings.append(Finding("SOFT", "G1.4", company, qid, f"citation essay-length ({wc} words)"))

    # G2 rationale
    if rationale.strip():
        rw = word_count(rationale)
        if rw < 8:
            findings.append(Finding("HARD", "G2.1", company, qid, f"rationale too short ({rw} words)"))
        elif rw < 20 or rw > 120:
            findings.append(Finding("SOFT", "G2.1", company, qid, f"rationale length suboptimal ({rw} words)"))
        if rw > 200:
            findings.append(Finding("SOFT", "G2.1", company, qid, f"rationale wall-of-text ({rw} words)"))

        if not has_company_specific_content(rationale):
            findings.append(
                Finding("SOFT", "G2.2", company, qid, "rationale lacks company-specific tokens/numbers")
            )

        if ABSENCE_RE.search(rationale) and score is not None and round(float(score), 2) >= 0.5:
            findings.append(
                Finding(
                    "HARD",
                    "G2.3",
                    company,
                    qid,
                    f"absence language with score {score}",
                )
            )

        hay = (primary + " " + (citation or "")).lower().replace(" ", "")
        for claim in CLAIM_RE.findall(rationale):
            token = claim.lower().replace(" ", "")
            if token not in hay:
                findings.append(
                    Finding("HARD", "G2.4", company, qid, f"unsupported claim {claim!r} in rationale")
                )

        norm_r = " ".join(rationale.lower().split())
        for phrase in GENERIC_RATIONALE_PHRASES:
            if phrase in norm_r and not has_company_specific_content(rationale):
                findings.append(
                    Finding("SOFT", "G2.5", company, qid, f"generic rationale phrase: {phrase!r}")
                )
                break
            # "does not meet the criteria" alone is soft even with some specificity
            if phrase == "does not meet the criteria" and phrase in norm_r and rw < 25:
                findings.append(
                    Finding("SOFT", "G2.5", company, qid, "thin generic fail rationale")
                )

    return findings


def audit_clones(
    index: dict[str, list[tuple[str, str]]],
    *,
    soft: bool = False,
) -> list[Finding]:
    """index: key -> list of (company, text) for exact clone detection.

    soft=True emits SOFT G3.2 findings (true-negative absence clones).
    soft=False emits HARD G3.1/G3.2 findings (non-zero or engineered clones).
    """
    findings: list[Finding] = []
    for key, rows in index.items():
        by_norm: dict[str, list[str]] = defaultdict(list)
        for company, text in rows:
            n = normalize_text(text)
            if len(n) < 12:
                continue
            by_norm[n].append(company)
        for n, companies in by_norm.items():
            uniq = sorted(set(companies))
            if len(uniq) >= 2:
                if key.startswith("cite:"):
                    gate = "G3.1"
                    severity = "HARD"
                else:
                    gate = "G3.2"
                    severity = "SOFT" if soft else "HARD"
                qid = key.split(":", 1)[1]
                findings.append(
                    Finding(
                        severity,
                        gate,
                        ",".join(uniq[:8]),
                        qid,
                        f"exact clone across {len(uniq)} companies",
                        extra={"companies": uniq, "norm_preview": n[:160]},
                    )
                )
    return findings


def audit_near_dup_rationales(
    by_qid: dict[str, list[tuple[str, str]]],
    threshold: float = 0.92,
    *,
    soft_only: bool = False,
) -> list[Finding]:
    findings: list[Finding] = []
    for qid, rows in by_qid.items():
        # Deduplicate company first text
        items = []
        seen = set()
        for company, text in rows:
            if company in seen:
                continue
            seen.add(company)
            toks = tokenize(text)
            if len(toks) < 12:
                continue
            items.append((company, toks, text))
        for i in range(len(items)):
            for j in range(i + 1, len(items)):
                c1, t1, raw1 = items[i]
                c2, t2, raw2 = items[j]
                sim = jaccard(t1, t2)
                if sim >= threshold and normalize_text(raw1) != normalize_text(raw2):
                    findings.append(
                        Finding(
                            "SOFT",
                            "G3.3",
                            f"{c1},{c2}",
                            qid,
                            f"near-duplicate rationale jaccard={sim:.3f}",
                            extra={"companies": [c1, c2], "preview_a": raw1[:120], "preview_b": raw2[:120]},
                        )
                    )
    return findings


def audit_global_cite_templates(
    cite_to_companies: dict[str, set[str]],
    min_companies: int = 5,
) -> list[Finding]:
    findings: list[Finding] = []
    for n, companies in cite_to_companies.items():
        if len(n) < 20:
            continue
        if len(companies) >= min_companies:
            findings.append(
                Finding(
                    "SOFT",
                    "G3.4",
                    ",".join(sorted(companies)[:8]),
                    "*",
                    f"global citation template in {len(companies)} companies",
                    extra={"companies": sorted(companies), "norm_preview": n[:160]},
                )
            )
    return findings


def main() -> int:
    ap = argparse.ArgumentParser(description="Independent citation/rationale cohort audit")
    ap.add_argument(
        "--cache-dir",
        default="/data/scraping/datasets/cto_accelerator/ai_cache_v5_parsed",
    )
    ap.add_argument("--rubric", default=str(ROOT / "master_282_rubric.json"))
    ap.add_argument(
        "--out",
        default="/data/scraping/datasets/cto_accelerator/citation_independent_audit.json",
    )
    ap.add_argument("--limit-companies", type=int, default=0, help="0 = all")
    args = ap.parse_args()

    cache = Path(args.cache_dir)
    rubric_path = Path(args.rubric)
    rubric = json.loads(rubric_path.read_text()) if rubric_path.is_file() else None
    questions = load_questions(rubric)

    company_files = sorted(
        p for p in cache.glob("*.json") if not p.name.endswith(".primary_map.json")
    )
    if args.limit_companies:
        company_files = company_files[: args.limit_companies]

    all_findings: list[Finding] = []
    cite_index: dict[str, list[tuple[str, str]]] = defaultdict(list)
    # HARD rationale clones: non-zero scores OR engineered strings
    rat_hard_index: dict[str, list[tuple[str, str]]] = defaultdict(list)
    # SOFT rationale clones: true-negative absence statements
    rat_soft_index: dict[str, list[tuple[str, str]]] = defaultdict(list)
    rat_by_qid_hard: dict[str, list[tuple[str, str]]] = defaultdict(list)
    rat_by_qid_soft: dict[str, list[tuple[str, str]]] = defaultdict(list)
    cite_global: dict[str, set[str]] = defaultdict(set)
    stats = {
        "companies": 0,
        "records": 0,
        "cited": 0,
        "nonzero": 0,
        "zero": 0,
    }

    for path in company_files:
        company = path.stem
        map_path = path.with_name(f"{company}.primary_map.json")
        if not map_path.is_file():
            all_findings.append(
                Finding("HARD", "G0.0", company, "*", f"missing primary_map {map_path.name}")
            )
            continue
        primary_by_cat = json.loads(map_path.read_text())
        records = json.loads(path.read_text())
        if not isinstance(records, list):
            all_findings.append(Finding("HARD", "G0.0", company, "*", "extraction is not a list"))
            continue
        stats["companies"] += 1
        for rec in records:
            stats["records"] += 1
            score = rec.get("predicted_val")
            if score is not None and is_zero(score):
                stats["zero"] += 1
            elif score is not None:
                stats["nonzero"] += 1
            cite = rec.get("citation")
            qid = str(rec.get("q_id") or "?")
            # Citation clones HARD when non-zero OR scaffolding (narrow cross-score template catch).
            if cite and str(cite).strip():
                stats["cited"] += 1
                cite_global[normalize_text(str(cite))].add(company)
                scaff = is_scaffolding_citation(str(cite))
                nonzero = score is not None and not is_zero(score)
                if scaff or nonzero:
                    cite_index[f"cite:{qid}"].append((company, str(cite)))
            rationale = rec.get("rationale") or ""
            if rationale.strip():
                engineered = is_engineered_rationale(rationale)
                nonzero = score is not None and not is_zero(score)
                # HARD uniqueness: non-zero scores or engineered pipeline strings only.
                # Zero-score / null-score rationales (true negatives) are SOFT clones.
                if engineered or nonzero:
                    rat_hard_index[f"rat:{qid}"].append((company, rationale))
                    rat_by_qid_hard[qid].append((company, rationale))
                else:
                    rat_soft_index[f"rat:{qid}"].append((company, rationale))
                    rat_by_qid_soft[qid].append((company, rationale))
            all_findings.extend(audit_record(company, rec, primary_by_cat, questions))

    all_findings.extend(audit_clones(cite_index))
    all_findings.extend(audit_clones(rat_hard_index, soft=False))
    all_findings.extend(audit_clones(rat_soft_index, soft=True))
    all_findings.extend(audit_near_dup_rationales(rat_by_qid_hard))
    all_findings.extend(audit_near_dup_rationales(rat_by_qid_soft))
    all_findings.extend(audit_global_cite_templates(cite_global))

    hard = [f for f in all_findings if f.severity == "HARD"]
    soft = [f for f in all_findings if f.severity == "SOFT"]

    by_gate: dict[str, int] = defaultdict(int)
    for f in all_findings:
        by_gate[f.gate] += 1

    # Top clone clusters for report readability
    clone_cites = [f for f in hard if f.gate == "G3.1"]
    clone_rats = [f for f in hard if f.gate == "G3.2"]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gates_doc": "docs/CITATION_RATIONALE_AUDIT_GATES.md",
        "cache_dir": str(cache),
        "stats": stats,
        "cohort_status": "RED" if hard else "GREEN",
        "hard_count": len(hard),
        "soft_count": len(soft),
        "by_gate": dict(sorted(by_gate.items())),
        "clone_citation_clusters": len(clone_cites),
        "clone_rationale_clusters": len(clone_rats),
        "hard_samples": [asdict(f) for f in hard[:80]],
        "soft_samples": [asdict(f) for f in soft[:80]],
        "top_citation_clones": [asdict(f) for f in sorted(clone_cites, key=lambda x: -len(x.extra.get("companies", [])))[:25]],
        "top_rationale_clones": [asdict(f) for f in sorted(clone_rats, key=lambda x: -len(x.extra.get("companies", [])))[:25]],
    }

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2))

    print(json.dumps({
        "cohort_status": report["cohort_status"],
        "companies": stats["companies"],
        "records": stats["records"],
        "hard": len(hard),
        "soft": len(soft),
        "by_gate": report["by_gate"],
        "clone_citation_clusters": len(clone_cites),
        "clone_rationale_clusters": len(clone_rats),
        "out": str(out),
    }, indent=2))

    # Dense hard preview
    for f in hard[:30]:
        print(f"HARD {f.gate} {f.company} {f.q_id}: {f.detail}")

    return 1 if hard else 0


if __name__ == "__main__":
    raise SystemExit(main())
