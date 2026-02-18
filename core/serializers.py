from rest_framework import serializers
from .models import Agente, TipoLicencia, Solicitud
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired


# 1. Serializer pequeñito para mostrar datos básicos de jefes en el dropdown
class AgenteSimpleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agente
        fields = ["id", "nombre", "apellido", "legajo"]


# 2. El serializer principal de Agentes
class AgenteSerializer(serializers.ModelSerializer):
    # CAMBIO CRÍTICO: Ya no leemos una lista fija, la calculamos al vuelo
    supervisores_detalle = serializers.SerializerMethodField()

    es_jefe = serializers.SerializerMethodField()
    es_rrhh = serializers.SerializerMethodField()
    nombre_area = serializers.CharField(
        source="area.nombre", read_only=True
    )  # Para mostrar en el frontend

    class Meta:
        model = Agente
        fields = "__all__"

    def get_es_jefe(self, obj):
        # Ahora ser jefe depende de TU categoría, no de si alguien te eligió
        return obj.es_autoridad  # Usa la propiedad que creamos en el modelo

    def get_es_rrhh(self, obj):
        return obj.es_rrhh

    # --- AQUÍ ESTÁ LA MAGIA DE LA JERARQUÍA ---
    def get_supervisores_detalle(self, obj):
        """
        Retorna la lista de posibles Jefes para este agente.
        Regla: Misma Área + Categoría (02, 03 o 04).
        """
        if not obj.area:
            return []  # Si no tiene área asignada, no tiene jefes

        # Buscamos agentes de la MISMA ÁREA que sean AUTORIDADES
        jefes = Agente.objects.filter(
            area=obj.area, categoria__in=["02", "03", "04"]
        ).exclude(id=obj.id)  # Me excluyo a mí mismo (si yo fuera jefe también)

        return AgenteSimpleSerializer(jefes, many=True).data


class TipoLicenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoLicencia
        fields = "__all__"


