from django.contrib.auth import get_user_model
from django.core.cache import cache


from rest_framework.test import APITestCase
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

class JWTLogoutTests(AccountsAPITestCase):

    def setUp(self):
        self.user = User.objects.create_user(
            username="logout_test_user",
            password="StrongPassword!123",
        )

        token = RefreshToken.for_user(self.user)

        self.refresh_token = str(token)
        self.token_jti = token["jti"]

    def test_logout_blacklists_refresh_token(self):
        response = self.client.post(
            "/api/logout/",
            {"refresh": self.refresh_token},
            format="json",
        )

        self.assertEqual(response.status_code, 200)

        self.assertTrue(
            BlacklistedToken.objects.filter(
                token__jti=self.token_jti
            ).exists()
        )

    def test_blacklisted_refresh_token_cannot_be_reused(self):
        first_response = self.client.post(
            "/api/logout/",
            {"refresh": self.refresh_token},
            format="json",
        )

        second_response = self.client.post(
            "/api/logout/",
            {"refresh": self.refresh_token},
            format="json",
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 401)

    def test_invalid_refresh_token_is_rejected(self):
        response = self.client.post(
            "/api/logout/",
            {"refresh": "invalid-token"},
            format="json",
        )

        self.assertEqual(response.status_code, 401)

    def test_missing_refresh_token_is_rejected(self):
        response = self.client.post(
            "/api/logout/",
            {},
            format="json",
        )

        self.assertEqual(response.status_code, 400)

class JWTAuthenticationLifecycleTests(AccountsAPITestCase):

    def setUp(self):
        super().setUp()

        self.user = User.objects.create_user(
            username="jwt_lifecycle_user",
            password="StrongPassword!123",
        )

    def test_complete_jwt_lifecycle(self):

        # 1. Login
        login_response = self.client.post(
            "/api/login/",
            {
                "username": "jwt_lifecycle_user",
                "password": "StrongPassword!123",
            },
            format="json",
        )

        self.assertEqual(login_response.status_code, 200)

        access_token = login_response.data["access"]
        refresh_token = login_response.data["refresh"]

        # 2. Access protected profile
        profile_response = self.client.get(
            "/api/profile/",
            HTTP_AUTHORIZATION=f"Bearer {access_token}",
        )

        self.assertEqual(profile_response.status_code, 200)

        # 3. Refresh tokens
        refresh_response = self.client.post(
            "/api/token/refresh/",
            {"refresh": refresh_token},
            format="json",
        )

        self.assertEqual(refresh_response.status_code, 200)

        new_refresh_token = refresh_response.data["refresh"]
        new_access_token = refresh_response.data["access"]

        self.assertNotEqual(refresh_token, new_refresh_token)

        # 4. Old refresh token should be rejected
        old_token_response = self.client.post(
            "/api/token/refresh/",
            {"refresh": refresh_token},
            format="json",
        )

        self.assertEqual(old_token_response.status_code, 401)

        # 5. Logout using the new refresh token
        logout_response = self.client.post(
            "/api/logout/",
            {"refresh": new_refresh_token},
            format="json",
        )

        self.assertEqual(logout_response.status_code, 200)

        # 6. Reuse of logged-out refresh token should fail
        reuse_response = self.client.post(
            "/api/token/refresh/",
            {"refresh": new_refresh_token},
            format="json",
        )

        self.assertEqual(reuse_response.status_code, 401)