from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0008_book_add_author_category_fk'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='comment',
            unique_together=set(),
        ),
    ]
