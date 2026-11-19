
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError,NotFound

from django.db import transaction

from products.models import Product
from .models import CartItem,Cart
from .serializers import CartItemSerializer,CartSerializer,AddCartItemSerializer,UpdateCartItemSerializer


class CartAPI(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        cart,created=Cart.objects.get_or_create(user=request.user)
        cart=(
            Cart.objects
            .prefetch_related("items__product")
            .get(pk=cart.pk)
        )
        serializer=CartSerializer(cart)
        return Response(serializer.data,status=status.HTTP_200_OK)

class CartItemAdd(APIView):
    permission_classes=[IsAuthenticated]

    @transaction.atomic()
    def post(self,request):
        serializer=AddCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        #lock cart
        cart,created=(
                Cart.objects
                .select_for_update()
                .get_or_create(user=request.user)
        )
        requested_product=serializer.validated_data["product"]
        #lock product row
        try:
            product=Product.objects.select_for_update().get(pk=requested_product.pk)
        except Product.DoesNotExist:
            raise NotFound("Product not found.")
        quantity=serializer.validated_data["quantity"]
        cart_item=(
            CartItem.objects
            .select_for_update()
            .filter(
                cart=cart,
                product=product
            )
            .first()
        )
        if cart_item:
            new_quantity=cart_item.quantity+quantity
        else:
            new_quantity=quantity

        if new_quantity>product.stock:
             raise ValidationError({
                "quantity": (
                    f"Only {product.stock} units are currently available."
                )
            })

       
        if  cart_item is not None:
            cart_item.quantity=new_quantity
            cart_item.save(update_fields=["quantity"])
            response_status=status.HTTP_200_OK
        else:
            CartItem.objects.create(
                cart=cart,
                product=product,
                quantity=quantity
            )
            response_status=status.HTTP_201_CREATED

        return Response(
            CartSerializer(cart).data,
            status=response_status

        )

class CartItemUpdate(APIView):
    permission_classes=[IsAuthenticated]
    @transaction.atomic()
    def patch(self,request,item_id):

        serializer=UpdateCartItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
      
        try:
            cart=Cart.objects.select_for_update().get(
                user=request.user
            )
            cart_item=CartItem.objects.select_for_update().get(
                id=item_id,
                cart=cart,
            )
        except (Cart.DoesNotExist,CartItem.DoesNotExist):
            raise NotFound("Cart item not found.")
        product=Product.objects.select_for_update().get(
            pk=cart_item.product_id
        )
        quantity=serializer.validated_data["quantity"]
        if quantity >product.stock:
            raise ValidationError({
                "quantity": (
                    f"Only {product.stock} units are currently available."
                )
            })

        cart_item.quantity=quantity
        cart_item.save(update_fields=["quantity"])

        return Response(
            CartSerializer(cart).data,
            status=status.HTTP_200_OK,

        )

    @transaction.atomic()
    def delete(self,request,item_id):
        try:
            cart=Cart.objects.select_for_update().get(user=request.user)
            cart_item=CartItem.objects.select_for_update().get(
                id=item_id,
                cart=cart
            )
        except (Cart.DoesNotExist,CartItem.DoesNotExist):
            return Response(
                {"error":"Cart item not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        cart_item.delete()
        return Response(
            {"message": "Item removed from cart successfully."},
            status=status.HTTP_200_OK,
        )

