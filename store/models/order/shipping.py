from django.db import models
from .order import Order

class Shipment(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    address = models.TextField()
    status = models.CharField(max_length=50, default='Pending')
    method_name = models.CharField(max_length=50)
    fee = models.FloatField()

    class Meta:
        app_label = 'store'
