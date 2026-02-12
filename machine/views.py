from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .forms import FormMaquinaria, FormNuevoHorometro, FormNuevoKitReparacionFaena, FormEditKitsMaquinariaFaena, FormEditKitsMaquinariaFaenaAdd
from .models import Maquinaria, MaquinariaFaena, NuevoHorometro, HistorialStockKitsMaquinariaFaena, KitsMaquinariaFaena
from django.utils.datastructures import MultiValueDictKeyError
from core.models import TipoMaquinaria, MarcaMaquinaria, Faena
from core.utils import procesar_fotografia, validar_campo_vacio, formatear_fecha
from django.http import JsonResponse
from user.models import User, UsuarioProfile
from maintenance.models import NuevaSolicitudMantenimientoMaquinaria
from core.choices import progreso
import datetime
import os
from django.conf import settings
from django.template.loader import get_template
from xhtml2pdf import pisa
from django.db import IntegrityError
from django.db.models import Max, Subquery, OuterRef
from messenger.views import notificacion_maquinarias_email, notificacion_admin_jefe_mantencion_email
from core.decorators import admin_or_jefe_mantencion_required, admin_required, admin_or_jefe_mantencion_or_supervisor_required

@login_required
@admin_or_jefe_mantencion_or_supervisor_required
def new_machine(request): 
    context = {
        'formnuevamaquinaria': FormMaquinaria,   
        'sidebar': 'manage_machines',
        'sidebarmain': 'system_machines',
    }
    return render(request,'pages/machine/new_machine.html', context)

@login_required
@admin_or_jefe_mantencion_or_supervisor_required
def manage_machines(request):
    #request.session.pop('edit_username',None)
    #request.session.save()
    usuario = UsuarioProfile.objects.get(user=request.user.id)
    if usuario.faena.faena == "SIN ASIGNAR":
        maquinarias = list(Maquinaria.objects.all().order_by('-fechacreacion'))
    else:
        maquinarias = list(Maquinaria.objects.filter(faena=usuario.faena).order_by('-fechacreacion'))

    context = {
        'faenausuario': usuario.faena,
        'maquinarias': maquinarias,
        'sidebar': 'manage_machines',
        'sidebarmain': 'system_machines',  
    }
    return render(request,'pages/machine/manage_machines.html', context)

@login_required
@admin_or_jefe_mantencion_or_supervisor_required
def save_new_machine(request): 
    if request.method == 'POST':    
        tipo_instancia = TipoMaquinaria.objects.get(pk=request.POST['tipo'])    
        marca_instancia = MarcaMaquinaria.objects.get(pk=request.POST['marca'])  
        faena_instancia = Faena.objects.get(pk=request.POST['faena'])
        formulario = FormMaquinaria(data=request.POST)
        fechaAdquisicion = validar_campo_vacio('fechaAdquisicion',request)
        frecuenciaMantenimiento = validar_campo_vacio('frecuenciaMantenimiento',request)
        if formulario.is_valid():               
            maquinaria = Maquinaria(
                maquinaria = request.POST['maquinaria'],
                descripcion = request.POST['descripcion'],
                fechaAdquisicion = fechaAdquisicion,
                tipo = tipo_instancia,
                marca = marca_instancia,
                faena = faena_instancia,
                frecuenciaMantenimiento = frecuenciaMantenimiento,
                status = True,
            )    
            maquinaria.save()
            
            maquinaria = Maquinaria.objects.get(maquinaria=request.POST['maquinaria'])
            faena = MaquinariaFaena(
                maquinaria = maquinaria,
                faena = faena_instancia,
                status = True,
                creador = request.user.first_name+" "+request.user.last_name,                
            )
            faena.save()
            notificacion_maquinarias_email(request, maquinaria, "creada")
            messages.success(request, 'Maquinaria creada correctamente', extra_tags='')
            return redirect('manage_machines')          
        else:                
            messages.error(request, 'Error en el Formulario', extra_tags='Vuelva a intentarlo')
            context = {
                'formnuevamaquinaria': formulario,
                'marca':request.POST['marca'],
                'sidebar': 'manage_machines',
                'sidebarmain': 'system_machines',     
            }         
            return render(request,'pages/machine/new_machine.html',context)
    else:
        return redirect('new_machine')

