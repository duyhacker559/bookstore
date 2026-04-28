from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import numpy as np
from sklearn.neural_network import MLPClassifier


POSITIVE_EVENTS = {"purchase", "checkout", "addCart", "add_to_cart", "payment_success"}
TRACKED_EVENTS = ["click", "search", "view", "addCart", "checkout", "purchase"]


@dataclass
class ModelState:
    model: MLPClassifier | None = None
    trained_samples: int = 0


def _safe_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _features_from_events(events: List[Dict[str, Any]]) -> np.ndarray:
    event_counts = {name: 0.0 for name in TRACKED_EVENTS}
    categories = set()
    search_query_len = []

    for event in events:
        event_type = str(event.get("event_type") or "").strip()
        if event_type in event_counts:
            event_counts[event_type] += 1.0
        categories.add(str(event.get("category") or "unknown"))
        q = str(event.get("query_text") or "").strip()
        if q:
            search_query_len.append(float(len(q.split())))

    total = max(len(events), 1)
    vector = [event_counts[name] / total for name in TRACKED_EVENTS]
    vector.append(len(categories) / total)
    vector.append(sum(search_query_len) / max(len(search_query_len), 1))
    return np.array(vector, dtype=np.float32)


def build_training_matrix(all_events: List[Dict[str, Any]]) -> Tuple[np.ndarray, np.ndarray]:
    by_user: Dict[int, List[Dict[str, Any]]] = {}
    for event in all_events:
        try:
            user_id = int(event.get("user_id"))
        except (TypeError, ValueError):
            continue
        by_user.setdefault(user_id, []).append(event)

    xs = []
    ys = []
    for user_events in by_user.values():
        xs.append(_features_from_events(user_events))
        label = 0
        for e in user_events:
            if str(e.get("event_type") or "") in POSITIVE_EVENTS:
                label = 1
                break
        ys.append(label)

    if not xs:
        return np.zeros((0, len(TRACKED_EVENTS) + 2), dtype=np.float32), np.zeros((0,), dtype=np.int32)

    return np.vstack(xs), np.array(ys, dtype=np.int32)


def train_deep_model(state: ModelState, all_events: List[Dict[str, Any]]) -> Dict[str, Any]:
    x, y = build_training_matrix(all_events)
    if len(x) < 5:
        return {
            "trained": False,
            "reason": "not_enough_samples",
            "trained_samples": int(len(x)),
            "required_minimum": 5,
        }

    clf = MLPClassifier(hidden_layer_sizes=(32, 16), activation="relu", max_iter=300, random_state=42)
    clf.fit(x, y)
    state.model = clf
    state.trained_samples = int(len(x))

    probs = clf.predict_proba(x)[:, 1] if hasattr(clf, "predict_proba") else np.zeros((len(x),), dtype=np.float32)
    return {
        "trained": True,
        "trained_samples": int(len(x)),
        "mean_purchase_propensity": round(float(np.mean(probs)), 4),
        "model_type": "MLPClassifier",
        "feature_count": int(x.shape[1]),
    }


def predict_user_propensity(state: ModelState, user_events: List[Dict[str, Any]]) -> float:
    if not user_events:
        return 0.2
    if state.model is None:
        # Rule-based fallback before model is trained.
        add_cart = sum(1 for e in user_events if str(e.get("event_type")) in {"addCart", "add_to_cart"})
        checkout = sum(1 for e in user_events if str(e.get("event_type")) in {"checkout", "purchase"})
        base = 0.25 + min(add_cart * 0.08, 0.3) + min(checkout * 0.12, 0.35)
        return round(float(min(max(base, 0.05), 0.97)), 4)

    x = _features_from_events(user_events).reshape(1, -1)
    prob = float(state.model.predict_proba(x)[0][1])
    return round(float(min(max(prob, 0.01), 0.99)), 4)


def recommend_products(user_events: List[Dict[str, Any]], candidates: List[Dict[str, Any]], top_k: int) -> List[Dict[str, Any]]:
    category_scores: Dict[str, float] = {}
    for e in user_events:
        cat = str(e.get("category") or "").strip().lower()
        if not cat:
            continue
        et = str(e.get("event_type") or "")
        weight = 0.1
        if et in {"view", "click"}:
            weight = 0.2
        elif et in {"addCart", "add_to_cart"}:
            weight = 0.4
        elif et in {"checkout", "purchase"}:
            weight = 0.6
        category_scores[cat] = category_scores.get(cat, 0.0) + weight

    ranked = []
    for idx, product in enumerate(candidates):
        pid = int(product.get("id") or product.get("product_id") or 0)
        if pid <= 0:
            continue
        cat = str(product.get("category") or "").strip().lower()
        title = str(product.get("title") or "").strip().lower()
        score = 0.15 + max(category_scores.get(cat, 0.0), 0.0)
        for token, val in category_scores.items():
            if token and token in title:
                score += min(val, 0.25)
        score -= idx * 0.01
        ranked.append(
            {
                "product_id": pid,
                "score": round(float(min(max(score, 0.01), 0.99)), 4),
                "reason": "Matched behavior patterns and category affinity",
            }
        )

    ranked.sort(key=lambda x: x["score"], reverse=True)
    return ranked[: max(1, top_k)]
