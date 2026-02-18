from rest_framework import viewsets
from .models import Agente, TipoLicencia, Solicitud
from .serializers import (
    AgenteSerializer,
    TipoLicenciaSerializer,
    SolicitudSerializer,
    ActivacionPaso1Serializer,
    ActivacionPaso2Serializer,
)
from django.core.mail import send_mail
from django.conf import settings
import csv
from django.http import HttpResponse
from rest_framework.decorators import action
from rest_framework.response import Response
from django.core.signing import TimestampSigner
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from .utils import generar_pdf_legajo


# Vista para ver/editar Agentes
class AgenteViewSet(viewsets.ModelViewSet):
    serializer_class = AgenteSerializer

    def get_queryset(self):
        # Empezamos con todos los agentes
        queryset = Agente.objects.all()

        # Buscamos si vienen datos en la URL
        legajo = self.request.query_params.get("legajo")
        dni = self.request.query_params.get("dni")

        # Si vienen los dos, filtramos para ver si coinciden
        if legajo and dni:
            queryset = queryset.filter(legajo=legajo, dni=dni)

        return queryset

    @action(detail=False, methods=["post"])
    def validar_identidad(self, request):
        """Paso 1: Recibe Legajo+DNI+Fecha. Retorna un Token Temporal."""
        serializer = ActivacionPaso1Serializer(data=request.data)

        if serializer.is_valid():
            agente = serializer.context["agente"]

            # Generamos un token firmado que vale por 10 minutos
            signer = TimestampSigner()
            token = signer.sign(agente.id)

            # Determinamos qué tipo de usuario es para decirle al frontend qué mostrar
            es_rrhh = agente.es_rrhh  # Misma lógica de tu modelo
            tipo_input = "password" if es_rrhh else "pin"

            return Response(
                {
                    "status": "ok",
                    "token": token,
                    "tipo_usuario": tipo_input,
                    "mensaje": "Identidad validada. Proceda a configurar su clave.",
                }
            )

        return Response(serializer.errors, status=400)

    @action(detail=False, methods=["post"])
    def activar_cuenta(self, request):
        """Paso 2: Recibe Token+Clave. Crea el Usuario Django y activa."""
        serializer = ActivacionPaso2Serializer(data=request.data)

        if serializer.is_valid():
            agente = serializer.context["agente"]
            password = serializer.validated_data["password"]

            # 1. Crear el Usuario Django (Auth)
            # Usamos el legajo como username para garantizar unicidad
            username = str(agente.legajo)

            try:
                # Si existía un usuario viejo huerfano, lo borramos para evitar error
                User.objects.filter(username=username).delete()

                user = User.objects.create_user(
                    username=username, email=agente.email, password=password
                )

                # 2. Vincular Agente -> Usuario
                agente.usuario = user
                agente.save()

                return Response(
                    {"status": "ok", "mensaje": "¡Cuenta activada exitosamente!"}
                )

            except Exception as e:
                return Response({"error": str(e)}, status=500)

        return Response(serializer.errors, status=400)

    @action(detail=False, methods=["post"])
    def login(self, request):
        """Recibe Legajo y Password/PIN. Valida contra Django Auth con mensajes inteligentes."""
        legajo = request.data.get("legajo")
        password = request.data.get("password")

        if not legajo or not password:
            return Response({"error": "Faltan datos"}, status=400)

        # 1. Intentamos autenticar (Usuario ya activo y clave correcta)
        user = authenticate(username=str(legajo), password=password)

        if user is not None:
            if hasattr(user, "agente_perfil"):
                agente = user.agente_perfil
                serializer = AgenteSerializer(agente)
                return Response(serializer.data)
            else:
                return Response(
                    {"error": "Usuario válido pero sin perfil de Agente asociado."},
                    status=403,
                )

        # 2. Si falló la autenticación, investigamos POR QUÉ para ayudar al usuario
        else:
            # Buscamos si el legajo existe en nuestra base de empleados
            try:
                agente = Agente.objects.get(legajo=legajo)

                # CASO A: El empleado existe, pero NO tiene usuario vinculado (No activó cuenta)
                if agente.usuario is None:
                    return Response(
                        {
                            "error": "⚠️ Tu cuenta no está activada. Haz clic en 'Activar mi cuenta' abajo.",
                            "necesita_activacion": True,
                        },
                        status=401,
                    )

                # CASO B: El empleado existe Y tiene usuario -> La contraseña está mal
                else:
                    return Response(
                        {
                            "error": "⛔ Contraseña o PIN incorrecto. Inténtalo de nuevo."
                        },
                        status=401,
                    )

            except Agente.DoesNotExist:
                # CASO C: El legajo ni siquiera existe en la base de datos
                return Response({"error": "⛔ Legajo no encontrado."}, status=404)


