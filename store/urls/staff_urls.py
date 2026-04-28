from django.urls import path
from django.views.generic import RedirectView

from store.controllers.staffController.views import (
    manage_shipments, staff_home, update_shipment_status,
    staff_products, staff_add_product, staff_edit_product, staff_delete_product,
    staff_analytics, staff_feedback_moderation, staff_inbox, staff_inbox_thread, staff_inbox_updates, staff_inbox_thread_updates,
    staff_ai_train_model,
)

urlpatterns = [
    path("", staff_home, name="staff_home"),
    path("shipments/", manage_shipments, name="staff_manage_shipments"),
    path("shipments/<int:shipment_id>/status/", update_shipment_status, name="staff_update_shipment_status"),
    path("products/", staff_products, name="staff_products"),
    path("products/", staff_products, name="staff_books"),
    path("products/add/", staff_add_product, name="staff_add_product"),
    path("products/add/", staff_add_product, name="staff_add_book"),
    path("products/<int:book_id>/edit/", staff_edit_product, name="staff_edit_product"),
    path("products/<int:book_id>/edit/", staff_edit_product, name="staff_edit_book"),
    path("products/<int:book_id>/delete/", staff_delete_product, name="staff_delete_product"),
    path("products/<int:book_id>/delete/", staff_delete_product, name="staff_delete_book"),
    path("books/", RedirectView.as_view(pattern_name="staff_products", permanent=False)),
    path("feedback/", staff_feedback_moderation, name="staff_feedback_moderation"),
    path("inbox/", staff_inbox, name="staff_inbox"),
    path("inbox/updates/", staff_inbox_updates, name="staff_inbox_updates"),
    path("inbox/<int:message_id>/", staff_inbox_thread, name="staff_inbox_thread"),
    path("inbox/<int:message_id>/updates/", staff_inbox_thread_updates, name="staff_inbox_thread_updates"),
    path("ai/train/", staff_ai_train_model, name="staff_ai_train_model"),
    path("analytics/", staff_analytics, name="staff_analytics"),
]
