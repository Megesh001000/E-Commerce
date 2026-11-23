from django.urls import path
from .views import RegisterAPI,LoginAPI,ProfileAPI,CookieTokenRefreshAPI,CSRFTokenAPI,CookieLogoutAPI


urlpatterns=[
    path("register/",RegisterAPI.as_view(),name="register"),
    path("login/",LoginAPI.as_view(),name="login"),
    path("profile/",ProfileAPI.as_view(),name="profile"),
    path("logout/",CookieLogoutAPI.as_view(),name="logout"),
    path("token/refresh/",CookieTokenRefreshAPI.as_view(),name="token-refresh"),
    path("csrf/",CSRFTokenAPI.as_view(),name="csrf-token"),

    
]