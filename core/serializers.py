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
    # Campo mágico: muestra los detalles de los supervisores, no solo el ID
    supervisores_detalle = AgenteSimpleSerializer(
        source="supervisores", many=True, read_only=True
    )

    es_jefe = serializers.SerializerMethodField()
    es_rrhh = serializers.SerializerMethodField()

    class Meta:
        model = Agente
        fields = "__all__"

    def get_es_jefe(self, obj):
        return obj.subordinados.exists()

    def get_es_rrhh(self, obj):
        return obj.es_rrhh


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
        # PASO 1: DETECTAR SI ES UN TRÁMITE ADMINISTRATIVO
        if self.instance and set(data.keys()) == {"estado"}:
            return data

        if self.instance:
            # Validación de cambios críticos
            fecha_entrante = data.get("fecha_inicio", self.instance.fecha_inicio)
            tipo_entrante = data.get("tipo", self.instance.tipo)
            fecha_guardada = self.instance.fecha_inicio
            tipo_guardado = self.instance.tipo

            if fecha_entrante == fecha_guardada and tipo_entrante == tipo_guardado:
                return data

        # PASO 2: VALIDACIÓN DE REGLAS
        if self.instance:
            agente = data.get("agente", self.instance.agente)
            # tipo_licencia no se usa directamente en la query si ya filtramos por codigo abajo,
            # pero lo dejamos por consistencia si fuera necesario.
            # tipo_licencia = data.get('tipo', self.instance.tipo)
            fecha_obj = data.get("fecha_inicio", self.instance.fecha_inicio)
        else:
            agente = data.get("agente")
            tipo_licencia = data.get("tipo")  # Se obtiene del data
            fecha_obj = data.get("fecha_inicio")

        # --- REGLA 1: ART 85 ---
        # Verificamos el código usando el objeto tipo_licencia recuperado
        tipo_codigo = (
            tipo_licencia.codigo
            if hasattr(tipo_licencia, "codigo")
            else data.get("tipo").codigo
        )

        if tipo_codigo.lower() == "art_85":
            query_mensual = Solicitud.objects.filter(
                agente=agente,
                tipo__codigo__iexact="art_85",
                fecha_inicio__month=fecha_obj.month,
                fecha_inicio__year=fecha_obj.year,
            ).exclude(estado__contains="RECHAZADO")

            if self.instance:
                query_mensual = query_mensual.exclude(pk=self.instance.pk)

            if query_mensual.count() >= 2:
                # Corregido: Quitada la f
                raise serializers.ValidationError("⛔ Tope mensual alcanzado (2).")

            query_anual = Solicitud.objects.filter(
                agente=agente,
                tipo__codigo__iexact="art_85",
                fecha_inicio__year=fecha_obj.year,
            ).exclude(estado__contains="RECHAZADO")

            if self.instance:
                query_anual = query_anual.exclude(pk=self.instance.pk)

            if query_anual.count() >= 6:
                # Corregido: Quitada la f
                raise serializers.ValidationError("⛔ Tope anual alcanzado (6).")

        # --- REGLA 2: Duplicados ---
        duplicados = Solicitud.objects.filter(
            agente=agente, fecha_inicio=fecha_obj
        ).exclude(estado__contains="RECHAZADO")
        if self.instance:
            duplicados = duplicados.exclude(pk=self.instance.pk)

        if duplicados.exists():
            raise serializers.ValidationError("⚠️ Fecha duplicada.")

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

        try:
            agente_id = signer.unsign(token, max_age=600)
        except (BadSignature, SignatureExpired):
            raise serializers.ValidationError(
                "⛔ Su sesión de activación expiró. Vuelva a empezar."
            )

        agente = Agente.objects.get(id=agente_id)

        es_rrhh = agente.es_rrhh

        if es_rrhh:
            if len(password) < 8:
                raise serializers.ValidationError(
                    "⛔ La contraseña debe tener al menos 8 caracteres."
                )
            if password.isdigit():
                raise serializers.ValidationError(
                    "⛔ La contraseña debe ser alfanumérica (letras y números)."
                )
        else:
            # REGLAS PARA USUARIO COMÚN (PIN)
            if not password.isdigit() or len(password) != 6:
                raise serializers.ValidationError(
                    "⛔ El PIN debe ser numérico de 6 dígitos."
                )

            dni_str = str(agente.dni).replace(".", "").strip()

            # 1. Chequeo Estricto: El PIN no puede ser igual al DNI (por si acaso)
            if password == dni_str:
                raise serializers.ValidationError(
                    "⛔ El PIN no puede ser idéntico a su DNI."
                )

            # 2. Chequeo de Patrones (Tu corrección)
            # Verificamos si los primeros 4 o últimos 4 del DNI están metidos en el PIN
            if len(dni_str) >= 4:
                primeros_4 = dni_str[:4]  # Ej: 1234
                ultimos_4 = dni_str[-4:]  # Ej: 5678

                if primeros_4 in password:
                    raise serializers.ValidationError(
                        f"⛔ El PIN no puede contener los primeros dígitos de su DNI ({primeros_4})."
                    )

                if ultimos_4 in password:
                    raise serializers.ValidationError(
                        f"⛔ El PIN no puede contener los últimos dígitos de su DNI ({ultimos_4})."
                    )

            # 3. Chequeo de Fecha de Nacimiento
            fecha_str = str(agente.fecha_nacimiento).replace("-", "")  # YYYYMMDD
            if password in fecha_str:
                raise serializers.ValidationError(
                    "⛔ Por seguridad, el PIN no puede contener su fecha de nacimiento."
                )

            # 4. Chequeo de secuencias obvias (Opcional pero recomendado)
            if password in ["123456", "000000", "111111", "654321"]:
                raise serializers.ValidationError(
                    "⛔ El PIN es demasiado inseguro. No use secuencias simples."
                )

        self.context["agente"] = agente
        return data
