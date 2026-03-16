from django.db import models
from store.models.book.book import Book

class Inventory(models.Model):
    book = models.OneToOneField(Book, related_name='inventory', on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)

    def __str__(self):
        return f"Inventory {self.book.title}: {self.quantity}"
