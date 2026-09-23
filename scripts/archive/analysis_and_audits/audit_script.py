import json
import csv
import re
import os

# Paths
brain_dir = "/Users/geoffrey/.gemini/antigravity/brain/50b6e66f-df5c-492d-ac2c-8d017d39cdda"
artifact_path = os.path.join(brain_dir, "binarization_audit.md")

# Load 282
with open('master_282_rubric.json', 'r') as f:
    r282 = json.load(f)

dict_282 = {q.get('new_q_id', q.get('q_id')): q['text'] for q in r282}

# Load 363 CSV
clusters = {}
with open('data/processed/master_decomposed_rubric_inventory.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        orig = row['orig_q_id']
        if orig not in clusters:
            clusters[orig] = []
        clusters[orig].append({'id': row['new_q_id'], 'text': row['text']})

# Filter to only binarized (len > 1)
binarized = {k: v for k, v in clusters.items() if len(v) > 1}

STOP_WORDS = {"the", "is", "at", "which", "on", "a", "an", "and", "or", "to", "in", "of", "for", "with", "as", "by", "does", "company", "startup", "have", "are", "they", "it", "this", "that", "be", "been", "has", "can", "will", "would", "should", "not", "no", "yes", "if", "from", "any", "how", "what", "their", "its", "there", "clear", "clearly", "more", "less", "than", "do", "we", "you", "about", "all", "some"}

def get_keywords(text):
    words = re.findall(r'\b[a-z]{3,}\b', text.lower())
    return set([w for w in words if w not in STOP_WORDS])

results = []

for orig_id, children in binarized.items():
    orig_text = dict_282.get(orig_id, "")
    orig_kw = get_keywords(orig_text)
    
    child_text = " ".join([c['text'] for c in children])
    child_kw = get_keywords(child_text)
    
    missing = orig_kw - child_kw
    added = child_kw - orig_kw
    
    results.append({
        'orig_id': orig_id,
        'orig_text': orig_text,
        'children': children,
        'missing': missing,
        'added': added
    })

# Generate Markdown
md = f"# Binarization Semantic Audit\n\n"
md += f"**Total Original Questions Binarized:** {len(binarized)}\n\n"
md += "This artifact provides a side-by-side cluster view for the human reviewer. It groups every original multi-part question with its new binary replacements. The semantic NLP script has automatically flagged potential word drift to speed up the review.\n\n"
md += "---\n\n"

for r in results:
    md += f"### {r['orig_id']}\n"
    md += f"**[ORIGINAL]** {r['orig_text']}\n"
    for c in r['children']:
        md += f"- **[{c['id']}]** {c['text']}\n"
    
    flags = []
    if r['missing']:
        flags.append(f"**⚠️ Potential Nuance Lost (Words missing from original):** {', '.join(sorted(r['missing']))}")
    if r['added']:
        flags.append(f"**👀 Potential Scope Creep (New words added):** {', '.join(sorted(r['added']))}")
        
    if flags:
        md += "\n> [!WARNING] \n> " + "\n> ".join(flags) + "\n"
    else:
        md += "\n> [!TIP]\n> ✅ *Clean mapping. No significant word drift detected.*\n"
        
    md += "\n---\n"

with open(artifact_path, 'w') as f:
    f.write(md)

print(f"Artifact created at {artifact_path}")
print(f"Total binarized count: {len(binarized)}")
