# store/services/recommendation.py

from store.models import Product

def recommend_books(product, limit=4):
    return Product.objects.exclude(id=product.id)[:limit]
