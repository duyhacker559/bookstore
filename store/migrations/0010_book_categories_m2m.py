from django.db import migrations, models


def populate_book_categories_m2m(apps, schema_editor):
    Book = apps.get_model('store', 'Book')
    Category = apps.get_model('store', 'Category')

    for book in Book.objects.all().iterator():
        category_ids = set()

        if getattr(book, 'category_fk_id', None):
            category_ids.add(book.category_fk_id)

        raw_category = (book.category or '').strip()
        if raw_category:
            category_obj, _ = Category.objects.get_or_create(name=raw_category)
            category_ids.add(category_obj.id)

        if category_ids:
            book.categories_m2m.add(*category_ids)


def reverse_populate_book_categories_m2m(apps, schema_editor):
    Book = apps.get_model('store', 'Book')

    for book in Book.objects.all().iterator():
        through = book.categories_m2m.through
        through.objects.filter(book_id=book.id).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0009_allow_multiple_comments_per_customer_book'),
    ]

    operations = [
        migrations.AddField(
            model_name='book',
            name='categories_m2m',
            field=models.ManyToManyField(blank=True, related_name='books_multi', to='store.category'),
        ),
        migrations.RunPython(populate_book_categories_m2m, reverse_populate_book_categories_m2m),
    ]
