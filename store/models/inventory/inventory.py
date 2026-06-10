from django.db import models
from store.models.product.product import Product

class Inventory(models.Model):
    product = models.OneToOneField(Product, related_name='inventory', on_delete=models.CASCADE)
    quantity = models.IntegerField(default=0)

    def __str__(self):
        return f"Inventory {self.product.title}: {self.quantity}"


