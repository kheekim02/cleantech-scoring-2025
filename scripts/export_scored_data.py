"""CleanTech Open 2025 Diligence Engine - Scored Data Exporter.

Exports judge scores, qualitative justifications, and review statuses
from the Supabase PostgreSQL database to structured CSV or JSON files.
"""
import os
import csv
import json
import argparse
import psycopg2

CATEGORY_NAMES = {
    'BC': 'Business Canvas',
    'ES': 'Environmental & Social',
    'F': 'Financials',
    'IP': 'Investor Pitch',
    'IS': 'Executive Summary / Impact',
    'L': 'Legal & Governance',
    'M': 'Market & Customers',
    'PMF': 'Product Market Fit',
    'T': 'Team Targets',
    'TP': 'Tech / Product',
}


def load_rubric_map() -> dict[str, dict]:
    """Load rubric question metadata from master_282_rubric.json."""
    rubric_candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "master_282_rubric.json"),
        os.path.join(os.getcwd(), "master_282_rubric.json"),
    ]
    for p in rubric_candidates:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return {
                        (q.get("new_q_id") or q.get("q_id")): q
                        for q in data
                        if (q.get("new_q_id") or q.get("q_id"))
                    }
            except Exception as e:
                print(f"Warning: Could not read {p}: {e}")
    return {}


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
            with open(p, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("DATABASE_URL="):
                        return line.split("=", 1)[1].strip().strip("'").strip('"').replace("?pgbouncer=true", "")
    raise ValueError("DATABASE_URL not found in environment or .env")


def export_scores(
    output_path: str = "cleantech_open_scores.csv",
    output_format: str = "csv",
    startup_id: str | None = None,
    judge_id: str | None = None,
) -> int:
    """Fetch human reviews from Supabase and export to CSV or JSON with standardized columns."""
    rubric_map = load_rubric_map()
    db_url = load_db_url()
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()

    query = """
        SELECT 
            hr.startup_id,
            COALESCE(se.company_name, hr.startup_id) AS company_name,
            hr.judge_id,
            hr.question_id,
            hr.score_value,
            hr.justification,
            hr.is_flagged,
            hr.updated_at
        FROM human_reviews hr
        LEFT JOIN startup_extractions se ON hr.startup_id = se.startup_id
        WHERE hr.startup_id NOT ILIKE '%%solarpure%%'
          AND hr.judge_id NOT IN (SELECT judge_id FROM judges WHERE is_test = TRUE)
          AND (%s IS NULL OR hr.startup_id = %s)
          AND (%s IS NULL OR hr.judge_id = %s)
        ORDER BY company_name ASC, hr.judge_id ASC, hr.question_id ASC;
    """
    cur.execute(query, (startup_id, startup_id, judge_id, judge_id))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    print(f"Retrieved {len(rows)} scored records from database.")

    expanded_records = []
    for r in rows:
        sid, cname, jid, qid, score_val, just, is_flagged, updated_at = r
        matched_q = rubric_map.get(qid, {})

        cat_code = matched_q.get("cat_code") or (qid.split("_")[0] if qid else "")
        cat_name = CATEGORY_NAMES.get(cat_code, cat_code)
        q_text = matched_q.get("text", "")
        flagged_val = "Yes" if is_flagged else "No"

        expanded_records.append({
            "startup_id": sid,
            "company_name": cname,
            "judge_id": jid,
            "category_code": cat_code,
            "category_name": cat_name,
            "question_id": qid,
            "question_text": q_text,
            "score": float(score_val) if score_val is not None else None,
            "justification": just,
            "flagged_for_review": flagged_val,
            "scored_at": updated_at.isoformat() if updated_at else None,
        })

    if output_format.lower() == "json":
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(expanded_records, f, indent=2)
    else:
        headers = [
            "Startup ID",
            "Company Name",
            "Judge ID",
            "Category Code",
            "Category Name",
            "Question ID",
            "Question Text",
            "Score",
            "Justification",
            "Flagged for Review",
            "Scored At",
        ]
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for rec in expanded_records:
                writer.writerow([
                    rec["startup_id"],
                    rec["company_name"],
                    rec["judge_id"],
                    rec["category_code"],
                    rec["category_name"],
                    rec["question_id"],
                    rec["question_text"],
                    rec["score"] if rec["score"] is not None else "",
                    rec["justification"] if rec["justification"] is not None else "",
                    rec["flagged_for_review"],
                    rec["scored_at"] if rec["scored_at"] is not None else "",
                ])

    print(f"Successfully exported {len(expanded_records)} records to: {output_path}")
    return len(expanded_records)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export Scored Diligence Data from Supabase")
    parser.add_argument("--output", "-o", default="cleantech_open_scores.csv", help="Output file path")
    parser.add_argument("--format", "-f", choices=["csv", "json"], default="csv", help="Output format")
    parser.add_argument("--startup", "-s", default=None, help="Filter by specific startup ID")
    parser.add_argument("--judge", "-j", default=None, help="Filter by specific judge ID")
    args = parser.parse_args()

    export_scores(
        output_path=args.output,
        output_format=args.format,
        startup_id=args.startup,
        judge_id=args.judge,
    )
