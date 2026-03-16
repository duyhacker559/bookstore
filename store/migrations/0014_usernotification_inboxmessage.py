from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0013_allow_multiple_ratings_per_customer_book"),
    ]

    operations = [
        migrations.CreateModel(
            name="UserNotification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("notification_type", models.CharField(choices=[("order", "Order"), ("payment", "Payment"), ("shipping", "Shipping"), ("moderation", "Moderation"), ("system", "System")], default="system", max_length=20)),
                ("title", models.CharField(max_length=200)),
                ("message", models.TextField()),
                ("link", models.CharField(blank=True, max_length=255)),
                ("is_read", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to="store.customer")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="InboxMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("subject", models.CharField(max_length=200)),
                ("content", models.TextField()),
                ("status", models.CharField(choices=[("unread", "Unread"), ("read", "Read")], default="unread", max_length=20)),
                ("staff_note", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("read_at", models.DateTimeField(blank=True, null=True)),
                ("book", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="inbox_messages", to="store.book")),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="inbox_messages", to="store.customer")),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
    ]
