from django.shortcuts import render
from twilio.rest import Client
from django.conf import settings
from django.core.mail import send_mail
from user.models import User
from core.models import Faena
from twilio.base.exceptions import TwilioRestException

CORREO_ADICIONAL = 'administracionflota@geoatacama.cl'
#CORREO_ADICIONAL = 'cconelli@isamax.cl'
CORREO_CELERY = 'cconelli@isamax.cl'

def send_sms_message(numero,mensaje):
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            from_=settings.TWILIO_PHONE_NUMBER,
            body=mensaje,
            to='+56'+str(numero)
            )
        return message
    except TwilioRestException as e:
        return None

def send_email_message(to_email, subject, message):
    try:
        send_mail(subject, message, settings.EMAIL_HOST_USER, [to_email])
        return
    except Exception as e:
        return {"error": str(e)}

def notificacion_vehiculos_email(request, vehiculo, action):
    action = action.capitalize()
    mensaje_notificacion = f'Vehículo: {vehiculo.placaPatente} \n{action} por: {request.user.first_name} {request.user.last_name} \n\nMás información en www.sicgeoatacama.cl'
    subject = f'Vehículo {vehiculo.placaPatente} {action}'
    destinatarios = User.objects.filter(role__in=[User.Role.JEFE_MANTENCION]).values_list('email', flat=True)
    destinatarios = list(destinatarios) + [CORREO_ADICIONAL]
    for to_email in destinatarios:
        send_email_message(to_email, subject, mensaje_notificacion)

def notificacion_maquinarias_email(request, maquinaria, action):
    action = action.capitalize()
    mensaje_notificacion = f'Maquinaria: {maquinaria.maquinaria} \n{action} por: {request.user.first_name} {request.user.last_name} \n\nMás información en www.sicgeoatacama.cl'
    subject = f'Maquinaria {maquinaria.maquinaria} {action}'
    destinatarios = User.objects.filter(role__in=[User.Role.JEFE_MANTENCION]).values_list('email', flat=True)
    destinatarios = list(destinatarios) + [CORREO_ADICIONAL]
    for to_email in destinatarios:
        send_email_message(to_email, subject, mensaje_notificacion)
        
def notificacion_usuarios_email(request, usuario, action):
    action = action.capitalize()
    # Maneja correctamente el caso en que el registro se realiza sin un usuario autenticado
    if request.user.is_authenticated:
        actor = f'{request.user.first_name} {request.user.last_name}'
    else:
        actor = 'Registro interno web Geoatacama'
    mensaje_notificacion = f'Usuario: {usuario.first_name} {usuario.last_name} \n{action} por: {actor}\n\nMás información en www.sicgeoatacama.cl'
    subject = f'Usuario {usuario.first_name} {usuario.last_name} {action}'
    destinatarios = [CORREO_ADICIONAL]
    for to_email in destinatarios:
        send_email_message(to_email, subject, mensaje_notificacion)
        
def notificacion_mantenedor_email(request, seccion, nombre, action):
    action = action.capitalize()
    mensaje_notificacion = f'Mantenedor de {nombre}: {seccion} \n{action} por: {request.user.first_name} {request.user.last_name} \n\nMás información en www.sicgeoatacama.cl'
    subject = f'Mantenedor de {nombre}: {seccion} {action}'
    destinatarios = [CORREO_ADICIONAL]
    for to_email in destinatarios:
        send_email_message(to_email, subject, mensaje_notificacion)

def notificacion_mi_usuario_email(request, usuario, nombre, action):
    action = action.capitalize()
    # Verifica usuario autenticado evitando el error 500 al registrarse desde outside
    if request.user.is_authenticated:
        actor = f'{request.user.first_name} {request.user.last_name}'
    else: 
        actor = 'Registro interno web Geoatacama'
    mensaje_notificacion = f'{nombre}: {usuario.username} \n{action} por: {actor}\n\nMás información en www.sicgeoatacama.cl'
    subject = f'{nombre} {action}: {usuario.username}'
    destinatarios = User.objects.filter(username=usuario.username).values_list('email', flat=True)
    destinatarios = list(destinatarios)
    for to_email in destinatarios:
        send_email_message(to_email, subject, mensaje_notificacion)

