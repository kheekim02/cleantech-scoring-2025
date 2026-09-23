import json
import psycopg2

DB_URL = 'postgresql://postgres.ubuqkdhajnnagropmatv:yNWp%21c%23ZRf6HQD2@aws-0-us-west-2.pooler.supabase.com:6543/postgres'
RUBRIC_PATH = './master_282_rubric.json'

# Load and rename key
with open(RUBRIC_PATH, 'r') as f:
    master_rubric = json.load(f)

for q in master_rubric:
    q['new_q_id'] = q.pop('q_id')

def update_all():
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    
    cur.execute("SELECT startup_id, payload FROM startup_extractions")
    startups = cur.fetchall()
    
    for row in startups:
        startup_id = row[0]
        payload = row[1]
        
        payload['human_questions'] = master_rubric
        payload['ai_cats'] = {}
        
        cur.execute("""
            UPDATE startup_extractions
            SET payload = %s
            WHERE startup_id = %s
        """, (json.dumps(payload), startup_id))
        
    conn.commit()
    cur.close()
    conn.close()
    print("Successfully injected fixed payload with new_q_id.")

if __name__ == '__main__':
    update_all()
