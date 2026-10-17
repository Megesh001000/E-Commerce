
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError

from products.models import Product
from .models import CartItem,Cart
from .serializers import CartItemSerializer,CartSerializer

class CartAPI(APIView):
    def get(self,request):
        cart,created=Cart.objects.get_or_create(user=request.user)

        serializer=CartSerializer(cart)
        return Response(serializer.data,status=status.HTTP_200_OK)

class CartItemAdd(APIView):
    def post(self,request):
        product_id=request.data.get("product")
        quantity=request.data.get("quantity",1)

        if not product_id:
             return Response(
                {"error": "Product ID is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            quantity=int(quantity)
        except (TypeError,ValueError):
             return Response(
                {"error": "Quantity must be a whole number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if quantity <1 :
            return Response(
                {"error": "Quantity must be at least 1."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            product=Product.objects.get(id=product_id)
        except (Product.DoesNotExist,ValueError):
            return Response(
                {"error":"Product nor found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cart,created=Cart.objects.get_or_create(
            user=request.user
        )

        cart_item,item_created=CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity":quantity}
        )
        if not item_created:
            cart_item.quantity+=quantity
            cart_item.save(update_fields=["quantity"])

        return Response(
            CartSerializer(cart).data,
            status=status.HTTP_200_OK if not item_created else status.HTTP_201_CREATED

        )

class CartItemUpdate(APIView):
    permission_classes=[IsAuthenticated]
    def patch(self,request,item_id):
        try:
            quantity=int(request.data.get("quantity"))
        except (TypeError,ValueError):
            return Response(
                {"error":"Quantity must be a whole number."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if quantity <1:
            return Response(
                {"error":"Quantity must be at least 1."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            cart=Cart.objects.get(user=request.user)
            cart_item=CartItem.objects.get(
                id=item_id,
                cart=cart
            )
        except (Cart.DoesNotExist,CartItem.DoesNotExist):
            return Response(
                {"error":"Cart item not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        cart_item.quantity=quantity
        cart_item.save(update_fields=["quantity"])

        return Response(
            CartSerializer(cart).data,
            status=status.HTTP_200_OK
        )
    def delete(self,request,item_id):
            try:
                cart=Cart.objects.get(user=request.user)
                cart_item=CartItem.objects.get(
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
    
    
            
# class CartItemDelete(APIView):
#     permissions_classes=[IsAuthenticated]
    