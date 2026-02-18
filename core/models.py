from django.db import models
from django.contrib.auth.models import User


# 1. NUEVA TABLA: ÁREAS DE TRABAJO
class Area(models.Model):
    nombre = models.CharField(
        max_length=100, unique=True, help_text="Ej: Servicios Generales, RRHH, Alumnado"
    )

    def __str__(self):
        return self.nombre


# 2. TABLA DE AGENTES (EMPLEADOS)
class Agente(models.Model):
    # Definición de Jerarquías según tu estructura
    CATEGORIAS = [
        ("02", "02 - Director"),  # Autoriza
        ("03", "03 - Jefe de Departamento"),  # Autoriza
        ("04", "04 - Jefe de División"),  # Autoriza
        ("05", "05 - Supervisión"),  # (No Autoriza)
        ("06", "06 - Operativo / Ordenanza"),  # (No Autoriza)
        ("07", "07 - Auxiliar / Ordenanza"),  # (No Autoriza)
    ]

    # Identificadores
    legajo = models.IntegerField(unique=True, help_text="Número de legajo en RRHH")
    id_sistema_reloj = models.IntegerField(unique=True, null=True, blank=True)

    # Datos Personales
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    dni = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(blank=True, null=True)

    # NUEVO: Estructura Organizativa (Reemplaza a supervisores manuales)
    area = models.ForeignKey(
        Area,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Área donde se desempeña",
    )
    categoria = models.CharField(
        max_length=2,
        choices=CATEGORIAS,
        default="06",
        help_text="Define si puede autorizar o no",
    )

    # Datos de Sistema (Login y Seguridad)
    fecha_nacimiento = models.DateField(
        null=True, blank=True, help_text="Dato obligatorio para activar cuenta"
    )
    usuario = models.OneToOneField(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="agente_perfil",
    )
    es_rrhh = models.BooleanField(
        default=False, help_text="Marcar si pertenece a Personal (Gestión Global)"
    )

    def __str__(self):
        return f"{self.legajo} - {self.apellido}, {self.nombre}"

    # Método auxiliar para saber si es Autoridad (Cat 02, 03, 04)
    @property
    def es_autoridad(self):
        return self.categoria in ["02", "03", "04"]


# 3. TABLA DE TIPOS DE LICENCIA
class TipoLicencia(models.Model):
    codigo = models.CharField(max_length=20, unique=True)
    descripcion = models.CharField(max_length=100)
    texto_para_reloj = models.CharField(max_length=100)
    requiere_aviso = models.BooleanField(default=True)
    es_franquicia = models.BooleanField(default=False)
    limite_mensual = models.IntegerField(default=0)
    limite_anual = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"


# 4. TABLA DE SOLICITUDES
class Solicitud(models.Model):
    ESTADOS = [
        ("PENDIENTE_VALIDACION", "Esperando validación de aviso (Jefe)"),
        ("AVISO_CONFIRMADO", "Aviso OK - Pasa a RRHH"),
        ("AVISO_NEGADO", "Jefe indica SIN AVISO (A Descuento)"),
        ("APROBADO", "Finalizado OK (Listo para inyectar)"),
        ("RECHAZADO", "Rechazado por RRHH"),
        ("IMPACTADO", "Ya inyectado en el Reloj"),
    ]

    agente = models.ForeignKey(
        Agente, on_delete=models.CASCADE, related_name="solicitudes"
    )
    tipo = models.ForeignKey(TipoLicencia, on_delete=models.PROTECT)
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_inicio = models.DateField()
    dias = models.IntegerField(default=1)

    # El agente selecciona a QUÉ jefe le avisó (Se filtrará por Área)
    jefe_seleccionado = models.ForeignKey(
        Agente,
        on_delete=models.PROTECT,
        related_name="avisos_recibidos",
        null=True,
        blank=True,
    )

    motivo = models.TextField(blank=True, null=True)
    estado = models.CharField(
        max_length=30, choices=ESTADOS, default="PENDIENTE_VALIDACION"
    )
    archivo_adjunto = models.FileField(upload_to="certificados/", blank=True, null=True)
    motivo_rechazo = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.agente} - {self.tipo} ({self.fecha_inicio})"
