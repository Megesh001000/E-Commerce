from django.contrib.auth import get_user_model
from django.core.cache import cache


from rest_framework.test import APITestCase,APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken

User = get_user_model()


class AccountsAPITestCase(APITestCase):

    def setUp(self):
        super().setUp()
        cache.clear()
class RegistrationPasswordSecurityTests(AccountsAPITestCase):

    def test_numeric_password_is_rejected(self):
        response = self.client.post(
            "/api/register/",
            {
                "username": "numeric_user",
                "email": "numeric@example.com",
                "password": "123456789",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.data)

    def test_common_password_is_rejected(self):
        response = self.client.post(
            "/api/register/",
            {
                "username": "common_user",
                "email": "common@example.com",
                "password": "password",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_strong_password_is_accepted(self):
        password = "N7!vQ2#pL9@xR4"

        response = self.client.post(
            "/api/register/",
            {
                "username": "secure_user",
                "email": "secure@example.com",
                "password": password,
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)

        user = User.objects.get(username="secure_user")

        self.assertTrue(user.check_password(password))



class LoginBruteForceProtectionTests(AccountsAPITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="axes_test_user",
            password="StrongPassword!123",
        )

    def test_login_is_blocked_after_five_failed_attempts(self):

        responses = []

        for _ in range(5):
            response = self.client.post(
                "/api/login/",
                {
                    "username": "axes_test_user",
                    "password": "WrongPassword123",
                },
                format="json",
            )
            responses.append(response)

        # First four attempts should be rejected normally.
        for  index,response in enumerate(responses):
            expected_status=429 if index ==4 else 400
        self.assertEqual(response.status_code, expected_status)

        # Fifth failed attempt should trigger the lockout.
        # self.assertEqual(responses[4].status_code, 429)

    def test_locked_user_cannot_login_with_correct_password(self):

        for _ in range(5):
            self.client.post(
                "/api/login/",
                {
                    "username": "axes_test_user",
                    "password": "WrongPassword123",
                },
                format="json",
            )

        response = self.client.post(
            "/api/login/",
            {
                "username": "axes_test_user",
                "password": "StrongPassword!123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 429)

class JWTLogoutTests(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="logout_test_user",
            password="StrongPassword!123",
        )

        token = RefreshToken.for_user(self.user)

        self.refresh_token = str(token)
        self.token_jti = token["jti"]

    def test_logout_blacklists_refresh_token(self):

        self.client.cookies["refresh_token"] = self.refresh_token

        response = self.client.post(
            "/api/logout/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            BlacklistedToken.objects.filter(
                token__jti=self.token_jti
            ).exists()
        )

        self.assertIn("refresh_token", response.cookies)

    def test_blacklisted_refresh_token_cannot_be_reused(self):

        self.client.cookies["refresh_token"] = self.refresh_token

        first_response = self.client.post(
            "/api/logout/",
            {},
            format="json",
        )

        self.assertEqual(first_response.status_code, 200)

        # Simulate an attempt to reuse the old token.
        self.client.cookies["refresh_token"] = self.refresh_token

        second_response = self.client.post(
            "/api/logout/",
            {},
            format="json",
        )

        self.assertEqual(second_response.status_code, 401)

    def test_invalid_refresh_token_is_rejected(self):

        self.client.cookies["refresh_token"] = "invalid-token"

        response = self.client.post(
            "/api/logout/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_missing_refresh_token_is_rejected(self):

        response = self.client.post(
            "/api/logout/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 401)

class JWTAuthenticationLifecycleTests(AccountsAPITestCase):

    def setUp(self):
        super().setUp()

        self.user = User.objects.create_user(
            username="jwt_lifecycle_user",
            password="StrongPassword!123",
        )

    def test_complete_jwt_lifecycle(self):

        # 1. Obtain CSRF token
        csrf_response = self.client.get("/api/csrf/")
        csrf_token = csrf_response.data["csrfToken"]

        # 2. Login
        login_response = self.client.post(
            "/api/login/",
            {
                "username": "jwt_lifecycle_user",
                "password": "StrongPassword!123",
            },
            HTTP_X_CSRFTOKEN=csrf_token,
            format="json",
        )

        self.assertEqual(login_response.status_code, 200)

        access_token = login_response.data["access"]
        refresh_token = login_response.cookies["refresh_token"].value

        # 3. Access protected profile
        profile_response = self.client.get(
            "/api/profile/",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        self.assertEqual(profile_response.status_code, 200)

        # 4. Refresh tokens using the cookie
        refresh_response = self.client.post(
            "/api/token/refresh/",
            {},
            HTTP_X_CSRFTOKEN=csrf_token,
            format="json",
        )

        self.assertEqual(refresh_response.status_code, 200)

        new_access_token = refresh_response.data["access"]
        new_refresh_token = refresh_response.cookies["refresh_token"].value

        self.assertNotEqual(refresh_token, new_refresh_token)

        # 5. Attempt to reuse the old refresh token
        self.client.cookies["refresh_token"] = refresh_token

        old_token_response = self.client.post(
            "/api/token/refresh/",
            {},
            HTTP_X_CSRFTOKEN=csrf_token,
            format="json",
        )

        self.assertEqual(
            old_token_response.status_code,
            401,
            f"Status: {old_token_response.status_code}, "
            f"Response: {old_token_response.data}"
        )

        # Restore the new refresh token
        self.client.cookies["refresh_token"] = new_refresh_token

        # 6. Logout using the new refresh token
        logout_response = self.client.post(
            "/api/logout/",
            {"refresh": new_refresh_token},
            format="json",
        )

        self.assertEqual(logout_response.status_code, 200)

        # 7. Attempt to reuse the logged-out refresh token
        reuse_response = self.client.post(
            "/api/token/refresh/",
            {},
            HTTP_X_CSRFTOKEN=csrf_token,
            format="json",
        )

        self.assertEqual(reuse_response.status_code, 401)

class CookieCSRFProtectionTests(AccountsAPITestCase):

    def setUp(self):
        super().setUp()

        self.client = APIClient(enforce_csrf_checks=True)

        self.user = User.objects.create_user(
            username="csrf_test_user",
            password="StrongPassword!123",
        )

    def get_csrf_token(self):
        response = self.client.get("/api/csrf/")

        self.assertEqual(response.status_code, 200)

        return response.data["csrfToken"]

    def test_login_requires_csrf_token(self):

        response = self.client.post(
            "/api/login/",
            {
                "username": "csrf_test_user",
                "password": "StrongPassword!123",
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        csrf_token = self.get_csrf_token()

        response = self.client.post(
            "/api/login/",
            {
                "username": "csrf_test_user",
                "password": "StrongPassword!123",
            },
            HTTP_X_CSRFTOKEN=csrf_token,
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.assertNotIn("refresh", response.data)
        self.assertIn("refresh_token", response.cookies)
        self.assertTrue(
            response.cookies["refresh_token"]["httponly"]
        )

    def test_refresh_requires_csrf_token(self):

        csrf_token = self.get_csrf_token()

        login_response = self.client.post(
            "/api/login/",
            {
                "username": "csrf_test_user",
                "password": "StrongPassword!123",
            },
            HTTP_X_CSRFTOKEN=csrf_token,
            format="json",
        )

        self.assertEqual(login_response.status_code, 200)

        response = self.client.post(
            "/api/token/refresh/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        response = self.client.post(
            "/api/token/refresh/",
            {},
            HTTP_X_CSRFTOKEN=csrf_token,
            format="json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.data)


    def test_logout_requires_csrf_token(self):
        token = RefreshToken.for_user(self.user)

        self.client.cookies["refresh_token"] = str(token)

        # Logout without CSRF token must fail.
        response = self.client.post(
            "/api/logout/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 403)

        # Obtain CSRF token.
        csrf_response = self.client.get("/api/csrf/")
        csrf_token = csrf_response.data["csrfToken"]

        # Logout with valid CSRF token should succeed.
        response = self.client.post(
            "/api/logout/",
            {},
            HTTP_X_CSRFTOKEN=csrf_token,
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            BlacklistedToken.objects.filter(
                token__jti=token["jti"]
            ).exists()
        )