import logging
import json
import re
import unicodedata
import urllib.error
import urllib.request
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
    description="RAG microservice for consulting chat and KB retrieval",
)


class ChatRequest(BaseModel):
    session_id: str
    user_id: int
    question: str
    context: Dict[str, Any] = {}


class FeedbackRequest(BaseModel):
    session_id: str
    user_id: int
    helpful: bool
    note: Optional[str] = None


class KBSearchRequest(BaseModel):
    query: str
    top_k: int = 5
    category: Optional[str] = None


KB_DOCS = [
    {
        "chunk_id": "chunk_policy_refund",
        "title": "Refund policy",
        "content": "Eligible products can be refunded according to the return window and condition rules.",
        "source_ref": "docs/policy/refund",
        "tags": ["refund", "policy", "return"],
    },
    {
        "chunk_id": "chunk_shipping_methods",
        "title": "Shipping options",
        "content": "Standard, express, and overnight shipping are available with different fees and timelines.",
        "source_ref": "docs/shipping/options",
        "tags": ["shipping", "delivery", "options"],
    },
    {
        "chunk_id": "chunk_python_books",
        "title": "Beginner Python recommendations",
        "content": "Choose beginner Python books with practical exercises and clear explanations.",
        "source_ref": "catalog/books/python-beginner",
        "tags": ["python", "book", "programming", "beginner"],
    },
]

SUMMER_BOOK_SALE = {
    "name": "SALE SÁCH MÙA HÈ",
    "start_date": "01/04/2026",
    "end_date": "30/04/2026",
    "default_discount_percent": 20,
}


def _check_auth(auth_header: Optional[str]) -> None:
    expected = f"Bearer {settings.AUTH_TOKEN}"
    if auth_header != expected:
        raise HTTPException(status_code=401, detail="Unauthorized")


def _normalize_text(text: str) -> str:
    lowered = (text or "").lower().strip()
    decomposed = unicodedata.normalize("NFD", lowered)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def _tokenize(text: str) -> List[str]:
    normalized = _normalize_text(text)
    return [token for token in re.split(r"[^a-z0-9]+", normalized) if token]


def _detect_intent(question: str) -> str:
    q = _normalize_text(question)
    if any(token in q for token in ["refund", "return", "doi tra", "hoan tien"]):
        return "policy_support"
    if any(token in q for token in ["ship", "shipping", "delivery", "giao hang"]):
        return "shipping_support"
    if any(token in q for token in ["suggest", "recommend", "goi y", "de xuat", "nen mua"]):
        return "product_recommendation"
    if any(token in q for token in ["chien tranh", "war", "lich su quan su"]):
        return "war_book_consulting"
    return "general_consulting"


def _is_opening_question(question: str) -> bool:
    normalized = _normalize_text(question)
    opening_tokens = [
        "tu van",
        "tu van giup",
        "chao",
        "hello",
        "hi",
        "xin chao",
        "toi can goi y",
    ]
    if normalized in opening_tokens:
        return True
    return len(_tokenize(normalized)) <= 3


def _search_kb(question: str, top_k: int = 5) -> List[Dict[str, Any]]:
    q_tokens = set(_tokenize(question))
    scored = []
    for doc in KB_DOCS:
        doc_tokens = set(_tokenize(doc["title"] + " " + doc["content"] + " " + " ".join(doc["tags"])))
        overlap = len(q_tokens.intersection(doc_tokens))
        score = overlap / max(len(q_tokens), 1)
        if score > 0:
            scored.append(
                {
                    "chunk_id": doc["chunk_id"],
                    "title": doc["title"],
                    "content": doc["content"],
                    "score": round(score, 4),
                    "source_ref": doc["source_ref"],
                }
            )

    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k]


def _recommend_from_catalog(question: str, context: Dict[str, Any], top_k: int = 3) -> List[int]:
    hints = context.get("catalog_hints") if isinstance(context.get("catalog_hints"), list) else []
    if not hints:
        return []

    tokens = set(_tokenize(question))
    preferred_category = str(context.get("preferred_category") or "").lower().strip()
    budget_max = context.get("budget_max")
    session_events = context.get("session_events") if isinstance(context.get("session_events"), list) else []

    event_category_tokens = []
    for event in session_events:
        event_str = str(event or "").lower().strip()
        if ":" in event_str:
            parts = event_str.split(":", 1)
            if len(parts) == 2 and parts[1]:
                event_category_tokens.append(parts[1])

    scored = []
    for idx, item in enumerate(hints):
        try:
            product_id = int(item.get("id"))
        except (TypeError, ValueError):
            continue

        title = str(item.get("title") or "")
        category = str(item.get("category") or "")
        text = (title + " " + category).lower()
        item_tokens = set(_tokenize(text))

        score = 0.2 + (len(tokens.intersection(item_tokens)) * 0.2)
        if preferred_category and preferred_category in text:
            score += 0.25
        if any(token and token in text for token in event_category_tokens):
            score += 0.15
        try:
            if budget_max is not None and float(item.get("price")) <= float(budget_max):
                score += 0.12
        except (TypeError, ValueError):
            pass

        score -= idx * 0.01
        scored.append((product_id, score))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    return [pair[0] for pair in scored[:top_k]]


