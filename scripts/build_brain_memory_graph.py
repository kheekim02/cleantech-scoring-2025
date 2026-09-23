import json
import time
from pathlib import Path
import networkx as nx
from networkx.readwrite import json_graph

from graphify.extract import extract_markdown
from graphify import cluster, export

brain_dir = Path("/Users/geoffrey/.gemini/antigravity/brain").resolve()
out_dir = brain_dir / "graphify-out"
out_dir.mkdir(parents=True, exist_ok=True)

# 1. Load existing code-only graph if present
existing_graph_file = out_dir / "graph.json"
if existing_graph_file.exists():
    data = json.loads(existing_graph_file.read_text(encoding="utf-8"))
    if "links" not in data and "edges" in data:
        data["links"] = data["edges"]
    try:
        G = json_graph.node_link_graph(data, edges="links")
    except TypeError:
        G = json_graph.node_link_graph(data)
    print(f"Loaded existing code graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
else:
    G = nx.Graph()

# 2. Find and extract markdown files
md_files = [
    f for f in brain_dir.rglob("*.md")
    if ".system_generated" not in str(f) and "graphify-out" not in str(f)
]
print(f"Found {len(md_files)} markdown files in brain")

t0 = time.time()
md_nodes_added = 0
md_edges_added = 0

for f in md_files:
    try:
        res = extract_markdown(f)
        for n in res.get("nodes", []):
            nid = n.get("id")
            if not nid:
                continue
            if not G.has_node(nid):
                G.add_node(nid, **n)
                md_nodes_added += 1
            else:
                # Update attributes if needed
                for k, v in n.items():
                    if k not in G.nodes[nid]:
                        G.nodes[nid][k] = v

        for e in res.get("edges", []):
            src = e.get("source")
            tgt = e.get("target")
            if src and tgt and G.has_node(src) and G.has_node(tgt):
                if not G.has_edge(src, tgt):
                    edata = {k: v for k, v in e.items() if k not in ("source", "target")}
                    G.add_edge(src, tgt, **edata)
                    md_edges_added += 1
    except Exception as err:
        pass

print(f"Added {md_nodes_added} markdown nodes and {md_edges_added} edges in {time.time()-t0:.2f}s")
print(f"Combined Brain Graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

# 3. Community detection (Leiden)
print("Running community detection...")
communities = cluster.cluster(G)
labels = cluster.label_communities_by_hub(G, communities)
print(f"Clustered into {len(communities)} communities")

# 4. Save graph.json and labels
labels_json = {str(k): v for k, v in labels.items()}
(out_dir / ".graphify_labels.json").write_text(json.dumps(labels_json, indent=2), encoding="utf-8")
(out_dir / ".graphify_python").write_text("/Users/geoffrey/.local/share/uv/tools/graphifyy/bin/python", encoding="utf-8")
(out_dir / ".graphify_root").write_text(str(brain_dir), encoding="utf-8")

export.to_json(G, communities, str(out_dir / "graph.json"), community_labels=labels)
export.to_html(G, communities, str(out_dir / "graph.html"), community_labels=labels)
print(f"Saved graph.json and graph.html to {out_dir}")

