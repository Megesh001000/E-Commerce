from rest_framework import generics,filters
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound,ValidationError
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from django.utils.dateparse import parse_date

from ..models import Order

from .serializers import AdminOrderSerializer,FulfillmentStatusUpdateSerializer

from .permissions import IsOrderStaff

from ..fulfillment_services import update_order_fulfillment_status

class StaffOrderPagination(PageNumberPagination):
    page_size=20
    page_size_query_parem="page_size"
    max_page_size=100
class AdminOrderListView(generics.ListAPIView):
    serializer_class=AdminOrderSerializer
    permission_classes=[IsOrderStaff]

    pagination_class=StaffOrderPagination

    filter_backends=[filters.SearchFilter,filters.OrderingFilter]
    search_fields=[
        "user__email",
        "user__username",
        "items__product_name",
    ]
    ordering_fields=[
        "created_at",
        "total_amount",
        "status",
        "payment_status",
        "fulfillment_status",
    ]
    ordering=["-created_at"]
    def get_queryset(self):
        queryset=(
            Order.objects
            .select_related("user")
            .prefetch_related("items")
        )

        params=self.request.query_params

        # Filter by order status
        order_status=params.get("status")
        if order_status:
            queryset=queryset.filter(order_status=status)

        #filter by payment status
        payment_status=params.get("payment_status")
        if payment_status:
            queryset=queryset.filter(payment_status=payment_status)

        #filter by fulfillment status
        fulfillment_status=params.get("fulfillment_status")
        if fulfillment_status:
            queryset=queryset.filter(fulfillment_status=fulfillment_status)

        #filter by start date 
        date_from=params.get("date_from")
        if date_from:
            parsed_date_from=parse_date(date_from)

            if  parsed_date_from  is None:
                raise ValidationError({
                    "date_from": "Use YYYY-MM-DD format."
                })

            queryset=queryset.filter(
                created_at__date__gte=parsed_date_from
            )

        #filter by end date
        date_to=params.get("date_to")
        if date_to:
            parsed_date_to=parse_date(date_to)

            if parsed_date_to is None:
                raise ValidationError({
                    "date_to": "Use YYYY-MM-DD format."
                })
            queryset=queryset.filter(
                created_at__date__lte=parsed_date_to
            )

        if date_from and date_to:
            if parsed_date_from > parsed_date_to:
                raise ValidationError({
                    "date_to": "End date cannot be before start date."
                })
        return queryset




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
        