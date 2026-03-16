from store.models.communication import UserNotification


def create_user_notification(customer, title, message, notification_type="system", link=""):
    return UserNotification.objects.create(
        customer=customer,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
    )