# Vista para ver/editar Tipos de Licencia
class TipoLicenciaViewSet(viewsets.ModelViewSet):
    queryset = TipoLicencia.objects.all()
    serializer_class = TipoLicenciaSerializer


# Vista para ver/editar Solicitudes
class SolicitudViewSet(viewsets.ModelViewSet):
    serializer_class = SolicitudSerializer

    def get_queryset(self):
        # Ordenamos por fecha de inicio (las más nuevas primero)
        queryset = Solicitud.objects.all().order_by("-fecha_inicio")

        # Filtramos por el ID del agente si viene en la URL
        agente_id = self.request.query_params.get("agente")

        if agente_id:
            queryset = queryset.filter(agente=agente_id)

        # Filtro 2: Solicitudes que me enviaron a mí (Soy jefe)
        jefe_id = self.request.query_params.get("jefe")
        if jefe_id:
            # Solo me interesan los que están esperando MI validación
            queryset = queryset.filter(
                jefe_seleccionado=jefe_id, estado="PENDIENTE_VALIDACION"
            )
        # si la url dice ?modo_rrhh=true, devolvemos todo lo confirmado
        modo_rrhh = self.request.query_params.get("modo_rrhh")
        if modo_rrhh == "true":
            queryset = queryset.filter(
                estado__in=[
                    "AVISO_CONFIRMADO",
                    "AVISO_NEGADO",
                    "APROBADO",
                    "IMPACTADO",
                    "RECHAZADO_RRHH",
                    "RECHAZADO",
                ]
            )

        return queryset

    # NUEVO: Interceptamos el guardado para mandar mail
    def perform_create(self, serializer):
        # 1. Guardamos la solicitud
        solicitud = serializer.save()

        # 2. Preparamos el email
        jefe = solicitud.jefe_seleccionado
        agente = solicitud.agente

        asunto = f"NUEVO AVISO: {agente.apellido} cargó una solicitud"
        mensaje = f"""
        Hola {jefe.nombre},
        
        El agente {agente.nombre} {agente.apellido} (Legajo {agente.legajo}) ha cargado un aviso de ausencia.
        
        Tipo: {solicitud.tipo.descripcion}
        Fecha: {solicitud.fecha_inicio}
        Motivo: {solicitud.motivo}
        
        Por favor, ingrese al sistema para validar si fue avisado en tiempo y forma.
        """

        # 3. Enviamos (Esto saldrá en tu terminal negra)
        if jefe and jefe.email:
            print(f"--- INTENTANDO ENVIAR MAIL A {jefe.email} ---")
            send_mail(
                asunto,
                mensaje,
                settings.EMAIL_HOST_USER,
                [jefe.email],
                fail_silently=False,
            )

    def perform_update(self, serializer):
        """
        Se ejecuta cuando RRHH o un Jefe actualiza una solicitud.
        Envía emails automáticos según el nuevo estado.
        """
        # 1. Guardar los cambios
        instance = serializer.save()
        agente = instance.agente

        # 2. Preparar variables para el email
        asunto = None
        mensaje = None

        # 3. Determinar qué email enviar según el NUEVO estado

        # CASO A: SOLICITUD APROBADA (Impactada en el sistema)
        if instance.estado == "IMPACTADO":
            print("🖨️ Generando PDF de respaldo...")
            generar_pdf_legajo(instance)

            asunto = f"✅ Solicitud Aprobada: {instance.tipo.descripcion}"
            mensaje = f"""
            Hola {agente.nombre},

            Tu solicitud de justificación para el día {instance.fecha_inicio} ha sido APROBADA e IMPACTADA en el sistema.

            Detalles:
            - Tipo: {instance.tipo.descripcion}
            - Días: {instance.dias}
            - Fecha: {instance.fecha_inicio}

            Saludos,
            Departamento de Personal - UTN
            """

        # CASO B: SOLICITUD RECHAZADA (Por RRHH o Jefe dijo "No avisó")
        elif instance.estado in ["RECHAZADO", "AVISO_NEGADO"]:
            # Obtener el motivo del rechazo (si existe)
            motivo_texto = (
                instance.motivo_rechazo
                if instance.motivo_rechazo
                else "Sin especificar"
            )

            # Determinar quién rechazó
            if instance.estado == "RECHAZADO":
                rechazado_por = "Recursos Humanos"
            else:  # AVISO_NEGADO
                rechazado_por = f"su supervisor ({instance.jefe_seleccionado.apellido if instance.jefe_seleccionado else 'N/A'})"

            asunto = f"❌ Solicitud Rechazada: {instance.tipo.descripcion}"
            mensaje = f"""
            Hola {agente.nombre},

            Te informamos que tu solicitud de justificación para el día {instance.fecha_inicio} ha sido RECHAZADA.

            ╔══════════════════════════════════════════════════════════╗
            ║  MOTIVO DEL RECHAZO:                                     ║
            ║  {motivo_texto[:54].ljust(54)} ║
            ╚══════════════════════════════════════════════════════════╝

            Detalles:
            - Tipo: {instance.tipo.descripcion}
            - Fecha solicitada: {instance.fecha_inicio}
            - Días: {instance.dias}
            - Estado actual: {instance.get_estado_display()}
            - Rechazado por: {rechazado_por}

            Por favor, comunícate con el Departamento de Personal para más información.

            Saludos,
            Departamento de Personal - UTN
            """

        # CASO C: JEFE CONFIRMÓ EL AVISO (Pasa a RRHH, pero no notificamos al agente aún)
        elif instance.estado == "AVISO_CONFIRMADO":
            # No enviamos email al agente en este estado intermedio
            # Solo notificamos cuando RRHH toma la decisión final
            pass

        # 4. ENVIAR EL EMAIL (si corresponde)
        if asunto and mensaje and agente.email:
            print(f"\n{'=' * 60}")
            print("📧 ENVIANDO EMAIL")
            print(f"{'=' * 60}")
            print(f"Para: {agente.email}")
            print(f"Asunto: {asunto}")
            print(f"Estado de la solicitud: {instance.estado}")
            print(f"{'=' * 60}\n")

            try:
                send_mail(
                    asunto,
                    mensaje,
                    settings.EMAIL_HOST_USER,  # 'sistema@frn.utn.edu.ar'
                    [agente.email],
                    fail_silently=False,
                )
                print("✅ ¡Email enviado correctamente!\n")
            except Exception as e:
                print(f"❌ Error al enviar email: {e}\n")
        else:
            # Debug: ¿Por qué no se envió?
            if not asunto:
                print(
                    f"ℹ️  No se envió email - Estado '{instance.estado}' no requiere notificación"
                )
            elif not agente.email:
                print(
                    f"⚠️  No se envió email - Agente {agente.legajo} no tiene email configurado"
                )

    # Función para manejo de borrado de solicitud
    def destroy(self, request, *args, **kwargs):
        # 1. Recuperamos la solicitud que quieren borrar
        instance = self.get_object()

        # 2. VERIFICACIÓN DE SEGURIDAD
        # Solo permitimos borrar si el Jefe todavía no la tocó (Pendiente)
        if instance.estado != "PENDIENTE_VALIDACION":
            # Importar ValidationError de rest_framework.exceptions al inicio del archivo si no está
            from rest_framework.exceptions import ValidationError

            raise ValidationError(
                f"⛔ No se puede eliminar esta solicitud porque ya se encuentra en estado '{instance.estado}'. Comuníquese con RRHH."
            )

        # 3. LÓGICA ANTI-GHOSTING (El punto que planteaste)
        # Si la solicitud tenía un jefe asignado, le avisamos que se canceló.
        jefe = instance.jefe_seleccionado
        agente = instance.agente

        if jefe and jefe.email:
            asunto = f"🚫 AVISO CANCELADO: {agente.apellido} anuló su solicitud"
            mensaje = f"""
            Hola {jefe.nombre},
            
            El agente {agente.nombre} {agente.apellido} ha decidido CANCELAR y ELIMINAR la solicitud que había cargado previamente.
            
            Detalle de lo eliminado:
            - Fecha original: {instance.fecha_inicio}
            - Tipo: {instance.tipo.descripcion}
            
            NO ES NECESARIO que ingrese al sistema para validarla. El trámite ha sido cerrado por el propio agente.
            
            Saludos.
            """
            print(f"🗑️ Enviando aviso de cancelación a {jefe.email}...")
            try:
                send_mail(
                    asunto,
                    mensaje,
                    settings.EMAIL_HOST_USER,
                    [jefe.email],
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Error enviando aviso de cancelación: {e}")

        # 4. Procedemos al borrado físico
        return super().destroy(request, *args, **kwargs)

    # Método de Reportes
    @action(
        detail=False, methods=["get"]
    )  # Se accede como /api/solicitudes/exportar_excel
    def exportar_excel(self, request):
        # 1. Recuperamos los filtros de fecha de la URL
        fecha_desde = request.query_params.get("desde")
        fecha_hasta = request.query_params.get("hasta")

        # 2. Base de la consulta (Solo cosas Cerradas: Aprobadas o Rechazadas)
        # No nos interesan las pendientes para un reporte de cierre.
        queryset = Solicitud.objects.filter(
            estado__in=["IMPACTADO", "RECHAZADO", "RECHAZADO_RRHH"]
        ).order_by("fecha_inicio")

        # 3. Aplicamos el rango de fechas (Si el usuario lo pidió)
        if fecha_desde and fecha_hasta:
            queryset = queryset.filter(fecha_inicio__range=[fecha_desde, fecha_hasta])

        # 4. Preparamos la respuesta HTTP tipo "Archivo Adjunto"
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            f'attachment; filename="Reporte_Licencias_{fecha_desde}_al_{fecha_hasta}.csv"'
        )

        # 5. Escribimos el CSV (Excel)
        writer = csv.writer(response)

        # ENCABEZADOS
        writer.writerow(
            [
                "Legajo",
                "Apellido",
                "Nombre",
                "Tipo Licencia",
                "Fecha Inicio",
                "Días",
                "Estado",
                "Motivo Rechazo",
                "Observaciones",
            ]
        )

        # FILAS DE DATOS
        for soli in queryset:
            # Limpiamos el motivo de rechazo (si es None, ponemos guión)
            rechazo = soli.motivo_rechazo if soli.motivo_rechazo else "-"
            motivo_agente = soli.motivo if soli.motivo else "-"

            writer.writerow(
                [
                    soli.agente.legajo,
                    soli.agente.apellido,
                    soli.agente.nombre,
                    soli.tipo.descripcion,
                    soli.fecha_inicio,
                    soli.dias,
                    soli.estado,
                    rechazo,
                    motivo_agente,
                ]
            )

        return response
