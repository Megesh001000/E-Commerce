from rest_framework import generics
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound,ValidationError
from rest_framework.response import Response

from ..models import Order

from .serializers import AdminOrderSerializer,FulfillmentStatusUpdateSerializer

from .permissions import IsOrderStaff

from ..fulfillment_services import update_order_fulfillment_status

class AdminOrderListView(generics.ListAPIView):
    serializer_class=AdminOrderSerializer
    permission_classes=[IsOrderStaff]

    queryset=(
        Order.objects
        .select_related("user")
        .prefetch_related("items")
        .order_by("-created_at")
    )

class AdminOrderDetailView(generics.RetrieveAPIView):
    serializer_class=AdminOrderSerializer
    permission_classes=[IsOrderStaff]

    queryset=(
        Order.objects.select_related("user").prefetch_related("items")
    )

class FulfillmentStatusUpdateView(APIView):
    permission_classes=[IsOrderStaff]

    def patch(self,request,pk):
        serializer=FulfillmentStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        new_status=serializer.validated_data["fulfillment_status"]

        try:
            result=update_order_fulfillment_status(
                order_id=pk,
                new_status=new_status
            )

        except Order.DoesNotExist:
            raise NotFound("Order not found.")

        except ValueError as exc:
            raise ValidationError({
                "fulfillment_status": str(exc)
            })

        order=(
            Order.objects
            .select_related("user")
            .prefetch_related("items")
            .get(pk=pk)
        )

        return Response(
            {
                "result":result,
                "order":AdminOrderSerializer(order).data
            },
            status=status.HTTP_200_OK

        )
        