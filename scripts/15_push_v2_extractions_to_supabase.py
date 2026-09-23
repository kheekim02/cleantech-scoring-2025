"""Supabase Synchronizer for Grounded Diligence Engine v2.

Safely merges Docling + SGLang + Instructor extractions (including bounding-box
and page provenance) into Supabase PostgreSQL database while preserving human reviews.
"""
import os
import glob
import time
import json
import argparse
import psycopg2
from datetime import datetime, timezone
from pathlib import Path


def load_db_url(env_file: str = ".env") -> str:
    """Read DATABASE_URL from environment or .env file."""
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"].replace("?pgbouncer=true", "")
    candidates = [
        env_file,
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
    ]
    for p in candidates:
        if os.path.exists(p):
            with open(p, "r") as f:
                for line in f:
                    if line.startswith("DATABASE_URL="):
                        return line.split("=", 1)[1].strip().strip("'").strip('"').replace("?pgbouncer=true", "")
    raise ValueError("DATABASE_URL not found in environment or .env")


def sync_v2_to_supabase(
    v2_cache_dir: str = "data/ai_cache_v2",
    startup_target: str | None = None,
    commit: bool = False,
) -> dict[str, int]:
    """Merge v2 extractions into Supabase."""
    start_time = time.time()
    db_url = load_db_url()
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    cache_files = sorted(glob.glob(os.path.join(v2_cache_dir, "*.json")))
    ready_cache = {}
    for cf in cache_files:
        sid = Path(cf).stem
        if startup_target and sid != startup_target:
            continue
        try:
            with open(cf, "r", encoding="utf-8") as fp:
                data = json.load(fp)
                if len(data) >= 10:  # Valid extracted cache
                    ready_cache[sid] = {item["q_id"]: item for item in data}
        except Exception as e:
            print(f"Error loading {cf}: {e}")

    print(f"Loaded {len(ready_cache)} v2 cache files to sync.")
    if not ready_cache:
        print("No matching v2 cache files found to sync.")
        return {"updated": 0, "citations": 0}

    cur.execute("SELECT startup_id, company_name, payload FROM startup_extractions ORDER BY company_name ASC;")
    rows = cur.fetchall()

    updated_count = 0
    total_citations = 0

    for sid, cname, payload in rows:
        if sid not in ready_cache:
            continue

        v2_q_map = ready_cache[sid]
        qs = payload.get("human_questions", [])
        startup_cits = 0

        for q in qs:
            qid = q.get("new_q_id", q.get("q_id"))
            v2_item = v2_q_map.get(qid)
            if not v2_item:
                continue

            q["ai_suggestion"] = v2_item.get("predicted_val")
            q["ai_confidence"] = v2_item.get("confidence")
            cit = v2_item.get("citation")
            q["verbatim_citation"] = cit
            q["source_pdf"] = v2_item.get("source_pdf")
            q["page_number"] = v2_item.get("page_number")
            q.pop("bbox", None)
            q["ai_rationale"] = v2_item.get("rationale")

            if cit:
                startup_cits += 1

        total_citations += startup_cits

        if "meta" not in payload:
            payload["meta"] = {}
        payload["meta"]["v2_ready"] = True
        payload["meta"]["v2_updated_at"] = datetime.now(timezone.utc).isoformat()

        if commit:
            cur.execute(
                "UPDATE startup_extractions SET payload = %s WHERE startup_id = %s;",
                (json.dumps(payload), sid)
            )
            conn.commit()

        updated_count += 1
        status_mode = "COMMITTED" if commit else "DRY-RUN"
        print(f"[{status_mode}] [{updated_count}/{len(ready_cache)}] {cname} ({sid}): {startup_cits} citations staged")

    elapsed = time.time() - start_time
    print("\n" + "=" * 50)
    print(f"SUPABASE V2 SYNC SUMMARY ({'LIVE COMMIT' if commit else 'DRY RUN'})")
    print(f"Time Elapsed:         {elapsed:.2f}s")
    print(f"Startups Synced:      {updated_count}")
    print(f"Total Citations:      {total_citations}")
    print("=" * 50)

    cur.close()
    conn.close()
    return {"updated": updated_count, "citations": total_citations}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Push v2 Extractions with Provenance to Supabase")
    parser.add_argument("--v2-dir", default="data/ai_cache_v2", help="V2 cache directory")
    parser.add_argument("--startup", default=None, help="Specific startup ID to sync")
    parser.add_argument("--commit", action="store_true", help="Perform live UPDATE on Supabase")
    args = parser.parse_args()

    sync_v2_to_supabase(
        v2_cache_dir=args.v2_dir,
        startup_target=args.startup,
        commit=args.commit,
    )
