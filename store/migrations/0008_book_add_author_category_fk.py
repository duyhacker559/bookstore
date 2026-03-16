# Migration to link Author and Category models to Book

from django.db import migrations, models
import django.db.models.deletion


def link_authors_categories(apps, schema_editor):
    """Link existing Author and Category records to Books"""
    Book = apps.get_model('store', 'Book')
    Author = apps.get_model('store', 'Author')
    Category = apps.get_model('store', 'Category')
    
    # Link authors by name matching
    author_cache = {}
    updated_books = []
    for book in Book.objects.all():
        if book.author and book.author.strip():
            if book.author not in author_cache:
                author_obj, created = Author.objects.get_or_create(
                    name=book.author,
                    defaults={'name': book.author}
                )
                author_cache[book.author] = author_obj
            book.author_fk = author_cache[book.author]
            print(f"[LINK AUTHOR] Book {book.id}: {book.title} -> Author: {book.author}")
            updated_books.append(book)
    
    # Link categories by name matching
    category_cache = {}
    for book in Book.objects.all():
        if book.category and book.category.strip():
            if book.category not in category_cache:
                cat_obj, created = Category.objects.get_or_create(
                    name=book.category,
                    defaults={'name': book.category}
                )
                category_cache[book.category] = cat_obj
            book.category_fk = category_cache[book.category]
            print(f"[LINK CATEGORY] Book {book.id}: {book.title} -> Category: {book.category}")
            if book not in updated_books:
                updated_books.append(book)
    
    if updated_books:
        Book.objects.bulk_update(
            updated_books,
            ['author_fk', 'category_fk'],
            batch_size=100
        )


def reverse_link(apps, schema_editor):
    """Clear ForeignKey links but keep string fields"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0007_consolidate_inventory'),
    ]

    operations = [
        migrations.AddField(
            model_name='book',
            name='author_fk',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, 
                                   related_name='books', to='store.author'),
        ),
        migrations.AddField(
            model_name='book',
            name='category_fk',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                   related_name='books', to='store.category'),
        ),
        migrations.RunPython(link_authors_categories, reverse_link),
    ]
