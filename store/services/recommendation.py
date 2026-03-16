# store/services/recommendation.py

from store.models import Book

def recommend_books(book, limit=4):
    return Book.objects.exclude(id=book.id)[:limit]
