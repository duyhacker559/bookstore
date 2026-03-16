# Migration to consolidate inventory management
# Ensures Book.stock and Inventory.quantity are in sync

from django.db import migrations, models
import django.db.models.deletion


def consolidate_inventory(apps, schema_editor):
    """Consolidate Book.stock with Inventory.quantity"""
    Book = apps.get_model('store', 'Book')
    Inventory = apps.get_model('store', 'Inventory')
    
    for book in Book.objects.all():
        try:
            inv = Inventory.objects.get(book=book)
            # Update Inventory quantity to match Book.stock if they differ
            if book.stock != inv.quantity:
                print(f"[CONSOLIDATE] Book {book.id} ({book.title}): "
                      f"Book.stock={book.stock}, Inventory.quantity={inv.quantity} -> using Book.stock")
                inv.quantity = book.stock
                inv.save()
        except Inventory.DoesNotExist:
            # Create missing Inventory record
            inv = Inventory.objects.create(book=book, quantity=book.stock)
            print(f"[CREATE] Inventory for Book {book.id} ({book.title}): quantity={book.stock}")


def reverse_consolidate(apps, schema_editor):
    """No-op reverse function"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0006_alter_comment_unique_constraint'),
    ]

    operations = [
        migrations.RunPython(consolidate_inventory, reverse_consolidate),
    ]
