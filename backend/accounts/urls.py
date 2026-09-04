from django.urls import path
from .views import RegisterAPI,LoginAPI,ProfileAPI


urlpatterns=[
    path("register/",RegisterAPI.as_view(),name="register"),
    path("login/",LoginAPI.as_view(),name="login"),
    path("profile/",ProfileAPI.as_view(),name="profile"),
]