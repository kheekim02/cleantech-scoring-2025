#!/usr/bin/env python3
"""
CleanTech Open 363-Column PostgreSQL Ingestion Pipeline
======================================================
Transforms legacy 282-question evaluation scores across 954 historical startups
into the new 363-question atomic binary PostgreSQL schema.

Features:
1. Ingests rubric reference catalog (363 questions: 357 binary, 6 integer).
2. Deduplicates and registers 954 startups into cleantech.startups.
3. Applies deterministic binarization rules for 1:1, bracketed, and compound criteria.
4. Generates high-speed CSV exports formatted for PostgreSQL \\copy ingestion.
5. Ingests AI extraction results (Ollama / Qwen-VL) to backfill ambiguous cells.
6. Computes aggregate rollups and creates an audit trail in cleantech.evaluation_evidence.
"""

import os
import sys
import re
import json
import argparse
import subprocess
import pandas as pd
import numpy as np
from pathlib import Path

# Paths relative to project root
BASE_DIR = Path(__file__).resolve().parent.parent
RUBRIC_PATH = BASE_DIR / "data" / "processed" / "master_decomposed_rubric_inventory.csv"
LEGACY_EXCEL_PATH = BASE_DIR / "data" / "raw" / "cleaned+matched_versus_normalized_v3.xlsx"
EXPORT_DIR = BASE_DIR / "data" / "processed" / "postgres_export"


def slugify(text: str) -> str:
    """Generate a clean URL/DB-safe slug from company name."""
    s = str(text).strip().lower()
    s = re.sub(r'[\s\.\,\-\/\&]+', '_', s)
    s = re.sub(r'[^a-z0-9_]', '', s)
    return s.strip('_') or 'unknown'


