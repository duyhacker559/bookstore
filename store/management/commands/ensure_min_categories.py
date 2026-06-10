from django.core.management.base import BaseCommand

from store.services.category_seed import ensure_minimum_product_categories


class Command(BaseCommand):
    help = "Ensure the store has at least N product categories."

    def add_arguments(self, parser):
        parser.add_argument("--min", type=int, default=10, help="Minimum category count (default: 10)")

    def handle(self, *args, **options):
        min_count = int(options["min"])
        result = ensure_minimum_product_categories(min_count=min_count)
        self.stdout.write(
            self.style.SUCCESS(
                f"Category check complete. Created: {result['created']}, Total: {result['total']}"
            )
        )