def _find_war_book(context: Dict[str, Any]) -> Dict[str, Any]:
    hints = context.get("catalog_hints") if isinstance(context.get("catalog_hints"), list) else []
    for item in hints:
        text = _normalize_text(str(item.get("title") or "") + " " + str(item.get("category") or ""))
        if any(token in text for token in ["chien tranh", "war", "quan su"]):
            return item

    return {
        "id": 0,
        "title": "Chiến Tranh và Hòa Bình",
        "price": 320000,
        "category": "van hoc nuoc ngoai",
    }


def _build_answer(
    intent: str,
    question: str,
    kb_hits: List[Dict[str, Any]],
    recommended_products: List[int],
    context: Dict[str, Any],
) -> str:
    if _is_opening_question(question):
        return "Bạn cần tư vấn về sách hay thời trang hàng hiệu?"

    if intent == "policy_support":
        return "Theo chính sách hiện tại, bạn có thể đổi/trả hoàn tiền nếu sản phẩm đủ điều kiện trong khung thời gian quy định."
    if intent == "shipping_support":
        return "Hệ thống có các tùy chọn giao hàng standard, express và overnight. Bạn có thể chọn theo thời gian và chi phí mong muốn."
    if intent == "war_book_consulting":
        war_book = _find_war_book(context)
        original_price = float(war_book.get("price") or 320000)
        discount_percent = SUMMER_BOOK_SALE["default_discount_percent"]
        sale_price = int(original_price * (100 - discount_percent) / 100)
        return (
            f"Chào bạn, LUMIÈRE có tựa sách “{war_book.get('title', 'Chiến Tranh và Hòa Bình')}” "
            "rất nổi tiếng trong danh mục sách văn học nước ngoài. "
            f"Hiện tại, sách này đang có ưu đãi đặc biệt trong chương trình {SUMMER_BOOK_SALE['name']} "
            f"của chúng tôi, kéo dài từ ngày {SUMMER_BOOK_SALE['start_date']} đến {SUMMER_BOOK_SALE['end_date']}. "
            f"Giá gốc của “{war_book.get('title', 'Chiến Tranh và Hòa Bình')}” là {int(original_price):,} VND, "
            f"hiện giảm còn {sale_price:,} VND ({discount_percent}% OFF)."
        )
    if intent == "product_recommendation":
        base = "Mình đã phân tích nhu cầu của bạn và chọn các sản phẩm phù hợp hơn."
        if recommended_products:
            return f"{base} Mã sản phẩm gợi ý: {', '.join(str(pid) for pid in recommended_products)}."
        return base + " Hiện chưa tìm được dữ liệu catalog phù hợp, bạn hãy bổ sung ngân sách hoặc thể loại."

    if kb_hits:
        return f"Mình đã tìm thấy thông tin liên quan: {kb_hits[0]['title']}. Bạn muốn mình tóm tắt kỹ hơn không?"
    return f"Mình đã ghi nhận câu hỏi: '{question}'. Bạn có thể thêm bộ lọc ngân sách/thể loại để mình tư vấn chính xác hơn."


