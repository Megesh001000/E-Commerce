from rest_framework import generics,filters,status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import NotFound,ValidationError

from django.db.models import F

from ..models import  Product,StockAdjustment
from ..services import adjust_product_stock
from .serializers import StaffInventoryProductSerializer,StockAdjustmentCreateSerializer,StockAdjustmentHistorySerializer
from .permissions  import IsInventoryStaff

class InventoryPagination(PageNumberPagination):
    page_size=20
    page_size_query_param="page_size"
    max_page_size=100

class InventoryProductListView(generics.ListAPIView):
    serializer_class=StaffInventoryProductSerializer
    permission_classes=[IsInventoryStaff]
    pagination_class=InventoryPagination

    filter_backends=[
        filters.SearchFilter,
        filters.OrderingFilter,
    ]

    search_fields=[
        "name",
        "category__name",
        "brand__name"
    ]

    ordering_fields=[
        "name",
        "price",
        "stock",
        "updated_at"
    ]
    ordering=["name"]

    queryset=(
        Product.objects.select_related("category","brand").all()
    )

class InventoryProductDetailView(generics.RetrieveAPIView):
    serializer_class=StaffInventoryProductSerializer
    permission_classes=[IsInventoryStaff]
    queryset=(
            Product.objects.select_related("category","brand").all()
        )
class StockAdjustmentCreateView(APIView):
    permission_classes=[IsInventoryStaff]
    def post(self,request,pk):
        serializer=StockAdjustmentCreateSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        try:
            adjustment=adjust_product_stock(
                product_id=pk,
                quantity_change=serializer.validated_data["quantity_change"],
            
                reason=serializer.validated_data["reason"],
                adjusted_by=request.user,
                note=serializer.validated_data.get("note",""),

            )
        except Product.DoesNotExist:
            raise NotFound("Product not found.")

        except ValueError as exc:
            raise ValidationError({
                "stock_adjustment": str(exc)
            })

        return Response(
            StockAdjustmentHistorySerializer(adjustment).data,
            status=status.HTTP_201_CREATED,
        )

class ProductStockAdjustmentHistoryView(generics.ListAPIView):
    
    serializer_class=StockAdjustmentHistorySerializer
    permission_classes=[IsInventoryStaff]
    pagination_class=InventoryPagination

    def get_queryset(self):
        product_id=self.kwargs["pk"]

        if not Product.objects.filter(pk=product_id).exists():
            raise NotFound("Product not found.")

        return (
            StockAdjustment.objects
            .filter(product_id=product_id)
            .select_related("product", "adjusted_by")
            .order_by("-created_at")
        )

class LowStockProductListView(generics.ListAPIView):
    serializer_class=StaffInventoryProductSerializer
    permission_classes=[IsInventoryStaff]
    pagination_Class=InventoryPagination

    filter_backends=[filters.SearchFilter,filters.OrderingFilter]

    search_fields=[
        "name",
        "category__name",
        "brand__name"
    ]
    ordering_fields=[
        "name",
        "stock",
        "updated_at"
    ]
    order=[
        "stock",
        "name"
    ]

    def get_queryset(Self):
        return(
            Product.objects
            .select_related("category","brand")
            .filter(stock__lte=F("low_stock_threshold"))

        )