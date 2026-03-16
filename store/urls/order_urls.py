from django.urls import path
from store.controllers.orderController.checkout_views import (
    add_to_cart, remove_from_cart, cart_view, checkout,
    payment_confirm, order_success, track_shipment, track_order
)

urlpatterns = [
    # Cart management
    path("add/<int:book_id>/", add_to_cart, name="add_to_cart"),
    path("remove/<int:book_id>/", remove_from_cart, name="remove_from_cart"),
    path("cart/", cart_view, name="cart"),
    
    # Checkout and payment
    path("checkout/", checkout, name="checkout"),
    path("<int:order_id>/payment/", payment_confirm, name="payment_initiate"),
    path("<int:order_id>/success/", order_success, name="order_success"),
    
    # Shipment tracking
    path("<int:order_id>/track/", track_order, name="order_track"),
    path("track/<int:shipment_id>/", track_shipment, name="shipment_track"),
]