def _build_gemini_prompt(
    question: str,
    intent: str,
    recommended_products: List[int],
    context: Dict[str, Any],
    fallback_answer: str,
) -> str:
    preferred_category = context.get("preferred_category")
    budget_max = context.get("budget_max")
    session_events = context.get("session_events") if isinstance(context.get("session_events"), list) else []
    catalog_hints = context.get("catalog_hints") if isinstance(context.get("catalog_hints"), list) else []

    shortlist = []
    for item in catalog_hints[:6]:
        if not isinstance(item, dict):
            continue
        shortlist.append(
            {
                "id": item.get("id"),
                "title": item.get("title"),
                "category": item.get("category"),
                "price": item.get("price"),
            }
        )

    prompt_payload = {
        "instruction": (
            "Bạn là trợ lý tư vấn mua sắm của bookstore LUMIERE. "
            "Trả lời bằng tiếng Việt tự nhiên, tập trung vào giá trị tư vấn mua hàng. "
            "Nếu có sản phẩm đề xuất thì nêu ngắn gọn lý do phù hợp. "
            "Không bịa chính sách ngoài dữ liệu đầu vào."
        ),
        "question": question,
        "intent": intent,
        "preferred_category": preferred_category,
        "budget_max": budget_max,
        "session_events": session_events[-10:],
        "recommended_product_ids": recommended_products,
        "catalog_shortlist": shortlist,
        "fallback_answer": fallback_answer,
    }
    return json.dumps(prompt_payload, ensure_ascii=False)


def _generate_with_gemini(prompt: str) -> Optional[str]:
    if not settings.GOOGLE_API_KEY:
        return None

    model = settings.GEMINI_MODEL or "gemini-2.5-flash"
    api_version = settings.GEMINI_API_VERSION or "v1beta"
    url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model}:generateContent?key={settings.GOOGLE_API_KEY}"
    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "generationConfig": {
            "temperature": 0.5,
            "maxOutputTokens": 512,
        },
    }

    request = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        logger.warning("Gemini HTTP error status=%s detail=%s", exc.code, detail)
        return None
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
        logger.warning("Gemini request failed: %s", exc)
        return None

    candidates = data.get("candidates") if isinstance(data, dict) else None
    if not isinstance(candidates, list) or not candidates:
        return None

    content = candidates[0].get("content") if isinstance(candidates[0], dict) else None
    parts = content.get("parts") if isinstance(content, dict) else None
    if not isinstance(parts, list):
        return None

    for part in parts:
        if isinstance(part, dict) and isinstance(part.get("text"), str) and part["text"].strip():
            return part["text"].strip()
    return None


@app.get("/")
async def root() -> dict:
    return {"service": "rag-service", "status": "running", "version": settings.API_VERSION}


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy", "service": "rag-service", "version": settings.API_VERSION}


@app.post("/api/v1/kb/search")
async def kb_search(payload: KBSearchRequest, authorization: Optional[str] = Header(default=None)) -> dict:
    _check_auth(authorization)
    chunks = _search_kb(payload.query, top_k=payload.top_k)
    if payload.category:
        filtered = [chunk for chunk in chunks if payload.category.lower() in chunk["title"].lower()]
        chunks = filtered if filtered else chunks
    return {"query": payload.query, "results": chunks}


@app.post("/api/v1/chat/query")
async def chat_query(payload: ChatRequest, authorization: Optional[str] = Header(default=None)) -> dict:
    _check_auth(authorization)

    intent = _detect_intent(payload.question)
    kb_hits = _search_kb(payload.question, top_k=3)
    recommended_products = _recommend_from_catalog(payload.question, payload.context, top_k=3)

    if intent == "war_book_consulting" and not recommended_products:
        war_book = _find_war_book(payload.context)
        if war_book.get("id"):
            recommended_products = [int(war_book["id"])]

    fallback_answer = _build_answer(intent, payload.question, kb_hits, recommended_products, payload.context)
    gemini_prompt = _build_gemini_prompt(
        question=payload.question,
        intent=intent,
        recommended_products=recommended_products,
        context=payload.context,
        fallback_answer=fallback_answer,
    )
    answer = _generate_with_gemini(gemini_prompt) or fallback_answer

    return {
        "answer": answer,
        "citations": [hit["chunk_id"] for hit in kb_hits],
        "recommended_products": recommended_products,
        "intent": intent,
    }


@app.post("/api/v1/chat/stream")
async def chat_stream(payload: ChatRequest, authorization: Optional[str] = Header(default=None)) -> Dict[str, List[str]]:
    _check_auth(authorization)
    return {
        "chunks": [
            "De xuat nhanh cho ban: ",
            "Sach nhap mon Python, ",
            "Sach bai tap thuc hanh, ",
            "va mot lua chon nang cao hon.",
        ]
    }


@app.post("/api/v1/chat/feedback")
async def chat_feedback(payload: FeedbackRequest, authorization: Optional[str] = Header(default=None)) -> dict:
    _check_auth(authorization)
    logger.info("chat feedback session=%s user=%s helpful=%s", payload.session_id, payload.user_id, payload.helpful)
    return {"status": "accepted"}
