from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

try:
    from neo4j import GraphDatabase  # type: ignore
except Exception:  # pragma: no cover
    GraphDatabase = None


@dataclass
class GraphRecommendation:
    product_id: int
    score: float
    source: str


class Neo4jService:
    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j") -> None:
        self.uri = uri
        self.user = user
        self.password = password
        self.database = database
        self.driver = None
        if GraphDatabase is not None:
            try:
                self.driver = GraphDatabase.driver(uri, auth=(user, password))
            except Exception:
                self.driver = None
        self._fallback_user_edges: Dict[int, Dict[int, float]] = defaultdict(lambda: defaultdict(float))
        self._fallback_similar: Dict[int, Dict[int, float]] = defaultdict(lambda: defaultdict(float))
        self._fallback_products: Dict[int, Dict[str, Any]] = {}

    def close(self) -> None:
        if self.driver is not None:
            self.driver.close()

    def build_graph(self, products: Iterable[Dict[str, Any]], events: Iterable[Dict[str, Any]]) -> Dict[str, int]:
        product_list = list(products)
        event_list = list(events)
        if self.driver is None:
            return self._build_fallback(product_list, event_list)

        try:
            with self.driver.session(database=self.database) as session:
                session.execute_write(self._create_graph_tx, product_list, event_list)
            return {"users": len({int(event["user_id"]) for event in event_list}), "products": len(product_list), "events": len(event_list)}
        except Exception:
            self.close()
            self.driver = None
            return self._build_fallback(product_list, event_list)

    def _create_graph_tx(self, tx, products: List[Dict[str, Any]], events: List[Dict[str, Any]]) -> None:
        for product in products:
            tx.run(
                """
                MERGE (p:Product {product_id: $product_id})
                SET p.title = $title,
                    p.description = $description,
                    p.category = $category
                """,
                product_id=int(product["product_id"]),
                title=str(product.get("title") or ""),
                description=str(product.get("description") or ""),
                category=str(product.get("category") or ""),
            )

        for event in events:
            weight = 1.0 if str(event.get("action") or "").lower() == "buy" else 0.4
            tx.run(
                """
                MERGE (u:User {user_id: $user_id})
                MERGE (p:Product {product_id: $product_id})
                MERGE (u)-[r:%s]->(p)
                SET r.weight = coalesce(r.weight, 0) + $weight,
                    r.timestamp = $timestamp
                """
                % ("BUY" if str(event.get("action") or "").lower() == "buy" else "VIEW"),
                user_id=int(event["user_id"]),
                product_id=int(event["product_id"]),
                weight=weight,
                timestamp=str(event.get("timestamp") or ""),
            )

        category_to_products: Dict[str, List[int]] = defaultdict(list)
        for product in products:
            category_to_products[str(product.get("category") or "").lower()].append(int(product["product_id"]))

        for product_ids in category_to_products.values():
            for source in product_ids:
                for target in product_ids:
                    if source == target:
                        continue
                    tx.run(
                        """
                        MATCH (a:Product {product_id: $source})
                        MATCH (b:Product {product_id: $target})
                        MERGE (a)-[r:SIMILAR]->(b)
                        SET r.weight = 0.75
                        """,
                        source=source,
                        target=target,
                    )

    def _build_fallback(self, products: List[Dict[str, Any]], events: List[Dict[str, Any]]) -> Dict[str, int]:
        self._fallback_products = {int(product["product_id"]): product for product in products}
        self._fallback_user_edges.clear()
        self._fallback_similar.clear()

        category_to_products: Dict[str, List[int]] = defaultdict(list)
        for product in products:
            category_to_products[str(product.get("category") or "").lower()].append(int(product["product_id"]))

        for category_products in category_to_products.values():
            for source in category_products:
                for target in category_products:
                    if source != target:
                        self._fallback_similar[source][target] = 0.75

        for event in events:
            user_id = int(event["user_id"])
            product_id = int(event["product_id"])
            action = str(event.get("action") or "view").lower()
            weight = 1.0 if action == "buy" else 0.4
            self._fallback_user_edges[user_id][product_id] += weight

        return {"users": len(self._fallback_user_edges), "products": len(products), "events": len(events)}

    def query_recommendation(self, user_id: int, top_k: int = 5) -> List[GraphRecommendation]:
        if self.driver is None:
            return self._query_fallback(user_id, top_k)

        try:
            with self.driver.session(database=self.database) as session:
                rows = session.execute_read(self._query_recommendation_tx, int(user_id), int(top_k))
            return [GraphRecommendation(**row) for row in rows]
        except Exception:
            self.close()
            self.driver = None
            return self._query_fallback(user_id, top_k)

    def _query_recommendation_tx(self, tx, user_id: int, top_k: int) -> List[Dict[str, Any]]:
        query = """
        MATCH (u:User {user_id: $user_id})-[r:VIEW|BUY]->(p:Product)
        OPTIONAL MATCH (p)-[s:SIMILAR]->(sp:Product)
        WITH coalesce(sp.product_id, p.product_id) AS product_id,
             sum(CASE type(r) WHEN 'BUY' THEN 1.0 ELSE 0.4 END) + coalesce(sum(s.weight), 0) AS score
        RETURN product_id, score
        ORDER BY score DESC
        LIMIT $top_k
        """
        rows = tx.run(query, user_id=user_id, top_k=top_k)
        return [
            {"product_id": int(row["product_id"]), "score": float(row["score"] or 0.0), "source": "neo4j"}
            for row in rows
            if row["product_id"] is not None
        ]

    def _query_fallback(self, user_id: int, top_k: int = 5) -> List[GraphRecommendation]:
        direct_scores = self._fallback_user_edges.get(int(user_id), {})
        scores: Dict[int, float] = defaultdict(float)

        for product_id, score in direct_scores.items():
            scores[product_id] += score
            for similar_id, similar_score in self._fallback_similar.get(product_id, {}).items():
                scores[similar_id] += score * similar_score

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[: max(1, top_k)]
        return [GraphRecommendation(product_id=product_id, score=float(score), source="graph-fallback") for product_id, score in ranked]

    def query_from_message(self, message: str, top_k: int = 5) -> List[GraphRecommendation]:
        if self.driver is not None:
            try:
                with self.driver.session(database=self.database) as session:
                    rows = session.execute_read(self._query_from_message_tx, message, int(top_k))
                return [GraphRecommendation(**row) for row in rows]
            except Exception:
                self.close()
                self.driver = None

        keywords = {token.strip().lower() for token in message.split() if token.strip()}
        scores: Dict[int, float] = defaultdict(float)
        for product_id, product in self._fallback_products.items():
            haystack = f"{product.get('title', '')} {product.get('description', '')} {product.get('category', '')}".lower()
            overlap = sum(1 for keyword in keywords if keyword and keyword in haystack)
            if overlap:
                scores[product_id] += float(overlap)
                for similar_id, similar_score in self._fallback_similar.get(product_id, {}).items():
                    scores[similar_id] += 0.5 * similar_score
        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)[: max(1, top_k)]
        return [GraphRecommendation(product_id=product_id, score=float(score), source="graph-message") for product_id, score in ranked]

    def _query_from_message_tx(self, tx, message: str, top_k: int) -> List[Dict[str, Any]]:
        query = """
        WITH toLower($message) AS message
        MATCH (p:Product)
        WITH p,
             reduce(score = 0.0, token IN split(message, ' ') | score + CASE WHEN token <> '' AND toLower(p.title) CONTAINS token THEN 1.0 ELSE 0.0 END) AS score
        WHERE score > 0
        OPTIONAL MATCH (p)-[s:SIMILAR]->(sp:Product)
        RETURN coalesce(sp.product_id, p.product_id) AS product_id,
               max(score + coalesce(s.weight, 0)) AS score
        ORDER BY score DESC
        LIMIT $top_k
        """
        rows = tx.run(query, message=message, top_k=top_k)
        return [
            {"product_id": int(row["product_id"]), "score": float(row["score"] or 0.0), "source": "neo4j-text"}
            for row in rows
            if row["product_id"] is not None
        ]
        