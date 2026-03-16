from django.urls import path
from store.controllers.bookController.views import book_list, book_catalog, book_detail
from store.controllers.orderController.checkout_views import add_to_cart, remove_from_cart, cart_view, update_cart_quantity
from store.controllers.bookController.recommendation_views import data_model_recommendation
from store.controllers.bookController.rating_comment_views import (
    add_rating_comment, book_reviews, mark_helpful, get_ratings_api
)
from store.controllers.api_views import book_list_api, book_detail_api, author_list_api, author_detail_api

urlpatterns = [
    path("", book_list, name="book_list"),
    path("books/", book_catalog, name="book_catalog"),
    path("cart/", cart_view, name="cart"),
    path("cart/update/<int:book_id>/", update_cart_quantity, name="update_cart_quantity"),
    path("add/<int:book_id>/", add_to_cart, name="add_to_cart"),
    path("remove/<int:book_id>/", remove_from_cart, name="remove_from_cart"),
    path("recommendations/", data_model_recommendation, name="recommendations"),
    
    # Rating and comment endpoints
    path("<int:book_id>/rate/", add_rating_comment, name="add_rating_comment"),
    path("<int:book_id>/reviews/", book_reviews, name="book_reviews"),
    path("comment/<int:comment_id>/helpful/", mark_helpful, name="mark_helpful"),
    
    # Book detail must be last since it catches all int book_id
    path("<int:book_id>/", book_detail, name="book_detail"),
    
    # JSON API endpoints
    path("api/books/", book_list_api, name="api_book_list"),
    path("api/books/<int:book_id>/", book_detail_api, name="api_book_detail"),
    path("api/authors/", author_list_api, name="api_author_list"),
    path("api/authors/<int:author_id>/", author_detail_api, name="api_author_detail"),
    path("api/books/<int:book_id>/ratings/", get_ratings_api, name="api_ratings"),
]
