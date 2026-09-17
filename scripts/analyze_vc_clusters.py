import os
import json
import re
import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist, squareform, cdist
from scipy.cluster.hierarchy import linkage, fcluster
import networkx as nx
from collections import Counter, defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSONL_PATH = os.path.join(BASE_DIR, "data", "processed", "vcuncovered_corpus.jsonl")
OUTPUT_ANALYSIS = os.path.join(BASE_DIR, "data", "processed", "vc_clusters_and_outliers.json")

# Custom stop words specific to VC blog boilerplate
STOP_WORDS = set([
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren't",
    "as", "at", "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can",
    "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't",
    "having", "he", "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", "himself",
    "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not",
    "of", "off", "on", "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over",
    "own", "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then", "there", "there's",
    "these", "they", "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too",
    "under", "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while", "who", "who's",
    "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're",
    "you've", "your", "yours", "yourself", "yourselves",
    # Editorial & generic venture terms to isolate philosophical distinctiveness
    "uncovered", "media", "substack", "read", "click", "podcast", "newsletter", "subscribe", "episode",
    "venture", "capital", "vc", "vcs", "investor", "investors", "investing", "investment", "investments",
    "firm", "firms", "company", "companies", "startup", "startups", "founder", "founders", "check", "fund",
    "funds", "stage", "seed", "also", "one", "two", "first", "new", "said", "says", "like", "get", "make",
    "people", "see", "way", "things", "time", "years", "even", "build", "building", "built", "much", "many"
])

def extract_investor_firm(title):
    t = title.replace("[Podcast]", "").replace("(podcast)", "").strip()
    t = re.sub(r"^\(podcast\)\s*", "", t, flags=re.I)
    
    parts = re.split(r"[-–—]", t)
    if len(parts) >= 2:
        investor = parts[0].strip()
        firm = parts[1].strip()
        return investor, firm
    elif " at " in t:
        parts = t.split(" at ")
        return parts[0].strip(), parts[1].strip()
    return t, "Independent / Undisclosed"

def tokenize(text):
    text = re.sub(r"[^a-zA-Z\s]", " ", text.lower())
    tokens = [w for w in text.split() if len(w) > 2 and w not in STOP_WORDS]
    return tokens

def build_tfidf_matrix(documents):
    # Vocabulary & Document Frequencies
    doc_tokens = [tokenize(doc) for doc in documents]
    N = len(documents)
    
    dfs = defaultdict(int)
    for tokens in doc_tokens:
        unique_tokens = set(tokens)
        for t in unique_tokens:
            dfs[t] += 1
            
    # Filter vocabulary: min_df=2, max_df=0.8
    filtered_terms = [t for t, count in sorted(dfs.items()) if 2 <= count <= (N * 0.85)]
    vocab = {t: idx for idx, t in enumerate(filtered_terms)}
    vocab_list = filtered_terms
    
    # Compute TF-IDF
    V = len(vocab)
    matrix = np.zeros((N, V), dtype=np.float32)
    
    for i, tokens in enumerate(doc_tokens):
        tfs = Counter([t for t in tokens if t in vocab])
        doc_len = len(tokens) or 1
        for t, count in tfs.items():
            j = vocab[t]
            tf = count / doc_len
            idf = np.log((1 + N) / (1 + dfs[t])) + 1
            matrix[i, j] = tf * idf
            
        # L2 norm normalization
        norm = np.linalg.norm(matrix[i])
        if norm > 0:
            matrix[i] /= norm
            
    return matrix, vocab_list

