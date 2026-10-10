#!/bin/bash
# Full 92-company parsed-markdown scoring into ai_cache_v5_parsed.
# Resume-safe: existing complete caches are skipped by the extractor.
# Designed to run under tmux/nohup; survives SSH disconnect.
set -u
cd /data/scraping
export PYTHONPATH=/data/scraping
export PATH="/data/scraping/venv/bin:$PATH"

PARSED=/data/scraping/datasets/cto_accelerator/parsed_clean_v4
CACHE=/data/scraping/datasets/cto_accelerator/ai_cache_v5_parsed
RUBRIC=/data/scraping/datasets/cto_accelerator/master_282_rubric.json
ALLOW=/data/scraping/datasets/cto_accelerator/active_startup_allowlist.json
LOG=/data/scraping/logs/phase5_cohort92_parsed.log
PROGRESS=/data/scraping/logs/phase5_cohort92_progress.json
SUMMARY=/data/scraping/logs/phase5_cohort92_summary.json
PIDFILE=/data/scraping/logs/phase5_cohort92.pid

mkdir -p /data/scraping/logs "$CACHE"
echo $$ > "$PIDFILE"

# Append-only log; keep prior runs if restarted.
exec >>"$LOG" 2>&1

echo "========================================"
echo "COHORT_START $(date -Iseconds)"
echo "PID=$$ HOST=$(hostname) PWD=$(pwd)"
echo "CACHE=$CACHE"
echo "ALLOW=$ALLOW"

# Quick endpoint check
if ! curl -sf -o /dev/null http://127.0.0.1:11435/api/tags; then
  echo "FATAL: Ollama endpoint http://127.0.0.1:11435 not reachable"
  exit 1
fi
echo "OLLAMA_OK"

/data/scraping/venv/bin/python3 - <<'PY'
import json, os, subprocess, sys, time
from datetime import datetime, timezone
from pathlib import Path

parsed = Path("/data/scraping/datasets/cto_accelerator/parsed_clean_v4")
cache = Path("/data/scraping/datasets/cto_accelerator/ai_cache_v5_parsed")
rubric = "/data/scraping/datasets/cto_accelerator/master_282_rubric.json"
allow_path = "/data/scraping/datasets/cto_accelerator/active_startup_allowlist.json"
progress_path = Path("/data/scraping/logs/phase5_cohort92_progress.json")
summary_path = Path("/data/scraping/logs/phase5_cohort92_summary.json")

allow = json.loads(Path(allow_path).read_text())
startups = [row["startup_id"] for row in allow["startups"]]
if len(startups) != allow.get("count"):
    raise SystemExit(f"Allowlist count mismatch: {len(startups)} != {allow.get('count')}")
print(f"ALLOWLIST_COUNT {len(startups)}", flush=True)

missing_parsed = [s for s in startups if not (parsed / s).is_dir()]
if missing_parsed:
    print(f"FATAL missing parsed dirs ({len(missing_parsed)}): {missing_parsed}", flush=True)
    sys.exit(1)


def cache_stats(startup: str) -> dict:
    extraction = cache / f"{startup}.json"
    if not extraction.is_file():
        return {"records": 0, "scored": 0, "cited": 0, "withheld": 0, "complete": False}
    records = json.loads(extraction.read_text())
    scored = sum(1 for r in records if r.get("predicted_val") is not None)
    cited = sum(1 for r in records if r.get("citation"))
    withheld = sum(1 for r in records if r.get("predicted_val") is None)
    return {
        "records": len(records),
        "scored": scored,
        "cited": cited,
        "withheld": withheld,
        "complete": len(records) >= 282,
    }


def write_progress(state: dict) -> None:
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    progress_path.write_text(json.dumps(state, indent=2) + "\n")


companies = []
failures = []
t0 = time.time()

