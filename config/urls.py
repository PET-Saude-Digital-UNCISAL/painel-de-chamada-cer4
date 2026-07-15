"""Root URL configuration for the project."""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('__dev__/', include('core.dev_urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