class SolicitudSerializer(serializers.ModelSerializer):
    nombre_agente = serializers.CharField(source="agente.nombre", read_only=True)
    apellido_agente = serializers.CharField(source="agente.apellido", read_only=True)
    tipo_descripcion = serializers.CharField(source="tipo.descripcion", read_only=True)
    tipo_codigo = serializers.CharField(source="tipo.codigo", read_only=True)

    class Meta:
        model = Solicitud
        fields = "__all__"

    def validate(self, data):
        # 1. RECUPERACIÓN DE DATOS (Strategy: Incoming Data > Existing Data)
        # Definimos las variables críticas desde el principio para evitar el UnboundLocalError

        # AGENTE
        if "agente" in data:
            agente = data["agente"]
        elif self.instance:
            agente = self.instance.agente
        else:
            # Si es creación nueva y falta el agente, DRF lanzará error de campo requerido antes de llegar aquí.
            # Retornamos data para que siga el flujo estándar de error.
            return data

        # TIPO DE LICENCIA
        if "tipo" in data:
            tipo_licencia = data["tipo"]
        elif self.instance:
            tipo_licencia = self.instance.tipo
        else:
            return data

        # FECHA INICIO
        if "fecha_inicio" in data:
            fecha_obj = data["fecha_inicio"]
        elif self.instance:
            fecha_obj = self.instance.fecha_inicio
        else:
            return data

        # ------------------------------------------------------------------
        # PASO 2: Optimización para Actualizaciones de Estado (Aprobación Jefe/RRHH)
        # Si estamos editando y NO cambiaron las fechas ni el tipo, saltamos validaciones pesadas.
        if self.instance:
            # Verificamos si lo que viene en data es diferente a lo guardado
            cambia_fecha = (
                "fecha_inicio" in data
                and data["fecha_inicio"] != self.instance.fecha_inicio
            )
            cambia_tipo = "tipo" in data and data["tipo"] != self.instance.tipo

            # Si NO cambia ni fecha ni tipo, asumimos que es solo un cambio de estado/motivo
            # y retornamos data directamente.
            if not cambia_fecha and not cambia_tipo:
                return data
        # ------------------------------------------------------------------

        # PASO 3: VALIDACIÓN DE REGLAS DE NEGOCIO

        # --- REGLA 1: ART 85 (Topes Mensuales y Anuales) ---
        # Aseguramos obtener el código string correctamente
        try:
            codigo_str = tipo_licencia.codigo
        except AttributeError:
            # Fallback por si tipo_licencia viene como diccionario o ID raw (raro en este punto pero seguro)
            codigo_str = str(tipo_licencia)

        if codigo_str.lower() == "art_85":
            # Tope Mensual (2)
            query_mensual = Solicitud.objects.filter(
                agente=agente,
                tipo__codigo__iexact="art_85",
                fecha_inicio__month=fecha_obj.month,
                fecha_inicio__year=fecha_obj.year,
            ).exclude(estado__contains="RECHAZADO")  # Ignoramos rechazadas

            if self.instance:
                query_mensual = query_mensual.exclude(pk=self.instance.pk)

            if query_mensual.count() >= 2:
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            "⛔ Tope mensual para Art. 85 alcanzado (máximo 2)."
                        ]
                    }
                )

            # Tope Anual (6)
            query_anual = Solicitud.objects.filter(
                agente=agente,
                tipo__codigo__iexact="art_85",
                fecha_inicio__year=fecha_obj.year,
            ).exclude(estado__contains="RECHAZADO")

            if self.instance:
                query_anual = query_anual.exclude(pk=self.instance.pk)

            if query_anual.count() >= 6:
                raise serializers.ValidationError(
                    {
                        "non_field_errors": [
                            "⛔ Tope anual para Art. 85 alcanzado (máximo 6)."
                        ]
                    }
                )

        # --- REGLA 2: Duplicados (Mismo día) ---
        duplicados = Solicitud.objects.filter(
            agente=agente, fecha_inicio=fecha_obj
        ).exclude(
            estado__contains="RECHAZADO"
        )  # Permitimos re-pedir si la anterior fue rechazada

        if self.instance:
            duplicados = duplicados.exclude(pk=self.instance.pk)

        if duplicados.exists():
            raise serializers.ValidationError(
                {"fecha_inicio": "⚠️ Ya existe una solicitud activa para esta fecha."}
            )

        return data


# ---------------------------------------------------------
# WIZARD DE ACTIVACIÓN - PASO 1: IDENTIFICACIÓN
# ---------------------------------------------------------
class ActivacionPaso1Serializer(serializers.Serializer):
    legajo = serializers.IntegerField()
    dni = serializers.CharField()
    fecha_nacimiento = serializers.DateField()

    # ¡AQUÍ ESTABA EL ERROR! Ahora 'def validate' está identado DENTRO de la clase
    def validate(self, data):
        legajo = data.get("legajo")
        dni = data.get("dni")
        fecha_ingresada_obj = data.get("fecha_nacimiento")

        try:
            agente = Agente.objects.get(legajo=legajo)
        except Agente.DoesNotExist:
            raise serializers.ValidationError("⛔ No existe un agente con ese legajo.")

        if agente.usuario is not None:
            raise serializers.ValidationError(
                "✅ Esta cuenta YA está activa. Vaya al Login e ingrese con su clave."
            )

        dni_limpio = str(dni).replace(".", "").strip()
        agente_dni_limpio = str(agente.dni).replace(".", "").strip()

        if agente_dni_limpio != dni_limpio:
            raise serializers.ValidationError(
                "⛔ El DNI ingresado no coincide con nuestros registros."
            )

        if not agente.fecha_nacimiento:
            raise serializers.ValidationError(
                "⚠️ Error de datos: RRHH no cargó su fecha de nacimiento. Contáctelos."
            )

        str_fecha_real = agente.fecha_nacimiento.strftime("%Y-%m-%d")
        str_fecha_ingresada = fecha_ingresada_obj.strftime("%Y-%m-%d")

        if str_fecha_real != str_fecha_ingresada:
            raise serializers.ValidationError(
                "⛔ La fecha de nacimiento es incorrecta."
            )

        # Guardamos el agente en el contexto para la vista
        self.context["agente"] = agente
        return data


