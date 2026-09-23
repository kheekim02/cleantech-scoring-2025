"""CleanTech Open 2025 Diligence Engine - Scored Data Exporter.

Exports judge scores, qualitative justifications, AI predictions, and citation provenance
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
    """Fetch human reviews from Supabase and export to CSV or JSON with expanded columns."""
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
            hr.updated_at,
            se.payload->'human_questions' AS human_questions
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
        sid, cname, jid, qid, score_val, just, updated_at, hqs_raw = r

        qs = []
        if isinstance(hqs_raw, list):
            qs = hqs_raw
        elif isinstance(hqs_raw, str):
            try:
                qs = json.loads(hqs_raw)
            except Exception:
                qs = []

        matched_q = next((q for q in qs if q.get("new_q_id") == qid or q.get("q_id") == qid), {})

        cat_code = matched_q.get("cat_code") or (qid.split("_")[0] if qid else "")
        cat_name = CATEGORY_NAMES.get(cat_code, cat_code)
        q_text = matched_q.get("text", "")
        ai_sug = matched_q.get("ai_suggestion")
        ai_conf = matched_q.get("ai_confidence")

        concordance = "N/A"
        if score_val is not None and ai_sug is not None:
            concordance = "AGREED" if abs(float(score_val) - float(ai_sug)) < 0.001 else "OVERRULED"

        source_pdf = matched_q.get("source_pdf")
        page_num = matched_q.get("page_number")
        verbatim_cit = matched_q.get("verbatim_citation")

        expanded_records.append({
            "startup_id": sid,
            "company_name": cname,
            "judge_id": jid,
            "category_code": cat_code,
            "category_name": cat_name,
            "question_id": qid,
            "question_text": q_text,
            "human_score": float(score_val) if score_val is not None else None,
            "human_justification": just,
            "ai_suggestion": float(ai_sug) if ai_sug is not None else None,
            "ai_confidence": float(ai_conf) if ai_conf is not None else None,
            "ai_concordance": concordance,
            "source_deliverable": source_pdf,
            "citation_page": page_num,
            "verbatim_citation": verbatim_cit,
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
            "Human Score",
            "Human Justification",
            "AI Suggestion",
            "AI Confidence",
            "AI Concordance",
            "Source Deliverable",
            "Citation Page",
            "Verbatim Citation",
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
                    rec["human_score"] if rec["human_score"] is not None else "",
                    rec["human_justification"] if rec["human_justification"] is not None else "",
                    rec["ai_suggestion"] if rec["ai_suggestion"] is not None else "",
                    rec["ai_confidence"] if rec["ai_confidence"] is not None else "",
                    rec["ai_concordance"],
                    rec["source_deliverable"] if rec["source_deliverable"] is not None else "",
                    rec["citation_page"] if rec["citation_page"] is not None else "",
                    rec["verbatim_citation"] if rec["verbatim_citation"] is not None else "",
                    rec["scored_at"] if rec["scored_at"] is not None else "",
                ])

    print(f"Successfully exported {len(expanded_records)} expanded records to: {output_path}")
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
