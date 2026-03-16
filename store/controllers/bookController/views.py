from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.db.models import Count, Q
from store.models.book.book import Book
from store.models.category.category import Category


def book_list(request):
    return _render_book_list(request, catalog_only=False)


def book_catalog(request):
    return _render_book_list(request, catalog_only=True)


def _render_book_list(request, catalog_only=False):
    books = Book.objects.prefetch_related("images", "categories_m2m").all()

    # Search
    q = request.GET.get("q", "").strip()
    if q:
        books = books.filter(
            Q(title__icontains=q)
            | Q(author__icontains=q)
            | Q(author_fk__name__icontains=q)
            | Q(category__icontains=q)
            | Q(category_fk__name__icontains=q)
            | Q(categories_m2m__name__icontains=q)
        )

    categories = []
    min_price = ""
    max_price = ""
    min_rating = ""
    in_stock = ""
    sort_by = "featured"

    if catalog_only:
        # Category filter
        categories = request.GET.getlist("cat")
        if categories:
            books = books.filter(
                Q(categories_m2m__name__in=categories)
                | Q(category__in=categories)
                | Q(category_fk__name__in=categories)
            )

        # Price filter
        min_price = request.GET.get("min_price")
        max_price = request.GET.get("max_price")

        if min_price:
            books = books.filter(price__gte=min_price)
        if max_price:
            books = books.filter(price__lte=max_price)

        # Rating filter
        min_rating = request.GET.get("min_rating")
        if min_rating:
            books = books.filter(rating__gte=min_rating)

        # Stock filter
        in_stock = request.GET.get("in_stock")
        if in_stock == "1":
            books = books.filter(stock__gt=0)

        # Sorting
        sort_by = request.GET.get("sort", "name")
        if sort_by == "price_low":
            books = books.order_by("price")
        elif sort_by == "price_high":
            books = books.order_by("-price")
        elif sort_by == "rating":
            books = books.order_by("-rating")
        else:
            books = books.order_by("title")
    else:
        # Home page keeps a simple, curated ordering and no filter controls.
        books = books.order_by("-rating", "title")

    books = books.distinct()

    # Pagination
    paginator = Paginator(books, 12)
    page_number = request.GET.get("page", 1)
    page_obj = paginator.get_page(page_number)

    # Attach cover image to each visible book
    for book in page_obj.object_list:
        cover = book.images.filter(is_cover=True).first() or book.images.first()
        book.cover_image = cover.image.url if cover and cover.image else ""

    # Get all unique categories for filter sidebar (catalog page only)
    category_counts = {}
    active_filters_count = 0
    if catalog_only:
        for category_obj in Category.objects.annotate(book_count=Count("books_multi", distinct=True)).order_by("name"):
            if category_obj.name and category_obj.book_count:
                category_counts[category_obj.name] = category_obj.book_count

        active_filters_count = len(categories)
        if min_price:
            active_filters_count += 1
        if max_price:
            active_filters_count += 1
        if min_rating:
            active_filters_count += 1
        if in_stock == "1":
            active_filters_count += 1

    recommended_books = []
    if not catalog_only:
        recommended_books = list(
            Book.objects.prefetch_related("images", "categories_m2m")
            .filter(stock__gt=0)
            .order_by("-rating", "title")[:4]
        )
        for recommended in recommended_books:
            cover = recommended.images.filter(is_cover=True).first() or recommended.images.first()
            recommended.cover_image = cover.image.url if cover and cover.image else ""

    return render(
        request,
        "book/list.html",
        {
            "catalog_only": catalog_only,
            "page_obj": page_obj,
            "books": page_obj.object_list,
            "total_books": paginator.count,
            "q": q,
            "min_price": min_price,
            "max_price": max_price,
            "min_rating": min_rating,
            "in_stock": in_stock,
            "sort_by": sort_by,
            "selected_categories": categories,
            "category_counts": category_counts,
            "active_filters_count": active_filters_count,
            "recommended_books": recommended_books,
        },
    )


def book_detail(request, book_id):
    book = get_object_or_404(Book.objects.prefetch_related("images", "categories_m2m"), id=book_id)
    cover = book.images.filter(is_cover=True).first() or book.images.first()
    book.cover_image = cover.image.url if cover and cover.image else ""
    return render(request, "book/detail.html", {"book": book})
