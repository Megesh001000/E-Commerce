from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.utils.dateparse import parse_date

from rest_framework import status
from rest_framework.test import APIRequestFactory,force_authenticate

from categories.models import Category
from ..models import Product,StockAdjustment

from .views import (
    InventoryProductListView,
    InventoryProductDetailView,
    StockAdjustmentCreateView,
    ProductStockAdjustmentHistoryView,
    LowStockProductListView,
)

User=get_user_model()

class StaffInventoryAPITest(TestCase):
    def setUp(self):
        self.factory=APIRequestFactory()
        self.list_view=InventoryProductListView.as_view()
        self.detail_view=InventoryProductDetailView.as_view()
        self.adjustment_view=StockAdjustmentCreateView.as_view()
        self.history_view=ProductStockAdjustmentHistoryView.as_view()
        self.low_stock_view=LowStockProductListView.as_view()

        self.customer=User.objects.create_user(
            username="inventory_customer",
            password="test-password",
        )
        self.inventory_staff=User.objects.create_user(
            username="inventory_staff",
            password="test-password",
            is_staff=True,
        )
        self.unassigned_staff=User.objects.create_user(
            username="unassigned_inventory_staff",
            password="test-password",
            is_staff=True,
        )
        group,_=Group.objects.get_or_create(
            name="InventoryStaff"
        )
        self.inventory_staff.groups.add(group)
        self.category=Category.objects.create(
            name="Inventory API Category",

        )
        self.product=Product.objects.create(
            name="Inventory API Product",
            category=self.category,
            price=Decimal("100.00"),
            stock=10,
        )

    def test_customer_cannot_access_inventory(self):
        request=self.factory.get("/api/staff/inventory/")
        force_authenticate(request,user=self.customer)
        response=self.list_view(request)
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        
        )

    def test_unassigned_staff_cannot_access_inventory(self):
        request=self.factory.get("/api/staff/inventory/")
        force_authenticate(request,user=self.unassigned_staff)
        response=self.list_view(request)
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
    def test_anonymous_user_cannot_access_inventory(self):
        request = self.factory.get("/api/staff/inventory/")

        response = self.list_view(request)

        self.assertIn(
            response.status_code,
            [
                status.HTTP_401_UNAUTHORIZED,
                status.HTTP_403_FORBIDDEN,
            ],
        )
    def test_inventory_staff_can_list_products(self):
        request=self.factory.get("/api/staff/inventory/")
        force_authenticate(request,user=self.inventory_staff)
        response=self.list_view(request)
        self.assertEqual(response.status_code,status.HTTP_200_OK)
        self.assertEqual(response.data["count"],1)
        self.assertEqual(
            str(response.data["results"][0]["id"]),
            str(self.product.pk)
        )
    def test_inventory_staff_can_retrieve_product(self):
        request=self.factory.get(f"/api/staff/inventory/{self.product.pk}/")
        force_authenticate(request,user=self.inventory_staff)
        response=self.detail_view(request,pk=str(self.product.pk),)
        self.assertEqual(response.status_code,status.HTTP_200_OK)
        self.assertEqual(response.data["stock"],10)
    def test_inventory_staff_can_restock_product(self):
        request=self.factory.post(
            f"/api/staff/inventory/{self.product.pk}/adjustments/",
            {
                "quantity_change":20,
                "reason":StockAdjustment.Reason.RESTOCK,
                "note":"New stock received",
            },
            format="json",
        )
        force_authenticate(request,user=self.inventory_staff)
        response=self.adjustment_view(
            request,
            pk=str(self.product.pk)
        )
        self.product.refresh_from_db()
        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )
        self.assertEqual(self.product.stock, 30)
        self.assertEqual(response.data["previous_stock"], 10)
        self.assertEqual(response.data["new_stock"], 30)
        self.assertEqual(response.data["adjusted_by_username"], "inventory_staff")

    def test_insufficient_stock_adjustment_is_rejected(self):
        request = self.factory.post(
            f"/api/staff/inventory/{self.product.pk}/adjustments/",
            {
                "quantity_change": -15,
                "reason": StockAdjustment.Reason.DAMAGED,
            },
            format="json",
        )
        force_authenticate(request, user=self.inventory_staff)

        response = self.adjustment_view(
            request,
            pk=str(self.product.pk),
        )

        self.product.refresh_from_db()

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(self.product.stock, 10)
        self.assertEqual(StockAdjustment.objects.count(), 0)

    def test_inventory_staff_can_view_adjustment_history(self):
        request = self.factory.post(
            f"/api/staff/inventory/{self.product.pk}/adjustments/",
            {
                "quantity_change": 5,
                "reason": StockAdjustment.Reason.RESTOCK,
            },
            format="json",
        )
        force_authenticate(request, user=self.inventory_staff)

        create_response = self.adjustment_view(
            request,
            pk=str(self.product.pk),
        )

        self.assertEqual(
            create_response.status_code,
            status.HTTP_201_CREATED,
        )

        history_request = self.factory.get(
            f"/api/staff/inventory/{self.product.pk}/adjustments/history/"
        )
        force_authenticate(
            history_request,
            user=self.inventory_staff,
        )

        history_response = self.history_view(
            history_request,
            pk=str(self.product.pk),
        )

        self.assertEqual(
            history_response.status_code,
            status.HTTP_200_OK,
        )
        self.assertEqual(history_response.data["count"], 1)
        self.assertEqual(
            history_response.data["results"][0]["quantity_change"],
            5,
        )

    def test_inventory_staff_can_view_low_stock_products(self):
        low_product = Product.objects.create(
            name="Low Stock Product",
            category=self.category,
            price=Decimal("200.00"),
            stock=2,
            low_stock_threshold=5,
        )

        threshold_product = Product.objects.create(
            name="Threshold Stock Product",
            category=self.category,
            price=Decimal("300.00"),
            stock=5,
            low_stock_threshold=5,
        )

        normal_product = Product.objects.create(
            name="Normal Stock Product",
            category=self.category,
            price=Decimal("400.00"),
            stock=10,
            low_stock_threshold=5,
        )

        request = self.factory.get("/api/staff/inventory/low-stock/")
        force_authenticate(request, user=self.inventory_staff)

        response = self.low_stock_view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 2)

        returned_ids = {
            str(item["id"])
            for item in response.data["results"]
        }

        self.assertIn(str(low_product.pk), returned_ids)
        self.assertIn(str(threshold_product.pk), returned_ids)
        self.assertNotIn(str(normal_product.pk), returned_ids)