from rest_framework import generics,filters,status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.view import APIView
from rest_framework.exceptions import NotFound,ValidationError

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

    search_fieds=[
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

    queyset=(
        Product.objects.select_related("category","brand").all()
    )

class InventoryProductDetailView(generics.RetrieveAPIView):
    serializer_class=StaffInventoryProductSerializer
    permission_classes=[IsInventoryStaff]
    queyset=(
            Product.objects.select_related("category","brand").all()
        )