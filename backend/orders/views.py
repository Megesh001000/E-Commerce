from decimal import Decimal

from django.db import transaction

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status 
from rest_framework.permissions import IsAuthenticated

from cart.models import Cart
from products.models import Product
from .models import Order,OrderItem
from .serializers import OrderSerializer,OrderItemSerializer

class CheckOutView(APIView):
    permissions_classes=[IsAuthenticated]

    @transaction.atomic
    def post(self,request):

        try:
            cart=Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            return Response(
                {"error":"Your Cart is empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart_items=list(
            cart.items.select_related("product").all()
        )
        if not cart_items:
            return Response(
                {"error": "Your cart is empty."},
                status=status.HTTP_400_BAD_REQUEST,
            )

       
        locked_products={}
        total_amount=Decimal(0.00)

        for cart_item in cart_items: #Lock product rows and validate stock.
            product=Product.objects.select_for_update().get(
                id=cart_item.product_id
            )

            if product.stock < cart_item.quantity:
                 return Response(
                    {
                        "error": (
                            f"Insufficient stock for {product.name}."
                        )
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            price=product.price
            locked_products[product.id] = product


            total_amount+=price * cart_item.quantity

            order=Order.objects.create(
                user=request.user,
                total_amount=total_amount,
                status=Order.Status.PENDING,
                stock_reserved=True
            )
            order_items=[]   # Save purchase details and reserve the stock.
                   

            for cart_item in cart_items:
                product = locked_products[cart_item.product_id]

            order_items.append(
                OrderItem(
                    order=order,
                    product=product,
                    product_name=product.name,
                    price=price,
                    quantity=cart_item.quantity,
                )
            )

            product.stock-=cart_item.quantity
            product.save(update_fields=["stock"])
       

        OrderItem.objects.bulk_create(order_items)
        # Empty the cart so the same items aren't checked out again.
        cart.items.all().delete()

        return Response(
            OrderSerializer(order).data,
            status=status.HTTP_201_CREATED,
        )
