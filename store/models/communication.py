from django.db import models
from store.models.customer.customer import Customer
from store.models.product.product import Book


class UserNotification(models.Model):
    TYPE_CHOICES = [
        ("order", "Order"),
        ("payment", "Payment"),
        ("shipping", "Shipping"),
        ("moderation", "Moderation"),
        ("system", "System"),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="notifications")
    notification_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="system")
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        app_label = "store"

    def __str__(self):
        return f"{self.customer.name}: {self.title}"


class InboxMessage(models.Model):
    STATUS_CHOICES = [
        ("unread", "Unread"),
        ("read", "Read"),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="inbox_messages")
    book = models.ForeignKey(Book, on_delete=models.SET_NULL, null=True, blank=True, related_name="inbox_messages")
    subject = models.CharField(max_length=200)
    content = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="unread")
    staff_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        app_label = "store"

    def __str__(self):
        return f"Inbox {self.id} by {self.customer.name}"


class InboxReply(models.Model):
    SENDER_CHOICES = [
        ("customer", "Customer"),
        ("staff", "Staff"),
    ]

    inbox_message = models.ForeignKey(InboxMessage, on_delete=models.CASCADE, related_name="replies")
    sender_type = models.CharField(max_length=20, choices=SENDER_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        app_label = "store"

    def __str__(self):
        return f"Reply {self.id} on Inbox {self.inbox_message_id}"


class AIChatSession(models.Model):
    SOURCE_CHOICES = [
        ("widget", "Widget"),
        ("api", "API"),
    ]

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="ai_chat_sessions")
    session_id = models.CharField(max_length=120, db_index=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="widget")
    started_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_activity_at"]
        app_label = "store"
        constraints = [
            models.UniqueConstraint(fields=["customer", "session_id"], name="uniq_customer_ai_session")
        ]

    def __str__(self):
        return f"AI Session {self.session_id} for {self.customer.name}"


class AIChatMessage(models.Model):
    ROLE_CHOICES = [
        ("user", "User"),
        ("assistant", "Assistant"),
        ("system", "System"),
    ]

    TYPE_CHOICES = [
        ("chat_question", "Chat Question"),
        ("chat_answer", "Chat Answer"),
        ("recommendation", "Recommendation"),
        ("error", "Error"),
    ]

    session = models.ForeignKey(AIChatSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    message_type = models.CharField(max_length=30, choices=TYPE_CHOICES, default="chat_answer")
    content = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        app_label = "store"

    def __str__(self):
        return f"{self.role} message {self.id} in session {self.session_id}"