@login_required
@admin_or_jefe_mantencion_or_supervisor_required
def status_machine(request):
    if request.method == 'POST': 
        maquinaria = Maquinaria.objects.get(id=request.POST['maquinaria_id'])
        if (maquinaria.status):
            Maquinaria.objects.filter(id=request.POST['maquinaria_id']).update(status=False)
            notificacion_maquinarias_email(request, maquinaria, "deshabilitada")
            messages.success(request, 'Maquinaria Deshabilitada Correctamente')
            return redirect('manage_machines') 
        else:            
            Maquinaria.objects.filter(id=request.POST['maquinaria_id']).update(status=True)
            notificacion_maquinarias_email(request, maquinaria, "habilitada")
            messages.success(request, 'Maquinaria Habilitada Correctamente')  
        return redirect('manage_machines') 
    else:
        return redirect('manage_machines') 

@login_required
@admin_or_jefe_mantencion_or_supervisor_required
def edit_machine_profile(request):
        try:
            request.session['edit_machine_id'] = request.POST['maquinaria_id']            
        except MultiValueDictKeyError:
            request.session['edit_machine_id'] = request.session['edit_machine_id']
        maquinaria = Maquinaria.objects.get(id=request.session['edit_machine_id'])
        solicitudesMantenimiento = NuevaSolicitudMantenimientoMaquinaria.objects.filter(maquinaria=maquinaria).order_by('-fechacreacion')
        tipo_actual = TipoMaquinaria.objects.filter(tipo=maquinaria.tipo)
        marca_actual = MarcaMaquinaria.objects.filter(marca=maquinaria.marca)
        faena_actual = Faena.objects.filter(faena=maquinaria.faena)
        fecha_adquisicion = formatear_fecha(maquinaria.fechaAdquisicion)
        historialfaenas = list(MaquinariaFaena.objects.filter(maquinaria=maquinaria).order_by('-fechacreacion'))
        horometros = NuevoHorometro.objects.filter(maquinaria=maquinaria).order_by('-fechacreacion')
        if request.user.role == "SUPERVISOR":
            faena_disabled = True
        else:
            faena_disabled = False
        ####### context        
        context = {
            'sidebar': 'manage_machines',
            'sidebarmain': 'system_machines',
            'maquinaria': maquinaria,
            'faena':maquinaria.faena.id,
            'historialfaenas': historialfaenas,
            'solicitudesMantenimiento': solicitudesMantenimiento,
            'choicesprogreso': progreso,
            'horometros': horometros,
            'formnuevamaquinaria': FormMaquinaria(initial={
                'maquinaria': maquinaria.maquinaria,
                'descripcion': maquinaria.descripcion,
                'fechaAdquisicion': fecha_adquisicion,
                'tipo': maquinaria.tipo,
                'marca': maquinaria.marca,
                'faena': maquinaria.faena,
                'frecuenciaMantenimiento': maquinaria.frecuenciaMantenimiento,
                },
                tipo_actual=tipo_actual,
                marca_actual=marca_actual,
                faena_actual=faena_actual,
                faena_disabled=faena_disabled,
            ),          
        }
        return render(request,'pages/machine/edit_machine_profile.html', context)

@login_required
@admin_or_jefe_mantencion_or_supervisor_required
def save_edit_machine_profile(request):  
    if request.method == 'POST': 
        fechaAdquisicion = validar_campo_vacio('fechaAdquisicion',request)
        frecuenciaMantenimiento = validar_campo_vacio('frecuenciaMantenimiento',request)
        faena = Faena.objects.get(id=request.POST['faena'])
        maquinaria = Maquinaria.objects.get(id=request.POST['maquinaria_id'])
        if maquinaria.faena.id != faena.id:
            MaquinariaFaena.objects.filter(maquinaria=maquinaria,status=True).update(status=False)
            faena = MaquinariaFaena(
                maquinaria = maquinaria,
                faena = faena,
                status = True,
                creador = request.user.first_name+" "+request.user.last_name,                
            )
            faena.save()
        
        Maquinaria.objects.filter(id=request.POST['maquinaria_id']).update(
            maquinaria = request.POST['maquinaria'],
            descripcion = request.POST['descripcion'],
            fechaAdquisicion = fechaAdquisicion,
            tipo = request.POST['tipo'],
            marca = request.POST['marca'],
            faena = request.POST['faena'],
            frecuenciaMantenimiento = frecuenciaMantenimiento,
        )
        
        notificacion_maquinarias_email(request, maquinaria, "actualizada")
        messages.success(request, 'Datos Actualizados Correctamente') 
        return redirect('manage_machines') 
    else: 
        messages.error(request, "No se Actualizó", extra_tags='Vuelva a Intentarlo')
        context = {      
                'sidebar': 'manage_machines',
                'sidebarmain': 'system_machines',     
            }         
        return render(request,'pages/machines/edit_machine_profile.html', context)       

