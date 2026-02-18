from django.contrib import admin
from .models import Agente, TipoLicencia, Solicitud, Area

# 1. Registrar Áreas
admin.site.register(Area)


# 2. Registrar Agentes (Con configuración personalizada para ver las columnas nuevas)
@admin.register(Agente)
class AgenteAdmin(admin.ModelAdmin):
    list_display = ("legajo", "apellido", "nombre", "area", "categoria")
    list_filter = ("area", "categoria")
    search_fields = ("legajo", "apellido", "nombre")


# 3. Registrar Tipos de Licencia
admin.site.register(TipoLicencia)


# 4. Registrar Solicitudes
@admin.register(Solicitud)
class SolicitudAdmin(admin.ModelAdmin):
    list_display = ("agente", "tipo", "fecha_inicio", "estado")
    list_filter = ("estado", "tipo")
