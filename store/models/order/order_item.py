from django.db import models
from store.models.order.order import Order
from store.models.product.product import Product

class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Snapshot of price at purchase

    def __str__(self):
        return f"{self.quantity} x {self.product.title} in Order {self.order.id}"

    class Meta:
        app_label = 'store'


