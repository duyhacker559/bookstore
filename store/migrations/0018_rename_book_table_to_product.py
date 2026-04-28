# Generated migration to rename store_book table to store_product

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0017_aichatsession_aichatmessage_and_more'),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE store_book RENAME TO store_product;",
            reverse_sql="ALTER TABLE store_product RENAME TO store_book;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE store_book_categories_m2m RENAME TO store_product_categories_m2m;",
            reverse_sql="ALTER TABLE store_product_categories_m2m RENAME TO store_book_categories_m2m;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE store_bookdetail RENAME TO store_productdetail;",
            reverse_sql="ALTER TABLE store_productdetail RENAME TO store_bookdetail;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE store_bookimage RENAME TO store_productimage;",
            reverse_sql="ALTER TABLE store_productimage RENAME TO store_bookimage;",
        ),
        migrations.AlterModelOptions(
            name='book',
            options={'db_table': 'store_product'},
        ),
        migrations.AlterModelTable(
            name='book',
            table='store_product',
        ),
    ]
