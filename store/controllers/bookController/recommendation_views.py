from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Q, F, Count, Value, CharField, Min, Max, DecimalField, Case, When, FloatField, IntegerField
from django.db.models.functions import Cast, Coalesce
from store.models.recommendation.recommendation import Recommendation
from store.models.book.book import Book
from store.models.order.order_item import OrderItem
from store.models.customer.customer import Customer


PRIMARY_RECOMMENDATION_LIMIT = 12
FRAME_RECOMMENDATION_LIMIT = 8
TOTAL_RECOMMENDATION_LIMIT = PRIMARY_RECOMMENDATION_LIMIT

@login_required(login_url='/customer/login/')
def data_model_recommendation(request):
    try:
        customer = Customer.objects.get(user=request.user)
    except Customer.DoesNotExist:
        customer = None
    
    # Get user's purchase history for smart recommendations
    user_purchases = set()
    user_categories = []
    if customer:
        purchased_books = OrderItem.objects.filter(order__customer=customer).values_list('book_id', flat=True).distinct()
        user_purchases = set(purchased_books)
        purchased_book_objects = Book.objects.prefetch_related('categories_m2m').filter(id__in=purchased_books)
        user_categories = sorted({
            category_name
            for book in purchased_book_objects
            for category_name in book.category_names
        })
    
    # Get filter parameters
    query = request.GET.get("q", "").strip()
    price_min = request.GET.get("price_min", "").strip()
    price_max = request.GET.get("price_max", "").strip()
    category = request.GET.get("category", "").strip()
    rating_min = request.GET.get("rating_min", "").strip()
    filter_type = request.GET.get("filter", "all").strip()

    # Base candidate set
    # world_pick uses global catalog behavior (including already purchased books)
    if filter_type == "world_pick":
        recommendations = Book.objects.prefetch_related('images', 'categories_m2m')
    else:
        recommendations = Book.objects.prefetch_related('images', 'categories_m2m').exclude(id__in=user_purchases)
    
    # Apply search filter
    if query:
        recommendations = recommendations.filter(
            Q(title__icontains=query)
            | Q(author__icontains=query)
            | Q(author_fk__name__icontains=query)
            | Q(category__icontains=query)
            | Q(category_fk__name__icontains=query)
            | Q(categories_m2m__name__icontains=query)
        )
    
    # Apply price range filter
    if price_min:
        try:
            recommendations = recommendations.filter(price__gte=float(price_min))
        except ValueError:
            pass
    if price_max:
        try:
            recommendations = recommendations.filter(price__lte=float(price_max))
        except ValueError:
            pass
    
    # Apply category filter
    if category:
        recommendations = recommendations.filter(
            Q(categories_m2m__name__iexact=category)
            | Q(category__icontains=category)
            | Q(category_fk__name__iexact=category)
        )
    
    # Apply rating filter
    if rating_min:
        try:
            recommendations = recommendations.filter(rating__gte=float(rating_min))
        except ValueError:
            pass

    recommendations = recommendations.distinct()
    
    # Apply filter type logic
    if filter_type == "trending":
        # Books with most reviews = popular/trending
        recommendations = recommendations.annotate(
            popularity=Count('orderitem')
        ).order_by('-popularity')[:TOTAL_RECOMMENDATION_LIMIT]
    elif filter_type == "world_pick":
        # Global picks based on overall purchase behavior across all users
        recommendations = recommendations.annotate(
            popularity=Count('orderitem')
        ).order_by('-popularity', '-rating', '-review_count')[:TOTAL_RECOMMENDATION_LIMIT]
    elif filter_type == "new":
        # Newest books based on created_at
        recommendations = recommendations.order_by('-created_at')[:TOTAL_RECOMMENDATION_LIMIT]
    elif filter_type == "rated":
        # Highest rated books
        recommendations = recommendations.filter(rating__gt=0).order_by('-rating', '-review_count')[:TOTAL_RECOMMENDATION_LIMIT]
    elif filter_type == "deals":
        # Best deals (lowest prices in their category)
        recommendations = recommendations.order_by('price')[:TOTAL_RECOMMENDATION_LIMIT]
    elif filter_type == "similar":
        # If user has purchase history, recommend similar books
        if user_categories:
            recommendations = recommendations.filter(
                Q(categories_m2m__name__in=user_categories)
                | Q(category__in=user_categories)
                | Q(category_fk__name__in=user_categories)
            ).distinct().order_by('-rating', '-review_count')[:TOTAL_RECOMMENDATION_LIMIT]
        else:
            recommendations = recommendations.order_by('-review_count', '-rating')[:TOTAL_RECOMMENDATION_LIMIT]
    else:  # "all" - standard recommendations
        # Smart recommendation: highly rated + popular + not yet purchased
        recommendations = recommendations.annotate(
            score=Case(
                When(rating__gte=4.5, then=Value(3)),
                When(rating__gte=4.0, then=Value(2)),
                When(rating__gte=3.5, then=Value(1)),
                default=Value(0),
                output_field=IntegerField()
            ) + Count('orderitem')
        ).order_by('-score', '-rating')[:TOTAL_RECOMMENDATION_LIMIT]
    
    def _decorate_books(book_list):
        for book in book_list:
            book_category_names = set(book.category_names)
            match_score = 0
            if user_categories and book_category_names.intersection(user_categories):
                match_score += 30
            if book.rating >= 4.0:
                match_score += 25
            if book.review_count >= 10:
                match_score += 20
            if not user_purchases:
                match_score += 25
            book.match_score = min(match_score, 100)
            book.match_reason = _get_match_reason(book, user_categories)

            cover = book.images.filter(is_cover=True).first() or book.images.first()
            book.cover_image = cover.image.url if cover and cover.image else ""

    # Prepare personalized section
    recommendation_list = list(recommendations)
    _decorate_books(recommendation_list)

    recommendation_list = sorted(
        recommendation_list,
        key=lambda b: (
            b.match_score,
            b.rating or 0,
            b.review_count or 0,
        ),
        reverse=True,
    )
    primary_books = recommendation_list[:PRIMARY_RECOMMENDATION_LIMIT]
    top_match_score = primary_books[0].match_score if primary_books else 0

    # Build separate frames only on the default personalized mode
    world_pick_books = []
    if filter_type in {"all", "trending", "rated", "deals"}:
        excluded_ids = {book.id for book in primary_books}

        world_pick_qs = Book.objects.prefetch_related('images', 'categories_m2m').exclude(id__in=user_purchases).exclude(id__in=excluded_ids)
        if query:
            world_pick_qs = world_pick_qs.filter(
                Q(title__icontains=query)
                | Q(author__icontains=query)
                | Q(author_fk__name__icontains=query)
                | Q(category__icontains=query)
                | Q(category_fk__name__icontains=query)
                | Q(categories_m2m__name__icontains=query)
            )
        if price_min:
            try:
                world_pick_qs = world_pick_qs.filter(price__gte=float(price_min))
            except ValueError:
                pass
        if price_max:
            try:
                world_pick_qs = world_pick_qs.filter(price__lte=float(price_max))
            except ValueError:
                pass
        if category:
            world_pick_qs = world_pick_qs.filter(
                Q(categories_m2m__name__iexact=category)
                | Q(category__icontains=category)
                | Q(category_fk__name__iexact=category)
            )
        if rating_min:
            try:
                world_pick_qs = world_pick_qs.filter(rating__gte=float(rating_min))
            except ValueError:
                pass

        world_pick_qs = world_pick_qs.distinct().annotate(
            popularity=Count('orderitem')
        ).order_by('-popularity', '-rating', '-review_count')[:FRAME_RECOMMENDATION_LIMIT]
        world_pick_books = list(world_pick_qs)
        _decorate_books(world_pick_books)
    
    # Get available categories for filter
    all_categories = sorted({
        category_name
        for book in Book.objects.prefetch_related('categories_m2m').all()
        for category_name in book.category_names
    })
    
    # Get price range for filter
    price_stats = Book.objects.aggregate(min_price=Min('price'), max_price=Max('price'))
    
    return render(request, "recommendation/list.html", {
        "books": primary_books,
        "world_pick_books": world_pick_books,
        "total_recommendations": len(primary_books) + len(world_pick_books),
        "top_match_score": top_match_score,
        "query": query,
        "price_min": price_min,
        "price_max": price_max,
        "category": category,
        "rating_min": rating_min,
        "filter_type": filter_type,
        "categories": all_categories,
        "min_price": price_stats.get("min_price") or 0,
        "max_price": price_stats.get("max_price") or 100,
    })

def _get_match_reason(book, user_categories):
    """Generate a human-readable reason why this book is recommended."""
    reasons = []
    if book.rating >= 4.5:
        reasons.append("⭐ Highly Rated")
    if book.review_count >= 20:
        reasons.append("🔥 Popular")
    shared_categories = [name for name in book.category_names if name in user_categories]
    if shared_categories:
        reasons.append(f"📚 {shared_categories[0]}")
    return " • ".join(reasons) if reasons else "✨ Curated Pick"
