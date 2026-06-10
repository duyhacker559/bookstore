import json

from django.http import JsonResponse, Http404
from django.views.decorators.csrf import csrf_exempt
from django.forms.models import model_to_dict
from store.models.product.product import Product
from store.models.author.author import Author
from store.auth import require_api_auth
from store.ai_service_client import AIServiceClient, AIServiceError, AIServiceUnavailable


@require_api_auth
def product_list_api(request):
    """Get all books - Requires authentication"""
    books = Product.objects.prefetch_related("categories_m2m").all()
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
    return JsonResponse({"products": data})


@require_api_auth
def product_detail_api(request, book_id):
    """Get book details - Requires authentication"""
    try:
        b = Product.objects.prefetch_related("categories_m2m").get(id=book_id)
    except Product.DoesNotExist:
        raise Http404("Product not found")
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
    return JsonResponse({"product": data})


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

    client = AIServiceClient()
    try:
        result = client.recommend(
            user_id=int(user_id),
            candidate_product_ids=candidate_product_ids,
            candidate_products=payload.get("candidate_products", []),
            events=payload.get("events", []),
            session_events=payload.get("session_events", []),
            query=payload.get("query", ""),
            context=payload.get("context", {}),
            top_k=int(top_k),
        )
        return JsonResponse(result)
    except AIServiceUnavailable as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    except AIServiceError as exc:
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
    question = str(payload.get("question", "")).strip()
    context = payload.get("context", {})

    if not user_id:
        return JsonResponse({"error": "Missing user_id"}, status=400)
    if not question:
        return JsonResponse({"error": "Missing question"}, status=400)

    candidate_products = payload.get("candidate_products", [])
    if candidate_products:
        for product in candidate_products:
            if "id" in product and "product_id" not in product:
                product["product_id"] = product["id"]
    
    if not candidate_products:
        books = Product.objects.prefetch_related("categories_m2m").all()
        candidate_products = [
            {
                "product_id": b.id,
                "title": b.title,
                "product_type": b.product_type,
                "author": b.author,
                "brand": b.brand,
                "creator": b.creator_display,
                "price": float(b.price) if b.price else None,
                "stock": b.stock,
                "category": b.primary_category,
                "categories": b.category_names,
            }
            for b in books
        ]

    client = AIServiceClient()
    try:
        result = client.chat(
            user_id=int(user_id),
            session_id=session_id,
            question=question,
            candidate_products=candidate_products,
            events=payload.get("events", []),
            session_events=payload.get("session_events", []),
            context=context,
            top_k=int(payload.get("top_k", 5)),
        )
        return JsonResponse(result)
    except AIServiceUnavailable as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    except AIServiceError as exc:
        return JsonResponse({"error": str(exc)}, status=400)


