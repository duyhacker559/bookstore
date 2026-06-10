# Generated manually to properly rename models and fields
from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ('store', '0017_aichatsession_aichatmessage_and_more'),
    ]

    operations = [
        migrations.RenameModel(old_name='Book', new_name='Product'),
        migrations.RenameModel(old_name='BookImage', new_name='ProductImage'),
        migrations.RenameModel(old_name='BookDetail', new_name='ProductDetail'),
        
        migrations.RenameField(model_name='cartitem', old_name='book', new_name='product'),
        migrations.RenameField(model_name='comment', old_name='book', new_name='product'),
        migrations.RenameField(model_name='inboxmessage', old_name='book', new_name='product'),
        migrations.RenameField(model_name='inventory', old_name='book', new_name='product'),
        migrations.RenameField(model_name='orderitem', old_name='book', new_name='product'),
        migrations.RenameField(model_name='productimage', old_name='book', new_name='product'),
        migrations.RenameField(model_name='productdetail', old_name='book', new_name='product'),
        migrations.RenameField(model_name='rating', old_name='book', new_name='product'),
        migrations.RenameField(model_name='recommendation', old_name='recommended_books', new_name='recommended_products'),
    ]