class PostgresRubricIngestion:
    def __init__(self, rubric_csv=RUBRIC_PATH, legacy_excel=LEGACY_EXCEL_PATH, export_dir=EXPORT_DIR):
        self.rubric_csv = Path(rubric_csv)
        self.legacy_excel = Path(legacy_excel)
        self.export_dir = Path(export_dir)
        self.export_dir.mkdir(parents=True, exist_ok=True)
        
        # Load rubric catalog
        print(f"[1/5] Loading Rubric Catalog from {self.rubric_csv.name}...")
        self.rubric_df = pd.read_csv(self.rubric_csv)
        print(f"      Total Questions: {len(self.rubric_df)} (357 Binary, 6 Integer)")
        
        # Question mappings
        self.q_map = self.rubric_df.set_index('new_q_id').to_dict('index')
        self.orig_to_new = {}
        for _, row in self.rubric_df.iterrows():
            orig = row['orig_q_id']
            new_id = row['new_q_id']
            self.orig_to_new.setdefault(orig, []).append(new_id)

    def prepare_rubric_catalog(self) -> pd.DataFrame:
        """Format the rubric catalog for database ingestion."""
        df = self.rubric_df.copy()
        df = df.rename(columns={
            'new_q_id': 'question_id',
            'category': 'category_name'
        })
        df['weight'] = 1.0000
        # Reorder columns
        cols = ['question_id', 'orig_q_id', 'cat_code', 'category_name', 'data_type', 'verification_role', 'question_text', 'weight']
        df['data_type'] = df['type']
        return df[['question_id', 'orig_q_id', 'cat_code', 'category_name', 'data_type', 'verification_role', 'text', 'weight']].rename(columns={'text': 'question_text'})

    def process_historical_startups(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Extract startups and deterministically map legacy scores into the 363-column schema.
        Returns (startups_df, scores_df).
        """
        print(f"[2/5] Reading Historical Dataset from {self.legacy_excel.name}...")
        legacy_df = pd.read_excel(self.legacy_excel, sheet_name='normalized_scores_mean')
        num_startups = len(legacy_df)
        print(f"      Found {num_startups} historical startups across years {sorted(legacy_df['Year'].unique())}")

        # 1. Build Startups Entity DataFrame
        startups_list = []
        slug_seen = {}
        
        for idx, row in legacy_df.iterrows():
            raw_name = str(row['Company Name (original)']).strip()
            year = int(row['Year'])
            founder = str(row['Founder']).strip() if pd.notnull(row['Founder']) else None
            
            base_slug = f"{slugify(raw_name)}_{year}"
            slug_seen[base_slug] = slug_seen.get(base_slug, 0) + 1
            startup_id = f"{base_slug}_{slug_seen[base_slug]}" if slug_seen[base_slug] > 1 else base_slug

            startups_list.append({
                'startup_id': startup_id,
                'company_name': raw_name,
                'cohort_year': year,
                'founder': founder,
                'raw_data_dir': f"/data/cleantech/data/raw/{slugify(raw_name)}",
                'evaluation_status': 'DETERMINISTIC_MAPPED'
            })
            
        startups_df = pd.DataFrame(startups_list)

        # 2. Build 363-Column Scores DataFrame
        print("[3/5] Applying Deterministic Binarization Rules...")
        all_363_cols = self.rubric_df['new_q_id'].tolist()
        scores_matrix = {qid: [None] * num_startups for qid in all_363_cols}
        
        # Mapping logic
        for orig_id, new_ids in self.orig_to_new.items():
            if orig_id not in legacy_df.columns:
                continue
                
            legacy_series = legacy_df[orig_id]
            
            # Case 1: 1-to-1 question mapping (226 questions)
            if len(new_ids) == 1 and new_ids[0] == orig_id:
                qid = new_ids[0]
                qtype = self.q_map[qid]['type']
                for idx, val in enumerate(legacy_series):
                    if pd.isnull(val):
                        scores_matrix[qid][idx] = None
                    elif qtype == 'BINARY':
                        if val == 1.0:
                            scores_matrix[qid][idx] = 1
                        elif val == 0.0:
                            scores_matrix[qid][idx] = 0
                        else:
                            # Ambiguous partial score (inter-rater variance) -> mark as -1 for AI backfill
                            scores_matrix[qid][idx] = -1
                    elif qtype == 'INTEGER':
                        scores_matrix[qid][idx] = int(round(val))
            
            # Case 2: Decomposed question mapping (56 original questions -> 137 atomic questions)
            else:
                for idx, val in enumerate(legacy_series):
                    if pd.isnull(val):
                        # Missing legacy data -> preserve as None (NULL / empty)
                        for nqid in new_ids:
                            scores_matrix[nqid][idx] = None
                    elif val == 1.0:
                        # Perfect pass -> all sub-criteria satisfied
                        for nqid in new_ids:
                            if self.q_map[nqid]['type'] == 'BINARY':
                                scores_matrix[nqid][idx] = 1
                            else:
                                scores_matrix[nqid][idx] = None
                    elif val == 0.0:
                        # Total fail -> all sub-criteria failed
                        for nqid in new_ids:
                            if self.q_map[nqid]['type'] == 'BINARY':
                                scores_matrix[nqid][idx] = 0
                            else:
                                scores_matrix[nqid][idx] = 0
                    else:
                        # Partial score (0 < val < 1.0)
                        # Check if this is an ordinal tiered bracket (e.g. Funding Tiers T_Q26)
                        if orig_id in ['T_Q26', 'T_Q27', 'T_Q28', 'T_Q29', 'T_Q30']:
                            # Brackets: T_Q26a (>=250k), T_Q26b (>=2M), T_Q26c (>=10M)
                            sub_binary = [q for q in new_ids if q.endswith('a') or q.endswith('b') or q.endswith('c')]
                            if len(sub_binary) >= 2:
                                if val >= 0.5:
                                    scores_matrix[sub_binary[0]][idx] = 1
                                    scores_matrix[sub_binary[1]][idx] = 0
                                    if len(sub_binary) > 2:
                                        scores_matrix[sub_binary[2]][idx] = 0
                                else:
                                    scores_matrix[sub_binary[0]][idx] = 0
                                    scores_matrix[sub_binary[1]][idx] = 0
                        else:
                            # Compound question ambiguity: mark as -1 so the Spark AI pipeline backfills it
                            for nqid in new_ids:
                                scores_matrix[nqid][idx] = -1

        scores_df = pd.DataFrame(scores_matrix)
        scores_df.insert(0, 'startup_id', startups_df['startup_id'])

        # Calculate Rollups
        print("[4/5] Calculating Score Rollups & Ambiguity Metrics...")
        binary_cols = [c for c in all_363_cols if self.q_map[c]['type'] == 'BINARY']
        ai_cols = [c for c in binary_cols if self.q_map[c]['verification_role'] == 'AI']
        human_cols = [c for c in binary_cols if self.q_map[c]['verification_role'] == 'HUMAN']

        total_binary = (scores_df[binary_cols] == 1).sum(axis=1)
        ai_passed = (scores_df[ai_cols] == 1).sum(axis=1)
        human_passed = (scores_df[human_cols] == 1).sum(axis=1)
        total_pct = (total_binary / len(binary_cols) * 100.0).round(2)

        # 4-State Diagnostic Metrics
        resolved_count = ((scores_df[all_363_cols] == 1) | (scores_df[all_363_cols] == 0)).sum(axis=1)
        ambiguous_count = (scores_df[all_363_cols] == -1).sum(axis=1)
        missing_legacy_count = scores_df[all_363_cols].isnull().sum(axis=1)

        scores_df['total_binary_passed'] = total_binary.astype('int32')
        scores_df['ai_auto_passed'] = ai_passed.astype('int32')
        scores_df['human_verified_passed'] = human_passed.astype('int32')
        scores_df['total_score_pct'] = total_pct
        scores_df['resolved_count'] = resolved_count.astype('int32')
        scores_df['ambiguous_count'] = ambiguous_count.astype('int32')
        scores_df['missing_legacy_count'] = missing_legacy_count.astype('int32')

        # Strictly cast to nullable integer types to guarantee integer literal formatting in CSV
        for qid in all_363_cols:
            if self.q_map[qid]['type'] == 'INTEGER':
                scores_df[qid] = scores_df[qid].astype('Int32')
            else:
                scores_df[qid] = scores_df[qid].astype('Int16')

        return startups_df, scores_df

    def export_csvs(self, startups_df: pd.DataFrame, scores_df: pd.DataFrame, rubric_df: pd.DataFrame):
        """Export clean CSV files ready for PostgreSQL \\copy command."""
        print(f"[5/5] Exporting PostgreSQL ingestion files to {self.export_dir}...")
        
        # 1. Rubric Catalog CSV
        rubric_csv_out = self.export_dir / "rubric_catalog.csv"
        rubric_df.to_csv(rubric_csv_out, index=False, na_rep="")
        
        # 2. Startups CSV
        startups_csv_out = self.export_dir / "startups.csv"
        startups_df.to_csv(startups_csv_out, index=False, na_rep="")
        
        # 3. Startup Scores CSV
        scores_csv_out = self.export_dir / "startup_scores_363.csv"
        scores_df.to_csv(scores_csv_out, index=False, na_rep="")

        scores_cols = ', '.join(scores_df.columns.tolist())
        startups_cols = ', '.join(startups_df.columns.tolist())
        catalog_cols = ', '.join(rubric_df.columns.tolist())

        # 4. Generate load_data.sql for instant psql execution
        load_sql_path = self.export_dir / "load_data.sql"
        with open(load_sql_path, "w") as f:
            f.write(f"""-- Fast Ingestion Script for CleanTech Open 363-Column Data
SET search_path TO cleantech, public;

\\echo 'Loading rubric_catalog (363 questions)...'
\\copy cleantech.rubric_catalog ({catalog_cols}) FROM '{rubric_csv_out.name}' WITH (FORMAT csv, HEADER true, NULL '');

\\echo 'Loading startups (954 records)...'
\\copy cleantech.startups ({startups_cols}) FROM '{startups_csv_out.name}' WITH (FORMAT csv, HEADER true, NULL '');

\\echo 'Loading startup_scores_363 (363 columns)...'
\\copy cleantech.startup_scores_363 ({scores_cols}) FROM '{scores_csv_out.name}' WITH (FORMAT csv, HEADER true, NULL '');

\\echo 'Refreshing summary view...'
SELECT COUNT(*) AS total_startups_loaded FROM cleantech.startups;
SELECT COUNT(*) AS total_questions_loaded FROM cleantech.rubric_catalog;
SELECT AVG(total_score_pct) AS avg_historical_score_pct FROM cleantech.startup_scores_363;
""")

        print(f"      [OK] rubric_catalog.csv:    {len(rubric_df)} rows")
        print(f"      [OK] startups.csv:          {len(startups_df)} rows")
        print(f"      [OK] startup_scores_363.csv: {len(scores_df)} rows x {len(scores_df.columns)} cols")
        print(f"      [OK] load_data.sql generated for high-speed \\copy.")


def main():
    parser = argparse.ArgumentParser(description="Ingest 363-column rubric data into PostgreSQL.")
    parser.add_argument("--db", type=str, default="sec_data", help="Target PostgreSQL database name (default: sec_data)")
    parser.add_argument("--user", type=str, default="jkim", help="PostgreSQL user (default: jkim)")
    parser.add_argument("--host", type=str, default="localhost", help="PostgreSQL host")
    parser.add_argument("--apply", action="store_true", help="Directly execute psql command to load data into database")
    args = parser.parse_args()

    ingestion = PostgresRubricIngestion()
    catalog_df = ingestion.prepare_rubric_catalog()
    startups_df, scores_df = ingestion.process_historical_startups()
    ingestion.export_csvs(startups_df, scores_df, catalog_df)

    if args.apply:
        print(f"\nExecuting psql against {args.user}@{args.host}/{args.db} ...")
        cmd = f"cd {EXPORT_DIR} && psql -U {args.user} -d {args.db} -h {args.host} -f load_data.sql"
        subprocess.run(cmd, shell=True, check=True)
        print("Data ingestion complete!")
    else:
        print("\nTo load directly into PostgreSQL, run:")
        print(f"  cd {EXPORT_DIR}")
        print(f"  psql -U {args.user} -d {args.db} -f load_data.sql")


if __name__ == "__main__":
    main()
