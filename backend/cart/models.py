from django.db import models
from django.conf import settings
from django.db import models


class Cart(models.Model):

    user=models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='name'
    )
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at=models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart - {self.user}"

class CartItem(models.Model):
    cart=models.ForeignKey(
        Cart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    product=models.ForeignKey(
        "products.Product",
        on_delete=models.PROTECT,
        related_name='cart_items'
    )
    quantity=models.PositiveIntegerField(default=1)
    added_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints=[
            models.UniqueConstraint(
                fields=["cart","product"],
                name="unique_product_per_cart",


            ),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=1),
                name="cart_item_quantity_at_least_one"
            ),
        ]

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"
