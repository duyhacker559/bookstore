from decimal import Decimal
from random import choice, randint, uniform
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from store.models.product.product import Book
from store.models.product.product_image import BookImage
from store.models.category.category import Category

SAMPLE_BRANDS = [
    "Urban Thread",
    "Northwind",
    "Basic Works",
    "Aster",
    "Mono Fit",
    "Blue Yard",
    "Driftline",
    "Nova Fabric",
]

SAMPLE_MATERIALS = ["Cotton", "Linen", "Denim", "Polyester", "Wool", "Rayon"]
SAMPLE_SIZES = ["XS,S,M,L", "S,M,L,XL", "M,L,XL", "Free Size"]
SAMPLE_CATEGORIES = ["Fashion", "Essential", "Streetwear", "Lifestyle", "Seasonal"]
SAMPLE_TYPES = ["T-Shirt", "Hoodie", "Shirt", "Jacket", "Pants", "Dress"]


class Command(BaseCommand):
    help = "Safely seed clothing products only (never modifies book products or existing images)."

    def add_arguments(self, parser):
        parser.add_argument("count", type=int, nargs="?", default=20, help="Number of clothing items to create")
        parser.add_argument("--start", type=int, default=1, help="Start index for naming")
        parser.add_argument("--download-images", action="store_true", help="Download online cover images for new items")

    def _download_image(self, seed):
        url = f"https://picsum.photos/seed/clothing-only-{seed}/800/1000.jpg"
        try:
            with urlopen(url, timeout=12) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError, OSError):
            return None

    def handle(self, *args, **options):
        count = max(int(options["count"]), 0)
        start = int(options["start"])
        download_images = bool(options["download_images"])

        created = 0
        skipped = 0
        image_created = 0
        seed_stamp = timezone.now().strftime("%Y%m%d")

        for i in range(start, start + count):
            product_name = choice(SAMPLE_TYPES)
            title = f"Demo Clothing {seed_stamp}-{i:03d} {product_name}"

            if Book.objects.filter(title=title).exists():
                skipped += 1
                continue

            category_name = choice(SAMPLE_CATEGORIES)
            category_obj, _ = Category.objects.get_or_create(name=category_name)

            clothing = Book.objects.create(
                title=title,
                product_type=Book.PRODUCT_TYPE_CLOTHING,
                author="",
                brand=choice(SAMPLE_BRANDS),
                price=Decimal(f"{uniform(12.0, 159.0):.2f}"),
                stock=randint(3, 120),
                category=category_name,
                category_fk=category_obj,
                size_options=choice(SAMPLE_SIZES),
                material=choice(SAMPLE_MATERIALS),
                gender_target=choice(["Men", "Women", "Unisex"]),
                description=f"Seeded clothing item for demo on {timezone.now().date()}.",
                rating=Decimal("0.0"),
                review_count=0,
            )
            clothing.categories_m2m.add(category_obj)
            created += 1

            if download_images:
                image_bytes = self._download_image(i)
                if image_bytes:
                    image = BookImage.objects.create(book=clothing, is_cover=True)
                    filename = f"clothing_seed_{clothing.id}_{i}.jpg"
                    image.image.save(filename, ContentFile(image_bytes), save=True)
                    image_created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Clothing seed complete. Created: {created}, Skipped duplicates: {skipped}, Images downloaded: {image_created}"
            )
        )
