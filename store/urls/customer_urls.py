from django.urls import path
from store.controllers.customerController import views

urlpatterns = [
    path("register/", views.register, name="register"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("profile/", views.customer_home, name="customer_home"),
    path("notifications/", views.notifications, name="customer_notifications"),
    path("notifications/updates/", views.notification_updates, name="customer_notification_updates"),
    path("notifications/<int:notification_id>/read/", views.mark_notification_read, name="customer_mark_notification_read"),
    path("notifications/read-all/", views.mark_all_notifications_read, name="customer_mark_all_notifications_read"),
    path("inbox/", views.customer_inbox, name="customer_inbox"),
    path("inbox/updates/", views.customer_inbox_updates, name="customer_inbox_updates"),
    path("inbox/<int:message_id>/", views.customer_inbox_thread, name="customer_inbox_thread"),
    path("inbox/<int:message_id>/updates/", views.customer_inbox_thread_updates, name="customer_inbox_thread_updates"),
    path("settings/", views.profile_settings, name="customer_profile_settings"),
    path("settings/update/", views.update_profile, name="customer_update_profile"),
    path("settings/avatar/remove/", views.remove_avatar, name="customer_remove_avatar"),
    path("settings/password/", views.change_password, name="customer_change_password"),
]
