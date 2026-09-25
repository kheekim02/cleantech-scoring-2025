import os
import glob
import time
import json
import psycopg2

import re
from datetime import datetime, timezone

start_time = time.time()

# 1. Database Connection
with open('.env') as f:
    for line in f:
        if line.startswith('DATABASE_URL='):
            db_url = line.split('=', 1)[1].strip().strip("'").replace('?pgbouncer=true', '')

conn = psycopg2.connect(db_url)
cur = conn.cursor()

import sys

raw_base = '/Users/geoffrey/Global_Key_Advisors/Migrating_Automated_Startup_Scraper/data/raw'
clean_cache_dir = sys.argv[1] if len(sys.argv) > 1 else 'data/ai_cache_v3_strict'

def normalize(s):
    if not s: return ""
    s = re.sub(r'[•●○\u200b\xa0\r\n\t]+', ' ', s)
    s = re.sub(r'[^a-zA-Z0-9]+', ' ', s)
    return ' '.join(s.lower().split())

negative_patterns = [
    r'does not contain', r'does not mention', r'no mention', r'no information',
    r'not provided', r'not explicitly mentioned', r'there is no', r'neither.*is mentioned'
]

def is_negative_statement(text):
    if not text: return False
    text_lower = text.lower()
    return any(re.search(pat, text_lower) for pat in negative_patterns)

# 2. Get all clean cache files with 282 completed questions
cache_files = sorted(glob.glob(os.path.join(clean_cache_dir, '*.json')))
ready_cache = {}
for cf in cache_files:
    sid = os.path.basename(cf).replace('.json', '')
    try:
        with open(cf, 'r') as fp:
            data = json.load(fp)
            if len(data) == 282:
                ready_cache[sid] = {item['q_id']: item for item in data}
    except Exception as e:
        print(f"Error loading {cf}: {e}")

print(f"Found {len(ready_cache)} fully completed clean extraction cache files (282 questions).")

# 3. Query startups from database
cur.execute("SELECT startup_id, company_name, payload FROM startup_extractions ORDER BY company_name ASC;")
rows = cur.fetchall()

total_citations_all = 0
total_matched_all = 0
updated_startups = 0

print(f"Processing database updates for completed startups...")

for sid, cname, payload in rows:
    if sid not in ready_cache:
        continue

    clean_q_map = ready_cache[sid]
    parsed_base = 'data/parsed_clean'
    folder = os.path.join(parsed_base, sid, 'converted')
    
    # Pre-index all PDF pages for this startup
    corpus = []
    if os.path.exists(folder):
        md_paths = glob.glob(os.path.join(folder, '*.md'))
        for p in md_paths:
            fname_pdf = os.path.basename(p).replace('.md', '')
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Split by <!-- Page X -->
                pages = re.split(r'<!--\s*Page\s*(\d+)\s*-->', content)
                if len(pages) > 1:
                    for i in range(1, len(pages), 2):
                        p_num = int(pages[i])
                        txt = normalize(pages[i+1])
                        corpus.append((fname_pdf, p_num, txt))
                else:
                    corpus.append((fname_pdf, 1, normalize(content)))
            except Exception:
                pass

    qs = payload.get('human_questions', [])
    startup_matched = 0
    startup_cits = 0

    for q in qs:
        qid = q.get('new_q_id', q.get('q_id'))
        clean_item = clean_q_map.get(qid)
        
        if clean_item:
            q['ai_suggestion'] = clean_item.get('predicted_val')
            q['ai_confidence'] = clean_item.get('confidence')
            q['ai_rationale'] = clean_item.get('rationale')
            cit = clean_item.get('citation')
            q['verbatim_citation'] = cit
        else:
            cit = q.get('verbatim_citation')

        # Reverse index citation to PDF and page number
        if cit and len(cit.strip()) > 5 and not is_negative_statement(cit):
            startup_cits += 1
            clean_cit = normalize(cit)
            words = clean_cit.split()
            prefix = ' '.join(words[:8]) if len(words) >= 8 else clean_cit
            prefix_short = ' '.join(words[:5]) if len(words) >= 5 else clean_cit

            found_file = None
            found_page = None

            # Tier 1: exact normalized match
            for fname, p_num, p_txt in corpus:
                if clean_cit in p_txt:
                    found_file, found_page = fname, p_num
                    break

            # Tier 2: 8-word prefix match
            if not found_file and len(words) >= 8:
                for fname, p_num, p_txt in corpus:
                    if prefix in p_txt:
                        found_file, found_page = fname, p_num
                        break

            # Tier 3: 5-word prefix match
            if not found_file and len(prefix_short) > 15:
                for fname, p_num, p_txt in corpus:
                    if prefix_short in p_txt:
                        found_file, found_page = fname, p_num
                        break

            # Tier 4: Quoted substrings inside citation
            if not found_file:
                quoted = re.findall(r'[\'\"]([^\'\"]{10,})[\'\"]', cit)
                for subq in quoted:
                    clean_sub = normalize(subq)
                    sub_words = clean_sub.split()
                    sub_prefix = ' '.join(sub_words[:6]) if len(sub_words) >= 6 else clean_sub
                    for fname, p_num, p_txt in corpus:
                        if clean_sub in p_txt or (len(sub_prefix) > 15 and sub_prefix in p_txt):
                            found_file, found_page = fname, p_num
                            break
                    if found_file:
                        break

            if found_file:
                q['source_pdf'] = found_file
                q['page_number'] = found_page
                startup_matched += 1
            else:
                q['source_pdf'] = None
                q['page_number'] = None
        else:
            q['source_pdf'] = None
            q['page_number'] = None

    total_citations_all += startup_cits
    total_matched_all += startup_matched

    # Mark payload as clean AI ready
    if 'meta' not in payload:
        payload['meta'] = {}
    payload['meta']['clean_ready'] = True
    payload['meta']['clean_updated_at'] = datetime.now(timezone.utc).isoformat()
    payload['meta']['model_version'] = 'v5_strict_grounded'

    # Save back to database
    cur.execute(
        "UPDATE startup_extractions SET payload = %s WHERE startup_id = %s;",
        (json.dumps(payload), sid)
    )
    conn.commit()
    updated_startups += 1

    pct = (startup_matched / startup_cits * 100) if startup_cits > 0 else 0
    print(f"[{updated_startups:2d}/{len(ready_cache)}] {cname} ({sid}): {startup_matched}/{startup_cits} citations mapped ({pct:.1f}%)")

elapsed = time.time() - start_time
print(f"\n==========================================")
print(f"COMPLETED CLEAN EXTRACTION SYNC IN {elapsed:.2f}s")
print(f"Startups updated in Supabase: {updated_startups}")
match_pct_total = (total_matched_all / total_citations_all * 100) if total_citations_all > 0 else 0
print(f"Total Citations Matched to PDF & Page: {total_matched_all}/{total_citations_all} ({match_pct_total:.1f}%)")
print(f"==========================================")
