from __future__ import annotations

from typing import Dict, Iterable, List

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer


class ProductEmbedder:
    def __init__(self) -> None:
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), lowercase=True)
        self._fitted = False

    def _build_text(self, item: Dict[str, object]) -> str:
        title = str(item.get("title") or "")
        description = str(item.get("description") or "")
        category = str(item.get("category") or "")
        return f"{title} {description} {category}".strip()

    def fit(self, products: Iterable[Dict[str, object]]) -> "ProductEmbedder":
        texts = [self._build_text(product) for product in products]
        if not texts:
            texts = ["placeholder"]
        self.vectorizer.fit(texts)
        self._fitted = True
        return self

    def encode_texts(self, texts: List[str]) -> np.ndarray:
        if not self._fitted:
            self.fit([{"title": "placeholder", "description": "placeholder", "category": "placeholder"}])
        matrix = self.vectorizer.transform(texts)
        return matrix.toarray().astype(np.float32)

    def encode_product(self, product: Dict[str, object]) -> np.ndarray:
        return self.encode_texts([self._build_text(product)])[0]

    def encode_query(self, query: str) -> np.ndarray:
        return self.encode_texts([query])[0]