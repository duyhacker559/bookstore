import logging
import json
from pathlib import Path
import re
import unicodedata
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel

from config import get_settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)
settings = get_settings()

app = FastAPI(
    title=settings.API_TITLE,
    version=settings.API_VERSION,
    description="Behavior scoring and product recommendation microservice",
)


class ScoreContext(BaseModel):
    hour: Optional[int] = None
    device: Optional[str] = None
    preferred_category: Optional[str] = None
    budget_max: Optional[float] = None
    query_text: Optional[str] = None


class BehaviorScoreRequest(BaseModel):
    user_id: int
    session_events: List[str] = []
    context: ScoreContext = ScoreContext()


class RecommendRequest(BaseModel):
    user_id: int
    candidate_product_ids: List[int] = []
    candidate_products: List[Dict[str, Any]] = []
    context: Dict[str, Any] = {}
    top_k: int = 5


class FeedbackRequest(BaseModel):
    user_id: int
    product_id: int
    feedback_type: str


class TrainSample(BaseModel):
    text: str
    category: str


class TrainRequest(BaseModel):
    samples: List[TrainSample] = []


def _check_auth(auth_header: Optional[str]) -> None:
    expected = f"Bearer {settings.AUTH_TOKEN}"
    if auth_header != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


CATEGORY_SYNONYMS: Dict[str, set[str]] = {
    "programming": {
        "python",
        "lap trinh",
        "coding",
        "code",
        "cong nghe",
        "ky thuat",
    },
    "fashion": {
        "thoi trang",
        "hang hieu",
        "fashion",
        "hoodie",
        "ao",
        "quan",
    },
    "romance": {
        "tinh cam",
        "lang man",
        "ngon tinh",
        "romance",
    },
    "war_history": {
        "chien tranh",
        "lich su",
        "quan su",
        "war",
    },
    "business": {
        "kinh doanh",
        "business",
        "startup",
        "quan tri",
    },
    "self_help": {
        "phat trien ban than",
        "self help",
        "ky nang",
        "dong luc",
    },
}

TRAINED_SYNONYMS: Dict[str, set[str]] = {}


def _load_trained_synonyms() -> None:
    path = Path(settings.TRAIN_DATA_PATH)
    if not path.exists():
        return

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not load behavior train data: %s", exc)
        return

    if not isinstance(payload, dict):
        return

    loaded_count = 0
    for category, values in payload.items():
        if not isinstance(category, str) or not isinstance(values, list):
            continue
        normalized_category = _canonical_category(category)
        tokens = {str(item).strip().lower() for item in values if isinstance(item, str) and str(item).strip()}
        if not normalized_category or not tokens:
            continue
        TRAINED_SYNONYMS.setdefault(normalized_category, set()).update(tokens)
        loaded_count += len(tokens)

    if loaded_count:
        logger.info("Loaded %s trained behavior tokens from %s", loaded_count, path)


def _save_trained_synonyms() -> bool:
    path = Path(settings.TRAIN_DATA_PATH)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {category: sorted(values) for category, values in TRAINED_SYNONYMS.items() if values}
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return True
    except OSError as exc:
        logger.warning("Could not save behavior train data: %s", exc)
        return False


def _normalize_text(text: str) -> str:
    lowered = (text or "").lower().strip()
    decomposed = unicodedata.normalize("NFD", lowered)
    ascii_text = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", ascii_text).strip()


def _tokenize(text: str) -> List[str]:
    normalized = _normalize_text(text)
    return [token for token in re.split(r"[^a-z0-9]+", normalized) if token]


def _all_synonyms() -> Dict[str, set[str]]:
    combined: Dict[str, set[str]] = {key: set(values) for key, values in CATEGORY_SYNONYMS.items()}
    for category, values in TRAINED_SYNONYMS.items():
        combined.setdefault(category, set()).update(values)
    return combined


