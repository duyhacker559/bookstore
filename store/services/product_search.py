"""
Product Search & Filter - Search and filter products based on category-specific attributes
"""

from django.db.models import Q, QuerySet
from store.models import Book


class ProductSearchFilter:
    """Handles search and filtering of products based on category attributes"""
    
    @staticmethod
    def filter_by_category(queryset: QuerySet, product_type: str) -> QuerySet:
        """Filter products by category (book or clothing)"""
        if product_type in ['book', 'clothing']:
            return queryset.filter(product_type=product_type)
        return queryset
    
    @staticmethod
    def search_books(queryset: QuerySet, query: str) -> QuerySet:
        """Search books by title, author, publisher"""
        return queryset.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
            # Note: JSONField search would need database-specific queries
            # For now, use full-text search in application layer
        )
    
    @staticmethod
    def search_clothing(queryset: QuerySet, query: str) -> QuerySet:
        """Search clothing by title, brand, material"""
        return queryset.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query)
        )
    
    @staticmethod
    def search(queryset: QuerySet, query: str, product_type: str = None) -> QuerySet:
        """Universal search that adapts to product type"""
        if not query:
            return queryset
        
        if product_type == 'book':
            return ProductSearchFilter.search_books(queryset, query)
        elif product_type == 'clothing':
            return ProductSearchFilter.search_clothing(queryset, query)
        else:
            # Search all products
            return queryset.filter(
                Q(title__icontains=query) |
                Q(description__icontains=query)
            )
    
    @staticmethod
    def filter_books_by_author(queryset: QuerySet, author: str) -> QuerySet:
        """Filter books by author (in-memory since it's in JSONField)"""
        results = []
        for product in queryset.filter(product_type='book'):
            if isinstance(product.attributes, dict):
                book_details = product.attributes.get('book_details', {})
                if book_details.get('author', '').lower() == author.lower():
                    results.append(product.id)
        return queryset.filter(id__in=results) if results else queryset.none()
    
    @staticmethod
    def filter_clothing_by_brand(queryset: QuerySet, brand: str) -> QuerySet:
        """Filter clothing by brand (in-memory since it's in JSONField)"""
        results = []
        for product in queryset.filter(product_type='clothing'):
            if isinstance(product.attributes, dict):
                clothing_details = product.attributes.get('clothing_details', {})
                if clothing_details.get('brand', '').lower() == brand.lower():
                    results.append(product.id)
        return queryset.filter(id__in=results) if results else queryset.none()
    
    @staticmethod
    def filter_clothing_by_size(queryset: QuerySet, size: str) -> QuerySet:
        """Filter clothing by available size"""
        results = []
        for product in queryset.filter(product_type='clothing'):
            if isinstance(product.attributes, dict):
                clothing_details = product.attributes.get('clothing_details', {})
                sizes = clothing_details.get('sizes', '')
                size_list = [s.strip() for s in sizes.split(',')]
                if size.upper() in [s.upper() for s in size_list]:
                    results.append(product.id)
        return queryset.filter(id__in=results) if results else queryset.none()
    
    @staticmethod
    def filter_by_price_range(queryset: QuerySet, min_price: float = None, max_price: float = None) -> QuerySet:
        """Filter products by price range"""
        if min_price is not None:
            queryset = queryset.filter(price__gte=min_price)
        if max_price is not None:
            queryset = queryset.filter(price__lte=max_price)
        return queryset
    
    @staticmethod
    def filter_by_stock(queryset: QuerySet, in_stock_only: bool = False) -> QuerySet:
        """Filter products by stock availability"""
        if in_stock_only:
            return queryset.filter(stock__gt=0)
        return queryset


# Usage Example:
# 
# books = ProductSearchFilter.filter_by_category(Book.objects.all(), 'book')
# results = ProductSearchFilter.search(books, 'python', product_type='book')
# results = ProductSearchFilter.filter_books_by_author(results, 'John Doe')
# results = ProductSearchFilter.filter_by_price_range(results, min_price=100, max_price=500)
#
# clothing = ProductSearchFilter.filter_by_category(Book.objects.all(), 'clothing')
# results = ProductSearchFilter.filter_clothing_by_brand(clothing, 'Nike')
# results = ProductSearchFilter.filter_clothing_by_size(results, 'M')
