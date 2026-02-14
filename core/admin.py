from django.contrib import admin
from .models import Agente, TipoLicencia, Solicitud

# Configuración para la tabla AGENTES
@admin.register(Agente)
class AgenteAdmin(admin.ModelAdmin):
    list_display = ('legajo', 'apellido', 'nombre', 'id_sistema_reloj', 'email')
    search_fields = ('legajo', 'apellido', 'nombre')
    list_filter = ('supervisores',) # Filtro rápido por supervisor
    
    # Esto permite seleccionar supervisores de forma más amigable (con buscador)
    # en lugar de una lista gigante.
    filter_horizontal = ('supervisores',)

# Configuración para la tabla TIPOS DE LICENCIA
@admin.register(TipoLicencia)
class TipoLicenciaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'descripcion', 'texto_para_reloj', 'requiere_aviso')
    search_fields = ('codigo', 'descripcion')

# Configuración para la tabla SOLICITUDES
@admin.register(Solicitud)
class SolicitudAdmin(admin.ModelAdmin):
    list_display = ('fecha_inicio', 'agente', 'tipo', 'estado', 'jefe_seleccionado')
    list_filter = ('estado', 'tipo', 'fecha_inicio')
    search_fields = ('agente__apellido', 'agente__legajo') # Busca por apellido del agente
    
    # Hacemos que la fecha de solicitud sea de solo lectura (para que nadie la truque)
    readonly_fields = ('fecha_solicitud',)
