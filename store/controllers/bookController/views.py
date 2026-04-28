from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.urls import reverse
from store.models.product.product import Book
from store.models.category.category import Category
from store.services.ai_behavior_tracking import track_behavior_event


def home(request):
    return _render_catalog(request, catalog_only=False)


def catalog(request):
    return _render_catalog(request, catalog_only=True)


def catalog_redirect(request):
    return redirect("catalog")


def _product_type_labels():
    labels = {key: value for key, value in Book.PRODUCT_TYPE_CHOICES}
    for product_type in Book.objects.values_list("product_type", flat=True).distinct():
        if product_type and product_type not in labels:
            labels[product_type] = product_type.replace("_", " ").title()
    return labels


def _render_catalog(request, catalog_only=False, forced_product_type=None):
    books = Book.objects.prefetch_related("images", "categories_m2m").all()
    scoped_books = Book.objects.prefetch_related("categories_m2m").all()

    # Search
    q = request.GET.get("q", "").strip()
    if q:
        books = books.filter(
            Q(title__icontains=q)
            | Q(author__icontains=q)
            | Q(brand__icontains=q)
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
    product_type = (forced_product_type or request.GET.get("type", "")).strip().lower()

    if product_type in {Book.PRODUCT_TYPE_BOOK, Book.PRODUCT_TYPE_CLOTHING}:
        books = books.filter(product_type=product_type)
        scoped_books = scoped_books.filter(product_type=product_type)

    product_type_labels = _product_type_labels()
    product_type_counts = {
        entry["product_type"]: entry["total"]
        for entry in Book.objects.values("product_type").annotate(total=Count("id"))
        if entry["product_type"]
    }
    available_product_types = [
        {
            "value": type_key,
            "label": product_type_labels.get(type_key, type_key.replace("_", " ").title()),
            "count": product_type_counts.get(type_key, 0),
        }
        for type_key in sorted(product_type_counts.keys())
    ]

    top_product_type_label = "Products"
    if available_product_types:
        top_product_type_label = max(available_product_types, key=lambda item: item["count"])["label"]

    show_type_filter = forced_product_type is None
    catalog_url_name = "catalog"
    catalog_url = reverse(catalog_url_name)
    collection_title = "Our Store Collection"
    collection_subtitle = "Discover books, apparel, and more in one catalog"

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
        for category_obj in Category.objects.filter(books_multi__in=scoped_books).annotate(book_count=Count("books_multi", distinct=True)).distinct().order_by("name"):
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
        if product_type in {Book.PRODUCT_TYPE_BOOK, Book.PRODUCT_TYPE_CLOTHING}:
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
            "product_type": product_type,
            "show_type_filter": show_type_filter,
            "catalog_url_name": catalog_url_name,
            "catalog_url": catalog_url,
            "collection_title": collection_title,
            "collection_subtitle": collection_subtitle,
            "available_product_types": available_product_types,
            "top_product_type_label": top_product_type_label,
            "selected_categories": categories,
            "category_counts": category_counts,
            "active_filters_count": active_filters_count,
            "recommended_books": recommended_books,
        },
    )

def detail_redirect(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    return redirect("detail", product_type=book.product_type, book_id=book.id)


def detail(request, product_type, book_id):
    book = get_object_or_404(Book.objects.prefetch_related("images", "categories_m2m"), id=book_id)
    normalized_type = (product_type or "").strip().lower()
    if normalized_type not in {Book.PRODUCT_TYPE_BOOK, Book.PRODUCT_TYPE_CLOTHING}:
        return redirect("detail", product_type=book.product_type, book_id=book.id)

    if book.product_type != normalized_type:
        return redirect("detail", product_type=book.product_type, book_id=book.id)

    cover = book.images.filter(is_cover=True).first() or book.images.first()
    book.cover_image = cover.image.url if cover and cover.image else ""
    track_behavior_event(request, event_type="product_detail_view", product=book)
    is_clothing_detail = book.product_type == Book.PRODUCT_TYPE_CLOTHING
    return render(
        request,
        "book/detail.html",
        {
            "book": book,
            "is_clothing_detail": is_clothing_detail,
            "is_book_detail": not is_clothing_detail,
        },
    )
