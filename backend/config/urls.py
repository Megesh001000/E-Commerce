
from django.contrib import admin
from django.conf.urls.static import static
from django.conf import settings
from django.urls import path,include



urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/',include('accounts.urls')),
    path('api/',include('products.urls')),
    path('api/',include('cart.urls')),
    path('api/',include('orders.urls')),
    path(
        "api/staff/orders/",
        include("orders.staff_api.urls"),
    ),
]

urlpatterns+=static(
    settings.MEDIA_URL,
    document_root=settings.MEDIA_ROOT
)