def notificacion_admin_jefe_mantencion_email(request, documento, nombre, action):
    action = action.capitalize()
    mensaje_notificacion = f'{nombre}: {documento.nombredocumento} \nFaena: {documento.faena} \n{action} por: {request.user.first_name} {request.user.last_name} \n\nMás información en www.sicgeoatacama.cl'
    subject = f'{nombre} {documento.nombredocumento} {action}'
    destinatarios = User.objects.filter(role__in=[User.Role.JEFE_MANTENCION]).values_list('email', flat=True)
    destinatarios = list(destinatarios) + [CORREO_ADICIONAL]
    for to_email in destinatarios:
        send_email_message(to_email, subject, mensaje_notificacion)        

def notificacion_cambio_faena_vehiculo_email(request, datos, action):
    action = action.capitalize()
    faenaAnterior = Faena.objects.get(id=datos.faenaAnterior)
    mensaje_notificacion = f'Asignación de faena \n\nVehículo:{datos.vehiculo.tipo} \nPlaca Patente: {datos.vehiculo.placaPatente} \nFaena Origen: {faenaAnterior.faena} \nFaena Destino: {datos.faena}\n{action} por: {request.user.first_name} {request.user.last_name} \n\nMás información en www.sicgeoatacama.cl'
    subject = f'Asignación de faena {datos.vehiculo.placaPatente}'
    jefe_mantencion = User.objects.filter(role__in=[User.Role.JEFE_MANTENCION]).values_list('email', flat=True)
    supervisor = User.objects.filter(role__in=[User.Role.SUPERVISOR], usuarioprofile__faena=datos.faena).values_list('email', flat=True)
    destinatarios = list(jefe_mantencion) + list(supervisor) + [CORREO_ADICIONAL]
    for to_email in destinatarios:
        send_email_message(to_email, subject, mensaje_notificacion)

def notificacion_nuevo_mantenimiento_vehiculos_email_sms(request, mantenimiento, problemas, progreso, action):
    action = action.capitalize()
    problemas_list = [str(problema) for problema in problemas]
    problemas_str = " - ".join(problemas_list)
    mensaje_notificacion = (
        f'Nuevo mantenimiento\n'
        f'Vehículo: {mantenimiento.patente}\n'
        f'{action} por: {request.user.first_name} {request.user.last_name}\n'
        f'Turno: {mantenimiento.get_turno_display()}\n'
        f'Faena: {mantenimiento.faena}\n'
        f'Progreso: {progreso}\n'
        f'Problemas: {problemas_str}\n\n'
        f'Más información en www.sicgeoatacama.cl'
    )    
    subject = f'Nuevo mantenimiento {mantenimiento.patente}'
    
    admin_and_jefe_email = User.objects.filter(role__in=[User.Role.JEFE_MANTENCION]).values_list('email', flat=True)
    supervisor_email = User.objects.filter(role=User.Role.SUPERVISOR, usuarioprofile__faena=mantenimiento.faena.id).values_list('email', flat=True)
    destinatarios_email = list(admin_and_jefe_email) + list(supervisor_email) + [CORREO_ADICIONAL]
    
    admin_and_jefe_phones = User.objects.filter(role__in=[User.Role.ADMINISTRADOR, User.Role.JEFE_MANTENCION]).values_list('phone', flat=True)
    supervisor_phones = User.objects.filter(role=User.Role.SUPERVISOR, usuarioprofile__faena=mantenimiento.faena.id).values_list('phone', flat=True)
    destinatarios_phones = list(admin_and_jefe_phones) + list(supervisor_phones)
    
    for to_email in destinatarios_email:
        send_email_message(to_email, subject, mensaje_notificacion)
    for to_phone in destinatarios_phones:
        send_sms_message(to_phone,mensaje_notificacion)

