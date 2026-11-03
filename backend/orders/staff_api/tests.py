from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase

from rest_framework import status
from rest_framework.test import APIRequestFactory,force_authenticate

from ..models import Order, OrderEmailNotification

from .views import (
    AdminOrderListView,
    AdminOrderDetailView,
    FulfillmentStatusUpdateView,
)

User=get_user_model()

class StaffOrderAPITest(TestCase):
    def setUp(self):
        self.factory=APIRequestFactory()

        self.list_view=AdminOrderListView.as_view()
        self.detail_view=AdminOrderDetailView.as_view()
        self.update_view=FulfillmentStatusUpdateView.as_view()

        # Normal customer
        self.customer = User.objects.create_user(
            username="staff_test_customer",
            password="test-password",
        )

        # Warehouse staff
        self.warehouse_staff = User.objects.create_user(
            username="warehouse_test_user",
            password="test-password",
            is_staff=True,
            email="warehouse@example.com",
        )

        warehouse_group,_=Group.objects.get_or_create(name="WarehouseStaff")

        self.warehouse_staff.groups.add(warehouse_group)

        # Staff user without an approved group
        self.unassigned_staff = User.objects.create_user(
            username="unassigned_staff",
            password="test-password",
            is_staff=True,
        )

        self.order=Order.objects.create(
            user=self.customer,
            total_amount=Decimal("125.00"),
            status=Order.Status.CONFIRMED,
            payment_status="captured",
            stock_reserved=False,
            fulfillment_status=Order.FulfillmentStatus.NOT_READY,

        )

    def test_customer_cannot_access_staff_order_list(self):
        request=self.factory.get("/api/staff/orders/")
        force_authenticate(request,user=self.customer)

        response=self.list_view(request)
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )
    def test_staff_without_approved_group_is_rejected(self):
        request=self.factory.get("/api/staff/orders/")
        force_authenticate(request,user=self.unassigned_staff)

        response=self.list_view(request)
        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

    def test_warehouse_staff_can_list_orders(self):
        request=self.factory.get("/api/staff/orders/")
        force_authenticate(request,user=self.warehouse_staff)

        response=self.list_view(request)
        self.assertEqual(response.status_code,status.HTTP_200_OK)

        results=(
            response.data["results"] if isinstance(response.data,dict) and "results" in response.data else response.data
        )


        self.assertEqual(len(results), 1)
        self.assertEqual(
            str(results[0]["id"]),
            str(self.order.pk),
        )

    def test_warehouse_staff_can_retrieve_order(self):
        request=self.factory.get(f"/api/staff/orders/{self.order.pk}/")
        force_authenticate(request,user=self.warehouse_staff)
        response=self.detail_view(
            request,
            pk=str(self.order.pk),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            str(response.data["id"]),
            str(self.order.pk),
        )
    def test_warehouse_staff_can_update_fulfillment_status(self):
        request=self.factory.patch(
            f"/api/staff/orders/{self.order.pk}/fulfillment/",
            {
                "fulfillment_status":(Order.FulfillmentStatus.PROCESSING)
            },
            format="json",
        )
        force_authenticate(request,user=self.warehouse_staff)

        with patch("orders.fulfillment_services.send_order_notification") as mock_send:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                response=self.update_view(
                    request,
                    pk=str(self.order.pk),
                )
        self.assertEqual(response.status_code,status.HTTP_200_OK)

        self.order.refresh_from_db()

        self.assertEqual(self.order.fulfillment_status,Order.FulfillmentStatus.PROCESSING)
        self.assertEqual(response.data["result"],"updated")
        self.assertEqual(len(callbacks), 1)

        mock_send.assert_called_once_with(
            self.order.pk,
            OrderEmailNotification.NotificationType.PROCESSING,
        )
    def test_invalid_fulfillment_transition_is_rejected(self):
        self.order.fulfillment_status = (
            Order.FulfillmentStatus.PROCESSING
        )
        self.order.save(update_fields=["fulfillment_status"])

        request = self.factory.patch(
            f"/api/staff/orders/{self.order.pk}/fulfillment/",
            {
                "fulfillment_status": (
                    Order.FulfillmentStatus.DELIVERED
                )
            },
            format="json",
        )
        force_authenticate(request, user=self.warehouse_staff)

        response = self.update_view(
            request,
            pk=str(self.order.pk),
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.order.refresh_from_db()

        self.assertEqual(
            self.order.fulfillment_status,
            Order.FulfillmentStatus.PROCESSING,
        )

    def test_repeated_fulfillment_update_does_not_send_email_again(self):
        self.order.fulfillment_status = (
            Order.FulfillmentStatus.PROCESSING
        )
        self.order.save(update_fields=["fulfillment_status"])

        request = self.factory.patch(
            f"/api/staff/orders/{self.order.pk}/fulfillment/",
            {
                "fulfillment_status": (
                    Order.FulfillmentStatus.PROCESSING
                )
            },
            format="json",
        )
        force_authenticate(request, user=self.warehouse_staff)

        with patch(
            "orders.fulfillment_services.send_order_notification"
        ) as mock_send:
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                response = self.update_view(
                    request,
                    pk=str(self.order.pk),
                )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["result"], "unchanged")

        self.assertEqual(len(callbacks), 0)
        mock_send.assert_not_called()

    def test_anonymous_user_cannot_access_staff_order_list(self):
        request=self.factory.get("/api/staff/orders/")
        response=self.list_view(request)

        self.assertIn(response.status_code,[status.HTTP_401_UNAUTHORIZED,status.HTTP_403_FORBIDDEN])

    def test_order_list_filters_by_payment_and_fulfillment_status(self):
        request=self.factory.get(
            "/api/staff/orders/",
            {
                "payment_status":"captured",
                "fulfillment_status":"not_ready"

            },
        )
        force_authenticate(request,user=self.warehouse_staff)
        response=self.list_view(request)
        self.assertEqual(response.status_code,status.HTTP_200_OK)
        results=response.data["results"]
        self.assertEqual(len(results),1)
        self.assertEqual(
            str(results[0]["id"]),str(self.order.pk)
        )
    def test_order_list_searches_by_customer_username(self):
        request=self.factory.get(
            "/api/staff/orders/",
            {
                "search":"staff_test_customer"
            },
        )
        force_authenticate(request,user=self.warehouse_staff)
        response=self.list_view(request)
        self.assertEqual(response.status_code,status.HTTP_200_OK)
        self.assertEqual(response.data["count"],1)
        self.assertEqual(str(response.data["results"][0]["id"]),str(self.order.pk))

    def test_order_list_filters_by_date_range(self):
        request = self.factory.get(
            "/api/staff/orders/",
            {
                "date_from": "2000-01-01",
                "date_to": "2100-01-01",
            },
        )
        force_authenticate(request, user=self.warehouse_staff)

        response = self.list_view(request)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
    def test_order_list_rejects_invalid_date(self):
        request = self.factory.get(
            "/api/staff/orders/",
            {"date_from": "invalid-date"},
        )
        force_authenticate(request, user=self.warehouse_staff)

        response = self.list_view(request)

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_order_list_can_be_sorted_by_total_amount(self):
        Order.objects.create(
            user=self.customer,
            total_amount=Decimal("300.00"),
            status=Order.Status.PENDING,
            payment_status="pending",
            stock_reserved= False,

        )
        Order.objects.create(
            user=self.customer,
            total_amount=Decimal("200.00"),
            status=Order.Status.PENDING,
            payment_status="pending",
            stock_reserved= False,

        )

        request=self.factory.get(
            "/api/staff/orders/",
            {"ordering":"-total_amount"}
        )
        force_authenticate(request,user=self.warehouse_staff)
        response=self.list_view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)

        amounts=[
            Decimal(item["total_amount"])
            for item in response.data["results"]
        ]
        self.assertEqual(amounts,sorted(amounts,reverse=True))

    def test_order_list_pagination(self):
        for amt in ["200.00","300.00"]:
            Order.objects.create(
            user=self.customer,
            total_amount=Decimal(amt),
            status=Order.Status.PENDING,
            payment_status="pending",
            stock_reserved=False,
        )
        request=self.factory.get(
            "/api/staff/orders",
            {"page":1,"page_size":1}
        )
        force_authenticate(request,user=self.warehouse_staff)
        response=self.list_view(request)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)
        self.assertEqual(len(response.data["results"]), 1)
        self.assertIsNotNone(response.data["next"])
        self.assertIsNone(response.data["previous"])