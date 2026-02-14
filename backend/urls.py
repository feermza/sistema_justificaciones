from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from core.views import AgenteViewSet, TipoLicenciaViewSet, SolicitudViewSet

# Importaciones para archivos media
from django.conf import settings
from django.conf.urls.static import static

#El Router crea las direcciones automáticamente
router = DefaultRouter()
router.register(r'agentes', AgenteViewSet, basename='agente')
router.register(r'licencias', TipoLicenciaViewSet)
router.register(r'solicitudes', SolicitudViewSet, basename='solicitud')

urlpatterns = [
    path('admin/', admin.site.urls),
    #Aquí "pegamos" nuestras rutas de la API
    path('api/', include(router.urls)),
]

# Truco: Si estamos en modo desarrollo, permitir descargar archivos
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root= settings.MEDIA_ROOT)