def _canonical_category(raw_value: str) -> str:
    normalized_value = _normalize_text(raw_value)
    if not normalized_value:
        return ""

    synonyms = _all_synonyms()
    if normalized_value in synonyms:
        return normalized_value

    for category, tokens in synonyms.items():
        if normalized_value == category or normalized_value in tokens:
            return category

    return normalized_value


def _extract_category_weights_from_text(text: str, weight: float) -> Dict[str, float]:
    normalized = _normalize_text(text)
    if not normalized:
        return {}

    result: Dict[str, float] = {}
    for category, tokens in _all_synonyms().items():
        if any(token in normalized for token in tokens):
            result[category] = result.get(category, 0.0) + weight
    return result


def _extract_event_weights(session_events: List[str], query_text: str = "") -> Dict[str, float]:
    category_scores: Dict[str, float] = {}

    for event in session_events:
        for category, value in _extract_category_weights_from_text(str(event or ""), weight=0.2).items():
            category_scores[category] = category_scores.get(category, 0.0) + value

    for category, value in _extract_category_weights_from_text(query_text, weight=0.25).items():
        category_scores[category] = category_scores.get(category, 0.0) + value

    return category_scores


def _score_candidate(
    candidate: Dict[str, Any],
    preferred_category: str,
    budget_max: Optional[float],
    event_weights: Dict[str, float],
    index_position: int,
) -> tuple[float, str]:
    base = max(0.35, 0.8 - (index_position * 0.03))
    reason = "Matches your recent browsing pattern"

    category = _normalize_text(str(candidate.get("category") or ""))
    title = _normalize_text(str(candidate.get("title") or ""))
    price = candidate.get("price")
    preferred = _canonical_category(preferred_category)

    if preferred and preferred in (category + " " + title):
        base += 0.18
        reason = "Aligned with your preferred category"

    event_bonus = 0.0
    for token, weight in event_weights.items():
        if token in category or token in title:
            event_bonus += weight
    if event_bonus > 0:
        base += min(event_bonus, 0.2)
        reason = "Similar to categories you interacted with"

    if budget_max is not None:
        try:
            if float(price) <= float(budget_max):
                base += 0.08
                reason = "Fits your expected budget"
            else:
                base -= 0.1
        except (TypeError, ValueError):
            pass

    return round(min(max(base, 0.05), 0.99), 4), reason


@app.get("/")
async def root() -> dict:
    return {"service": "behavior-service", "status": "running", "version": settings.API_VERSION}


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "service": "behavior-service", "version": settings.API_VERSION}


@app.get("/api/v1/behavior/train/snapshot")
async def train_snapshot(authorization: Optional[str] = Header(default=None)) -> dict:
    _check_auth(authorization)
    return {
        "categories": {key: sorted(list(values)) for key, values in TRAINED_SYNONYMS.items()},
        "train_data_path": settings.TRAIN_DATA_PATH,
        "model_version": "behavior-rules-v3-vi",
    }


@app.post("/api/v1/behavior/score")
async def score_behavior(payload: BehaviorScoreRequest, authorization: Optional[str] = Header(default=None)) -> dict:
    _check_auth(authorization)

    event_bonus = min(len(payload.session_events) * 0.03, 0.2)
    purchase_propensity = 0.32 + event_bonus

    if payload.context.hour is not None and 19 <= payload.context.hour <= 23:
        purchase_propensity += 0.08
    if payload.context.device and payload.context.device.lower() in {"mobile", "android", "ios"}:
        purchase_propensity += 0.03

    purchase_propensity = round(min(max(purchase_propensity, 0.05), 0.97), 4)
    event_weights = _extract_event_weights(payload.session_events, query_text=payload.context.query_text or "")

    ranked_categories = sorted(event_weights.items(), key=lambda x: x[1], reverse=True)
    next_best_categories = [item[0] for item in ranked_categories[:3]]
    if payload.context.preferred_category:
        preferred = _canonical_category(payload.context.preferred_category)
        if preferred and preferred not in next_best_categories:
            next_best_categories.insert(0, preferred)
    if not next_best_categories:
        next_best_categories = ["programming", "fashion", "romance"]

    value_band = "medium"
    if payload.context.budget_max is not None:
        try:
            budget = float(payload.context.budget_max)
            if budget < 20:
                value_band = "low"
            elif budget > 80:
                value_band = "high"
        except (TypeError, ValueError):
            value_band = "medium"

    return {
        "user_id": payload.user_id,
        "purchase_propensity": purchase_propensity,
        "next_best_categories": next_best_categories,
        "value_band": value_band,
        "model_version": "behavior-rules-v3-vi",
    }


