from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0011_alter_book_author_alter_book_author_fk_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="rating",
            name="is_hidden",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="comment",
            name="is_hidden",
            field=models.BooleanField(default=False),
        ),
    ]
