from django.core.management.base import BaseCommand
from random import uniform, randint, choice
from decimal import Decimal
from django.utils import timezone

from store.models.book.book import Book

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

    def handle(self, *args, **options):
        count = options['count']
        start = options['start']
        created = 0
        updated = 0

        for i in range(start, start + count):
            title = f"Sample Book {i}"
            author = choice(SAMPLE_AUTHORS)
            price = Decimal(f"{uniform(5.0, 99.99):.2f}")
            stock = randint(1, 200)
            category = choice(SAMPLE_CATEGORIES)
            description = f"This is a sample description for {title}. Generated on {timezone.now().date()}"

            obj, created_flag = Book.objects.update_or_create(
                title=title,
                defaults={
                    'author': author,
                    'price': price,
                    'stock': stock,
                    'category': category,
                    'description': description,
                    'rating': Decimal('0.0'),
                    'review_count': 0,
                }
            )

            if created_flag:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(f"Books processed: {count} (created: {created}, updated: {updated})"))
