from collections import Counter
from typing import Dict, List, Optional

from django.utils import timezone

SESSION_KEY = "ai_behavior_events"
MAX_EVENTS = 60


def track_behavior_event(request, event_type: str, product=None, metadata: Optional[Dict] = None) -> None:
    events = request.session.get(SESSION_KEY, [])
    event: Dict = {
        "type": (event_type or "unknown").strip().lower(),
        "timestamp": timezone.now().isoformat(),
    }

    if product is not None:
        event["product_id"] = int(product.id)
        event["product_type"] = str(getattr(product, "product_type", "") or "").strip().lower()
        event["title"] = str(getattr(product, "title", "") or "")

    if metadata and isinstance(metadata, dict):
        event["metadata"] = metadata

    events.append(event)
    if len(events) > MAX_EVENTS:
        events = events[-MAX_EVENTS:]

    request.session[SESSION_KEY] = events
    request.session.modified = True


def get_recent_behavior_events(request, limit: int = 20) -> List[Dict]:
    events = request.session.get(SESSION_KEY, [])
    if not isinstance(events, list):
        return []
    valid = [item for item in events if isinstance(item, dict)]
    return valid[-limit:]


def get_recently_viewed_product_ids(request, limit: int = 12) -> List[int]:
    events = get_recent_behavior_events(request, limit=MAX_EVENTS)
    seen = set()
    product_ids: List[int] = []

    for event in reversed(events):
        if event.get("type") != "product_detail_view":
            continue
        try:
            product_id = int(event.get("product_id"))
        except (TypeError, ValueError):
            continue
        if product_id in seen:
            continue
        seen.add(product_id)
        product_ids.append(product_id)
        if len(product_ids) >= limit:
            break

    return product_ids


def infer_preferred_category_from_events(request) -> str:
    events = get_recent_behavior_events(request, limit=MAX_EVENTS)
    counter: Counter = Counter()

    for event in events:
        if event.get("type") != "product_detail_view":
            continue
        product_type = str(event.get("product_type") or "").strip().lower()
        if product_type:
            counter[product_type] += 1

    if not counter:
        return ""
    return counter.most_common(1)[0][0]


def build_session_event_signals(request, limit: int = 30) -> List[str]:
    events = get_recent_behavior_events(request, limit=limit)
    signals: List[str] = []

    for event in events:
        event_type = str(event.get("type") or "").strip().lower()
        if not event_type:
            continue
        signals.append(event_type)
        product_type = str(event.get("product_type") or "").strip().lower()
        if product_type:
            signals.append(f"{event_type}:{product_type}")

    return signals[-limit:]
