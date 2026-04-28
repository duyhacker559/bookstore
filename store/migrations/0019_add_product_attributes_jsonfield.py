# Generated migration to add attributes JSONField for category-specific product data

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0018_rename_book_table_to_product'),
    ]

    operations = [
        migrations.AddField(
            model_name='book',
            name='attributes',
            field=models.JSONField(default=dict, blank=True, help_text='Category-specific attributes (book_details or clothing_details)'),
        ),
        migrations.AlterField(
            model_name='book',
            name='author',
            field=models.CharField(max_length=255, blank=True, default="", help_text="[DEPRECATED] Use attributes['book_details']['author'] instead"),
        ),
        migrations.AlterField(
            model_name='book',
            name='brand',
            field=models.CharField(max_length=255, blank=True, default="", help_text="[DEPRECATED] Use attributes['clothing_details']['brand'] instead"),
        ),
        migrations.AlterField(
            model_name='book',
            name='size_options',
            field=models.CharField(max_length=100, blank=True, default="", help_text="[DEPRECATED] Use attributes['clothing_details']['sizes'] instead"),
        ),
        migrations.AlterField(
            model_name='book',
            name='material',
            field=models.CharField(max_length=120, blank=True, default="", help_text="[DEPRECATED] Use attributes['clothing_details']['material'] instead"),
        ),
        migrations.AlterField(
            model_name='book',
            name='gender_target',
            field=models.CharField(max_length=32, blank=True, default="", help_text="[DEPRECATED] Use attributes['clothing_details']['gender_target'] instead"),
        ),
    ]
