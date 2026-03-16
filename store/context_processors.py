from django.db.utils import OperationalError, ProgrammingError


def notification_counts(request):
    if not request.user.is_authenticated:
        return {
            "notifications_unread_count": 0,
            "staff_inbox_unread_count": 0,
            "staff_inbox_read_count": 0,
        }

    try:
        from store.models.customer.customer import Customer
        from store.models.communication import UserNotification, InboxMessage

        customer = Customer.objects.filter(user=request.user).first()
        notifications_unread_count = 0
        if customer:
            notifications_unread_count = UserNotification.objects.filter(customer=customer, is_read=False).count()

        staff_inbox_unread_count = 0
        staff_inbox_read_count = 0
        if request.user.is_staff:
            staff_inbox_unread_count = InboxMessage.objects.filter(status="unread").count()
            staff_inbox_read_count = InboxMessage.objects.filter(status="read").count()

        return {
            "notifications_unread_count": notifications_unread_count,
            "staff_inbox_unread_count": staff_inbox_unread_count,
            "staff_inbox_read_count": staff_inbox_read_count,
        }
    except (OperationalError, ProgrammingError):
        return {
            "notifications_unread_count": 0,
            "staff_inbox_unread_count": 0,
            "staff_inbox_read_count": 0,
        }
