from __future__ import annotations

from collections import defaultdict
from typing import Dict, List, Optional

from faiss_service import FaissVectorStore, VectorSearchResult
from neo4j_service import GraphRecommendation, Neo4jService


def combine_hybrid_score(lstm_score: float, graph_score: float, rag_score: float, w1: float = 0.4, w2: float = 0.3, w3: float = 0.3) -> float:
    return round((w1 * float(lstm_score)) + (w2 * float(graph_score)) + (w3 * float(rag_score)), 6)


class RAGPipeline:
    def __init__(self, vector_store: FaissVectorStore, graph_service: Neo4jService) -> None:
        self.vector_store = vector_store
        self.graph_service = graph_service

    def retrieve(self, query: str, user_id: Optional[int] = None, top_k: int = 5) -> Dict[str, List[Dict[str, object]]]:
        vector_hits = self.vector_store.search(query, top_k=top_k)
        if user_id is not None:
            graph_hits = self.graph_service.query_recommendation(user_id, top_k=top_k)
        else:
            graph_hits = self.graph_service.query_from_message(query, top_k=top_k)
        combined = self._merge(vector_hits, graph_hits)
        return {
            "vector_hits": [self._vector_hit_dict(item) for item in vector_hits],
            "graph_hits": [self._graph_hit_dict(item) for item in graph_hits],
            "combined": combined,
        }

    def generate_response(self, message: str, user_id: Optional[int] = None, top_k: int = 5) -> str:
        payload = self.retrieve(query=message, user_id=user_id, top_k=top_k)
        combined = payload["combined"]
        if not combined:
            return "Tôi chưa tìm thấy sản phẩm phù hợp, hãy mô tả rõ hơn về nhu cầu của bạn."

        best = combined[0]
        titles = [item.get("title", "") for item in combined[:3] if item.get("title")]
        title_text = ", ".join(titles)
        return (
            f"Gợi ý phù hợp nhất là {best.get('title', 'sản phẩm phù hợp')}. "
            f"Các lựa chọn liên quan gồm: {title_text}. "
            f"Dựa trên truy vấn của bạn, tôi ưu tiên nhóm sản phẩm có mô tả và liên kết đồ thị tương đồng."
        )

    def _merge(self, vector_hits: List[VectorSearchResult], graph_hits: List[GraphRecommendation]) -> List[Dict[str, object]]:
        merged: Dict[int, Dict[str, object]] = defaultdict(lambda: {"product_id": 0, "title": "", "description": "", "category": "", "lstm": 0.0, "graph": 0.0, "rag": 0.0, "score": 0.0})

        for item in vector_hits:
            current = merged[item.product_id]
            current["product_id"] = item.product_id
            current["title"] = item.title
            current["description"] = item.description
            current["category"] = item.category
            current["rag"] = max(current["rag"], float(item.score))

        for item in graph_hits:
            current = merged[item.product_id]
            current["product_id"] = item.product_id
            current["graph"] = max(current["graph"], float(item.score))

        for item in merged.values():
            item["score"] = combine_hybrid_score(item["lstm"], item["graph"], item["rag"])

        return sorted(merged.values(), key=lambda row: row["score"], reverse=True)

    def _vector_hit_dict(self, item: VectorSearchResult) -> Dict[str, object]:
        return {
            "product_id": item.product_id,
            "title": item.title,
            "description": item.description,
            "category": item.category,
            "score": float(item.score),
            "source": "faiss",
        }

    def _graph_hit_dict(self, item: GraphRecommendation) -> Dict[str, object]:
        return {
            "product_id": item.product_id,
            "score": float(item.score),
            "source": item.source,
        }