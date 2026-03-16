from django.urls import path

from store.controllers.staffController.views import (
    manage_shipments, staff_home, update_shipment_status,
    staff_books, staff_add_book, staff_edit_book, staff_delete_book,
    staff_analytics, staff_feedback_moderation, staff_inbox, staff_inbox_thread, staff_inbox_updates, staff_inbox_thread_updates,
)

urlpatterns = [
    path("", staff_home, name="staff_home"),
    path("shipments/", manage_shipments, name="staff_manage_shipments"),
    path("shipments/<int:shipment_id>/status/", update_shipment_status, name="staff_update_shipment_status"),
    path("books/", staff_books, name="staff_books"),
    path("books/add/", staff_add_book, name="staff_add_book"),
    path("books/<int:book_id>/edit/", staff_edit_book, name="staff_edit_book"),
    path("books/<int:book_id>/delete/", staff_delete_book, name="staff_delete_book"),
    path("feedback/", staff_feedback_moderation, name="staff_feedback_moderation"),
    path("inbox/", staff_inbox, name="staff_inbox"),
    path("inbox/updates/", staff_inbox_updates, name="staff_inbox_updates"),
    path("inbox/<int:message_id>/", staff_inbox_thread, name="staff_inbox_thread"),
    path("inbox/<int:message_id>/updates/", staff_inbox_thread_updates, name="staff_inbox_thread_updates"),
    path("analytics/", staff_analytics, name="staff_analytics"),
]
