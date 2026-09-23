import os
import glob
import time
import json
import psycopg2
import pymupdf
import re

start_time = time.time()

# 1. Database Connection
with open('.env') as f:
    for line in f:
        if line.startswith('DATABASE_URL='):
            db_url = line.split('=', 1)[1].strip().strip("'").replace('?pgbouncer=true', '')

conn = psycopg2.connect(db_url)
cur = conn.cursor()

raw_base = '/Users/geoffrey/Global_Key_Advisors/Migrating_Automated_Startup_Scraper/data/raw'

def normalize(s):
    if not s: return ""
    s = re.sub(r'[•●○\u200b\xa0\r\n\t]+', ' ', s)
    s = re.sub(r'[^a-zA-Z0-9]+', ' ', s)
    return ' '.join(s.lower().split())

cur.execute("SELECT startup_id, payload FROM startup_extractions ORDER BY startup_id ASC;")
rows = cur.fetchall()

print(f"Loaded {len(rows)} startups from database. Beginning reverse-indexing...")

total_citations_all = 0
total_matched_all = 0
updated_startups = 0

for sid, payload in rows:
    folder = os.path.join(raw_base, sid)
    if not os.path.exists(folder):
        print(f"  [!] Folder not found for {sid}, skipping.")
        continue
        
    pdf_paths = glob.glob(os.path.join(folder, '**', '*.pdf'), recursive=True)
    if not pdf_paths:
        continue
        
    # Pre-index all PDF pages for this startup
    corpus = []
    for p in pdf_paths:
        fname = os.path.basename(p)
        try:
            doc = pymupdf.open(p)
            for p_idx, page in enumerate(doc):
                txt = normalize(page.get_text())
                corpus.append((fname, p_idx + 1, txt))
        except Exception:
            pass

    qs = payload.get('human_questions', [])
    startup_matched = 0
    startup_cits = 0
    
    for q in qs:
        cit = q.get('verbatim_citation')
        if cit and len(cit.strip()) > 5:
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

            # Tier 3: 5-word prefix match (if reasonably specific)
            if not found_file and len(prefix_short) > 15:
                for fname, p_num, p_txt in corpus:
                    if prefix_short in p_txt:
                        found_file, found_page = fname, p_num
                        break
                        
            if found_file:
                q['source_pdf'] = found_file
                q['page_number'] = found_page
                startup_matched += 1
            else:
                q['source_pdf'] = None
                q['page_number'] = None

    total_citations_all += startup_cits
    total_matched_all += startup_matched
    
    # Save back to database
    cur.execute(
        "UPDATE startup_extractions SET payload = %s WHERE startup_id = %s;",
        (json.dumps(payload), sid)
    )
    conn.commit()
    updated_startups += 1
    
    pct = (startup_matched / startup_cits * 100) if startup_cits > 0 else 0
    print(f"[{sid}] {startup_matched}/{startup_cits} citations matched ({pct:.1f}%)")

elapsed = time.time() - start_time
print(f"\n==========================================")
print(f"COMPLETED REVERSE-INDEXING IN {elapsed:.2f}s")
print(f"Startups updated: {updated_startups}/{len(rows)}")
print(f"Total citations indexed: {total_matched_all}/{total_citations_all} ({total_matched_all/total_citations_all*100:.1f}%)")
print(f"==========================================")

cur.close()
conn.close()
