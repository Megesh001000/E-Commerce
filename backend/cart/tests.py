from django.contrib.auth import get_user_model
from django.urls import reverse

from rest_framework.test import APITestCase
from rest_framework import status

from categories.models import Category
from products.models import Product
from cart.models import Cart,CartItem


User=get_user_model()

class CartAPITest(APITestCase):
    def setUp(self):
        self.user=User.objects.create_user(
            username="cartuser",
            email="cartuser@example.com",
            password="TestPassword123!"
        )
        self.category=Category.objects.create(
            name="Electronics"
        )

        self.product=Product.objects.create(
             name="Wireless Mouse",
            category=self.category,
            price="500.00",
            stock=10
        )
        self.client.force_authenticate(user=self.user)
        self.cart_url=reverse("cart-detail")
        self.add_url=reverse("cart-item-add")

    def test_get_empty_cart(self):
        response=self.client.get(self.cart_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["items"], [])
        self.assertTrue(
            Cart.objects.filter(user=self.user).exists()
        )

    def test_add_product_to_cart(self):
        response=self.client.post(
            self.add_url,
            {
                "product_id":str(self.product.id),
                "quantity":2,
            },
            format="json"
        )


        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
            response.data
        )

        self.assertTrue(
            CartItem.objects.filter(
                cart__user=self.user,
                product=self.product,
                quantity=2
            ).exists()
        )
     # 3. Add an existing product again
    def test_add_existing_product_increases_quantity(self):
        self.client.post(
            self.add_url,
            {
                "product_id": str(self.product.id),
                "quantity": 2
            },
            format="json"
        )

        response = self.client.post(
            self.add_url,
            {
                "product_id": str(self.product.id),
                "quantity": 3
            },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
            response.data
        )


        cart_item = CartItem.objects.get(
            cart__user=self.user,
            product=self.product
        )

        self.assertEqual(cart_item.quantity, 5)

    # 4. Reject quantity greater than available stock
    def test_add_quantity_greater_than_stock(self):
        response = self.client.post(
            self.add_url,
            {
                "product_id": str(self.product.id),
                "quantity": 15
            },
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

        self.assertFalse(
            CartItem.objects.filter(
                cart__user=self.user,
                product=self.product
            ).exists()
        )

    # 5. Update cart item quantity
    def test_update_cart_item_quantity(self):
        cart = Cart.objects.create(user=self.user)

        cart_item = CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=2
        )

        update_url = reverse(
            "cart-item-update",
            kwargs={"item_id": cart_item.id}
        )

        response = self.client.patch(
            update_url,
            {"quantity": 4},
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 4)

    # 6. Reject update beyond available stock
    def test_update_quantity_greater_than_stock(self):
        cart = Cart.objects.create(user=self.user)

        cart_item = CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=2
        )

        update_url = reverse(
            "cart-item-update",
            kwargs={"item_id": cart_item.id}
        )

        response = self.client.patch(
            update_url,
            {"quantity": 15},
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

        cart_item.refresh_from_db()
        self.assertEqual(cart_item.quantity, 2)

    # 7. Delete a cart item
    def test_delete_cart_item(self):
        cart = Cart.objects.create(user=self.user)

        cart_item = CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=2
        )

        delete_url = reverse(
            "cart-item-update",
            kwargs={"item_id": cart_item.id}
        )

        response = self.client.delete(delete_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertFalse(
            CartItem.objects.filter(id=cart_item.id).exists()
        )

    # 8. Prevent access to another user's cart item
    def test_user_cannot_update_another_users_cart_item(self):
        another_user = User.objects.create_user(
            username="anotheruser",
            email="another@example.com",
            password="TestPassword123!"
        )

        another_cart = Cart.objects.create(user=another_user)

        another_item = CartItem.objects.create(
            cart=another_cart,
            product=self.product,
            quantity=2
        )

        update_url = reverse(
            "cart-item-update",
            kwargs={"item_id": another_item.id}
        )

        response = self.client.patch(
            update_url,
            {"quantity": 5},
            format="json"
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND
        )

    # 9. Prevent access to another user's cart item when deleting
    def test_user_cannot_delete_another_users_cart_item(self):
        another_user = User.objects.create_user(
            username="anotheruser",
            email="another@example.com",
            password="TestPassword123!"
        )

        another_cart = Cart.objects.create(user=another_user)

        another_item = CartItem.objects.create(
            cart=another_cart,
            product=self.product,
            quantity=2
        )

        delete_url = reverse(
            "cart-item-update",
            kwargs={"item_id": another_item.id}
        )

        response = self.client.delete(delete_url)

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND
        )

        self.assertTrue(
            CartItem.objects.filter(id=another_item.id).exists()
        )

    # 10. Require authentication
    def test_cart_requires_authentication(self):
        cart = Cart.objects.create(user=self.user)

        cart_item = CartItem.objects.create(
            cart=cart,
            product=self.product,
            quantity=2
        )

        update_url = reverse(
            "cart-item-update",
            kwargs={"item_id": cart_item.id}
        )

        self.client.force_authenticate(user=None)

        responses = [
            self.client.get(self.cart_url),
            self.client.post(
                self.add_url,
                {
                    "product_id": str(self.product.id),
                    "quantity": 1
                },
                format="json"
            ),
            self.client.patch(
                update_url,
                {"quantity": 3},
                format="json"
            ),
            self.client.delete(update_url),
        ]

        for response in responses:
            self.assertIn(
                response.status_code,
                [
                    status.HTTP_401_UNAUTHORIZED,
                    status.HTTP_403_FORBIDDEN
                ]
            )