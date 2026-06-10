from django.db import models
from .product import Product

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='books/images/')
    is_cover = models.BooleanField(default=False)

    class Meta:
        db_table = 'store_productimage'

    def __str__(self):
        return f"Image for {self.product.title} ({'cover' if self.is_cover else 'image'})"
