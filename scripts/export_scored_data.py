"""CleanTech Open 2025 Diligence Engine - Scored Data Exporter.

Exports all judge scores and qualitative justifications from the Supabase PostgreSQL
database to structured CSV or JSON files.
"""
import os
import csv
import json
import argparse
import psycopg2


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
    """Fetch human reviews from Supabase and export to CSV or JSON."""
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
            hr.updated_at
        FROM human_reviews hr
        LEFT JOIN startup_extractions se ON hr.startup_id = se.startup_id
        WHERE (%s IS NULL OR hr.startup_id = %s)
          AND (%s IS NULL OR hr.judge_id = %s)
        ORDER BY company_name ASC, hr.judge_id ASC, hr.question_id ASC;
    """
    cur.execute(query, (startup_id, startup_id, judge_id, judge_id))
    rows = cur.fetchall()
    cur.close()
    conn.close()

    print(f"Retrieved {len(rows)} scored records from database.")

    if output_format.lower() == "json":
        data = [
            {
                "startup_id": r[0],
                "company_name": r[1],
                "judge_id": r[2],
                "question_id": r[3],
                "score_value": float(r[4]) if r[4] is not None else None,
                "justification": r[5],
                "updated_at": r[6].isoformat() if r[6] else None,
            }
            for r in rows
        ]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    else:
        headers = [
            "Startup ID",
            "Company Name",
            "Judge ID",
            "Question ID",
            "Score",
            "Justification",
            "Updated At",
        ]
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for r in rows:
                writer.writerow([
                    r[0],
                    r[1],
                    r[2],
                    r[3],
                    r[4] if r[4] is not None else "",
                    r[5] if r[5] is not None else "",
                    r[6].isoformat() if r[6] else "",
                ])

    print(f"Successfully exported {len(rows)} records to: {output_path}")
    return len(rows)


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
