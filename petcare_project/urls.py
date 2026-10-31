"""
Enrutamiento principal del proyecto PetCare.

Incluye el panel de administración, las páginas HTML, la API REST, la
documentación OpenAPI (Swagger/Redoc) y el endpoint de salud para AWS.
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path, re_path
from drf_spectacular.views import SpectacularRedocView, SpectacularSwaggerView

from petcare import api_views
from petcare.views import redirect_to_home

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('petcare.urls')),

    # Esquema y documentación de la API
    path('api/schema/', api_views.PetCareSpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# =====================================================================
# FALLBACK DE RUTAS (equivalente al re_path de EVA 2 / CarritoShop)
# Cualquier URL web desconocida vuelve a la portada. Se excluyen /admin/,
# /api/, /static/ y /media/ para no romper el panel, la API ni los archivos.
# =====================================================================
urlpatterns += [
    re_path(
        r'^(?!admin(?:/|$)|api(?:/|$)|static(?:/|$)|media(?:/|$)).*$',
        redirect_to_home,
        name='catch_all',
    ),
]

handler404 = 'petcare.views.error_404'
handler500 = 'petcare.views.error_500'
