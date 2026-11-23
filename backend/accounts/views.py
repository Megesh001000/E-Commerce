from django.shortcuts import render
from django.conf import settings
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie,csrf_protect

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import RefreshToken


from .serializer import RegisterSerializer,LoginSerializer


class RegisterAPI(APIView):
    def post(self,request):
        serializer=RegisterSerializer(data=request.data)


        if serializer.is_valid():
            serializer.save()


            return Response(
                {
                    "message":"User registered successfully"
                },
                status=status.HTTP_201_CREATED
            )
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_protect, name="dispatch")
class LoginAPI(APIView):
    def post(self,request):

     
            serializer=LoginSerializer(data=request.data,context={"request":request})

            if serializer.is_valid():
                tokens=dict(serializer.validated_data)

                refresh_token=tokens.pop("refresh")
                response=Response(tokens,status=status.HTTP_200_OK)

                response.set_cookie(
                    key="refresh_token",
                    value=refresh_token,
                    max_age=int(
                        settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()
                    ),
                httponly=True,
                secure=not settings.DEBUG,
                samesite="Lax",
                path="/api/"
    
                )
                return response

            
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)


class ProfileAPI(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        return Response(
            {
                "username":request.user.username,
                "email":request.user.email,
             }
        )

@method_decorator(csrf_protect, name="dispatch")
class CookieTokenRefreshAPI(APIView):
    permission_classes=[AllowAny]
    authentication_classes=[]

    def get_authenticate_header(self, request):
        return 'Bearer realm="api"'

    def post(self,request):
        refresh_token=request.COOKIES.get("refresh_token")
        if not refresh_token:
            return Response(
                {"error": "Refresh token cookie is missing."},
                status=status.HTTP_401_UNAUTHORIZED
            )
        serializer=TokenRefreshSerializer(
            data={"refresh":refresh_token}
        )
        try:
            serializer.is_valid(raise_exception=True)
        except TokenError as error:
            raise InvalidToken(error.args[0]) from error

        tokens=serializer.validated_data
        response=Response(
            {"access":tokens["access"]},status=status.HTTP_200_OK,
        )
        new_refresh=tokens.get("refresh",refresh_token)

        response.set_cookie(
            key="refresh_token",
            value=new_refresh,
            max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
            httponly=True,
            secure=not settings.DEBUG,
            samesite="Lax",
            path="/api/",
        )
        return response

@method_decorator(ensure_csrf_cookie,name="dispatch")
class CSRFTokenAPI(APIView):
    permission_classes=[AllowAny]
    authentication_classes=[]
    def get(self,request):
        return Response({
            "csrfToken":get_token(request)
        })

@method_decorator(csrf_protect,name="dispatch")
class CookieLogoutAPI(APIView):
    permission_classes=[AllowAny]
    authentication_classes=[]

    def post(self,request):
        refresh_token=request.COOKIES.get("refresh_token")

        if not refresh_token:
            return Response(
                {"error": "Refresh token cookie is missing."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        try:
            token=RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            response = Response(
                {"error": "Invalid or already revoked refresh token."},
                status=status.HTTP_401_UNAUTHORIZED
            )
            response.delete_cookie(
                "refresh_token",
                path="/api/",
                samesite="Lax"
            )

            return response
        response = Response(
            {"message": "Successfully logged out."},
            status=status.HTTP_200_OK
        )

        response.delete_cookie(
            "refresh_token",
            path="/api/",
            samesite="Lax"
        )
        return response


