from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('', include('core.urls')),
    path('academics/', include('academics.urls')),
    path('finance/', include('finance.urls')),
    path('documents/', include('documents.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
