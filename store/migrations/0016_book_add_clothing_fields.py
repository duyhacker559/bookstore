from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0015_inboxreply"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="brand",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="book",
            name="gender_target",
            field=models.CharField(blank=True, default="", max_length=32),
        ),
        migrations.AddField(
            model_name="book",
            name="material",
            field=models.CharField(blank=True, default="", max_length=120),
        ),
        migrations.AddField(
            model_name="book",
            name="product_type",
            field=models.CharField(choices=[("book", "Book"), ("clothing", "Clothing")], db_index=True, default="book", max_length=20),
        ),
        migrations.AddField(
            model_name="book",
            name="size_options",
            field=models.CharField(blank=True, default="", help_text="Comma-separated sizes, e.g. S,M,L,XL", max_length=100),
        ),
        migrations.AlterField(
            model_name="book",
            name="author",
            field=models.CharField(blank=True, default="", help_text="Legacy field - use author_fk instead", max_length=255),
        ),
    ]
