from  django.urls import path
from .views import (
    InventoryProductListView,
    InventoryProductDetailView,
    StockAdjustmentCreateView,
    ProductStockAdjustmentHistoryView,
    LowStockProductListView,
    InventorySummaryView,
)

app="staff_inventory"

urlpatterns=[
    path("",InventoryProductListView.as_view(),name="inventory-list"),
    path("<uuid:pk>/",InventoryProductDetailView.as_view(),name="inventory-detail"),
    path("<uuid:pk>/adjustments/",StockAdjustmentCreateView.as_view(),name="stock-adjustment"),
    path("<uuid:pk>/adjustments/history/",ProductStockAdjustmentHistoryView.as_view(),name="stock-adjustment-history"),
    path("low-stock/",LowStockProductListView.as_view(),name="low-stock-products"),
    path("summary/",InventorySummaryView.as_view(),name="inventory-summary"),
]