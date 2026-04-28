from django.urls import path
from store.controllers.bookController.views import home, catalog, catalog_redirect, detail_redirect, detail
from store.controllers.orderController.checkout_views import add_to_cart, remove_from_cart, cart_view, update_cart_quantity
from store.controllers.bookController.recommendation_views import data_model_recommendation
from store.controllers.bookController.rating_comment_views import (
    add_rating_comment, product_reviews, mark_helpful, get_ratings_api
)
from store.controllers.api_views import (
    product_list_api,
    product_detail_api,
    author_list_api,
    author_detail_api,
    ai_recommend_gateway,
    ai_chat_gateway,
    ai_advanced_recommend_gateway,
    ai_advanced_chat_gateway,
    ai_advanced_events_gateway,
    ai_advanced_train_gateway,
    ai_advanced_trends_gateway,
    ai_advanced_alerts_gateway,
)

urlpatterns = [
    path("", home, name="home"),
    path("books/", catalog, name="catalog"),
    path("clothing/", catalog_redirect, name="catalog_redirect"),
    path("cart/", cart_view, name="cart"),
    path("cart/update/<int:book_id>/", update_cart_quantity, name="update_cart_quantity"),
    path("add/<int:book_id>/", add_to_cart, name="add_to_cart"),
    path("remove/<int:book_id>/", remove_from_cart, name="remove_from_cart"),
    path("recommendations/", data_model_recommendation, name="recommendations"),
    path("productDetail/<str:product_type>/<int:book_id>/", detail, name="detail"),
    
    # Rating and comment endpoints
    path("<int:book_id>/rate/", add_rating_comment, name="add_rating_comment"),
    path("<int:book_id>/reviews/", product_reviews, name="product_reviews"),
    path("comment/<int:comment_id>/helpful/", mark_helpful, name="mark_helpful"),
    
    # Book detail must be last since it catches all int book_id
    path("<int:book_id>/", detail_redirect, name="detail_redirect"),
    
    # JSON API endpoints
    path("api/books/", product_list_api, name="api_product_list"),
    path("api/books/<int:book_id>/", product_detail_api, name="api_product_detail"),
    path("api/authors/", author_list_api, name="api_author_list"),
    path("api/authors/<int:author_id>/", author_detail_api, name="api_author_detail"),
    path("api/books/<int:book_id>/ratings/", get_ratings_api, name="api_ratings"),
    path("api/ai/recommend/", ai_recommend_gateway, name="api_ai_recommend"),
    path("api/ai/chat/", ai_chat_gateway, name="api_ai_chat"),
    path("api/ai/advanced/recommend/", ai_advanced_recommend_gateway, name="api_ai_advanced_recommend"),
    path("api/ai/advanced/chat/", ai_advanced_chat_gateway, name="api_ai_advanced_chat"),
    path("api/ai/advanced/events/", ai_advanced_events_gateway, name="api_ai_advanced_events"),
    path("api/ai/advanced/train/", ai_advanced_train_gateway, name="api_ai_advanced_train"),
    path("api/ai/advanced/trends/", ai_advanced_trends_gateway, name="api_ai_advanced_trends"),
    path("api/ai/advanced/alerts/", ai_advanced_alerts_gateway, name="api_ai_advanced_alerts"),
]
