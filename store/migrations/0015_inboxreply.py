from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0014_usernotification_inboxmessage"),
    ]

    operations = [
        migrations.CreateModel(
            name="InboxReply",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sender_type", models.CharField(choices=[("customer", "Customer"), ("staff", "Staff")], max_length=20)),
                ("content", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("inbox_message", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="replies", to="store.inboxmessage")),
            ],
            options={
                "ordering": ["created_at"],
            },
        ),
    ]
