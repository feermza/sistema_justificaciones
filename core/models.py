from django.db import models

# 1. TABLA DE AGENTES (EMPLEADOS)
class Agente(models.Model):
    # Identificadores
    legajo = models.IntegerField(unique=True, help_text="Número de legajo en RRHH")
    
    # IMPORTANTE: Este es el ID clave para la integración futura
    id_sistema_reloj = models.IntegerField(
        unique=True, 
        null=True, 
        blank=True, 
        help_text="ID interno que usa la base de datos del reloj digital (Legacy)"
    )
    
    # Datos Personales
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    dni = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(blank=True, null=True)
    
    # Jerarquía: Un agente puede tener varios supervisores asignados
    supervisores = models.ManyToManyField(
        'self', 
        symmetrical=False, 
        related_name='subordinados', 
        blank=True,
        help_text="Personas habilitadas para autorizar a este agente"
    )

    def __str__(self):
        return f"{self.legajo} - {self.apellido}, {self.nombre}"


# 2. TABLA DE TIPOS DE LICENCIA (REGLAS DEL CCT)
class TipoLicencia(models.Model):
    # Nuestro código interno (Ej: ART_85)
    codigo = models.CharField(max_length=20, unique=True)
    descripcion = models.CharField(max_length=100, help_text="Nombre para mostrar en la web")
    
    # IMPORTANTE: El texto exacto que necesita el sistema viejo
    texto_para_reloj = models.CharField(
        max_length=100, 
        help_text="Texto exacto que se inyectará en la base vieja (Ej: 'Ausente con aviso')"
    )
    
    # Reglas de Negocio
    requiere_aviso = models.BooleanField(default=True, help_text="Si requiere validación del jefe")
    es_franquicia = models.BooleanField(default=False, help_text="Si es reducción horaria (Art 55/Lactancia)")
    
    limite_mensual = models.IntegerField(default=0, help_text="0 = Sin límite")
    limite_anual = models.IntegerField(default=0, help_text="0 = Sin límite")

    def __str__(self):
        return f"{self.codigo} - {self.descripcion}"


# 3. TABLA DE SOLICITUDES (EL TRÁMITE DÍA A DÍA)
class Solicitud(models.Model):
    ESTADOS = [
        ('PENDIENTE_VALIDACION', 'Esperando validación de aviso (Jefe)'),
        ('AVISO_CONFIRMADO', 'Aviso OK - Pasa a RRHH'),
        ('AVISO_NEGADO', 'Jefe indica SIN AVISO (A Descuento)'),
        ('APROBADO', 'Finalizado OK (Listo para inyectar)'),
        ('RECHAZADO', 'Rechazado por RRHH'),
        ('IMPACTADO', 'Ya inyectado en el Reloj'),
    ]

    agente = models.ForeignKey(Agente, on_delete=models.CASCADE, related_name='solicitudes')
    tipo = models.ForeignKey(TipoLicencia, on_delete=models.PROTECT)
    
    fecha_solicitud = models.DateTimeField(auto_now_add=True)
    fecha_inicio = models.DateField(help_text="Día de la falta o inicio de licencia")
    dias = models.IntegerField(default=1)
    
    # El agente selecciona a QUÉ jefe le avisó (de su lista de supervisores)
    jefe_seleccionado = models.ForeignKey(
        Agente, 
        related_name='avisos_recibidos', 
        on_delete=models.PROTECT,
        null=True,
        blank=True
    )
    
    motivo = models.TextField(blank=True, null=True)
    estado = models.CharField(max_length=30, choices=ESTADOS, default='PENDIENTE_VALIDACION')
    archivo_adjunto = models.FileField(upload_to='certificados/', blank=True, null=True)

    jefe_seleccionado = models.ForeignKey(Agente, on_delete=models.SET_NULL, null=True, related_name='solicitudes_a_revisar')

    motivo_rechazo = models.TextField(blank=True, null=True, help_text="Razón por la cual RRHH rechazó la solicitud")

    def __str__(self):
        return f"{self.agente} - {self.tipo} ({self.fecha_inicio})"
