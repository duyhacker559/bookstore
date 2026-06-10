from django.db import models
from store.models.customer.customer import Customer
from store.models.product.product import Product

class Rating(models.Model):
    SCORE_CHOICES = [
        (1, '⭐ 1 Star'),
        (2, '⭐⭐ 2 Stars'),
        (3, '⭐⭐⭐ 3 Stars'),
        (4, '⭐⭐⭐⭐ 4 Stars'),
        (5, '⭐⭐⭐⭐⭐ 5 Stars'),
    ]
    
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='ratings_given')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ratings')
    score = models.IntegerField(choices=SCORE_CHOICES, default=5)
    is_hidden = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        app_label = 'store'

    def __str__(self):
        return f"Rating {self.score} for {self.product.title} by {self.customer.name}"


class Comment(models.Model):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='comments_made')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='comments')
    rating = models.ForeignKey(Rating, on_delete=models.CASCADE, related_name='comments', null=True, blank=True)
    title = models.CharField(max_length=200)
    content = models.TextField()
    is_hidden = models.BooleanField(default=False)
    is_verified_purchase = models.BooleanField(default=False)  # True if customer bought the product
    helpful_count = models.PositiveIntegerField(default=0)  # "Helpful" votes
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Multiple comments per customer per product are allowed.
        ordering = ['-helpful_count', '-created_at']
        app_label = 'store'

    def __str__(self):
        return f"Comment by {self.customer.name} on {self.product.title}"


