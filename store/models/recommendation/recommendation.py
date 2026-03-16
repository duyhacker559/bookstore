from django.db import models
from django.conf import settings
from store.models.book.book import Book

class Recommendation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    recommended_books = models.ManyToManyField(Book)
    generated_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Recommendation for {self.user} at {self.generated_at}"

    class Meta:
        app_label = 'store'
