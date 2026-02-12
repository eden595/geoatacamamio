from datetime import datetime
from django.shortcuts import render, redirect
from django.contrib.auth.views import LoginView, LogoutView
from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from rut_chile import rut_chile
from vehicle.forms import FormNuevoVehiculo, FormInformacionTecnica
from vehicle.models import Vehiculo, DocumentacionesVehiculo, InformacionTecnicaVehiculo
from core.models import Tipo, Ano, Marca, Modelo, Color
from django.utils.datastructures import MultiValueDictKeyError
from core.utils import procesar_fotografia, validar_campo_vacio, validar_archivo_vacio, formatear_fecha
from .models import VehiculoAsignado, DocumentoPorFaena
from .forms import FormVehiculoAsignacion
from core.models import Faena, TipoDocumentoFaena
from django.core.exceptions import ObjectDoesNotExist
import datetime
from django.http import JsonResponse
import re
from messenger.views import notificacion_cambio_faena_vehiculo_email
from core.decorators import admin_or_jefe_mantencion_required

@login_required
@admin_or_jefe_mantencion_required
def manage_vehicles_mining(request):
    #request.session.pop('edit_username',None)
    #request.session.save()
    vehiculos = list(Vehiculo.objects.filter(status=True).order_by('-fechacreacion')) 
    vehiculos_asignados = list(VehiculoAsignado.objects.filter(status=True).order_by('-fechacreacion')) 

    mapeo_faenas = {vehiculo.vehiculo_id: vehiculo.faena for vehiculo in vehiculos_asignados}
    for vehiculo in vehiculos:
        if vehiculo.id in mapeo_faenas:
            vehiculo.faena_asignada = mapeo_faenas[vehiculo.id]
        else:
            vehiculo.faena_asignada = "SIN ASIGNAR"  

    context = {
        'vehiculos': vehiculos,
        'sidebar': 'manage_vehicles_mining',
        'sidebarmain': 'system_vehicles',  
    }
    return render(request,'pages/mining/manage_vehicles_mining.html', context)
    
@login_required
@admin_or_jefe_mantencion_required
def edit_vehicle_mining(request):
        try:
            request.session['edit_placaPatente'] = request.POST['placaPatente']            
        except MultiValueDictKeyError:
            request.session['edit_placaPatente'] = request.session['edit_placaPatente']
            
        vehiculo = Vehiculo.objects.get(placaPatente=request.session['edit_placaPatente'])
        historial_vehiculos_asignados = VehiculoAsignado.objects.filter(vehiculo_id=vehiculo.id).order_by('-fechacreacion')
        fecha_hoy = datetime.date.today().strftime('%Y-%m-%d')
        
        tipo_documentos = TipoDocumentoFaena.objects.all()
        unique_tipo_documentos = []
        existing_names = set()
        for tipo_documento in tipo_documentos:
            if tipo_documento.faena not in existing_names:
                unique_tipo_documentos.append(tipo_documento)
                existing_names.add(tipo_documento.faena)
                
        vehiculo_asignado = VehiculoAsignado.objects.get(vehiculo_id=vehiculo.id, status=True)
        faena = Faena.objects.get(faena=vehiculo_asignado.faena)
        context = {
            'sidebar': 'manage_vehicles_mining',
            'sidebarmain': 'system_vehicles',
            'documentacionfaena': unique_tipo_documentos,
            'vehiculo': vehiculo,
            'historial_vehiculos_asignados': historial_vehiculos_asignados,
            'faenaAnterior': faena.id,
            'formasignacionvehiculo': FormVehiculoAsignacion(initial={
                'vehiculo': vehiculo.placaPatente,
                'faenaAnterior': faena.faena,
                'fechaInicial': fecha_hoy,
                'creador': request.user.first_name+' '+request.user.last_name,
                },
            ),    
        }
        return render(request,'pages/mining/edit_vehicle_mining.html', context)

