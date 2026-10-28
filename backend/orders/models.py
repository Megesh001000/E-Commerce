from django.db import models
from django.conf import settings
from django.conf import settings
from django.core.validators import MaxValueValidator,MinValueValidator
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

    is_for_someone_else=models.BooleanField(default=False)

    delivery_address_snapshot = models.JSONField(
    null=True,
    blank=True,
    default=None,
    )
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
    reconciliation_required = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True, default="")

    def  __str__(self):
        return f"{self.event_type} - {self.event_id}"
        
        
class DeliveryAddress(models.Model):
    id=models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    user=models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE,related_name="delivery_address")
    label=models.CharField(max_length=30,default="home")
    recipient_name=models.CharField(max_length=120)
    phone=models.CharField(max_length=30)

    address_line1=models.CharField(max_length=255)
    address_line2=models.CharField(max_length=255,blank=True,default="")
    locality=models.CharField(max_length=120,blank=True,default="")
    city=models.CharField(max_length=100)
    state=models.CharField(max_length=100)
    postal_code=models.CharField(max_length=20)
    country=models.CharField(max_length=100,default="India")

    latitude=models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[
            MinValueValidator(-90),MaxValueValidator(90)
        ]
    )
    longitude=models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[
            MinValueValidator(-180),MaxValueValidator(180)
        ]
    )

    is_default=models.BooleanField(default=False)


    
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    class Meta:
        ordering=("-is_default","-updated_at")
        indexes=[models.Index(fields=["user","is_default"])]
    def __str__(self):
        return f"{self.label}: {self.address_line1}, {self.city}"

    def to_order_snapshot(self):
        return{
            "saved_address_id":str(self.pk),
            "label":self.label,
            "recipient_name":self.recipient_name,
            "phone":self.phone,
            "address_line1":self.address_line1,
            "address_line2":self.address_line2,
            "locality": self.locality,
            "city": self.city,
            "state": self.state,
            "postal_code": self.postal_code,
            "country": self.country,
            "latitude": str(self.latitude),
            "longitude": str(self.longitude),
        }