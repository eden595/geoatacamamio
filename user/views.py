from datetime import datetime
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth import authenticate, login, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm, PasswordResetForm, SetPasswordForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from rut_chile import rut_chile
from .forms import (FormRegistro, FormRegistroExtra, FormRegistroSeccion, FormRegistroLicenciasUsuarioFecha, FormRegistroLicenciasUsuarioNoProfesionales, 
                    FormRegistroLicenciasUsuarioProfesionales, FormRegistroLicenciasUsuarioProfesionalesAntiguas, FormDocumentacionUsuario)
from .models import Usuario, UsuarioProfile, LicenciasUsuario, DocumentacionUsuario, User
from core.models import Ciudad, Nacionalidad, Genero, Faena, TipoDocumentoFaenaGeneral
from core.utils import procesar_fotografia
from django.utils import timezone
from django.utils.http import urlsafe_base64_decode
from django.utils.encoding import force_str
from django.utils.datastructures import MultiValueDictKeyError
from django.core.mail import BadHeaderError
from django.db.models import Q
from django.http import JsonResponse
from messenger.views import notificacion_usuarios_email, notificacion_mi_usuario_email
from core.decorators import admin_required, sondaje_admin_or_base_datos_or_supervisor_required
import json
from django.contrib.auth.views import LoginView
from .forms import CustomAuthenticationForm
from django.db import transaction

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    authentication_form = CustomAuthenticationForm
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context
    
class CustomLogoutView(LogoutView):
    next_page = reverse_lazy('logincustom')

