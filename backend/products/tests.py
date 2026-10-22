import json

from unittest.mock import patch


from rest_framework.test import APITestCase,APIRequestFactory
from rest_framework import status


from products.models import Brand,Product
from categories.models import Category
from accounts.models import  User

from django.urls import resolve
from django.tests import override_settings






class ProductAPITests(APITestCase):

    def test_product_list_returns_200(self):  #Test For Getting product
        response=self.client.get('/api/products/')

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

    def test_search_products(self):  #Test For Searching
        category=Category.objects.create(name="Mobile")
        brand=Brand.objects.create(name="Samsung")

        Product.objects.create(
            name="Samsung Galaxy",
            category=category,
            brand=brand,
            price="25000.00",
            stock=10,
        )

        Product.objects.create(
            name="Apple iPhone",
            category=category,
            price="50000.00",
            stock=5,
        )

        response=self.client.get("/api/products/?search=Samsung")

        self.assertEqual(response.status_code,status.HTTP_200_OK)
        self.assertEqual(response.data["count"],1)
        self.assertEqual(
            response.data["results"][0]["name"],
            "Samsung Galaxy"
        )

    def test_invalid_min_price_returns_499(self): #Test For  price data type validation field
        response=self.client.get("/api/products/?min_price=abc")

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    def test_product_list_has_paginnation_field(self):
        response=self.client.get("/api/products/")
        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
    )


        self.assertIn("count",response.data)
        self.assertIn("next",response.data)
        self.assertIn("previous",response.data)
        self.assertIn("results",response.data)


    def test_in_stock_filter_excludes_out_of_stock_products(self): # Test For stocks search
        
        category=Category.objects.create(name="Mobiles")

        Product.objects.create(
            name="Available Phone",
            category=category,
            price="20000.00",
            stock=5,
        )

        Product.objects.create(
            name="Unavailable Phone",
            category=category,
            price="15000.00",
            stock=0,
        )
        response = self.client.get(
            "/api/products/?in_stock=true"
        )


        self.assertEqual(response.status_code,status.HTTP_200_OK)

        self.assertEqual(response.data["count"],1)
        self.assertEqual(response.data["results"][0]["name"],"Available Phone")


    def test_brand_filter_returns_matching_products(self): #test brand filter

        category=Category.objects.create(name="Mobiles")
        samsung=Brand.objects.create(name="Samsung")
        apple=Brand.objects.create(name="Apple")

        Product.objects.create(
            name="Samsung Galaxy",
                category=category,
                brand=samsung,
                price="25000.00",
                stock=5,
            )

        Product.objects.create(
            name="Apple iPhone",
            category=category,
            brand=apple,
            price="50000.00",
            stock=5,
        )
        response=self.client.get("/api/products/?brand=samsung")
        # print("Status:", response.status_code)
        # print("Response:", response.data)
        self.assertEqual(
            response.status_code,status.HTTP_200_OK
        )
        self.assertEqual(response.data["count"],1)
        self.assertEqual(response.data["results"][0]["name"], "Samsung Galaxy")

    def  test_anonymous_user_cannot_create_product(self): #Test for anonymous user is prevented from creating a product
        response=self.client.post(
            "/api/products/",
            {},
            format='json'
        )


        self.assertEqual(response.status_code,status.HTTP_401_UNAUTHORIZED)


    def test_for_staff_user_can_create_product(self): #Test staffuser create product

        category=Category.objects.create(name="Mobiles")
        staff_user=User.objects.create_user(
            username="staff_test",
            password="Test123",
            is_staff=True
        )

        self.client.force_authenticate(user=staff_user) #force_authenticat this make no need of jwt

        data = {
            "name": "Test Samsung",
            "category_id": str(category.id),
            "price": "25000.00",
            "stock": 10,
        }

        response=self.client.post(
            "/api/products/",
            data,
            format="json"
        )
        self.assertEqual(response.status_code,status.HTTP_201_CREATED)
        self.assertEqual(Product.objects.count(),1)

    def test_regular_user_cannot_create_product(self):
        user=User.objects.create_user(
            username="regularuser_test",
            password="Test321",
            is_staff=False
        )
        self.client.force_authenticate(user=user)

        response=self.client.post(
            "/api/products/",
            {},
            format='json'
        )

        self.assertEqual(
            response.status_code,status.HTTP_403_FORBIDDEN
        )
    
    def test_regular_user_cannot_update_product(self): #test for regular user should not update product
        category=Category.objects.create(name="Mobiles")
        product = Product.objects.create(
            name="Test Phone",
            category=category,
            price="20000.00",
            stock=5,
        )
        user=User.objects.create_user(
            username="Regularuser",
            password="Test12",
            is_staff=False
        )
        self.client.force_authenticate(user=user)
        print(user)
        response = self.client.patch(
            f"/api/products/{product.id}/",
            {"price": "15000.00"},
            format="json",
        )
       

        self.assertEqual(
         
            response.status_code,status.HTTP_403_FORBIDDEN
        )

    def test_regular_user_cannot_delete_product(self):
        category = Category.objects.create(name="Mobiles")

        product = Product.objects.create(
            name="Test Phone",
            category=category,
            price="20000.00",
            stock=5,
        )

        regular_user=User.objects.create_user(
                username="regularuser_test",
                password="Test321",
                is_staff=False

        )

        self.client.force_authenticate(user=regular_user)

        response=self.client.delete(
              f"/api/products/{product.id}/"
        )

        self.assertEqual(
            response.status_code,status.HTTP_403_FORBIDDEN
        )
        self.assertTrue(
            Product.objects.filter(id=product.id).exists()
        )



















