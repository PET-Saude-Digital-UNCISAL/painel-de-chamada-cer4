"""Root URL configuration for the project."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('__dev__/', include('core.dev_urls')),

]