@app.post("/api/v1/behavior/recommend")
async def recommend_products(payload: RecommendRequest, authorization: Optional[str] = Header(default=None)) -> dict:
    _check_auth(authorization)

    preferred_category = _canonical_category(str(payload.context.get("preferred_category") or "").strip())
    budget_max = payload.context.get("budget_max")
    session_events = payload.context.get("session_events") if isinstance(payload.context.get("session_events"), list) else []
    query_text = str(payload.context.get("query_text") or "")
    event_weights = _extract_event_weights(session_events, query_text=query_text)

    if payload.candidate_products:
        candidates = payload.candidate_products
    else:
        candidates = [{"id": pid, "title": f"Product {pid}", "category": "", "price": None} for pid in payload.candidate_product_ids]

    scored = []
    for idx, candidate in enumerate(candidates):
        try:
            product_id = int(candidate.get("id") or candidate.get("product_id"))
        except (TypeError, ValueError):
            continue
        score, reason = _score_candidate(candidate, preferred_category, budget_max, event_weights, idx)
        scored.append(
            {
                "product_id": product_id,
                "score": score,
                "reason": reason,
            }
        )

    if not scored:
        fallback_ids = payload.candidate_product_ids[: payload.top_k] if payload.candidate_product_ids else [101, 205, 309][: payload.top_k]
        scored = [
            {
                "product_id": pid,
                "score": round(0.75 - (idx * 0.05), 4),
                "reason": "Popular among similar customers",
            }
            for idx, pid in enumerate(fallback_ids)
        ]

    scored.sort(key=lambda item: item["score"], reverse=True)
    ranked = scored[: payload.top_k]

    recommendations = []
    for recommendation in ranked:
        recommendations.append(
            {
                "product_id": recommendation["product_id"],
                "score": recommendation["score"],
                "reason": recommendation["reason"],
            }
        )

    return {
        "user_id": payload.user_id,
        "top_k": payload.top_k,
        "recommendations": recommendations,
    }


@app.post("/api/v1/behavior/train")
async def train_behavior(payload: TrainRequest, authorization: Optional[str] = Header(default=None)) -> dict:
    _check_auth(authorization)

    trained = 0
    for sample in payload.samples:
        category = _canonical_category(sample.category)
        if not category:
            continue

        tokens = set(_tokenize(sample.text))
        normalized_phrase = _normalize_text(sample.text)
        if normalized_phrase:
            tokens.add(normalized_phrase)

        filtered = {token for token in tokens if len(token) >= 2}
        if not filtered:
            continue

        TRAINED_SYNONYMS.setdefault(category, set()).update(filtered)
        trained += 1

    persisted = _save_trained_synonyms()

    return {
        "status": "trained",
        "trained_samples": trained,
        "categories": sorted(TRAINED_SYNONYMS.keys()),
        "persisted": persisted,
        "train_data_path": settings.TRAIN_DATA_PATH,
        "model_version": "behavior-rules-v3-vi",
    }


_load_trained_synonyms()


@app.post("/api/v1/behavior/feedback")
async def behavior_feedback(payload: FeedbackRequest, authorization: Optional[str] = Header(default=None)) -> dict:
    _check_auth(authorization)

    logger.info("behavior feedback user=%s product=%s type=%s", payload.user_id, payload.product_id, payload.feedback_type)
    return {"status": "accepted", "message": "Feedback captured"}

