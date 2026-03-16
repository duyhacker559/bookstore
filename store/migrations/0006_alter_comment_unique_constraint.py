# Generated migration to add unique_together constraint to Comment model

from django.db import migrations
from django.db.models import F, Max


def remove_duplicate_comments(apps, schema_editor):
    """Remove duplicate comments, keeping only the latest one per customer/book"""
    Comment = apps.get_model('store', 'Comment')
    
    # Find duplicate comments (multiple comments by same customer for same book)
    seen = set()
    to_delete = []
    
    for comment in Comment.objects.all().order_by('customer_id', 'book_id', '-created_at'):
        key = (comment.customer_id, comment.book_id)
        if key in seen:
            to_delete.append(comment.id)
        else:
            seen.add(key)
    
    # Delete duplicates (keeping the most recent one)
    if to_delete:
        Comment.objects.filter(id__in=to_delete).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0005_rating_comment'),
    ]

    operations = [
        migrations.RunPython(remove_duplicate_comments),
        migrations.AlterUniqueTogether(
            name='comment',
            unique_together={('customer', 'book')},
        ),
    ]

