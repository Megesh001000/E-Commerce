from django.urls import path
from .views import RegisterAPI,LoginAPI,ProfileAPI
from rest_framework_simplejwt.views import TokenRefreshView,TokenBlacklistView


urlpatterns=[
    path("register/",RegisterAPI.as_view(),name="register"),
    path("login/",LoginAPI.as_view(),name="login"),
    path("profile/",ProfileAPI.as_view(),name="profile"),
    path("token/refresh/",TokenRefreshView.as_view(),name="token-refresh"),
    path("logout/",TokenBlacklistView.as_view(),name="logout"),
    
    
]