def main():
    print("Loading VC Uncovered corpus...")
    with open(JSONL_PATH, "r", encoding="utf-8") as f:
        raw_posts = [json.loads(line) for line in f]

    # Filter out announcement post
    posts = [p for p in raw_posts if p.get("slug") != "introducing-vc-uncovered"]
    N = len(posts)
    print(f"Loaded {N} active investor profiles.")

    investor_metadata = []
    documents = []

    for p in posts:
        inv, firm = extract_investor_firm(p["title"])
        subtitle = p.get("subtitle") or ""
        clean_text = p.get("clean_text") or ""
        
        # Pull key quotes / headings
        headings = [line.replace("###", "").strip() for line in clean_text.split("\n") if line.startswith("###")]
        
        investor_metadata.append({
            "id": p["id"],
            "slug": p["slug"],
            "title": p["title"],
            "investor_name": inv,
            "firm_name": firm,
            "subtitle": subtitle,
            "wordcount": p["wordcount"],
            "post_date": p["post_date"],
            "tags": p["tags"],
            "headings": headings,
            "outbound_links_count": len(p["outbound_links"]),
            "canonical_url": p["canonical_url"]
        })
        # Full text document for semantic analysis
        documents.append(f"{subtitle} {clean_text}")

    # Build TF-IDF
    print("Vectorizing text & computing latent semantic space...")
    tfidf_matrix, vocab = build_tfidf_matrix(documents)
    
    # Truncated SVD (PCA for text)
    U, S, Vt = np.linalg.svd(tfidf_matrix, full_matrices=False)
    # Keep top 15 components
    K_COMPONENTS = 15
    dense_embeddings = U[:, :K_COMPONENTS] * S[:K_COMPONENTS]
    # Normalize dense embeddings
    dense_norms = np.linalg.norm(dense_embeddings, axis=1, keepdims=True)
    dense_norms[dense_norms == 0] = 1.0
    dense_embeddings = dense_embeddings / dense_norms

    # Pairwise Cosine Distance Matrix
    dist_matrix = squareform(pdist(dense_embeddings, metric="cosine"))

    # Hierarchical Clustering
    Z = linkage(pdist(dense_embeddings, metric="cosine"), method="ward")
    # Form 5 dominant strategic clumps/clusters
    N_CLUSTERS = 5
    cluster_labels = fcluster(Z, t=N_CLUSTERS, criterion="maxclust")

    # Cluster profiling: Find top distinctive keywords per cluster
    clusters_data = defaultdict(list)
    for idx, c_id in enumerate(cluster_labels):
        clusters_data[int(c_id)].append(idx)

    cluster_summaries = {}
    cluster_names = {
        1: "Industrial, Defense & Regulated Deeptech",
        2: "Non-Consensus, Lived-Experience & 'Earned Secret' Backers",
        3: "Fintech, Financial Inclusion & Capital Velocity",
        4: "Operator-Led, GTM & Post-Check Acceleration",
        5: "Consumer, Cultural & Demographic Shifts"
    }

    print("\n--- IDENTIFYING LIKE-MINDED CLUMPS (CLUSTERING) ---")
    for c_id, doc_indices in sorted(clusters_data.items()):
        # Calculate cluster centroid
        centroid = np.mean(dense_embeddings[doc_indices], axis=0)
        centroid /= (np.linalg.norm(centroid) or 1.0)
        
        # Calculate top distinctive terms in TF-IDF space
        cluster_tfidf_mean = np.mean(tfidf_matrix[doc_indices], axis=0)
        top_term_indices = np.argsort(cluster_tfidf_mean)[::-1][:12]
        top_terms = [vocab[i] for i in top_term_indices]
        
        members = [f"{investor_metadata[i]['investor_name']} ({investor_metadata[i]['firm_name']})" for i in doc_indices]
        
        cluster_summaries[c_id] = {
            "cluster_id": c_id,
            "size": len(doc_indices),
            "top_terms": top_terms,
            "key_members": members[:8],
            "all_member_slugs": [investor_metadata[i]["slug"] for i in doc_indices]
        }
        print(f"\nCluster {c_id}: {len(doc_indices)} Investors")
        print(f"  Top Concepts: {', '.join(top_terms[:8])}")
        print(f"  Notable Members: {', '.join(members[:4])}")

    # Outlier Detection
    print("\n--- DETECTING PHILOSOPHICAL & STRATEGIC OUTLIERS ---")
    # Metric 1: Distance from own cluster centroid
    # Metric 2: Distance from global median of all investors
    global_centroid = np.median(dense_embeddings, axis=0)
    global_centroid /= np.linalg.norm(global_centroid)

    outlier_scores = []
    for idx, emb in enumerate(dense_embeddings):
        c_id = int(cluster_labels[idx])
        c_indices = clusters_data[c_id]
        c_centroid = np.mean(dense_embeddings[c_indices], axis=0)
        c_centroid /= np.linalg.norm(c_centroid)
        
        cluster_dist = 1.0 - np.dot(emb, c_centroid)
        global_dist = 1.0 - np.dot(emb, global_centroid)
        
        # Combined anomaly score
        anomaly_score = float((0.6 * cluster_dist) + (0.4 * global_dist))
        
        outlier_scores.append({
            "idx": idx,
            "slug": investor_metadata[idx]["slug"],
            "name": investor_metadata[idx]["investor_name"],
            "firm": investor_metadata[idx]["firm_name"],
            "cluster_id": c_id,
            "anomaly_score": round(anomaly_score, 4),
            "cluster_distance": round(float(cluster_dist), 4),
            "global_distance": round(float(global_dist), 4),
            "subtitle": investor_metadata[idx]["subtitle"],
            "distinctive_headings": investor_metadata[idx]["headings"][:3]
        })

    outlier_scores.sort(key=lambda x: x["anomaly_score"], reverse=True)

    print("\nTop 10 Outliers (Farthest from Conventional VC Clumps):")
    for o in outlier_scores[:10]:
        print(f"  - {o['name']} ({o['firm']}) | Anomaly Score: {o['anomaly_score']}")
        print(f"    Core Thesis: {o['subtitle'][:110]}...")

    # Save detailed JSON output
    final_analysis = {
        "total_investors_analyzed": N,
        "clusters": cluster_summaries,
        "top_outliers": outlier_scores[:15],
        "all_investors": [
            {
                **investor_metadata[i],
                "cluster_id": int(cluster_labels[i]),
                "anomaly_score": next(o["anomaly_score"] for o in outlier_scores if o["idx"] == i)
            }
            for i in range(N)
        ]
    }

    with open(OUTPUT_ANALYSIS, "w", encoding="utf-8") as f:
        json.dump(final_analysis, f, indent=2, ensure_ascii=False)

    print(f"\nAnalysis complete! Full results saved to {OUTPUT_ANALYSIS}")

if __name__ == "__main__":
    main()
