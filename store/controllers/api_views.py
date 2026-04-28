import json

from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.forms.models import model_to_dict
from store.models.product.product import Book
from store.models.author.author import Author
from store.auth import require_api_auth
from store.behavior_client import BehaviorClient, BehaviorServiceError, BehaviorServiceUnavailable
from store.rag_client import RAGClient, RAGServiceError, RAGServiceUnavailable
from store.ai_behavior_client import AIBehaviorClient, AIBehaviorServiceError, AIBehaviorServiceUnavailable


@require_api_auth
def product_list_api(request):
    """Get all books - Requires authentication"""
    books = Book.objects.prefetch_related("categories_m2m").all()
    data = [
        {
            "id": b.id,
            "title": b.title,
            "product_type": b.product_type,
            "author": b.author,
            "brand": b.brand,
            "creator": b.creator_display,
            "price": float(b.price),
            "stock": b.stock,
            "category": b.primary_category,
            "categories": b.category_names,
        }
        for b in books
    ]
    return JsonResponse({"books": data})


@require_api_auth
def product_detail_api(request, book_id):
    """Get book details - Requires authentication"""
    try:
        b = Book.objects.prefetch_related("categories_m2m").get(id=book_id)
    except Book.DoesNotExist:
        raise Http404("Book not found")
    data = model_to_dict(
        b,
        fields=[
            "id",
            "title",
            "product_type",
            "author",
            "brand",
            "price",
            "stock",
            "description",
            "rating",
            "review_count",
            "size_options",
            "material",
            "gender_target",
        ],
    )
    data["price"] = float(data["price"]) if data.get("price") is not None else None
    data["creator"] = b.creator_display
    data["category"] = b.primary_category
    data["categories"] = b.category_names
    return JsonResponse({"book": data})


@require_api_auth
def author_list_api(request):
    """Get all authors - Requires authentication"""
    authors = Author.objects.all()
    data = [model_to_dict(a, fields=["id", "name"]) for a in authors]
    return JsonResponse({"authors": data})


@require_api_auth
def author_detail_api(request, author_id):
    """Get author details - Requires authentication"""
    try:
        a = Author.objects.get(id=author_id)
    except Author.DoesNotExist:
        raise Http404("Author not found")
    data = model_to_dict(a)
    return JsonResponse({"author": data})


def _json_payload(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None


@csrf_exempt
@require_api_auth
def ai_recommend_gateway(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    payload = _json_payload(request)
    if payload is None:
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    user_id = payload.get("user_id")
    if not user_id:
        return JsonResponse({"error": "Missing user_id"}, status=400)

    top_k = payload.get("top_k", 5)
    candidate_product_ids = payload.get("candidate_product_ids", [])

    client = BehaviorClient()
    try:
        result = client.recommend(
            user_id=int(user_id),
            candidate_product_ids=candidate_product_ids,
            top_k=int(top_k),
        )
        return JsonResponse(result)
    except BehaviorServiceUnavailable as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    except BehaviorServiceError as exc:
        return JsonResponse({"error": str(exc)}, status=400)


@csrf_exempt
@require_api_auth
def ai_chat_gateway(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    payload = _json_payload(request)
    if payload is None:
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    session_id = payload.get("session_id", "web-session")
    user_id = payload.get("user_id")
    question = payload.get("question", "").strip()
    context = payload.get("context", {})

    if not user_id:
        return JsonResponse({"error": "Missing user_id"}, status=400)
    if not question:
        return JsonResponse({"error": "Missing question"}, status=400)

    client = RAGClient()
    try:
        result = client.query_chat(
            session_id=session_id,
            user_id=int(user_id),
            question=question,
            context=context,
        )
        return JsonResponse(result)
    except RAGServiceUnavailable as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    except RAGServiceError as exc:
        return JsonResponse({"error": str(exc)}, status=400)


@csrf_exempt
@require_api_auth
def ai_advanced_recommend_gateway(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    payload = _json_payload(request)
    if payload is None:
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    user_id = payload.get("user_id")
    if not user_id:
        return JsonResponse({"error": "Missing user_id"}, status=400)

    top_k = payload.get("top_k", 5)
    candidate_products = payload.get("candidate_products", [])

    client = AIBehaviorClient()
    try:
        result = client.recommend(
            user_id=int(user_id),
            top_k=int(top_k),
            candidate_products=candidate_products if isinstance(candidate_products, list) else [],
        )
        return JsonResponse(result)
    except AIBehaviorServiceUnavailable as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    except AIBehaviorServiceError as exc:
        return JsonResponse({"error": str(exc)}, status=400)


@csrf_exempt
@require_api_auth
def ai_advanced_chat_gateway(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    payload = _json_payload(request)
    if payload is None:
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    user_id = payload.get("user_id")
    question = str(payload.get("question") or "").strip()
    session_id = str(payload.get("session_id") or "web-session")
    context = payload.get("context") if isinstance(payload.get("context"), dict) else {}

    if not user_id:
        return JsonResponse({"error": "Missing user_id"}, status=400)
    if not question:
        return JsonResponse({"error": "Missing question"}, status=400)

    client = AIBehaviorClient()
    try:
        result = client.chat(
            user_id=int(user_id),
            question=question,
            session_id=session_id,
            context=context,
        )
        return JsonResponse(result)
    except AIBehaviorServiceUnavailable as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    except AIBehaviorServiceError as exc:
        return JsonResponse({"error": str(exc)}, status=400)


@csrf_exempt
@require_api_auth
def ai_advanced_events_gateway(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    payload = _json_payload(request)
    if payload is None:
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    client = AIBehaviorClient()
    try:
        if isinstance(payload.get("events"), list):
            result = client.ingest_batch(payload.get("events") or [])
        else:
            result = client.ingest_event(payload)
        return JsonResponse(result)
    except AIBehaviorServiceUnavailable as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    except AIBehaviorServiceError as exc:
        return JsonResponse({"error": str(exc)}, status=400)


@csrf_exempt
@require_api_auth
def ai_advanced_train_gateway(request):
    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    payload = _json_payload(request)
    if payload is None:
        return JsonResponse({"error": "Invalid JSON payload"}, status=400)

    min_events = payload.get("min_events", 50)
    client = AIBehaviorClient()
    try:
        result = client.train(min_events=int(min_events))
        return JsonResponse(result)
    except AIBehaviorServiceUnavailable as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    except AIBehaviorServiceError as exc:
        return JsonResponse({"error": str(exc)}, status=400)


@require_api_auth
def ai_advanced_trends_gateway(request):
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        top_k = int(request.GET.get("top_k", "5"))
    except ValueError:
        return JsonResponse({"error": "Invalid top_k"}, status=400)

    client = AIBehaviorClient()
    try:
        result = client.trends(top_k=top_k)
        return JsonResponse(result)
    except AIBehaviorServiceUnavailable as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    except AIBehaviorServiceError as exc:
        return JsonResponse({"error": str(exc)}, status=400)


@require_api_auth
def ai_advanced_alerts_gateway(request):
    if request.method != "GET":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    client = AIBehaviorClient()
    try:
        result = client.alerts()
        return JsonResponse(result)
    except AIBehaviorServiceUnavailable as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    except AIBehaviorServiceError as exc:
        return JsonResponse({"error": str(exc)}, status=400)