@login_required
@admin_or_jefe_mantencion_or_supervisor_required
def cargar_marca_por_tipo(request):
    tipo_id = request.GET.get('tipo_id')
    if tipo_id:
        marcas = MarcaMaquinaria.objects.filter(tipo=tipo_id,status=True)
        data = [{'id': marca.id, 'nombre': marca.marca} for marca in marcas]
        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({}, status=400)

@login_required    
def new_horometro_register(request):
    usuario = UsuarioProfile.objects.get(user=request.user.id)
    if usuario.faena.faena == "SIN ASIGNAR":
        maquinarias = Maquinaria.objects.filter(status=True).order_by('-maquinaria')
    else:
        maquinarias = Maquinaria.objects.filter(faena=usuario.faena, status=True).order_by('-maquinaria')

    context = {
        'formnuevohorometro': FormNuevoHorometro(maquinarias=maquinarias),   
        'sidebar': 'new_horometro_register',
        'sidebarmain': 'system_machines',
    }
    return render(request,'pages/machine/new_horometro.html', context)

@login_required
def save_new_horometro_register(request):
    if request.method == 'POST':
        #formulario = FormNuevoHorometro(data=request.POST)
        maquinaria = Maquinaria.objects.get(id= request.POST['maquinaria'])
        registro = NuevoHorometro(
            maquinaria = maquinaria,
            horometro = request.POST['horometro'],
            creador = request.user.first_name+" "+request.user.last_name,
            origen = "Formulario"
        )
        registro.save()             
        return JsonResponse({'success': True})
    else:
        return redirect('new_kilometraje_register')

@login_required
def machine_pdf_view(request):
    if request.method == 'POST':
        maquinaria = get_object_or_404(Maquinaria, id=request.POST['maquinaria_id'])
        current_datetime = datetime.datetime.now()

        context = {
            'maquinaria': maquinaria,
            'user_role': request.user.role,
            'current_datetime': current_datetime,
        }

        template_path = 'pages/pdfs/machine_pdf_template.html'
        template = get_template(template_path)
        html = template.render(context)
        filename = f'{maquinaria.maquinaria}-{current_datetime.strftime("%Y%m%d_%H%M%S")}.pdf'
        pdf_path = os.path.join(settings.MEDIA_ROOT, 'pdfs_temp', filename)
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        with open(pdf_path, 'wb') as pdf_file:
            pisa_status = pisa.CreatePDF(html, dest=pdf_file)
            if pisa_status.err:
                return JsonResponse({'error': 'Error al generar el PDF'})

        pdf_url = os.path.join(settings.MEDIA_URL, 'pdfs_temp', filename)
        return JsonResponse({'pdf_url': pdf_url, 'message': 'Documento creado con éxito'})
    else:
        return redirect('manage_machines')

@login_required
def manage_machines_kits_repair(request):
    # Se reestructura la consulta para listar asignaciones de Kits (KitsMaquinariaFaena) en lugar de registros históricos brutos.
    # Se implementa una lógica de cálculo de stock en tiempo real, obteniendo el saldo del último movimiento registrado 
    # para cada asignación, lo que permite visualizar la disponibilidad actual y consolidada del inventario por Faena.
    asignaciones = KitsMaquinariaFaena.objects.all().order_by('-status', '-fechacreacion')
    
    kits_para_mostrar = []

    for asignacion in asignaciones:
        ultimo_historial = HistorialStockKitsMaquinariaFaena.objects.filter(
            kitMaquinaria=asignacion
        ).order_by('-fechacreacion').first()
        
        stock_real = ultimo_historial.stockActual if ultimo_historial else 0
        asignacion.stock_calculado = stock_real 
        kits_para_mostrar.append(asignacion)

    context = {
        'kits_faena': kits_para_mostrar,
        'sidebarmenu': 'manage_machine',
        'sidebarsubmenu': 'manage_machines_kits_repair', 
        'sidebarmain': 'manage_system', 
    }
    
    return render(request, 'pages/machine/manage_machines_kits_repair.html', context)

@login_required
def new_machines_kits_repair(request):
    context = {
        'formnuevokitsfaena': FormNuevoKitReparacionFaena,
        'sidebar': 'manage_machines_kits_repair',
        'sidebarmain': 'system_machines',
    }
    return render(request,'pages/machine/new_machines_kits_repair.html', context)