# ---------------------------------------------------------
# WIZARD DE ACTIVACIÓN - PASO 2: DEFINICIÓN DE CLAVE
# ---------------------------------------------------------
class ActivacionPaso2Serializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField()

    def validate(self, data):
        token = data["token"]
        password = data["password"]
        signer = TimestampSigner()

        # 1. Validar Token
        try:
            agente_id = signer.unsign(token, max_age=600)
        except (BadSignature, SignatureExpired):
            raise serializers.ValidationError(
                "⛔ Su sesión de activación expiró. Vuelva a empezar."
            )

        agente = Agente.objects.get(id=agente_id)
        es_rrhh = agente.es_rrhh

        # --- VALIDACIONES DE SEGURIDAD ---

        if es_rrhh:
            # === REGLAS PARA RRHH (Password fuerte) ===
            if len(password) < 8:
                raise serializers.ValidationError(
                    "⛔ La contraseña debe tener al menos 8 caracteres."
                )
            if password.isdigit():
                raise serializers.ValidationError(
                    "⛔ La contraseña debe ser alfanumérica (letras y números)."
                )

        else:
            # === REGLAS PARA USUARIO COMÚN (PIN) ===

            # A. Formato Básico
            if not password.isdigit() or len(password) != 6:
                raise serializers.ValidationError(
                    "⛔ El PIN debe ser numérico de 6 dígitos."
                )

            # B. Bloqueo de Secuencias Obvias (NUEVO)
            # 1. Repetidos (Ej: 111111)
            if len(set(password)) == 1:
                raise serializers.ValidationError(
                    "⛔ No use el mismo número repetido (Ej: 111111)."
                )

            # 2. Secuencias Ascendentes/Descendentes (Ej: 123456, 654321)
            secuencia_asc = (
                "01234567890123456789"  # Doble para capturar ciclos si fuera necesario
            )
            secuencia_desc = "98765432109876543210"

            if password in secuencia_asc:
                raise serializers.ValidationError(
                    "⛔ No use secuencias ascendentes (Ej: 123456)."
                )
            if password in secuencia_desc:
                raise serializers.ValidationError(
                    "⛔ No use secuencias descendentes (Ej: 654321)."
                )

            # C. Bloqueo de DNI (Completo y Parcial)
            dni_str = str(agente.dni).replace(".", "").strip()

            if password == dni_str:
                raise serializers.ValidationError(
                    "⛔ El PIN no puede ser idéntico a su DNI."
                )

            if len(dni_str) >= 4:
                primeros_4 = dni_str[:4]
                ultimos_4 = dni_str[-4:]
                if primeros_4 in password:
                    raise serializers.ValidationError(
                        f"⛔ El PIN no puede contener el inicio de su DNI ({primeros_4})."
                    )
                if ultimos_4 in password:
                    raise serializers.ValidationError(
                        f"⛔ El PIN no puede contener el final de su DNI ({ultimos_4})."
                    )

            # D. Bloqueo de Fecha de Nacimiento (Formatos Varios)
            f_nac = agente.fecha_nacimiento
            variantes_fecha = [
                f_nac.strftime("%d%m%y"),  # "251180" (DDMMAA)
                f_nac.strftime("%d%m%Y"),  # "25111980"
                f_nac.strftime("%Y%m%d"),  # "19801125"
            ]
            if password in variantes_fecha:
                raise serializers.ValidationError(
                    "⛔ No use su fecha de nacimiento completa como PIN."
                )

            # Día y Mes juntos
            dia_mes = f_nac.strftime("%d%m")  # "2511"
            if dia_mes in password:
                raise serializers.ValidationError(
                    f"⛔ El PIN no puede contener su día y mes de nacimiento ({dia_mes})."
                )

            # Año completo
            anio = f_nac.strftime("%Y")  # "1980"
            if anio in password:
                raise serializers.ValidationError(
                    f"⛔ El PIN no puede contener su año de nacimiento ({anio})."
                )

        self.context["agente"] = agente
        return data
