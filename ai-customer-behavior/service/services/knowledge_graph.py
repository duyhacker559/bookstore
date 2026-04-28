from __future__ import annotations

from typing import Any, Dict, List, Tuple

import networkx as nx
import numpy as np


class KnowledgeGraphEngine:
    def __init__(self) -> None:
        self.graph = nx.MultiDiGraph()
        self.last_stats: Dict[str, Any] = {}

    def rebuild(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        g = nx.MultiDiGraph()

        for event in events:
            user_id = int(event.get("user_id") or 0)
            if user_id <= 0:
                continue

            user_node = f"user:{user_id}"
            event_type = str(event.get("event_type") or "unknown")
            category = str(event.get("category") or "unknown").strip().lower() or "unknown"
            product_id = int(event.get("product_id") or 0)
            query_text = str(event.get("query_text") or "").strip().lower()

            g.add_node(user_node, node_type="user", user_id=user_id)
            cat_node = f"category:{category}"
            g.add_node(cat_node, node_type="category", category=category)
            g.add_edge(user_node, cat_node, relation=event_type)

            if product_id > 0:
                product_node = f"product:{product_id}"
                g.add_node(product_node, node_type="product", product_id=product_id)
                g.add_edge(user_node, product_node, relation=event_type)
                g.add_edge(product_node, cat_node, relation="belongs_to")

            if query_text:
                query_node = f"query:{query_text[:80]}"
                g.add_node(query_node, node_type="query", text=query_text)
                g.add_edge(user_node, query_node, relation="search")
                g.add_edge(query_node, cat_node, relation="implies")

        self.graph = g
        self.last_stats = {
            "nodes": g.number_of_nodes(),
            "edges": g.number_of_edges(),
            "users": sum(1 for _, data in g.nodes(data=True) if data.get("node_type") == "user"),
            "products": sum(1 for _, data in g.nodes(data=True) if data.get("node_type") == "product"),
            "categories": sum(1 for _, data in g.nodes(data=True) if data.get("node_type") == "category"),
            "queries": sum(1 for _, data in g.nodes(data=True) if data.get("node_type") == "query"),
        }
        return self.last_stats

    def rag_retrieve(self, user_id: int, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        user_node = f"user:{int(user_id)}"
        if user_node not in self.graph:
            return []

        query_tokens = {token for token in query.lower().split() if token}
        hits: List[Tuple[float, str, Dict[str, Any]]] = []

        for neighbor in self.graph.neighbors(user_node):
            node_data = self.graph.nodes[neighbor]
            node_type = str(node_data.get("node_type") or "unknown")

            text = ""
            if node_type == "category":
                text = str(node_data.get("category") or "")
            elif node_type == "query":
                text = str(node_data.get("text") or "")
            elif node_type == "product":
                text = str(node_data.get("product_id") or "")

            overlap = len(query_tokens.intersection(set(text.split()))) if text else 0
            score = 0.3 + (overlap * 0.2)
            hits.append(
                (
                    score,
                    neighbor,
                    {
                        "node": neighbor,
                        "node_type": node_type,
                        "content": text,
                        "score": round(float(min(score, 0.99)), 4),
                    },
                )
            )

        hits.sort(key=lambda x: x[0], reverse=True)
        return [item[2] for item in hits[: max(1, top_k)]]

    def gnn_predict_categories(self, user_id: int, top_k: int = 5) -> List[Dict[str, Any]]:
        user_node = f"user:{int(user_id)}"
        if user_node not in self.graph:
            return []

        nodes = list(self.graph.nodes())
        node_to_idx = {n: i for i, n in enumerate(nodes)}

        n = len(nodes)
        if n == 0:
            return []

        a = np.zeros((n, n), dtype=np.float32)
        for src, dst in self.graph.edges():
            i = node_to_idx[src]
            j = node_to_idx[dst]
            a[i, j] = 1.0
            a[j, i] = 1.0

        # Add self-loop and normalize adjacency for message passing.
        a = a + np.eye(n, dtype=np.float32)
        deg = np.sum(a, axis=1)
        deg_inv_sqrt = np.power(deg, -0.5, where=deg > 0)
        d = np.diag(deg_inv_sqrt)
        a_hat = d @ a @ d

        emb_dim = 8
        rng = np.random.default_rng(seed=42)
        x = rng.normal(0, 1, size=(n, emb_dim)).astype(np.float32)
        w1 = rng.normal(0, 0.4, size=(emb_dim, emb_dim)).astype(np.float32)
        w2 = rng.normal(0, 0.4, size=(emb_dim, emb_dim)).astype(np.float32)

        h = np.maximum((a_hat @ x) @ w1, 0)
        h = np.maximum((a_hat @ h) @ w2, 0)

        u_idx = node_to_idx[user_node]
        u_vec = h[u_idx]

        scores = []
        for node, idx in node_to_idx.items():
            nd = self.graph.nodes[node]
            if nd.get("node_type") != "category":
                continue
            sim = float(np.dot(u_vec, h[idx]) / (np.linalg.norm(u_vec) * np.linalg.norm(h[idx]) + 1e-8))
            cat = str(nd.get("category") or "unknown")
            scores.append({"category": cat, "score": round((sim + 1.0) / 2.0, 4)})

        scores.sort(key=lambda x: x["score"], reverse=True)
        return scores[: max(1, top_k)]
