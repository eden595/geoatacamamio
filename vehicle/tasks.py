# tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from zipfile import ZipFile
from xhtml2pdf import pisa
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import get_template
from threading import Thread
from core.utils import check_and_convert_pdf
from core.models import Tipo
import os
import datetime
from .models import Vehiculo, OcultarOpcionesVehiculo, DocumentacionesVehiculo, InformacionTecnicaVehiculo
from mining.models import VehiculoAsignado
import time
from messenger.views import notificacion_celery_email

def create_vehicle_pdf(request,vehiculo):
    opciones = get_object_or_404(OcultarOpcionesVehiculo, tipo_vehiculo=vehiculo.tipo)
    vehiculoDocumentacion = DocumentacionesVehiculo.objects.get(vehiculo_id=vehiculo.id)
    vehiculoInformacion = InformacionTecnicaVehiculo.objects.get(vehiculo_id=vehiculo.id)
    current_datetime = datetime.datetime.now()
    image_paths_dict = {}
    document_fields = [
        'fotografiaFacturaCompra', 'fotografiaPadron', 'fotografiaPermisoCirculacion', 'fotografiaRevisionTecnica', 
        'fotografiaRevisionTecnicaGases', 'fotografiaSeguroObligatorio', 'fotografiaSeguroAutomotriz', 'fotografiaCertificadoGps', 
        'fotografiaCertificadoMantencion', 'fotografiaCertificadoOperatividad', 'fotografiaCertificadoGrua', 
        'fotografiaCertificadoLamina', 'fotografiaDocumentacionMiniBus', 'fotografiaCertificadoBarraAntiVuelco', 
        'fotografiaInteriorTablero', 'fotografiaInteriorCopiloto', 'fotografiaInteriorAtrasPiloto', 
        'fotografiaInteriorAtrasCopiloto', 'fotografiaExteriorFrontis', 'fotografiaExteriorAtras', 
        'fotografiaExteriorPiloto', 'fotografiaExteriorCopiloto'
    ]

    threads = []
    for field in document_fields:
        if getattr(opciones, field) == "Si":
            file_field = getattr(vehiculoDocumentacion, field)
            if file_field:
                file_path = file_field.path
                field_name = vehiculoDocumentacion._meta.get_field(field).verbose_name
                thread = Thread(target=lambda: image_paths_dict.update({field_name: check_and_convert_pdf(file_path)}))
                threads.append(thread)
                thread.start()

    for thread in threads:
        thread.join()

    verbose_names = [
        vehiculoDocumentacion._meta.get_field(field).verbose_name for field in document_fields
    ]
    sorted_image_paths_dict = {field: image_paths_dict[field] for field in verbose_names if field in image_paths_dict}

    context = {
        'vehiculo': vehiculo,
        'opciones': opciones,
        'informacion': vehiculoInformacion,
        'documentacion': vehiculoDocumentacion,
        'image_paths_dict': sorted_image_paths_dict,
        'user_role': request.user.role,
        'current_datetime': current_datetime,
    }

    template_path = 'pages/pdfs/vehicle_pdf_template.html'
    template = get_template(template_path)
    html = template.render(context)
    filename = f'{vehiculo.placaPatente}-{current_datetime.strftime("%Y%m%d_%H%M%S")}.pdf'
    pdf_path = os.path.join(settings.MEDIA_ROOT, 'pdfs_temp', filename)
    os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

    with open(pdf_path, 'wb') as pdf_file:
        pisa_status = pisa.CreatePDF(html, dest=pdf_file)
        if pisa_status.err:
            return None
    return pdf_path

def create_zip_file(pdf_files):
    current_datetime = datetime.datetime.now()
    formatted_datetime = current_datetime.strftime("%Y%m%d_%H%M%S")
    zip_filename = f'{settings.MEDIA_ROOT}/pdfs_temp_zip/vehiculos_{formatted_datetime}.zip'
    os.makedirs(os.path.dirname(zip_filename), exist_ok=True)
    with ZipFile(zip_filename, 'w') as zipf:
        for pdf_file in pdf_files:
            zipf.write(pdf_file, os.path.basename(pdf_file))
    return zip_filename

@shared_task(bind=True)
def generate_vehicle_pdfs_and_send_email(self):

    
    # Enviar correo electrónico
    notificacion_celery_email()
    time.sleep(60)
    notificacion_celery_email()
    return "done"