def notificacion_update_mantenimiento_vehiculos_email_sms(request, mantenimiento, problemas, progreso, action):
    action = action.capitalize()
    problemas_list = [str(problema) for problema in problemas]
    problemas_str = " - ".join(problemas_list)
    mensaje_notificacion = (
        f'Actualización mantenimiento\n'
        f'Vehículo: {mantenimiento.patente}\n'
        f'{action} por: {request.user.first_name} {request.user.last_name}\n'
        f'Turno: {mantenimiento.get_turno_display()}\n'
        f'Faena: {mantenimiento.faena}\n'
        f'Progreso: {progreso}\n'
        f'Problemas: {problemas_str}\n\n'
        f'Más información en www.sicgeoatacama.cl'
    )    
    subject = f'Actualización mantenimiento {mantenimiento.patente}'
    
    admin_and_jefe_email = User.objects.filter(role__in=[User.Role.JEFE_MANTENCION]).values_list('email', flat=True)
    supervisor_email = User.objects.filter(role=User.Role.SUPERVISOR, usuarioprofile__faena=mantenimiento.faena.id).values_list('email', flat=True)
    destinatarios_email = list(admin_and_jefe_email) + list(supervisor_email) + [CORREO_ADICIONAL]
    
    admin_and_jefe_phones = User.objects.filter(role__in=[User.Role.ADMINISTRADOR, User.Role.JEFE_MANTENCION]).values_list('phone', flat=True)
    supervisor_phones = User.objects.filter(role=User.Role.SUPERVISOR, usuarioprofile__faena=mantenimiento.faena.id).values_list('phone', flat=True)
    destinatarios_phones = list(admin_and_jefe_phones) + list(supervisor_phones)
    
    for to_email in destinatarios_email:
        send_email_message(to_email, subject, mensaje_notificacion)
    for to_phone in destinatarios_phones:
        send_sms_message(to_phone,mensaje_notificacion)
        
def notificacion_nuevo_mantenimiento_maquinaria_email_sms(request, mantenimiento, problemas, progreso, action):
    action = action.capitalize()
    problemas_list = [str(problema) for problema in problemas]
    problemas_str = " - ".join(problemas_list)
    mensaje_notificacion = (
        f'Nuevo mantenimiento\n'
        f'Maquinaria: {mantenimiento.maquinaria}\n'
        f'{action} por: {request.user.first_name} {request.user.last_name}\n'
        f'Turno: {mantenimiento.get_turno_display()}\n'
        f'Faena: {mantenimiento.faena}\n'
        f'Progreso: {progreso}\n'
        f'Problemas: {problemas_str}\n\n'
        f'Más información en www.sicgeoatacama.cl'
    )    
    subject = f'Nuevo mantenimiento {mantenimiento.maquinaria}'
    
    admin_and_jefe_email = User.objects.filter(role__in=[User.Role.JEFE_MANTENCION]).values_list('email', flat=True)
    supervisor_email = User.objects.filter(role=User.Role.SUPERVISOR, usuarioprofile__faena=mantenimiento.faena.id).values_list('email', flat=True)
    destinatarios_email = list(admin_and_jefe_email) + list(supervisor_email) + [CORREO_ADICIONAL]
    
    admin_and_jefe_phones = User.objects.filter(role__in=[User.Role.ADMINISTRADOR, User.Role.JEFE_MANTENCION]).values_list('phone', flat=True)
    supervisor_phones = User.objects.filter(role=User.Role.SUPERVISOR, usuarioprofile__faena=mantenimiento.faena.id).values_list('phone', flat=True)
    destinatarios_phones = list(admin_and_jefe_phones) + list(supervisor_phones)
    
    for to_email in destinatarios_email:
        send_email_message(to_email, subject, mensaje_notificacion)
    for to_phone in destinatarios_phones:
        send_sms_message(to_phone,mensaje_notificacion)

