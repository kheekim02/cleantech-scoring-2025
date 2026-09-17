import os
import json
import time
import sqlite3
import urllib.request
from bs4 import BeautifulSoup
from urllib.parse import urlparse

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw", "vcuncovered")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
JSONL_PATH = os.path.join(PROCESSED_DIR, "vcuncovered_corpus.jsonl")
DB_PATH = os.path.join(PROCESSED_DIR, "vcuncovered.db")

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(PROCESSED_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

def fetch_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))

def clean_and_extract_content(html_content):
    if not html_content:
        return "", []
    soup = BeautifulSoup(html_content, "html.parser")

    # Remove Substack interactive widgets, forms, styles, scripts
    for el in soup.select(".subscription-widget-wrap-editor, .subscription-widget, form, script, style, .pencraft"):
        el.decompose()

    # Extract outbound links
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        text = a.get_text().strip()
        if href.startswith("http") and not href.startswith("#"):
            links.append({"text": text, "url": href})

    # Extract clean text sections
    text_blocks = []
    for elem in soup.find_all(["h1", "h2", "h3", "p", "blockquote", "li"]):
        txt = elem.get_text().strip()
        if not txt:
            continue
        if elem.name in ["h1", "h2", "h3"]:
            text_blocks.append(f"\n### {txt}\n")
        elif elem.name == "blockquote":
            text_blocks.append(f"> {txt}")
        elif elem.name == "li":
            text_blocks.append(f"- {txt}")
        else:
            text_blocks.append(txt)

    clean_text = "\n\n".join(text_blocks).strip()
    return clean_text, links

