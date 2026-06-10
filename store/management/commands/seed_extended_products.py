from decimal import Decimal
from random import choice, randint, uniform

from django.core.management.base import BaseCommand

from store.models.category.category import Category
from store.models.product.attribute_manager import ProductAttributeManager
from store.models.product.product import Product


PRODUCT_TYPE_CONFIG = {
    Product.PRODUCT_TYPE_ELECTRONICS: {
        "title_prefix": "Demo Electronics",
        "categories": ["Electronics", "Technology"],
        "price_range": (99.0, 899.0),
        "details": lambda i: {
            "brand": choice(["Sony", "LG", "Samsung", "Panasonic"]),
            "model": f"EL-{i:03d}",
            "warranty_months": 12,
            "power": choice(["30W", "45W", "60W", "100W"]),
            "origin": choice(["Vietnam", "Korea", "Japan", "China"]),
        },
    },
    Product.PRODUCT_TYPE_MOBILE: {
        "title_prefix": "Demo Mobile",
        "categories": ["Mobile", "Electronics"],
        "price_range": (120.0, 1500.0),
        "details": lambda i: {
            "brand": choice(["Apple", "Samsung", "Xiaomi", "Oppo"]),
            "storage": choice(["64GB", "128GB", "256GB"]),
            "ram": choice(["4GB", "6GB", "8GB", "12GB"]),
            "battery": choice(["4000mAh", "4500mAh", "5000mAh"]),
            "os": choice(["Android", "iOS"]),
        },
    },
    Product.PRODUCT_TYPE_HOME_APPLIANCE: {
        "title_prefix": "Demo Home Appliance",
        "categories": ["Home Appliance", "Household"],
        "price_range": (40.0, 650.0),
        "details": lambda i: {
            "brand": choice(["Panasonic", "Sharp", "Electrolux", "Philips"]),
            "power": choice(["300W", "500W", "800W", "1200W"]),
            "capacity": choice(["1L", "1.5L", "2L", "5L"]),
            "energy_rating": choice(["A", "A+", "A++"]),
            "warranty_months": 12,
        },
    },
    Product.PRODUCT_TYPE_BEAUTY: {
        "title_prefix": "Demo Beauty",
        "categories": ["Beauty", "Personal Care"],
        "price_range": (5.0, 120.0),
        "details": lambda i: {
            "brand": choice(["Loreal", "Innisfree", "Vichy", "Nivea"]),
            "skin_type": choice(["All", "Dry", "Oily", "Sensitive"]),
            "volume": choice(["30ml", "50ml", "100ml", "200ml"]),
            "expiry_date": choice(["2027-12-31", "2028-06-30", "2029-01-31"]),
            "origin": choice(["France", "Korea", "Japan", "Vietnam"]),
        },
    },
    Product.PRODUCT_TYPE_FOOD: {
        "title_prefix": "Demo Food",
        "categories": ["Food", "Grocery"],
        "price_range": (1.5, 80.0),
        "details": lambda i: {
            "brand": choice(["Orion", "Nestle", "Vinamilk", "Acecook"]),
            "weight": choice(["250g", "500g", "1kg"]),
            "expiry_date": choice(["2026-12-31", "2027-03-31", "2027-09-30"]),
            "origin": choice(["Vietnam", "Thailand", "Japan", "Korea"]),
            "flavor": choice(["Original", "Chocolate", "Vanilla", "Spicy"]),
        },
    },
    Product.PRODUCT_TYPE_FURNITURE: {
        "title_prefix": "Demo Furniture",
        "categories": ["Furniture", "Home Decor"],
        "price_range": (35.0, 1200.0),
        "details": lambda i: {
            "material": choice(["Wood", "Metal", "Fabric", "Plastic"]),
            "dimensions": choice(["120x60x75cm", "80x80x45cm", "200x90x40cm"]),
            "weight": choice(["5kg", "12kg", "25kg", "40kg"]),
            "color": choice(["Black", "White", "Brown", "Gray"]),
            "style": choice(["Modern", "Minimal", "Classic", "Scandinavian"]),
        },
    },
    Product.PRODUCT_TYPE_SPORTS: {
        "title_prefix": "Demo Sports",
        "categories": ["Sports", "Outdoor"],
        "price_range": (8.0, 420.0),
        "details": lambda i: {
            "brand": choice(["Nike", "Adidas", "Puma", "Decathlon"]),
            "sport_type": choice(["Football", "Running", "Gym", "Badminton"]),
            "material": choice(["PU", "Mesh", "Cotton", "Polyester"]),
            "size": choice(["S", "M", "L", "XL", "Free Size"]),
            "gender_target": choice(["Unisex", "Men", "Women"]),
        },
    },
    Product.PRODUCT_TYPE_TOYS: {
        "title_prefix": "Demo Toy",
        "categories": ["Toys", "Kids"],
        "price_range": (3.0, 200.0),
        "details": lambda i: {
            "brand": choice(["Lego", "Hasbro", "Mattel", "Hot Wheels"]),
            "age_range": choice(["3+", "6+", "9+", "12+"]),
            "material": choice(["ABS", "Wood", "Fabric", "Silicone"]),
            "safety_certification": choice(["CE", "ASTM", "ISO", "QCVN"]),
            "educational": choice([True, False]),
        },
    },
}


class Command(BaseCommand):
    help = "Seed demo products for extended product types (electronics/mobile/home_appliance/beauty/food/furniture/sports/toys)."

    def add_arguments(self, parser):
        parser.add_argument("--per-type", type=int, default=5, help="Number of items to seed for each product type")
        parser.add_argument("--start", type=int, default=1, help="Start index for generated titles")

    def handle(self, *args, **options):
        per_type = max(0, int(options["per_type"]))
        start = int(options["start"])
        created = 0
        updated = 0

        for product_type, config in PRODUCT_TYPE_CONFIG.items():
            for offset in range(per_type):
                index = start + offset
                title = f"{config['title_prefix']} {index:03d}"
                category_name = choice(config["categories"])
                category_obj, _ = Category.objects.get_or_create(name=category_name)
                details = config["details"](index)

                defaults = {
                    "product_type": product_type,
                    "author": details.get("brand", ""),
                    "brand": details.get("brand", ""),
                    "price": Decimal(f"{uniform(*config['price_range']):.2f}"),
                    "stock": randint(3, 140),
                    "category": category_name,
                    "category_fk": category_obj,
                    "description": f"Seeded {product_type} product: {title}",
                    "rating": Decimal("0.0"),
                    "review_count": 0,
                }

                product, was_created = Product.objects.update_or_create(title=title, defaults=defaults)
                product.attributes = ProductAttributeManager.set_details_by_product_type(product_type, product.attributes or {}, details)
                product.save(update_fields=["attributes"])
                product.categories_m2m.add(category_obj)

                if was_created:
                    created += 1
                else:
                    updated += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Extended seed complete. Created: {created}, Updated: {updated}, Product types: {len(PRODUCT_TYPE_CONFIG)}"
            )
        )