def notificacion_update_mantenimiento_maquinaria_email_sms(request, mantenimiento, problemas, progreso, action):
    action = action.capitalize()
    problemas_list = [str(problema) for problema in problemas]
    problemas_str = " - ".join(problemas_list)
    mensaje_notificacion = (
        f'Actualización mantenimiento\n'
        f'Maquinaria: {mantenimiento.maquinaria}\n'
        f'{action} por: {request.user.first_name} {request.user.last_name}\n'
        f'Turno: {mantenimiento.get_turno_display()}\n'
        f'Faena: {mantenimiento.faena}\n'
        f'Progreso: {progreso}\n'
        f'Problemas: {problemas_str}\n\n'
        f'Más información en www.sicgeoatacama.cl'
    )    
    subject = f'Actualización mantenimiento {mantenimiento.maquinaria}'
    
    admin_and_jefe_email = User.objects.filter(role__in=[User.Role.JEFE_MANTENCION]).values_list('email', flat=True)
    supervisor_email = User.objects.filter(role=User.Role.SUPERVISOR, usuarioprofile__faena=mantenimiento.faena.id).values_list('email', flat=True)
    destinatarios_email = list(admin_and_jefe_email) + list(supervisor_email) + [CORREO_ADICIONAL]
    
    admin_and_jefe_phones = User.objects.filter(role__in=[User.Role.ADMINISTRADOR, User.Role.JEFE_MANTENCION]).values_list('phone', flat=True)
    supervisor_phones = User.objects.filter(role=User.Role.SUPERVISOR, usuarioprofile__faena=mantenimiento.faena.id).values_list('phone', flat=True)
    destinatarios_phones = list(admin_and_jefe_phones) + list(supervisor_phones)
    
    for to_email in destinatarios_email:
        send_email_message(to_email, subject, mensaje_notificacion)
    for to_phone in destinatarios_phones:
        send_sms_message(to_phone,mensaje_notificacion)

def notificacion_celery_email():
    mensaje_notificacion = f'Prueba celery uno'
    subject = f'Desde Celery Uno'
    destinatarios = [CORREO_CELERY]
    for to_email in destinatarios:
        send_email_message(to_email, subject, mensaje_notificacion)
        
def notificacion_jefe_mantencion_stock_minimo_kit_email_sms(request, kit_faena, stock_actual):
    """
    Orquesta el envío de alertas de stock crítico dirigidas específicamente a la jefatura de la faena afectada.
    """
    # Se estructura el cuerpo del mensaje incluyendo metadatos operativos clave (Kit, Faena, Stock, Responsable)
    # para proporcionar contexto inmediato sobre la necesidad de reposición al encargado.
    mensaje_notificacion = (
        f'ALERTA DE STOCK CRITICO\n'
        f'Kit: {kit_faena.kitMaquinaria.nombreKit}\n'
        f'Faena: {kit_faena.faena}\n'
        f'Stock Actual: {stock_actual}\n'
        f'Acción detonada por: {request.user.first_name} {request.user.last_name}\n'
        f'Por favor gestionar reposición de inventario.\n\n'
        f'Más información en www.sicgeoatacama.cl'
    )
    subject = f'ALERTA STOCK: {kit_faena.kitMaquinaria.nombreKit}'

    faena_objetivo = kit_faena.faena

    # Se realiza una consulta filtrada para identificar a los usuarios con rol 'JEFE_MANTENCION'.
    # Se utiliza la relación inversa con el modelo 'UsuarioProfile' (usuarioprofile__faena) para 
    # restringir los destinatarios únicamente a aquellos asignados administrativamente a la Faena de la incidencia.
    jefes_faena_qs = User.objects.filter(
        role=User.Role.JEFE_MANTENCION,
        usuarioprofile__faena=faena_objetivo 
    )

    destinatarios_email = list(jefes_faena_qs.values_list('email', flat=True))
    destinatarios_phones = list(jefes_faena_qs.values_list('phone', flat=True))

    # Se incorpora un correo de respaldo global (Hardcoded/Configuración) si la variable se encuentra definida en el ámbito.
    if 'CORREO_ADICIONAL' in globals():
        destinatarios_email.append(CORREO_ADICIONAL)

    # Ejecución del despacho de correos a la lista consolidada.
    for to_email in destinatarios_email:
        if to_email: 
            send_email_message(to_email, subject, mensaje_notificacion)

    # Ejecución del despacho de mensajería SMS a los dispositivos móviles registrados.
    for to_phone in destinatarios_phones:
        if to_phone:
            send_sms_message(to_phone, mensaje_notificacion)