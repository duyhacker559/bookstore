from django.core.management.base import BaseCommand
from random import uniform, randint, choice
from decimal import Decimal
from django.utils import timezone
from django.core.files.base import ContentFile
from urllib.request import urlopen
from urllib.error import URLError, HTTPError

from store.models.product.product import Book
from store.models.product.product_image import BookImage

SAMPLE_AUTHORS = [
    "Alice Walker",
    "George Orwell",
    "Jane Austen",
    "Mark Twain",
    "Ernest Hemingway",
    "Agatha Christie",
    "J. K. Rowling",
    "Stephen King",
    "Isaac Asimov",
    "Douglas Adams",
]

SAMPLE_BRANDS = [
    "Urban Thread",
    "Northwind",
    "Basic Works",
    "Aster",
    "Mono Fit",
    "Blue Yard",
]

SAMPLE_MATERIALS = ["Cotton", "Linen", "Denim", "Polyester", "Wool"]
SAMPLE_SIZES = ["XS,S,M,L", "S,M,L,XL", "M,L,XL", "Free Size"]

SAMPLE_CATEGORIES = [
    "Fiction",
    "Science",
    "History",
    "Biography",
    "Children",
    "Fantasy",
    "Mystery",
    "Romance",
]


class Command(BaseCommand):
    help = "Populate the database with sample Book items."

    def add_arguments(self, parser):
        parser.add_argument('count', type=int, nargs='?', default=100, help='Number of books to create (default: 100)')
        parser.add_argument('--start', type=int, default=1, help='Start index for numbering titles')
        parser.add_argument('--include-clothing', action='store_true', help='Generate a mixed catalog with clothing products')
        parser.add_argument('--clothing-count', type=int, default=30, help='Number of clothing products to create when --include-clothing is enabled')
        parser.add_argument('--download-images', action='store_true', help='Download cover images from online source and attach to products')
        parser.add_argument('--refresh-images', action='store_true', help='Force replacing existing cover images when downloading')

    def _download_image(self, seed, product_type):
        # Picsum provides free random images suitable for demo data.
        url = f"https://picsum.photos/seed/{product_type}-{seed}/800/1000.jpg"
        try:
            with urlopen(url, timeout=12) as resp:
                return resp.read()
        except (HTTPError, URLError, TimeoutError, OSError):
            return None

    def _upsert_product(self, index, product_type):
        is_clothing = product_type == Book.PRODUCT_TYPE_CLOTHING
        title = f"Sample Apparel {index}" if is_clothing else f"Sample Book {index}"
        author = "" if is_clothing else choice(SAMPLE_AUTHORS)
        brand = choice(SAMPLE_BRANDS) if is_clothing else ""
        size_options = choice(SAMPLE_SIZES) if is_clothing else ""
        material = choice(SAMPLE_MATERIALS) if is_clothing else ""
        gender_target = choice(["Men", "Women", "Unisex"]) if is_clothing else ""

        price = Decimal(f"{uniform(5.0, 99.99):.2f}")
        stock = randint(1, 200)
        category = choice(SAMPLE_CATEGORIES)
        description = f"This is a sample description for {title}. Generated on {timezone.now().date()}"

        obj, created_flag = Book.objects.update_or_create(
            title=title,
            defaults={
                'author': author,
                'product_type': product_type,
                'brand': brand,
                'price': price,
                'stock': stock,
                'category': category,
                'description': description,
                'rating': Decimal('0.0'),
                'review_count': 0,
                'size_options': size_options,
                'material': material,
                'gender_target': gender_target,
            }
        )
        return obj, created_flag

    def _attach_cover(self, book, index, product_type, refresh_images=False):
        cover = book.images.filter(is_cover=True).first() or book.images.first()
        if cover and cover.image and not refresh_images:
            return False

        img_bytes = self._download_image(index, product_type)
        if not img_bytes:
            return False

        if not cover:
            cover = BookImage.objects.create(book=book, is_cover=True)

        filename = f"{product_type}_{book.id}_{index}.jpg"
        cover.image.save(filename, ContentFile(img_bytes), save=True)
        return True

    def handle(self, *args, **options):
        count = options['count']
        start = options['start']
        include_clothing = options['include_clothing']
        clothing_count = max(options['clothing_count'], 0)
        download_images = options['download_images']
        refresh_images = options['refresh_images']
        created = 0
        updated = 0
        images_attached = 0

        # Always generate book products from the primary count.
        for i in range(start, start + count):
            obj, created_flag = self._upsert_product(i, Book.PRODUCT_TYPE_BOOK)
            if created_flag:
                created += 1
            else:
                updated += 1

            if download_images and self._attach_cover(obj, i, Book.PRODUCT_TYPE_BOOK, refresh_images=refresh_images):
                images_attached += 1

        # Optionally generate dedicated clothing products.
        if include_clothing:
            clothing_start = start + count
            for i in range(clothing_start, clothing_start + clothing_count):
                obj, created_flag = self._upsert_product(i, Book.PRODUCT_TYPE_CLOTHING)
                if created_flag:
                    created += 1
                else:
                    updated += 1

                if download_images and self._attach_cover(obj, i, Book.PRODUCT_TYPE_CLOTHING, refresh_images=refresh_images):
                    images_attached += 1

        total_target = count + (clothing_count if include_clothing else 0)
        summary = f"Products processed: {total_target} (created: {created}, updated: {updated})"
        if include_clothing:
            summary += f" | clothing: {clothing_count}"
        if download_images:
            summary += f" | cover images downloaded: {images_attached}"
        self.stdout.write(self.style.SUCCESS(summary))
