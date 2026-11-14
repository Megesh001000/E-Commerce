from decimal import Decimal

from django.test import TestCase
from django.contrib.auth import get_user_model

from categories.models import Category

from .models import Product,StockAdjustment
from .services import adjust_product_stock

User=get_user_model()

class  InventoryServiceTests(TestCase):
    def setUp(self):
        self.user=User.objects.create_user(
            username="inventory_staff",
            password="test-password",
        )

        self.category=Category.objects.create(name="Inventory Test Category",)
        self.product = Product.objects.create(
            name="Inventory Test Product",
            category=self.category,
            price=Decimal("100.00"),
            stock=10,
        )

        def test_restock_increases_product_stock(self):
            adjustment=adjust_product_stock(
                product_id=self.product.pk,
                quantity_change=20,
                reason=StockAdjustment.Reason.RESTOCK,
                adjusted_by=self.user,
                note="New stock received",
            )
            self.product.refresh_from_db()

            self.assertEqual(self.product.stock, 30)
            self.assertEqual(adjustment.previous_stock, 10)
            self.assertEqual(adjustment.new_stock, 30)
            self.assertEqual(adjustment.quantity_change, 20)
            self.assertEqual(adjustment.adjusted_by, self.user)

    def test_damaged_stocks_decreses_product_stock(self):
        adjustment=adjust_product_stock(
            product_id=self.product.pk,
            quantity_change=-3,
            reason=StockAdjustment.Reason.DAMAGED,
            adjusted_by=self.user,
            note="Three damaged units"
        )

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 7)
        self.assertEqual(adjustment.previous_stock, 10)
        self.assertEqual(adjustment.new_stock, 7)

    def test_stock_adjustment_history_is_created(self):
        adjust_product_stock(
            product_id=self.product.pk,
            quantity_change=5,
            reason=StockAdjustment.Reason.RESTOCK,
            adjusted_by=self.user,
        )
        self.assertEqual(
            StockAdjustment.objects.filter(
                product=self.product
            ).count(),1,
        )

    def test_zero_quantity_adjustment_is_rejected(self):
        with self.assertRaises(ValueError):
            adjust_product_stock(
                product_id=self.product.pk,
                quantity_change=0,
                reason=StockAdjustment.Reason.RESTOCK,
            )
            self.product.refresh_from_db()
            self.assertEqual(self.product.stock,0)
            self.assertEqual(StockAdjustment.objects.count(), 0)

    def test_invalid_reason_is_rejected(self):
        with self.assertRaises(ValueError):
            adjust_product_stock(
                product_id=self.product.pk,
                quantity_change=5,
                reason="invalid_reason"
            )
            self.product.refresh_from_db()
            self.assertEqual(self.product.stock,10)

    def test_restock_cannot_have_negative_quantity(self):
        with self.assertRaises(ValueError):
            adjust_product_stock(
                product_id=self.product.pk,
                quantity_change=-5,
                reason=StockAdjustment.Reason.RESTOCK,
            )

        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 10)

    def test_damaged_stock_cannot_have_positive_quantity(self):
            with self.assertRaises(ValueError):
                adjust_product_stock(
                    product_id=self.product.pk,
                    quantity_change=5,
                    reason=StockAdjustment.Reason.DAMAGED,
                )

            self.product.refresh_from_db()
            self.assertEqual(self.product.stock, 10)

    def test_stock_cannot_become_negative(self):
        with self.assertRaises(ValueError):
            adjust_product_stock(
                product_id=self.product.pk,
                quantity_change=-15,
                reason=StockAdjustment.Reason.DAMAGED,
            )

        self.product.refresh_from_db()

        self.assertEqual(self.product.stock, 10)
        self.assertEqual(StockAdjustment.objects.count(), 0)



