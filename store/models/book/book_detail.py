from django.db import models
from .book import Book

class BookDetail(models.Model):
    book = models.OneToOneField(Book, related_name='detail', on_delete=models.CASCADE)
    language = models.CharField(max_length=50, blank=True)
    number_of_pages = models.PositiveIntegerField(null=True, blank=True)
    publisher = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Detail for {self.book.title}"
