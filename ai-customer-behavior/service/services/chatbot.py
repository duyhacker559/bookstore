import json
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional


def generate_with_gemini(
    api_key: str,
    model: str,
    api_version: str,
    question: str,
    rag_chunks: List[Dict[str, Any]],
    trend_categories: List[Dict[str, Any]],
    fallback_answer: str,
) -> Optional[str]:
    if not api_key:
        return None

    url = f"https://generativelanguage.googleapis.com/{api_version}/models/{model}:generateContent?key={api_key}"
    prompt_payload = {
        "instruction": (
            "Bạn là AI tư vấn mua sắm cho hệ thống bookstore. "
            "Trả lời bằng tiếng Việt, ngắn gọn, có lý do rõ ràng. "
            "Ưu tiên dùng thông tin từ hành vi người dùng và tri thức đồ thị cung cấp."
        ),
        "question": question,
        "rag_chunks": rag_chunks,
        "trend_categories": trend_categories,
        "fallback_answer": fallback_answer,
    }

    body = {
        "contents": [{"role": "user", "parts": [{"text": json.dumps(prompt_payload, ensure_ascii=False)}]}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 400,
        },
    }

    req = urllib.request.Request(
        url=url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=12) as response:
            data = json.loads(response.read().decode("utf-8"))
        candidates = data.get("candidates") if isinstance(data, dict) else []
        if not candidates:
            return None
        parts = candidates[0].get("content", {}).get("parts", [])
        texts = [p.get("text", "") for p in parts if isinstance(p, dict)]
        content = "\n".join(t for t in texts if t).strip()
        return content or None
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None
