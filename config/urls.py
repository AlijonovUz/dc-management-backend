from django.contrib import admin
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('apps.users.urls')),

    path('api/docs/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]
