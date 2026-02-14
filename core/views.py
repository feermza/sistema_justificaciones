from rest_framework import viewsets
from .models import Agente, TipoLicencia, Solicitud
from .serializers import AgenteSerializer, TipoLicenciaSerializer, SolicitudSerializer
from django.core.mail import send_mail  # <--- IMPORTAR ESTO ARRIBA
from django.conf import settings
import csv
from django.http import HttpResponse
from rest_framework.decorators import action


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
