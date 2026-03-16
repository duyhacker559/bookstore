from django.http import JsonResponse, Http404
from django.forms.models import model_to_dict
from store.models.book.book import Book
from store.models.author.author import Author
from store.auth import require_api_auth


@require_api_auth
def book_list_api(request):
    """Get all books - Requires authentication"""
    books = Book.objects.prefetch_related("categories_m2m").all()
    data = [
        {
            "id": b.id,
            "title": b.title,
            "author": b.author,
            "price": float(b.price),
            "stock": b.stock,
            "category": b.primary_category,
            "categories": b.category_names,
        }
        for b in books
    ]
    return JsonResponse({"books": data})


@require_api_auth
def book_detail_api(request, book_id):
    """Get book details - Requires authentication"""
    try:
        b = Book.objects.prefetch_related("categories_m2m").get(id=book_id)
    except Book.DoesNotExist:
        raise Http404("Book not found")
    data = model_to_dict(b, fields=["id", "title", "author", "price", "stock", "description", "rating", "review_count"])
    data["price"] = float(data["price"]) if data.get("price") is not None else None
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
