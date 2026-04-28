from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional

import numpy as np

from embedding import ProductEmbedder

try:
    import faiss  # type: ignore
except Exception:  # pragma: no cover
    faiss = None


@dataclass
class VectorSearchResult:
    product_id: int
    score: float
    title: str
    description: str
    category: str


class FaissVectorStore:
    def __init__(self, embedder: Optional[ProductEmbedder] = None) -> None:
        self.embedder = embedder or ProductEmbedder()
        self.products: List[Dict[str, object]] = []
        self.product_ids: List[int] = []
        self.vectors: Optional[np.ndarray] = None
        self.index = None

    def build(self, products: Iterable[Dict[str, object]]) -> None:
        self.products = list(products)
        self.product_ids = [int(product["product_id"]) for product in self.products]
        self.embedder.fit(self.products)
        vectors = np.vstack([self.embedder.encode_product(product) for product in self.products]).astype(np.float32)
        norms = np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-12
        vectors = vectors / norms
        self.vectors = vectors

        if faiss is not None and len(vectors) > 0:
            self.index = faiss.IndexFlatIP(vectors.shape[1])
            self.index.add(vectors)
        else:
            self.index = None

    def search(self, query: str, top_k: int = 5) -> List[VectorSearchResult]:
        if not self.products:
            return []

        query_vector = self.embedder.encode_query(query).astype(np.float32)
        query_vector = query_vector / (np.linalg.norm(query_vector) + 1e-12)

        if self.index is not None:
            scores, indices = self.index.search(np.expand_dims(query_vector, axis=0), max(1, top_k))
            return self._results_from_indices(scores[0], indices[0])

        if self.vectors is None:
            return []

        scores = np.dot(self.vectors, query_vector)
        indices = np.argsort(scores)[::-1][: max(1, top_k)]
        return self._results_from_indices(scores[indices], indices)

    def _results_from_indices(self, scores: np.ndarray, indices: np.ndarray) -> List[VectorSearchResult]:
        results: List[VectorSearchResult] = []
        for score, index in zip(scores, indices):
            if int(index) < 0 or int(index) >= len(self.products):
                continue
            product = self.products[int(index)]
            results.append(
                VectorSearchResult(
                    product_id=int(product["product_id"]),
                    score=float(score),
                    title=str(product.get("title") or ""),
                    description=str(product.get("description") or ""),
                    category=str(product.get("category") or ""),
                )
            )
        return results