for idx, startup in enumerate(startups, 1):
    before = cache_stats(startup)
    write_progress({
        "phase": "scoring",
        "index": idx,
        "total": len(startups),
        "current": startup,
        "elapsed_sec": round(time.time() - t0, 1),
        "completed": [c["startup_id"] for c in companies if c.get("score_ok")],
        "failures": list(failures),
        "before": before,
    })
    print(f"SCORE_START {startup} {idx}/{len(startups)} {datetime.now().astimezone().isoformat()}", flush=True)
    print(f"  cache_before records={before['records']} scored={before['scored']} complete={before['complete']}", flush=True)

    proc = subprocess.run(
        [
            "/data/scraping/venv/bin/python3",
            "scripts/14_ai_copilot_extractor_v2.py",
            "--startup", startup,
            "--sglang-url", "http://127.0.0.1:11435/v1",
            "--model", "qwen3.8:27b-32k",
            "--concurrency", "2",
            "--parsed-dir", str(parsed),
            "--cache-dir", str(cache),
            "--rubric", rubric,
            "--allowlist", allow_path,
        ],
        cwd="/data/scraping",
        env={**os.environ, "PYTHONPATH": "/data/scraping"},
    )
    after = cache_stats(startup)
    ok = proc.returncode == 0 and after["complete"]
    row = {
        "startup_id": startup,
        "score_exit": proc.returncode,
        "score_ok": ok,
        **after,
    }
    companies.append(row)
    if not ok:
        failures.append(startup)
        print(f"SCORE_FAIL {startup} exit={proc.returncode} records={after['records']}", flush=True)
    else:
        print(
            f"SCORE_DONE {startup} scored={after['scored']} cited={after['cited']} withheld={after['withheld']}",
            flush=True,
        )

print(f"SCORE_ALL_DONE {datetime.now().astimezone().isoformat()}", flush=True)
write_progress({
    "phase": "auditing",
    "index": len(startups),
    "total": len(startups),
    "current": None,
    "elapsed_sec": round(time.time() - t0, 1),
    "completed": [c["startup_id"] for c in companies if c.get("score_ok")],
    "failures": list(failures),
})

print("AUDIT_BATCH_START", flush=True)
all_ok = True
for row in companies:
    startup = row["startup_id"]
    extraction = cache / f"{startup}.json"
    primary_map = cache / f"{startup}.primary_map.json"
    if not extraction.is_file() or not primary_map.is_file():
        row.update({"audit_exit": 2, "audit_pass": False})
        all_ok = False
        print(f"AUDIT {startup} exit=2 missing_files", flush=True)
        continue
    proc = subprocess.run(
        [
            "/data/scraping/venv/bin/python3",
            "scripts/audit_v5_parsed.py",
            "--primary-map", str(primary_map),
            "--extraction", str(extraction),
            "--rubric", rubric,
        ],
        cwd="/data/scraping",
        env={**os.environ, "PYTHONPATH": "/data/scraping"},
        capture_output=True,
        text=True,
    )
    ok = proc.returncode == 0
    all_ok = all_ok and ok and row.get("score_ok", False)
    row["audit_exit"] = proc.returncode
    row["audit_pass"] = ok
    print(f"AUDIT {startup} exit={proc.returncode} scored={row['scored']} cited={row['cited']} withheld={row['withheld']}", flush=True)

summary = {
    "started_elapsed_sec": round(time.time() - t0, 1),
    "allowlist_count": len(startups),
    "scored_ok": sum(1 for c in companies if c.get("score_ok")),
    "audit_pass_count": sum(1 for c in companies if c.get("audit_pass")),
    "all_audits_pass": all_ok and not failures,
    "failures": failures,
    "companies": companies,
    "finished_at": datetime.now(timezone.utc).isoformat(),
}
summary_path.write_text(json.dumps(summary, indent=2) + "\n")
print(f"SUMMARY_WRITTEN {summary_path}", flush=True)
print(f"AUDIT_BATCH_EXIT:{0 if summary['all_audits_pass'] else 1}", flush=True)
write_progress({
    "phase": "done",
    "index": len(startups),
    "total": len(startups),
    "current": None,
    "elapsed_sec": round(time.time() - t0, 1),
    "completed": [c["startup_id"] for c in companies if c.get("score_ok")],
    "failures": list(failures),
    "all_audits_pass": summary["all_audits_pass"],
})
sys.exit(0 if summary["all_audits_pass"] else 1)
PY
EXIT=$?
echo "COHORT_END $(date -Iseconds) EXIT=$EXIT"
rm -f "$PIDFILE"
exit "$EXIT"
