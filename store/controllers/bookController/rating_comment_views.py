from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Avg
from django.core.exceptions import ObjectDoesNotExist
from store.models.book.book import Book
from store.models.customer.customer import Customer
from store.models.rating.rating import Rating, Comment
from store.models.order.order_item import OrderItem


@login_required(login_url='login')
def add_rating_comment(request, book_id):
    """Add or update rating and comment for a book"""
    book = get_object_or_404(Book, id=book_id)
    customer = get_object_or_404(Customer, user=request.user)
    
    # Check if customer purchased this book
    has_purchased = OrderItem.objects.filter(
        order__customer=customer,
        book=book
    ).exists()
    
    if request.method == 'POST':
        score = int(request.POST.get('score', 5))
        title = request.POST.get('title', '')
        content = request.POST.get('content', '')
        
        # Create a rating snapshot per submission so each comment keeps its own score context.
        rating = Rating.objects.create(
            customer=customer,
            book=book,
            score=score,
        )
        
        # Create a new comment entry on each submission.
        if title and content:
            Comment.objects.create(
                customer=customer,
                book=book,
                rating=rating,
                title=title,
                content=content,
                is_verified_purchase=has_purchased,
            )
        
        # Update book's average rating and review count
        avg_rating = Rating.objects.filter(book=book, is_hidden=False).aggregate(
            avg=Avg('score')
        )['avg'] or 0
        # Count only comments that have both title and content (verified reviews)
        review_count = Comment.objects.filter(book=book, is_hidden=False).count()
        
        book.rating = round(float(avg_rating), 1)
        book.review_count = review_count
        book.save()
        
        return redirect('book_detail', book_id=book.id)
    
    # GET request - show form
    existing_rating = Rating.objects.filter(customer=customer, book=book).order_by('-created_at').first()
    existing_comment = Comment.objects.filter(customer=customer, book=book).first() if existing_rating else None
    
    return render(request, 'book/add_rating_comment.html', {
        'book': book,
        'existing_rating': existing_rating,
        'existing_comment': existing_comment,
        'has_purchased': has_purchased,
    })


@login_required(login_url='login')
def mark_helpful(request, comment_id):
    """Mark a comment as helpful"""
    comment = get_object_or_404(Comment, id=comment_id)
    
    if request.method == 'POST':
        comment.helpful_count += 1
        comment.save()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': 'success',
                'helpful_count': comment.helpful_count
            })
    
    return redirect('book_detail', book_id=comment.book.id)


def book_reviews(request, book_id):
    """Display all reviews and ratings for a book"""
    book = get_object_or_404(Book, id=book_id)
    
    # Get all ratings and comments
    ratings = Rating.objects.filter(book=book, is_hidden=False).order_by('-created_at')
    comments = Comment.objects.filter(book=book, is_hidden=False).select_related('customer__user', 'rating')

    # Add avatar URL for each commenter, with graceful fallback when no profile/avatar exists.
    for comment in comments:
        avatar_url = ''
        user = getattr(comment.customer, 'user', None)
        if user:
            try:
                if user.userprofile and user.userprofile.avatar:
                    avatar_url = user.userprofile.avatar.url
            except ObjectDoesNotExist:
                avatar_url = ''
        comment.avatar_url = avatar_url
    
    # Calculate rating breakdown
    breakdown = {}
    for i in range(1, 6):
        count = ratings.filter(score=i).count()
        breakdown[i] = count
    
    # Get average rating
    avg_rating = ratings.aggregate(Avg('score'))['score__avg'] or 0
    total_ratings = ratings.count()
    
    return render(request, 'book/reviews.html', {
        'book': book,
        'ratings': ratings,
        'comments': comments,
        'avg_rating': round(avg_rating, 1),
        'total_ratings': total_ratings,
        'breakdown': breakdown,
    })


def get_ratings_api(request, book_id):
    """API endpoint to get ratings and comments for a book"""
    book = get_object_or_404(Book, id=book_id)
    
    ratings = Rating.objects.filter(book=book, is_hidden=False)
    comments = Comment.objects.filter(book=book, is_hidden=False)
    
    data = {
        'book_id': book.id,
        'book_title': book.title,
        'average_rating': float(book.rating),
        'total_ratings': ratings.count(),
        'ratings': [
            {
                'id': r.id,
                'customer': r.customer.name,
                'score': r.score,
                'created_at': r.created_at.isoformat(),
            }
            for r in ratings
        ],
        'comments': [
            {
                'id': c.id,
                'customer': c.customer.name,
                'title': c.title,
                'content': c.content,
                'is_verified_purchase': c.is_verified_purchase,
                'helpful_count': c.helpful_count,
                'created_at': c.created_at.isoformat(),
            }
            for c in comments
        ]
    }
    
    return JsonResponse(data)
