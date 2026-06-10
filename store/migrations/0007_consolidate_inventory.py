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
            if book.stock != inv.quantity:
                inv.quantity = book.stock
                inv.save()
        except Inventory.DoesNotExist:
            Inventory.objects.create(book=book, quantity=book.stock)


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

