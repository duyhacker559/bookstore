from __future__ import annotations

import re
from collections import defaultdict
from typing import Dict, List, Optional, Set

from faiss_service import FaissVectorStore, VectorSearchResult
from neo4j_service import GraphRecommendation, Neo4jService


def combine_hybrid_score(lstm_score: float, graph_score: float, rag_score: float, w1: float = 0.4, w2: float = 0.3, w3: float = 0.3) -> float:
    return round((w1 * float(lstm_score)) + (w2 * float(graph_score)) + (w3 * float(rag_score)), 6)


# ---------------------------------------------------------------------------
# Intent helpers
# ---------------------------------------------------------------------------

# Maps normalised keyword → canonical category slug to exclude.
# Keys are lower-case tokens that appear in exclusion phrases.
_EXCLUDE_KEYWORDS: Dict[str, str] = {
    # Vietnamese
    "sách": "book",
    "book": "book",
    "books": "book",
    "tiểu thuyết": "novel",
    "novel": "novel",
    "novels": "novel",
}

# Patterns that signal "I do NOT want X":
#   "not book", "không phải sách", "other than books",
#   "ngoài sách", "except books", "no book", "without books"
_EXCLUSION_PATTERNS = re.compile(
    r"""
    (?:
        not\s+(?:a\s+)?|
        no\s+|
        without\s+|
        except\s+|
        other\s+than\s+|
        apart\s+from\s+|
        besides?\s+|
        không\s+phải\s+(?:là\s+)?|
        ngoài\s+(?:ra\s+)?|
        không\s+|
        trừ\s+
    )
    (\w+(?:\s+\w+)?)               # the thing being excluded
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _detect_excluded_categories(question: str) -> Set[str]:
    """Return a set of canonical category slugs that the user wants excluded."""
    excluded: Set[str] = set()
    for match in _EXCLUSION_PATTERNS.finditer(question):
        token = match.group(1).strip().lower()
        if token in _EXCLUDE_KEYWORDS:
            excluded.add(_EXCLUDE_KEYWORDS[token])
        # Also check individual words in multi-word token
        for word in token.split():
            if word in _EXCLUDE_KEYWORDS:
                excluded.add(_EXCLUDE_KEYWORDS[word])
    return excluded


def _category_is_excluded(category: str, excluded: Set[str]) -> bool:
    """Return True if the product's category matches any excluded slug."""
    if not excluded or not category:
        return False
    cat_lower = category.strip().lower()
    for slug in excluded:
        if slug in cat_lower or cat_lower in slug:
            return True
    return False


class RAGPipeline:
    def __init__(self, vector_store: FaissVectorStore, graph_service: Neo4jService) -> None:
        self.vector_store = vector_store
        self.graph_service = graph_service

    def retrieve(self, query: str, user_id: Optional[int] = None, top_k: int = 5) -> Dict[str, List[Dict[str, object]]]:
        vector_hits = self.vector_store.search(query, top_k=top_k)

        if user_id is not None and query.strip():
            # Personalized: match text query AND boost by user behavior
            graph_hits = self.graph_service.query_personalized_message(user_id, query, top_k=top_k)
        elif user_id is not None:
            # User known but no query text — pure behavior recommendation
            graph_hits = self.graph_service.query_recommendation(user_id, top_k=top_k)
        else:
            # Anonymous user — text-only graph search
            graph_hits = self.graph_service.query_from_message(query, top_k=top_k)

        # Detect categories the user wants excluded (e.g. "not books", "ngoài sách")
        excluded_categories = _detect_excluded_categories(query)

        # Pre-filter vector hits so excluded products don't pollute relevant_ids
        if excluded_categories:
            vector_hits = [h for h in vector_hits if not _category_is_excluded(h.category, excluded_categories)]

        # Build set of product_ids that have a valid vector or text-graph hit,
        # so we can filter out products that only have behavior score but are
        # completely unrelated to the query (e.g. old books surfacing in a
        # "Laptop" search because the user bought them before).
        relevant_ids = {item.product_id for item in vector_hits}
        if query.strip():
            relevant_ids |= {item.product_id for item in graph_hits if item.source in ("neo4j-personalized", "graph-personalized", "neo4j-text", "graph-message")}

        combined = self._merge(vector_hits, graph_hits, relevant_ids if query.strip() else None, excluded_categories)
        return {
            "vector_hits": [self._vector_hit_dict(item) for item in vector_hits],
            "graph_hits": [self._graph_hit_dict(item) for item in graph_hits],
            "combined": combined,
            "excluded_categories": list(excluded_categories),
        }

    def generate_response(self, message: str, user_id: Optional[int] = None, top_k: int = 5) -> str:
        payload = self.retrieve(query=message, user_id=user_id, top_k=top_k)
        combined = payload["combined"]
        excluded = set(payload.get("excluded_categories", []))

        if not combined:
            if excluded:
                return (
                    f"Tôi không tìm thấy sản phẩm phù hợp nào ngoài {', '.join(excluded)}. "
                    "Bạn có thể cung cấp thêm thông tin về loại sản phẩm bạn cần không?"
                )
            return "Tôi chưa tìm thấy sản phẩm nào phù hợp. Bạn có thể cung cấp thêm thông tin được không?"

        best = combined[0]
        titles = [item.get("title", "") for item in combined[:3] if item.get("title")]
        title_text = ", ".join(titles)
        return (
            f"Sản phẩm phù hợp nhất với yêu cầu của bạn là {best.get('title', 'một sản phẩm phù hợp')}. "
            f"Một số lựa chọn liên quan bao gồm: {title_text}. "
            "(Gợi ý được tổng hợp dựa trên độ tương đồng nội dung và dữ liệu tương tác đồ thị)"
        )

    def _merge(self, vector_hits: List[VectorSearchResult], graph_hits: List[GraphRecommendation], relevant_ids: Optional[set] = None, excluded_categories: Optional[Set[str]] = None) -> List[Dict[str, object]]:
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

        results = sorted(merged.values(), key=lambda row: row["score"], reverse=True)

        # Drop products unrelated to the text query (only surfaced by behavior score).
        if relevant_ids is not None:
            results = [r for r in results if r["product_id"] in relevant_ids or float(r["rag"]) > 0]

        # Drop products whose category the user explicitly wants excluded.
        if excluded_categories:
            results = [r for r in results if not _category_is_excluded(str(r.get("category", "")), excluded_categories)]

        return results

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
