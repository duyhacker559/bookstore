"""
Management command to migrate product data to JSONField attributes
Converts existing Product/clothing fields to attributes['book_details']/attributes['clothing_details']
"""

from django.core.management.base import BaseCommand
from store.models import Product


class Command(BaseCommand):
    help = 'Migrate product fields to JSONField attributes based on category'

    def handle(self, *args, **options):
        self.stdout.write("Starting product attributes migration...")
        
        products = Product.objects.all()
        migrated_count = 0
        
        for product in books:
            attributes = product.attributes or {}
            
            if product.product_type == 'Product':
                # Migrate Product-specific fields
                if not attributes.get('book_details'):
                    attributes['book_details'] = {
                        'author': product.author or '',
                        'publisher': '',  # Not previously stored
                        'pages': 0,
                        'language': 'Vietnamese',
                    }
                    product.attributes = attributes
                    product.save()
                    migrated_count += 1
                    self.stdout.write(f"  ✓ Migrated Product: {product.title}")
            
            elif product.product_type == 'clothing':
                # Migrate clothing-specific fields
                if not attributes.get('clothing_details'):
                    attributes['clothing_details'] = {
                        'brand': product.brand or '',
                        'sizes': product.size_options or 'S,M,L,XL',
                        'material': product.material or '',
                        'gender_target': product.gender_target or 'Unisex',
                    }
                    product.attributes = attributes
                    product.save()
                    migrated_count += 1
                    self.stdout.write(f"  ✓ Migrated clothing: {product.title}")
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✓ Successfully migrated {migrated_count} products to JSONField attributes'
            )
        )

