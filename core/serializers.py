from rest_framework import serializers
from .models import Agente, TipoLicencia, Solicitud

#1. Serializer pequeñito para mostrar datos básicos de jefes en el dropdown
class AgenteSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agente
        fields = ['id', 'nombre', 'apellido', 'legajo']

#2. El serializer principal de Agentes
class AgenteSerializer(serializers.ModelSerializer):
    # Campo mágico: muestra los detalles de los supervisores, no solo el ID
    supervisores_detalle = AgenteSimpleSerializer(source='supervisores', many=True, read_only=True)
    # Campo es jefe?
    es_jefe = serializers.SerializerMethodField()

    # Nuevo campo para saber si es personal de RRHH (Staff)
    es_rrhh = serializers.SerializerMethodField()

    class Meta:
        model = Agente
        fields = '__all__' # Transforma TODOS los campos a JSON

    def get_es_jefe(self, obj):
        # Retorna True si tiene gente a cargo (subordinados >0)
        return obj.subordinados.exists()
    
    # Si el usuario vinculado a este agente es Staff de Django, es RRHH
    def get_es_rrhh(self, obj):

        return obj.legajo <= 10

class TipoLicenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoLicencia
        fields = '__all__'

# backend/core/serializers.py

class SolicitudSerializer(serializers.ModelSerializer):
    nombre_agente = serializers.CharField(source='agente.nombre', read_only=True)
    apellido_agente = serializers.CharField(source='agente.apellido', read_only=True)
    
    # Para que Vue muestre el nombre, no el número ID
    tipo_descripcion = serializers.CharField(source='tipo.descripcion', read_only=True)
    tipo_codigo = serializers.CharField(source='tipo.codigo', read_only=True)
    
    class Meta:
        model = Solicitud
        fields = '__all__'

    def validate(self, data):
        """
        Lógica Estricta:
        1. Las validaciones de topes (Business Logic) SOLO se ejecutan al CREAR o al RE-PROGRAMAR (cambiar fecha).
        2. Las acciones administrativas (Aprobar, Rechazar, Observar) SE SALTAN los topes.
        """

        # ---------------------------------------------------------------------
        # PASO 1: DETECTAR SI ES UN TRÁMITE ADMINISTRATIVO (Edición de Estado)
        # ---------------------------------------------------------------------
        # Mejora: si sólo viene el campo "estado", es claramente un cambio administrativo
        if self.instance and set(data.keys()) == {'estado'}:
            # Es RRHH o un Jefe cambiando solo el estado
            return data
        
        if self.instance:
            # Estamos editando una solicitud existente.
            # Verificamos si los datos CRÍTICOS (Fecha y Tipo) son iguales a los que ya están en base de datos.
            
            # Valor que viene del frontend (o el que ya tiene si no viene)
            fecha_entrante = data.get('fecha_inicio', self.instance.fecha_inicio)
            tipo_entrante = data.get('tipo', self.instance.tipo)
            
            # Valor que está guardado en disco
            fecha_guardada = self.instance.fecha_inicio
            tipo_guardado = self.instance.tipo

            # SI NO CAMBIÓ LA FECHA Y NO CAMBIÓ EL TIPO...
            if fecha_entrante == fecha_guardada and tipo_entrante == tipo_guardado:
                # ... Es un trámite administrativo (RRHH o Jefe cambiando estado).
                # NO validamos topes. El cupo ya se descontó cuando se creó.
                return data

        # ---------------------------------------------------------------------
        # PASO 2: VALIDACIÓN DE REGLAS (Solo para Creación o Cambio de Fecha)
        # ---------------------------------------------------------------------
        # Si el código llega acá, es porque:
        # A) Es una solicitud NUEVA (Create).
        # B) Es una solicitud VIEJA a la que le están cambiando la fecha (Update crítico).
        
        # Recuperamos los datos a validar
        if self.instance:
            agente = data.get('agente', self.instance.agente)
            tipo_licencia = data.get('tipo', self.instance.tipo)
            fecha_obj = data.get('fecha_inicio', self.instance.fecha_inicio)
        else:
            agente = data.get('agente')
            tipo_licencia = data.get('tipo')
            fecha_obj = data.get('fecha_inicio')

        # --- REGLA 1: ART 85 (Control de Topes) ---
        if tipo_licencia.codigo.lower() == 'art_85':
            
            # Contamos cuántas hay activas en ese mes/año
            query_mensual = Solicitud.objects.filter(
                agente=agente,
                tipo__codigo__iexact='art_85',
                fecha_inicio__month=fecha_obj.month,
                fecha_inicio__year=fecha_obj.year
            ).exclude(estado__contains='RECHAZADO')
            
            # Si estoy editando y CAMBIANDO FECHA, me excluyo para no contar doble
            if self.instance:
                query_mensual = query_mensual.exclude(pk=self.instance.pk)
            
            if query_mensual.count() >= 2:
                raise serializers.ValidationError(f"⛔ Tope mensual alcanzado (2).")

            query_anual = Solicitud.objects.filter(
                agente=agente,
                tipo__codigo__iexact='art_85',
                fecha_inicio__year=fecha_obj.year
            ).exclude(estado__contains='RECHAZADO')

            if self.instance:
                query_anual = query_anual.exclude(pk=self.instance.pk)

            if query_anual.count() >= 6:
                raise serializers.ValidationError(f"⛔ Tope anual alcanzado (6).")

        # --- REGLA 2: Duplicados ---
        duplicados = Solicitud.objects.filter(agente=agente, fecha_inicio=fecha_obj).exclude(estado__contains='RECHAZADO')
        if self.instance:
            duplicados = duplicados.exclude(pk=self.instance.pk)
            
        if duplicados.exists():
             raise serializers.ValidationError("⚠️ Fecha duplicada.")

        return data