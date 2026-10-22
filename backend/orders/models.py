from django.db import models
from django.conf import settings

import uuid

from products.models import Product

class Order(models.Model):
    class Status(models.TextChoices):
        PENDING="pending","Pending"
        CONFIRMED="confirmed","Confirmed"
        CANCELLED="cancelled","Cancelled"

    id=models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False
    )
    user=models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="orders"
    )

    status=models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,

    )
    total_amount=models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,

    )
    stock_reserved=models.BooleanField(default=False)
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)
    razorpay_order_id=models.CharField(max_length=100,blank=True,null=True,unique=True)
    razorpay_payment_id=models.CharField(max_length=100,blank=True,null=True,unique=True)
    payment_status=models.CharField(max_length=20,default="pending")
    requires_reconciliation = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True, default="")


    def __str__(self):
        return f"Order {self.id} - {self.user}"

class OrderItem(models.Model):
    order=models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"

    )
    product=models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items"

    )
    product_name=models.CharField(max_length=100)
    price=models.DecimalField(max_digits=12,decimal_places=2)
    quantity=models.PositiveIntegerField()

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


    @property
    def sub_total(self):
        return self.price * self.quantity

class WebhookEvent(models.Model):
    event_id=models.CharField(max_length=100,unique=True)
    event_type=models.CharField(max_length=100)
    payload=models.JSONField()
    processed=models.BooleanField(default=False)
    received_at=models.DateTimeField(auto_now_add=True)
    processed_at=models.DateTimeField(null=True,blank=True)

    def  __str__(self):
        return f"{self.event_type} - {self.event_id}"