def register(request): 
    context = {
        'formregistro': FormRegistro,
        'sidebar': 'dashboard'
    }
    return render(request,'registration/register.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_user(request): 
    context = {
        'formregistro': FormRegistro,   
        'sidebar': 'manage_users',
        'sidebarmain': 'system_users',
    }
    return render(request,'pages/users/new_user.html', context)

def save_new_user(request): 
    origen = request.POST.get('ubicacion', None)
    
    if request.method == 'POST':        
        formulario = FormRegistro(data=request.POST)
        
        if not formulario.is_valid():
            return error_campos_origen(request, origen, formulario)
            
        if not rut_chile.is_valid_rut(request.POST['username']):
            return error_rut_origen(request, origen, formulario)

        try:
            with transaction.atomic():
                
                Usuario.objects.create_user(
                    username = request.POST['username'],
                    first_name = request.POST['first_name'],
                    last_name = request.POST['last_name'],
                    password = request.POST['password1'],
                    phone = request.POST['phone'],
                    email = request.POST['email'],
                    role = "SIN ASIGNAR",
                    is_active = False,
                )
                
                usuario = Usuario.objects.get(username=request.POST['username'])
                
                if origen == 'inside':
                    notificacion_usuarios_email(request, usuario, "creado")
                    messages.success(request, 'Usuario Creado Correctamente', extra_tags='Recuerda habilitar el perfil creado')
                    return redirect('manage_users')   
                    
                else:
                    notificacion_usuarios_email(request, usuario, "creado")
                    notificacion_mi_usuario_email(request, usuario,"Usuario", "creado")
                    messages.success(request, 'Usuario Creado Correctamente', extra_tags='Tu perfil sera habilitado en las próximas horas')
                    return redirect('logincustom')  

        except Exception as e:
            msg_error = f"Error del sistema: {str(e)}"

            if "UNIQUE constraint failed" in str(e) or "Duplicate entry" in str(e):
                if "email" in str(e):
                    msg_error = "Este correo electrónico ya está registrado."
                elif "phone" in str(e):
                    msg_error = "Este número de teléfono ya está registrado."

            formulario.add_error(None, msg_error)
            
            print(f"Error crítico en transacción save_new_user: {e}")
            return error_campos_origen(request, origen, formulario)
            
    else:
        if origen == 'inside' or (request.user.is_authenticated and request.user.role == 'ADMINISTRADOR'):
            return redirect('new_user')
        else:
            return redirect('register')

def error_rut_origen(request,origen,formulario):
    if origen == 'inside':
        messages.error(request, "Rut incorrecto", extra_tags='Vuelva a intentarlo')
        context = {
            'formregistro': formulario,   
            'sidebar': 'manage_users',
            'sidebarmain': 'system_users',         
        }         
        return render(request,'pages/users/new_user.html',context)
    else:
        messages.error(request, "Rut incorrecto", extra_tags='Vuelva a intentarlo')
        context = {
            'formregistro': formulario,           
        }         
        return render(request,'registration/register.html',context)

def error_campos_origen(request,origen,formulario):
    if origen == 'inside': 
        messages.error(request, "Corrija los datos incorrectos", extra_tags='Vuelva a intentarlo')
        context = {
            'formregistro': formulario,   
            'sidebar': 'manage_users',
            'sidebarmain': 'system_users',         
        }         
        return render(request,'pages/users/new_user.html',context)
    else:
        messages.error(request, "Corrija los datos incorrectos", extra_tags='Vuelva a intentarlo')
        context = {
            'formregistro': formulario,           
        }         
        return render(request,'registration/register.html',context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_users(request):
    request.session.pop('edit_username',None)
    request.session.save()
    usuarios = list(Usuario.objects.all().exclude(username='15.053.475-5').order_by('-date_joined'))
    usuariosProfile = list(UsuarioProfile.objects.all().exclude(user=2))
    context = {
        'usuarios': usuarios,
        'usuariosProfile': usuariosProfile,
        'sidebar': 'manage_users',
        'sidebarmain': 'system_users',  
    }
    return render(request,'pages/users/manage_users.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def status_user(request):
    if request.method == 'POST': 
        usuario = Usuario.objects.get(username=request.POST['username'])
        if (usuario.is_active): 
            Usuario.objects.filter(username=request.POST['username']).update(is_active=False)
            notificacion_usuarios_email(request, usuario, "deshabilitado")
            messages.success(request, 'Usuario Deshabilitado Correctamente')             
        else:            
            Usuario.objects.filter(username=request.POST['username']).update(is_active=True)
            notificacion_usuarios_email(request, usuario, "habilitado")
            messages.success(request, 'Usuario Habilitado correctamente')  
        return redirect('manage_users') 

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def edit_user_profile(request):
        try:
            request.session['edit_username'] = request.POST['username']            
        except MultiValueDictKeyError:
            request.session['edit_username'] = request.session['edit_username']
        usuario = Usuario.objects.get(username=request.session['edit_username'])
        usuarioProfile = UsuarioProfile.objects.get(user_id=usuario.id) 
        usuarioLicencias = LicenciasUsuario.objects.get(user_id=usuario.id)  
        usuarioDocumentacion = DocumentacionUsuario.objects.get(user_id=usuario.id)  
        ciudad_actual = Ciudad.objects.filter(ciudad=usuarioProfile.ciudad)
        nacionalidad_actual = Nacionalidad.objects.filter(nacionalidad=usuarioProfile.nacionalidad)
        genero_actual = Genero.objects.filter(genero=usuarioProfile.genero)
        faena_actual = Faena.objects.filter(faena=usuarioProfile.faena)
        
        urlUsuario = usuarioDocumentacion.fotografiaUsuario
        urlCedula = usuarioDocumentacion.fotografiaCedula
        urlLicencia = usuarioDocumentacion.fotografiaLicencia
        urlLicenciaInterna = usuarioDocumentacion.fotografiaLicenciaInterna
        if urlUsuario.url.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg")):
            extensionUsuario = "imagen"
        elif urlUsuario.url.lower().endswith((".pdf")):
            extensionUsuario = "pdf"
        else:
            extensionUsuario = "otro"
        if urlCedula.url.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg")):
            extensionCedula = "imagen"
        elif urlCedula.url.lower().endswith((".pdf")):
            extensionCedula = "pdf"
        else:
            extensionCedula = "otro"
        if urlLicencia.url.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg")):
            extensionLicencia = "imagen"
        elif urlLicencia.url.lower().endswith((".pdf")):
            extensionLicencia = "pdf"
        else:
            extensionLicencia = "otro"
        if urlLicenciaInterna.url.lower().endswith((".jpg", ".jpeg", ".png")):
            extensionLicenciaInterna = "imagen"
        elif urlLicenciaInterna.url.lower().endswith((".pdf")):
            extensionLicenciaInterna = "pdf"
        else:
            extensionLicenciaInterna = "otro"
        ####### START return fechas formateadas   
        if not usuarioProfile.fechaNacimiento:
            fecha_nacimiento =""
        else:
            fecha_nacimiento_original = str(datetime.strftime(usuarioProfile.fechaNacimiento, "%Y-%m-%d"))
            fecha_nacimiento_formateada = datetime.strptime(fecha_nacimiento_original, "%Y-%m-%d")
            fecha_nacimiento = fecha_nacimiento_formateada.strftime('%Y-%m-%d')
        if not usuarioProfile.fechaCedulaVencimiento:
            fecha_cedula_vencimiento =""
        else:
            fecha_cedula_vencimiento_original = str(datetime.strftime(usuarioProfile.fechaCedulaVencimiento, "%Y-%m-%d"))
            fecha_cedula_vencimiento_formateada = datetime.strptime(fecha_cedula_vencimiento_original, "%Y-%m-%d")
            fecha_cedula_vencimiento = fecha_cedula_vencimiento_formateada.strftime('%Y-%m-%d')
        if not usuarioLicencias.fechaLicenciaVencimiento:
            fecha_licencia_vencimiento =""
        else:
            fecha_licencia_vencimiento_original = str(datetime.strftime(usuarioLicencias.fechaLicenciaVencimiento, "%Y-%m-%d"))
            fecha_licencia_vencimiento_formateada = datetime.strptime(fecha_licencia_vencimiento_original, "%Y-%m-%d")
            fecha_licencia_vencimiento = fecha_licencia_vencimiento_formateada.strftime('%Y-%m-%d')
        if not usuarioLicencias.fechaLicenciaInternaVencimiento:
            fecha_licencia_interna_vencimiento =""
        else:
            fecha_licencia_interna_vencimiento_original = str(datetime.strftime(usuarioLicencias.fechaLicenciaInternaVencimiento, "%Y-%m-%d"))
            fecha_licencia_interna_vencimiento_formateada = datetime.strptime(fecha_licencia_interna_vencimiento_original, "%Y-%m-%d")
            fecha_licencia_interna_vencimiento = fecha_licencia_interna_vencimiento_formateada.strftime('%Y-%m-%d')
        ####### END return fechas formateadas     
        if request.user.role == "ADMINISTRADOR" or request.user.role == "CONTROLADOR" or request.user.role == "BASE DATOS":
            condicion = False
        else:
            condicion = True
        context = {
            'rut_username': usuario.username,
            'sidebar': 'manage_users',
            'sidebarmain': 'system_users',
            'usuario': usuario,
            'formregistro': FormRegistro(initial={
                'username': usuario.username,
                'first_name':usuario.first_name,
                'last_name': usuario.last_name,
                'email': usuario.email,
                'phone': usuario.phone,
                'role': usuario.role,
                },
                ocultar_password=True,
                ocultar_role=False,
                username_disabled=True,
                first_name_disabled=condicion,
                last_name_disabled=condicion,
                phone_disabled=condicion,
                email_disabled=condicion,
                role_disabled=condicion,
            ),   
            'formregistroextra': FormRegistroExtra(initial={
                'ciudad': usuarioProfile.ciudad,
                'nacionalidad': usuarioProfile.nacionalidad,
                'genero': usuarioProfile.genero,
                'fechaNacimiento': fecha_nacimiento,
                'fechaCedulaVencimiento': fecha_cedula_vencimiento,
                'faena': usuarioProfile.faena,
                },
                ciudad_disabled=condicion,
                nacionalidad_disabled=condicion,
                genero_disabled=condicion,
                fechanacimiento_disabled=condicion,
                fechacedulavencimiento_disabled=condicion,
                faena_disabled=condicion,
                ciudad_actual=ciudad_actual,
                nacionalidad_actual=nacionalidad_actual,
                genero_actual=genero_actual,
                faena_actual=faena_actual,
            ),
            'formregistroseccion': FormRegistroSeccion(initial={
                'seccionVehicular': usuarioProfile.seccionVehicular,
                'seccionSondaje': usuarioProfile.seccionSondaje,
                'seccionPrevencion': usuarioProfile.seccionPrevencion,
                },
                seccionVehicular_disabled=condicion,
                seccionSondaje_disabled=condicion,
                seccionPrevencion_disabled=condicion,
            ),
            'formregistrolicenciasusuariofecha': FormRegistroLicenciasUsuarioFecha(initial={
                'fechaLicenciaVencimiento': fecha_licencia_vencimiento,
                'fechaLicenciaInternaVencimiento': fecha_licencia_interna_vencimiento,
                },
                fechalicenciavencimiento_disabled=condicion,
                fechalicenciainternavencimiento_disabled=condicion,
            ),
            'formregistrolicenciasusuarionoprofesionales': FormRegistroLicenciasUsuarioNoProfesionales(initial={
                'licenciaClaseB': usuarioLicencias.licenciaClaseB,                   
                'licenciaClaseC': usuarioLicencias.licenciaClaseC,
                'licenciaClaseD': usuarioLicencias.licenciaClaseD,
                'licenciaClaseE': usuarioLicencias.licenciaClaseE,
                'licenciaClaseF': usuarioLicencias.licenciaClaseF,
                },
                licenciaclaseb_disabled=condicion,
                licenciaclasec_disabled=condicion,
                licenciaclased_disabled=condicion,
                licenciaclasee_disabled=condicion,
                licenciaclasef_disabled=condicion,
            ),
            'formregistrolicenciasusuarioprofesionales': FormRegistroLicenciasUsuarioProfesionales(initial={
                'licenciaClaseA1': usuarioLicencias.licenciaClaseA1,                   
                'licenciaClaseA2': usuarioLicencias.licenciaClaseA2,
                'licenciaClaseA3': usuarioLicencias.licenciaClaseA3,
                'licenciaClaseA4': usuarioLicencias.licenciaClaseA4,
                'licenciaClaseA5': usuarioLicencias.licenciaClaseA5,
                },
                licenciaclasea1_disabled=condicion,
                licenciaclasea2_disabled=condicion,
                licenciaclasea3_disabled=condicion,
                licenciaclasea4_disabled=condicion,
                licenciaclasea5_disabled=condicion,
            ),
            'formregistrolicenciasusuarioprofesionalesantiguas': FormRegistroLicenciasUsuarioProfesionalesAntiguas(initial={
                'licenciaClaseA1Antigua': usuarioLicencias.licenciaClaseA1Antigua,                   
                'licenciaClaseA2Antigua': usuarioLicencias.licenciaClaseA2Antigua,
                },
                licenciaclasea1antigua_disabled=condicion,
                licenciaclasea2antigua_disabled=condicion,
            ),    
            'formdocumentacionusuario': FormDocumentacionUsuario(initial={
                'fotografiaUsuario': usuarioDocumentacion.fotografiaUsuario,
                'fotografiaCedula': usuarioDocumentacion.fotografiaCedula,
                'fotografiaLicencia': usuarioDocumentacion.fotografiaLicencia,            
                },
            ),    
            'fotografiaUsuario': usuarioDocumentacion.fotografiaUsuario,            
            'fotografiaCedula': usuarioDocumentacion.fotografiaCedula,            
            'fotografiaLicencia': usuarioDocumentacion.fotografiaLicencia,   
            'fotografiaLicenciaInterna': usuarioDocumentacion.fotografiaLicenciaInterna, 
            'extensionUsuario': extensionUsuario,
            'extensionCedula': extensionCedula,
            'extensionLicencia': extensionLicencia,
            'extensionLicenciaInterna': extensionLicenciaInterna,
        }
        return render(request,'pages/users/edit_user_profile.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_user_profile(request):  
    if request.method == 'POST':
        usuario = Usuario.objects.get(username=request.POST['rut_username'])
        Usuario.objects.filter(username=request.POST['rut_username']).update(first_name=request.POST['first_name'])
        Usuario.objects.filter(username=request.POST['rut_username']).update(last_name=request.POST['last_name'])
        try:
            Usuario.objects.filter(username=request.POST['rut_username']).update(phone=request.POST['phone']) 
        except:
            return JsonResponse({'titleText': "N° de Teléfono ya existe",'text': "Intenta nuevamente"}, status=400)
        try:
            Usuario.objects.filter(username=request.POST['rut_username']).update(email=request.POST['email']) 
        except:
            return JsonResponse({'titleText': "Dirección de Correo ya existe",'text': "Intenta nuevamente"}, status=400)
        try:
            Usuario.objects.filter(username=request.POST['rut_username']).update(role=request.POST['role']) 
        except:
            pass
        try:
            UsuarioProfile.objects.filter(user_id=usuario.id).update(ciudad=request.POST['ciudad']) 
        except:
            pass
        try:
            UsuarioProfile.objects.filter(user_id=usuario.id).update(nacionalidad=request.POST['nacionalidad']) 
        except:
            pass
        try:
            UsuarioProfile.objects.filter(user_id=usuario.id).update(genero=request.POST['genero']) 
        except:
            pass
        try:
            UsuarioProfile.objects.filter(user_id=usuario.id).update(fechaNacimiento=request.POST['fechaNacimiento']) 
        except:
            pass
        try:
            UsuarioProfile.objects.filter(user_id=usuario.id).update(fechaCedulaVencimiento=request.POST['fechaCedulaVencimiento']) 
        except:
            pass
        try:
            UsuarioProfile.objects.filter(user_id=usuario.id).update(faena=request.POST['faena']) 
        except:
            pass
        try:
            UsuarioProfile.objects.filter(user_id=usuario.id).update(
                seccionVehicular=request.POST['seccionVehicular'],
                seccionSondaje=request.POST['seccionSondaje'],
                seccionPrevencion=request.POST['seccionPrevencion'],
            )
        except:
            return JsonResponse({'titleText': "Error al actualizar el Perfil",'text': "Intenta nuevamente"}, status=400)
        try:
            LicenciasUsuario.objects.filter(user_id=usuario.id).update(fechaLicenciaVencimiento=request.POST['fechaLicenciaVencimiento']) 
        except:
            LicenciasUsuario.objects.filter(user_id=usuario.id).update(fechaLicenciaVencimiento=None) 
        try:
            LicenciasUsuario.objects.filter(user_id=usuario.id).update(fechaLicenciaInternaVencimiento=request.POST['fechaLicenciaInternaVencimiento']) 
        except:
            LicenciasUsuario.objects.filter(user_id=usuario.id).update(fechaLicenciaInternaVencimiento=None)
        LicenciasUsuario.objects.filter(user_id=usuario.id).update(licenciaClaseB=request.POST['licenciaClaseB']) 
        LicenciasUsuario.objects.filter(user_id=usuario.id).update(licenciaClaseC=request.POST['licenciaClaseC']) 
        LicenciasUsuario.objects.filter(user_id=usuario.id).update(licenciaClaseD=request.POST['licenciaClaseD']) 
        LicenciasUsuario.objects.filter(user_id=usuario.id).update(licenciaClaseE=request.POST['licenciaClaseE']) 
        LicenciasUsuario.objects.filter(user_id=usuario.id).update(licenciaClaseF=request.POST['licenciaClaseF']) 
        LicenciasUsuario.objects.filter(user_id=usuario.id).update(licenciaClaseA1=request.POST['licenciaClaseA1']) 
        LicenciasUsuario.objects.filter(user_id=usuario.id).update(licenciaClaseA2=request.POST['licenciaClaseA2']) 
        LicenciasUsuario.objects.filter(user_id=usuario.id).update(licenciaClaseA3=request.POST['licenciaClaseA3']) 
        LicenciasUsuario.objects.filter(user_id=usuario.id).update(licenciaClaseA4=request.POST['licenciaClaseA4']) 
        LicenciasUsuario.objects.filter(user_id=usuario.id).update(licenciaClaseA5=request.POST['licenciaClaseA5']) 
        LicenciasUsuario.objects.filter(user_id=usuario.id).update(licenciaClaseA1Antigua=request.POST['licenciaClaseA1Antigua']) 
        LicenciasUsuario.objects.filter(user_id=usuario.id).update(licenciaClaseA2Antigua=request.POST['licenciaClaseA2Antigua']) 
        
        documentacionUsuario = DocumentacionUsuario.objects.get(user_id=usuario.id) 
        
        toggle_Usuario = request.POST.get('toggle-Usuario', 'no')
        procesar_fotografia(documentacionUsuario, toggle_Usuario, 'fotografiaUsuario','documentacion_usuario/no-avatar.png', request)
            
        toggle_Cedula = request.POST.get('toggle-Cedula', 'no')
        procesar_fotografia(documentacionUsuario, toggle_Cedula, 'fotografiaCedula','documentacion_usuario/no-imagen.png', request)
                
        toggle_Licencia = request.POST.get('toggle-Licencia', 'no')
        procesar_fotografia(documentacionUsuario, toggle_Licencia, 'fotografiaLicencia','documentacion_usuario/no-imagen.png', request)
        
        toggle_LicenciaInterna = request.POST.get('toggle-LicenciaInterna', 'no')
        procesar_fotografia(documentacionUsuario, toggle_LicenciaInterna, 'fotografiaLicenciaInterna','documentacion_usuario/no-imagen.png', request)

        documentacionUsuario.save()
        
        notificacion_usuarios_email(request, usuario, "actualizado")
        notificacion_mi_usuario_email(request, usuario,"Usuario", "actualizado")
        messages.success(request, 'Datos Actualizados Correctamente') 
        request.session.pop('edit_username',None)
        request.session.save()
        return redirect('manage_users') 
    
@login_required
def edit_my_profile(request):
    usuario = Usuario.objects.get(username=request.user.username)
    usuarioProfile = UsuarioProfile.objects.get(user_id=usuario.id)
    usuarioLicencias = LicenciasUsuario.objects.get(user_id=usuario.id)  
    usuarioDocumentacion = DocumentacionUsuario.objects.get(user_id=usuario.id)  
    ciudad_actual = Ciudad.objects.filter(ciudad=usuarioProfile.ciudad)
    nacionalidad_actual = Nacionalidad.objects.filter(nacionalidad=usuarioProfile.nacionalidad)
    genero_actual = Genero.objects.filter(genero=usuarioProfile.genero)
    faena_actual = Faena.objects.filter(faena=usuarioProfile.faena)
    tipoDocumentacionFaenaGeneral = TipoDocumentoFaenaGeneral.objects.filter(faena=usuarioProfile.faena)
    urlUsuario = usuarioDocumentacion.fotografiaUsuario
    urlCedula = usuarioDocumentacion.fotografiaCedula
    urlLicencia = usuarioDocumentacion.fotografiaLicencia
    urlLicenciaInterna = usuarioDocumentacion.fotografiaLicenciaInterna
    if urlUsuario.url.lower().endswith((".jpg", ".jpeg", ".png")):
        extensionUsuario = "imagen"
    elif urlUsuario.url.lower().endswith((".pdf")):
        extensionUsuario = "pdf"
    else:
        extensionUsuario = "otro"
    if urlCedula.url.lower().endswith((".jpg", ".jpeg", ".png")):
        extensionCedula = "imagen"
    elif urlCedula.url.lower().endswith((".pdf")):
        extensionCedula = "pdf"
    else:
        extensionCedula = "otro"
    if urlLicencia.url.lower().endswith((".jpg", ".jpeg", ".png")):
        extensionLicencia = "imagen"
    elif urlLicencia.url.lower().endswith((".pdf")):
        extensionLicencia = "pdf"
    else:
        extensionLicencia = "otro"        
    if urlLicenciaInterna.url.lower().endswith((".jpg", ".jpeg", ".png")):
        extensionLicenciaInterna = "imagen"
    elif urlLicenciaInterna.url.lower().endswith((".pdf")):
        extensionLicenciaInterna = "pdf"
    else:
        extensionLicenciaInterna = "otro"
    ####### START return fechas formateadas   
    if not usuarioProfile.fechaNacimiento:
        fecha_nacimiento =""
    else:
        fecha_nacimiento_original = str(datetime.strftime(usuarioProfile.fechaNacimiento, "%Y-%m-%d"))
        fecha_nacimiento_formateada = datetime.strptime(fecha_nacimiento_original, "%Y-%m-%d")
        fecha_nacimiento = fecha_nacimiento_formateada.strftime('%Y-%m-%d')
    if not usuarioProfile.fechaCedulaVencimiento:
        fecha_cedula_vencimiento =""
    else:
        fecha_cedula_vencimiento_original = str(datetime.strftime(usuarioProfile.fechaCedulaVencimiento, "%Y-%m-%d"))
        fecha_cedula_vencimiento_formateada = datetime.strptime(fecha_cedula_vencimiento_original, "%Y-%m-%d")
        fecha_cedula_vencimiento = fecha_cedula_vencimiento_formateada.strftime('%Y-%m-%d')
    if not usuarioLicencias.fechaLicenciaVencimiento:
        fecha_licencia_vencimiento =""
    else:
        fecha_licencia_vencimiento_original = str(datetime.strftime(usuarioLicencias.fechaLicenciaVencimiento, "%Y-%m-%d"))
        fecha_licencia_vencimiento_formateada = datetime.strptime(fecha_licencia_vencimiento_original, "%Y-%m-%d")
        fecha_licencia_vencimiento = fecha_licencia_vencimiento_formateada.strftime('%Y-%m-%d')
    if not usuarioLicencias.fechaLicenciaInternaVencimiento:
        fecha_licencia_interna_vencimiento =""
    else:
        fecha_licencia_interna_vencimiento_original = str(datetime.strftime(usuarioLicencias.fechaLicenciaInternaVencimiento, "%Y-%m-%d"))
        fecha_licencia_interna_vencimiento_formateada = datetime.strptime(fecha_licencia_interna_vencimiento_original, "%Y-%m-%d")
        fecha_licencia_interna_vencimiento = fecha_licencia_interna_vencimiento_formateada.strftime('%Y-%m-%d')
    ####### END return fechas formateadas        
    context = {
        'rut_username': usuario.username,
        'faena': usuarioProfile.faena,
        'sidebar': 'dashboard',
        'formregistro': FormRegistro(initial={
            'username': usuario.username,
            'first_name':usuario.first_name,
            'last_name': usuario.last_name,
            'email': usuario.email,
            'phone': usuario.phone,
            'role': usuario.role,
            },
            username_disabled=True,
            first_name_disabled=False,
            last_name_disabled=False,
            role_disabled=True,
            ocultar_password=True,
            ocultar_role=False,            
        ),   
        'formregistroextra': FormRegistroExtra(initial={
            'ciudad': usuarioProfile.ciudad,
            'nacionalidad': usuarioProfile.nacionalidad,
            'genero': usuarioProfile.genero,
            'fechaNacimiento': fecha_nacimiento,
            'fechaCedulaVencimiento': fecha_cedula_vencimiento,
            'faena': usuarioProfile.faena,
            },
            ciudad_disabled=False,
            nacionalidad_disabled=False,
            genero_disabled=False,
            faena_disabled=True,
            ciudad_actual=ciudad_actual,
            nacionalidad_actual=nacionalidad_actual,
            genero_actual=genero_actual,
            faena_actual=faena_actual,
        ),
        'formregistroseccion': FormRegistroSeccion(initial={
            'seccionVehicular': usuarioProfile.seccionVehicular,
            'seccionSondaje': usuarioProfile.seccionSondaje,
            'seccionPrevencion': usuarioProfile.seccionPrevencion,
            },
            seccionVehicular_disabled=True,
            seccionSondaje_disabled=True,
            seccionPrevencion_disabled=True,
        ),
        'formregistrolicenciasusuariofecha': FormRegistroLicenciasUsuarioFecha(initial={
            'fechaLicenciaVencimiento': fecha_licencia_vencimiento,
            'fechaLicenciaInternaVencimiento': fecha_licencia_interna_vencimiento,
            },
        ),
        'formregistrolicenciasusuarionoprofesionales': FormRegistroLicenciasUsuarioNoProfesionales(initial={
            'licenciaClaseB': usuarioLicencias.licenciaClaseB,                   
            'licenciaClaseC': usuarioLicencias.licenciaClaseC,
            'licenciaClaseD': usuarioLicencias.licenciaClaseD,
            'licenciaClaseE': usuarioLicencias.licenciaClaseE,
            'licenciaClaseF': usuarioLicencias.licenciaClaseF,
            },
        ),
        'formregistrolicenciasusuarioprofesionales': FormRegistroLicenciasUsuarioProfesionales(initial={
            'licenciaClaseA1': usuarioLicencias.licenciaClaseA1,                   
            'licenciaClaseA2': usuarioLicencias.licenciaClaseA2,
            'licenciaClaseA3': usuarioLicencias.licenciaClaseA3,
            'licenciaClaseA4': usuarioLicencias.licenciaClaseA4,
            'licenciaClaseA5': usuarioLicencias.licenciaClaseA5,
            },
        ),
        'formregistrolicenciasusuarioprofesionalesantiguas': FormRegistroLicenciasUsuarioProfesionalesAntiguas(initial={
            'licenciaClaseA1Antigua': usuarioLicencias.licenciaClaseA1Antigua,                   
            'licenciaClaseA2Antigua': usuarioLicencias.licenciaClaseA2Antigua,
            },
        ),  
        'fotografiaUsuario': usuarioDocumentacion.fotografiaUsuario,            
        'fotografiaCedula': usuarioDocumentacion.fotografiaCedula,            
        'fotografiaLicencia': usuarioDocumentacion.fotografiaLicencia,   
        'fotografiaLicenciaInterna': usuarioDocumentacion.fotografiaLicenciaInterna,
        'extensionUsuario': extensionUsuario,
        'extensionCedula': extensionCedula,
        'extensionLicencia': extensionLicencia,
        'extensionLicenciaInterna': extensionLicenciaInterna,
        'documentacionFaenaGeneral': tipoDocumentacionFaenaGeneral,
        
    }
    return render(request,'pages/users/my_profile.html', context)

@login_required
def save_edit_my_profile(request):  
    if request.method == 'POST':
        Usuario.objects.filter(username=request.user.username).update(first_name=request.POST['first_name'])
        Usuario.objects.filter(username=request.user.username).update(last_name=request.POST['last_name'])
        try:
            Usuario.objects.filter(username=request.user.username).update(phone=request.POST['phone']) 
        except:
            return JsonResponse({'titleText': "N° de Teléfono ya existe",'text': "Intenta nuevamente"}, status=400)
        try:
            Usuario.objects.filter(username=request.user.username).update(email=request.POST['email']) 
        except:
            return JsonResponse({'titleText': "Dirección de Correo ya existe",'text': "Intenta nuevamente"}, status=400)
        try:
            UsuarioProfile.objects.filter(user_id=request.user.id).update(ciudad=request.POST['ciudad']) 
        except:
            pass
        try:
            UsuarioProfile.objects.filter(user_id=request.user.id).update(nacionalidad=request.POST['nacionalidad']) 
        except:
            pass
        try:
            UsuarioProfile.objects.filter(user_id=request.user.id).update(genero=request.POST['genero']) 
        except:
            pass
        try:
            UsuarioProfile.objects.filter(user_id=request.usero.id).update(fechaNacimiento=request.POST['fechaNacimiento']) 
        except:
            pass
        try:
            UsuarioProfile.objects.filter(user_id=request.user.id).update(fechaCedulaVencimiento=request.POST['fechaCedulaVencimiento']) 
        except:
            pass
        try:
            LicenciasUsuario.objects.filter(user_id=request.user.id).update(fechaLicenciaVencimiento=request.POST['fechaLicenciaVencimiento']) 
        except:
            LicenciasUsuario.objects.filter(user_id=request.user.id).update(fechaLicenciaVencimiento=None) 
        try:
            LicenciasUsuario.objects.filter(user_id=request.user.id).update(fechaLicenciaInternaVencimiento=request.POST['fechaLicenciaInternaVencimiento']) 
        except:
            LicenciasUsuario.objects.filter(user_id=request.user.id).update(fechaLicenciaInternaVencimiento=None) 
        LicenciasUsuario.objects.filter(user_id=request.user.id).update(licenciaClaseB=request.POST['licenciaClaseB']) 
        LicenciasUsuario.objects.filter(user_id=request.user.id).update(licenciaClaseC=request.POST['licenciaClaseC']) 
        LicenciasUsuario.objects.filter(user_id=request.user.id).update(licenciaClaseD=request.POST['licenciaClaseD']) 
        LicenciasUsuario.objects.filter(user_id=request.user.id).update(licenciaClaseE=request.POST['licenciaClaseE']) 
        LicenciasUsuario.objects.filter(user_id=request.user.id).update(licenciaClaseF=request.POST['licenciaClaseF']) 
        LicenciasUsuario.objects.filter(user_id=request.user.id).update(licenciaClaseA1=request.POST['licenciaClaseA1']) 
        LicenciasUsuario.objects.filter(user_id=request.user.id).update(licenciaClaseA2=request.POST['licenciaClaseA2']) 
        LicenciasUsuario.objects.filter(user_id=request.user.id).update(licenciaClaseA3=request.POST['licenciaClaseA3']) 
        LicenciasUsuario.objects.filter(user_id=request.user.id).update(licenciaClaseA4=request.POST['licenciaClaseA4']) 
        LicenciasUsuario.objects.filter(user_id=request.user.id).update(licenciaClaseA5=request.POST['licenciaClaseA5']) 
        LicenciasUsuario.objects.filter(user_id=request.user.id).update(licenciaClaseA1Antigua=request.POST['licenciaClaseA1Antigua']) 
        LicenciasUsuario.objects.filter(user_id=request.user.id).update(licenciaClaseA2Antigua=request.POST['licenciaClaseA2Antigua']) 
        documentacionUsuario = DocumentacionUsuario.objects.get(user_id=request.user.id) 
        
        toggle_Usuario = request.POST.get('toggle-Usuario', 'no')
        procesar_fotografia(documentacionUsuario, toggle_Usuario, 'fotografiaUsuario','documentacion_usuario/no-avatar.png', request)
                    
        toggle_Cedula = request.POST.get('toggle-Cedula', 'no')
        procesar_fotografia(documentacionUsuario, toggle_Cedula, 'fotografiaCedula','documentacion_usuario/no-imagen.png', request)
        
        toggle_Licencia = request.POST.get('toggle-Licencia', 'no')
        procesar_fotografia(documentacionUsuario, toggle_Licencia, 'fotografiaLicencia','documentacion_usuario/no-imagen.png', request)
                
        toggle_LicenciaInterna = request.POST.get('toggle-LicenciaInterna', 'no')
        procesar_fotografia(documentacionUsuario, toggle_LicenciaInterna, 'fotografiaLicenciaInterna','documentacion_usuario/no-imagen.png', request)
        
        documentacionUsuario.save()
        usuario = Usuario.objects.get(username=request.user.username) 
        notificacion_mi_usuario_email(request, usuario,"Usuario", "actualizado")
        messages.success(request, 'Datos Actualizados Correctamente') 
        return redirect('edit_my_profile') 
    
@login_required
def save_password_change(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Contraseña Actualizada Correctamente') 
            return redirect('edit_my_profile')
        else:
            messages.error(request, 'Error en las Contraseñas', extra_tags='Intenta nuevamente')
            return redirect('password_change')
    else:
        messages.error(request, 'Error al Actualizar la Contraseña')
        return redirect('password_change')

def password_reset_send(request):
    if request.method == 'POST':
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data['email']
            associated_users = User.objects.filter(Q(email=data))
            if associated_users.exists():
                for user in associated_users:
                    try:
                        form.save(
                            request=request,
                            use_https=request.is_secure(),
                            email_template_name='registration/password_reset_email.html',
                        )
                        messages.success(request, 'Email enviado con éxito.', extra_tags='Siga las instrucciones en su correo electrónico')
                        return redirect('logincustom')
                    except BadHeaderError:
                        return HttpResponse('Solicitud Invalida.')
            else:
                messages.error(request, 'No hay usuarios registrados con ese email.', extra_tags='Intenta nuevamente')
                return redirect('password_reset')
        else:
            messages.error(request, 'Error en Email ingresado.', extra_tags='Intenta nuevamente')
            return redirect('password_reset')
            
    else:
        messages.error(request, 'Error en Email ingresado.', extra_tags='Intenta nuevamente')
        return redirect('password_reset')