def init_sqlite_db(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY,
            slug TEXT UNIQUE,
            title TEXT,
            subtitle TEXT,
            description TEXT,
            post_date TEXT,
            post_type TEXT,
            wordcount INTEGER,
            canonical_url TEXT,
            podcast_audio_url TEXT,
            reaction_count INTEGER,
            comment_count INTEGER,
            clean_text TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            post_id INTEGER,
            tag TEXT,
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS bylines (
            post_id INTEGER,
            name TEXT,
            handle TEXT,
            bio TEXT,
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS outbound_links (
            post_id INTEGER,
            link_text TEXT,
            link_url TEXT,
            link_domain TEXT,
            FOREIGN KEY (post_id) REFERENCES posts(id)
        )
    """)
    conn.commit()
    return conn

def main():
    print("=" * 60)
    print("VC UNCOVERED SCRAPER & PIPELINE")
    print("=" * 60)

    # 1. Fetch entire archive index
    print("\n[Step 1/3] Fetching complete archive index from Substack...")
    offset = 0
    all_archive_posts = []
    while True:
        archive_url = f"https://www.vcuncovered.com/api/v1/archive?sort=new&search=&offset={offset}&limit=50"
        try:
            batch = fetch_json(archive_url)
            if not batch:
                break
            all_archive_posts.extend(batch)
            offset += len(batch)
            print(f"  --> Discovered {len(all_archive_posts)} posts so far (offset {offset})...")
            if len(batch) < 10:
                break
            time.sleep(0.3)
        except Exception as e:
            print(f"  Error fetching archive at offset {offset}: {e}")
            break

    total_count = len(all_archive_posts)
    print(f"Total posts discovered: {total_count}")

    # 2. Fetch detailed post data (with local caching)
    print(f"\n[Step 2/3] Fetching detailed content for {total_count} posts...")
    corpus = []
    conn = init_sqlite_db(DB_PATH)
    cur = conn.cursor()

    for idx, meta in enumerate(all_archive_posts, 1):
        slug = meta.get("slug")
        post_id = meta.get("id")
        raw_file = os.path.join(RAW_DIR, f"{slug}.json")

        post_data = None
        if os.path.exists(raw_file):
            try:
                with open(raw_file, "r", encoding="utf-8") as f:
                    post_data = json.load(f)
            except Exception:
                post_data = None

        if not post_data:
            post_url = f"https://www.vcuncovered.com/api/v1/posts/{slug}"
            try:
                post_data = fetch_json(post_url)
                with open(raw_file, "w", encoding="utf-8") as f:
                    json.dump(post_data, f, indent=2)
                time.sleep(0.3)
            except Exception as e:
                print(f"  [{idx}/{total_count}] Failed to fetch {slug}: {e}")
                continue

        # Extract text & links
        body_html = post_data.get("body_html", "")
        clean_text, links = clean_and_extract_content(body_html)

        tags = [t.get("name") for t in post_data.get("postTags", []) if t.get("name")]
        bylines = post_data.get("publishedBylines", [])

        # Deduplicate outbound links
        unique_links = []
        seen_urls = set()
        for link in links:
            u = link["url"]
            if u not in seen_urls:
                seen_urls.add(u)
                unique_links.append(link)

        item = {
            "id": post_id,
            "slug": slug,
            "title": post_data.get("title"),
            "subtitle": post_data.get("subtitle"),
            "description": post_data.get("description"),
            "post_date": post_data.get("post_date"),
            "post_type": post_data.get("type"),
            "wordcount": post_data.get("wordcount"),
            "canonical_url": post_data.get("canonical_url"),
            "podcast_audio_url": post_data.get("podcast_url"),
            "reaction_count": post_data.get("reaction_count", 0),
            "comment_count": post_data.get("comment_count", 0),
            "tags": tags,
            "bylines": [{"name": b.get("name"), "handle": b.get("handle"), "bio": b.get("bio")} for b in bylines],
            "outbound_links": unique_links,
            "clean_text": clean_text
        }
        corpus.append(item)

        # Store in SQLite
        cur.execute("""
            INSERT OR REPLACE INTO posts (
                id, slug, title, subtitle, description, post_date, post_type,
                wordcount, canonical_url, podcast_audio_url, reaction_count,
                comment_count, clean_text
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            post_id, slug, item["title"], item["subtitle"], item["description"],
            item["post_date"], item["post_type"], item["wordcount"],
            item["canonical_url"], item["podcast_audio_url"],
            item["reaction_count"], item["comment_count"], item["clean_text"]
        ))

        cur.execute("DELETE FROM tags WHERE post_id = ?", (post_id,))
        for tag in tags:
            cur.execute("INSERT INTO tags (post_id, tag) VALUES (?, ?)", (post_id, tag))

        cur.execute("DELETE FROM bylines WHERE post_id = ?", (post_id,))
        for b in item["bylines"]:
            cur.execute("INSERT INTO bylines (post_id, name, handle, bio) VALUES (?, ?, ?, ?)",
                        (post_id, b.get("name"), b.get("handle"), b.get("bio")))

        cur.execute("DELETE FROM outbound_links WHERE post_id = ?", (post_id,))
        for l in unique_links:
            domain = urlparse(l["url"]).netloc
            cur.execute("INSERT INTO outbound_links (post_id, link_text, link_url, link_domain) VALUES (?, ?, ?, ?)",
                        (post_id, l["text"], l["url"], domain))

        conn.commit()
        print(f"  [{idx:2d}/{total_count}] Extracted: {str(item['title'])[:38]:<38} ({item['wordcount']} words, {len(unique_links)} links)")

    # 3. Save unified JSONL
    print(f"\n[Step 3/3] Saving corpus to JSONL...")
    with open(JSONL_PATH, "w", encoding="utf-8") as f:
        for entry in corpus:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    conn.close()

    print("\n" + "=" * 60)
    print("SCRAPE & INGESTION COMPLETE")
    print(f"Total posts processed:  {len(corpus)}")
    print(f"Raw files location:     {RAW_DIR}")
    print(f"JSONL corpus location:  {JSONL_PATH}")
    print(f"SQLite DB location:     {DB_PATH}")
    print("=" * 60)

if __name__ == "__main__":
    main()
