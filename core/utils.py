import os
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML


def generar_pdf_legajo(solicitud):
    try:
        context = {"solicitud": solicitud, "fecha_aprobacion": timezone.now()}
        html_string = render_to_string("core/pdf_solicitud.html", context)

        # Ruta: media/legajos/{legajo}/{año}/
        legajo_str = str(solicitud.agente.legajo)
        anio_str = str(solicitud.fecha_inicio.year)
        path_legajo = os.path.join(settings.MEDIA_ROOT, "legajos", legajo_str, anio_str)
        os.makedirs(path_legajo, exist_ok=True)

        nombre_archivo = f"solicitud_{solicitud.id}_{solicitud.tipo.codigo}.pdf"
        ruta_completa = os.path.join(path_legajo, nombre_archivo)

        HTML(string=html_string).write_pdf(ruta_completa)
        print(f"📄 PDF Generado: {ruta_completa}")
        return True
    except Exception as e:
        print(f"❌ Error PDF: {e}")
        return False
