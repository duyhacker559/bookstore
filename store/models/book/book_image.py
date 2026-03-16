from django.db import models
from .book import Book

class BookImage(models.Model):
    book = models.ForeignKey(Book, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='books/images/')
    is_cover = models.BooleanField(default=False)

    def __str__(self):
        return f"Image for {self.book.title} ({'cover' if self.is_cover else 'image'})"