@login_required
def save_new_machines_kits_repair(request):
    if request.method == 'POST':
        form = FormNuevoKitReparacionFaena(request.POST)
        if form.is_valid():
            try:
                nueva_solicitud = form.save(commit=False)
                nueva_solicitud.status = True
                nueva_solicitud.creador = request.user.first_name + " " + request.user.last_name
                nueva_solicitud.save()
                stock_inicial = nueva_solicitud.kitMaquinaria.stockMaximo or 0
                nueva = HistorialStockKitsMaquinariaFaena(
                    kitMaquinaria = nueva_solicitud,
                    faena = nueva_solicitud.faena,
                    stockMovimiento = stock_inicial, 
                    stockActual = stock_inicial,   
                    descripcion = 'Creación del Kit (Stock Inicial Completo)',
                    creador = request.user.first_name + " " + request.user.last_name,
                    status = True,
                )
                nueva.save()
                return JsonResponse({'success': True})
            except IntegrityError:
                return JsonResponse({'error': 'Error al generar el Kit'})
    else:
        return redirect('new_machines_kits_repair')
        
@login_required
def status_machines_kits_repair(request):
    if request.method == 'POST': 
        try:
            kit_faena_id = request.POST.get('kit_id')
            kit_faena = get_object_or_404(KitsMaquinariaFaena, id=kit_faena_id)
            
            if kit_faena.status: 
                kit_faena.status = False
                kit_faena.save()
                messages.success(request, 'Kit en Faena Deshabilitado')             
            else:            
                kit_faena.status = True
                kit_faena.save()
                messages.success(request, 'Kit en Faena Habilitado')  
            
            return redirect('manage_machines_kits_repair')
        except Exception as e:
            messages.error(request, 'Error al cambiar estado')
            return redirect('manage_machines_kits_repair')
    else:
        return redirect('manage_machines_kits_repair')
    
@login_required
def edit_machines_kits_repair(request):
    try:
        if request.method == 'POST' and 'kit_faena_id' in request.POST:
            request.session['kit_faena_id'] = request.POST['kit_faena_id']
        
        kit_faena_id = request.session.get('kit_faena_id')
        
        if not kit_faena_id:
            return redirect('manage_machines_kits_repair')

    except MultiValueDictKeyError:
        return redirect('manage_machines_kits_repair')

    kit_asignado = get_object_or_404(KitsMaquinariaFaena, id=kit_faena_id)

    historial = HistorialStockKitsMaquinariaFaena.objects.filter(kitMaquinaria=kit_asignado ).order_by('-fechacreacion')
    ultimo_registro = historial.first()
    stock_actual = ultimo_registro.stockActual if ultimo_registro else 0


    context = {
        'sidebar': 'manage_machines_kits_repair',
        'sidebarmain': 'system_machines',

        'kit_asignado': kit_asignado, 
        'kit_faena_id': kit_asignado.id,
        'stock_actual': stock_actual,
        
        'formeditkit': FormEditKitsMaquinariaFaena(initial={
            'kitMaquinaria': kit_asignado.kitMaquinaria,
            'faena': kit_asignado.faena,
            'stockActual': stock_actual,
        }),
        
        'formeditkitadd': FormEditKitsMaquinariaFaenaAdd, 
        'historial': historial,
    }
    
    return render(request, 'pages/machine/edit_machines_kits_repair.html', context)
    
@login_required
def save_edit_machines_kits_repair(request):
    if request.method == 'POST':
        try:
            kit_faena_id = request.POST.get('kit_faena_id')
            kit_asignado = get_object_or_404(KitsMaquinariaFaena, id=kit_faena_id)

            ultimo_historial = HistorialStockKitsMaquinariaFaena.objects.filter(
                kitMaquinaria=kit_asignado
            ).order_by('-fechacreacion').first()
            
            stock_actual_anterior = ultimo_historial.stockActual if ultimo_historial else 0
            
            movimiento = int(request.POST['stockMovimiento'])
            nuevo_stock = stock_actual_anterior + movimiento
            
            nueva_entrada = HistorialStockKitsMaquinariaFaena(
                kitMaquinaria = kit_asignado,
                faena = kit_asignado.faena,
                stockMovimiento = movimiento,
                stockActual = nuevo_stock,
                descripcion = request.POST['descripcion'],
                creador = request.user.first_name + " " + request.user.last_name,
                status = True,
            )
            nueva_entrada.save()
            kit_asignado.fechacreacion = datetime.datetime.now()
            kit_asignado.save(update_fields=['fechacreacion'])
            messages.success(request, 'Stock agregado Correctamente') 
            return redirect('manage_machines_kits_repair') 

        except Exception as e:
            print(e)
            messages.error(request, 'Error al Agregar Stock, intente Nuevamente') 
            return redirect('manage_machines_kits_repair') 

    else:
        return redirect('manage_machines_kits_repair')