@login_required
@admin_or_jefe_mantencion_required
def save_edit_vehicle_mining(request):
    if request.method == 'POST':
        vehiculo_asignado = VehiculoAsignado.objects.get(vehiculo_id=request.POST['vehiculo_id'], status=True)
        vehiculo = Vehiculo.objects.get(id=request.POST['vehiculo_id'])
        faena = Faena.objects.get(id=request.POST['faena'])
        
        claves = request.FILES.keys()
        prefijo_imagen = faena.faena+'_'
        for clave in claves:
            if clave.startswith(prefijo_imagen):
                archivo = validar_archivo_vacio(clave,request)
                # Si la clave comienza con el prefijo, agregar el valor correspondiente a la lista
                try:
                    documento_actual = DocumentoPorFaena.objects.get(patente=vehiculo.placaPatente, faena=faena.faena, tipoDocumento=clave, status=True)
                    DocumentoPorFaena.objects.filter(patente=vehiculo.placaPatente, faena=faena.faena, tipoDocumento=clave).update(status=False)
                    documento = DocumentoPorFaena(
                        faena=faena.faena,
                        patente=vehiculo.placaPatente,
                        creador=request.user.first_name + ' ' + request.user.last_name,
                        documento=archivo,
                        tipoDocumento= clave,
                        status=True,
                    )
                    documento.save()
                except ObjectDoesNotExist:
                    documento = DocumentoPorFaena(
                        faena=faena.faena,
                        patente=vehiculo.placaPatente,
                        creador=request.user.first_name + ' ' + request.user.last_name,
                        documento=archivo,
                        tipoDocumento= clave,
                        status=True,
                    )
                    documento.save()
                    
        fechas = request.POST.keys()
        prefijo_fecha = 'vencimiento'
        for fecha in fechas:            
            if fecha.startswith(prefijo_fecha):                
                nuevafecha = validar_campo_vacio(fecha,request)                
                tipo_documento = fecha.replace("vencimiento", "")
                DocumentoPorFaena.objects.filter(patente=vehiculo.placaPatente, faena=faena.faena, tipoDocumento=tipo_documento, status=True).update(fechaVencimiento=nuevafecha)
        
        toggles = request.POST.keys()
        prefijo_toggle = 'toggle-'+faena.faena+'_'
        for toggle in toggles:
            if toggle.startswith(prefijo_toggle):
                tipo_documento = toggle.replace("toggle-", "")           
                DocumentoPorFaena.objects.filter(patente=vehiculo.placaPatente, faena=faena.faena, tipoDocumento=tipo_documento).update(status=False)
                documento = DocumentoPorFaena(
                    faena=faena.faena,
                    patente=vehiculo.placaPatente,
                    creador=request.user.first_name + ' ' + request.user.last_name,
                    documento="/base/no-imagen.png",
                    tipoDocumento= tipo_documento,
                    status=True,
                    fechaVencimiento= None,
                )
                documento.save()

        #crea registro de faenas
        if (request.POST['faena'] == request.POST['faena_Anterior']):            
            messages.success(request, 'Datos actualizados correctamente')
            return redirect('manage_vehicles')
        #actualiza la fecha de solamente el elemnto anterior al que se esta creando    
        ultimo_vehiculo_asignado = VehiculoAsignado.objects.filter(vehiculo_id=request.POST['vehiculo_id']).order_by('-fechacreacion').first()
        if ultimo_vehiculo_asignado is not None:
            ultimo_vehiculo_asignado.fechaFinal = request.POST['fechaInicial']
            ultimo_vehiculo_asignado.status = False
            ultimo_vehiculo_asignado.save()
        
        vehiculo_actual = VehiculoAsignado(
            vehiculo = vehiculo,
            faena = faena,
            faenaAnterior = request.POST['faena_Anterior'],
            creador = request.user.first_name+' ' +request.user.last_name,
            fechaInicial = request.POST['fechaInicial'],
            status = True,
        )
        vehiculo_actual.save()
        notificacion_cambio_faena_vehiculo_email(request, vehiculo_actual, "asignado")
        messages.success(request, 'Datos actualizados correctamente') 
        return redirect('manage_vehicles')
    else: 
        return redirect('manage_vehicles')        
    
#obtine el parametro por ajax y devuelve los documentos que existen para la faena seleccionada
@login_required
@admin_or_jefe_mantencion_required
def select_documents_mining(request):
    if request.method == 'POST':
        faena_id = request.POST.get('faena_id')
        faena_texto = request.POST.get('faena_texto')
        patente = request.POST.get('patente')
        documentos = TipoDocumentoFaena.objects.filter(faena_id=faena_id,status=True).values('id', 'documento').order_by('documento')
        documentos_list = []
        for documento in documentos:
            tipo_documento = faena_texto + "_" + re.sub(r'\s+', '', documento['documento'])
            try:
                documento_actual = DocumentoPorFaena.objects.get(patente=patente, faena=faena_texto, tipoDocumento=tipo_documento, status=True)
                fecha_vencimmiento = formatear_fecha(documento_actual.fechaVencimiento)
                documentos_list.append({
                    'faena': documento_actual.faena,
                    'patente': documento_actual.patente,
                    'tipoDocumento': documento_actual.tipoDocumento,
                    'documento': documento_actual.documento.url,
                    'tipoDocumentoOriginal': documento['documento'],
                    'fechaVencimiento': fecha_vencimmiento,
                })
            except ObjectDoesNotExist:
                documentos_list.append({
                    'faena': faena_texto,
                    'patente': patente,
                    'tipoDocumento': tipo_documento,
                    'documento': "/media/base/no-imagen.png",
                    'tipoDocumentoOriginal': documento['documento'],
                    'fechaVencimiento': None,
                })
        data = {
            'documentos': documentos_list,
        }        
        return JsonResponse(data, safe=False)
    return JsonResponse({'error': 'Solicitud no válida'}, status=400)

