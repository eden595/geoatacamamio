from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.contrib import messages
from django.utils.datastructures import MultiValueDictKeyError
from core.decorators import sondaje_admin_or_base_datos_or_supervisor_required, admin_required
from .models import MarcaEquipo, TipoEquipo, NuevoEquipamiento
from .forms import FormMarcaEquipo, FormNuevoEquipamiento, FormTipoEquipo
from messenger.views import notificacion_mantenedor_email, notificacion_admin_jefe_mantencion_email
from core.models import Faena
from core.utils import formatear_fecha

@login_required
@admin_required
def manage_types_equipment(request): 
    storage = messages.get_messages(request)
    storage.used = True
    tipos = list(TipoEquipo.objects.all().order_by('id'))
    context = {
        'tipos': tipos,
        'sidebarsubmenu': 'manage_typeequipment',
        'sidebarmenu': 'manage_equipment',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/equipment/manage_types_equipment.html', context)

@login_required
@admin_required
def new_type_equipment(request):     
    context = {
        'formnuevotipomaquinaria': FormTipoEquipo, 
        'sidebarsubmenu': 'manage_typeequipment',
        'sidebarmenu': 'manage_equipment',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/equipment/new_type_equipment.html', context)

@login_required
@admin_required
def save_new_type_equipment(request):     
    if request.method == 'POST':
        formulario = FormTipoEquipo(data=request.POST)
        if formulario.is_valid():       
            tipo = TipoEquipo(
                tipo = request.POST['tipo'],
                status = True,
                creador = request.user.first_name+" "+request.user.last_name,
            )
            tipo.save()
            notificacion_mantenedor_email(request,tipo,'Tipo Equipo','creado')
            return JsonResponse({'success': True})
    else:
        return redirect('new_type_machine')

@login_required
@admin_required
def status_type_equipment(request):
    if request.method == 'POST': 
        tipo = TipoEquipo.objects.get(id=request.POST['id'])
        if (tipo.status): 
            TipoEquipo.objects.filter(id=request.POST['id']).update(status=False)
            notificacion_mantenedor_email(request,tipo,'Tipo Equipo','deshabilitado')
            messages.success(request, 'Tipo Equipo Deshabilitado Correctamente')  
        else:
            TipoEquipo.objects.filter(id=request.POST['id']).update(status=True)
            notificacion_mantenedor_email(request,tipo,'Tipo Equipo','habilitada')
            messages.success(request, 'Tipo Equipo Habilitado Correctamente') 
        return redirect('manage_types_equipment')
    else:
        messages.error(request, 'Error al Deshabilitar') 
        return redirect('manage_types_equipment')

@login_required
@admin_required
def manage_brands_equipment(request): 
    storage = messages.get_messages(request)
    storage.used = True
    marcas = list(MarcaEquipo.objects.all().order_by('id'))   
    context = {
        'marcas': marcas,
        'sidebarsubmenu': 'manage_brandequipment',
        'sidebarmenu': 'manage_equipment',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/equipment/manage_brands_equipment.html', context)

@login_required
@admin_required
def new_brand_equipment(request):     
    context = {
        'formmarcamaquinaria': FormMarcaEquipo, 
        'sidebarsubmenu': 'manage_brandequipment',
        'sidebarmenu': 'manage_equipment',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/equipment/new_brand_equipment.html', context)

@login_required
@admin_required
def save_new_brand_equipment(request):     
    if request.method == 'POST':
        tipo = TipoEquipo.objects.get(id=request.POST['tipo'])
        formulario = FormMarcaEquipo(data=request.POST)
        if formulario.is_valid():       
            marca = MarcaEquipo(
                tipo = tipo,
                marca = request.POST['marca'],
                status = True,
                creador = request.user.first_name+" "+request.user.last_name,
            )
            marca.save()
            notificacion_mantenedor_email(request,marca,'Marca Equipo','creada')
            return JsonResponse({'success': True})
    else:
        return redirect('new_brand_equipment')

@login_required
@admin_required
def status_brand_equipment(request):
    if request.method == 'POST': 
        marca = MarcaEquipo.objects.get(id=request.POST['id'])
        if (marca.status): 
            MarcaEquipo.objects.filter(id=request.POST['id']).update(status=False)
            notificacion_mantenedor_email(request,marca,'Marca de  equipo','deshabilitada')
            messages.success(request, 'Marca de Equipo Deshabilitada Correctamente')  
        else:
            MarcaEquipo.objects.filter(id=request.POST['id']).update(status=True)
            notificacion_mantenedor_email(request,marca,'Marca de equipo','habilitada')
            messages.success(request, 'Marca de Equipo Habilitada Correctamente') 
        return redirect('manage_brands_equipment')
    else:
        messages.error(request, 'Error al Deshabilitar') 
        return redirect('manage_brands_equipment')

@login_required
@admin_required
def manage_equipments(request): 
    storage = messages.get_messages(request)
    storage.used = True
    equipos = list(NuevoEquipamiento.objects.all().order_by('id'))   
    context = {
        'equipos': equipos,
        'sidebar': 'manage_equipments',
        'sidebarmain': 'system_equipments', 
    }
    return render(request,'pages/equipment/manage_equipment.html', context)

@login_required
@admin_required
def new_equipment(request):     
    context = {
        'formnuevoequipo': FormNuevoEquipamiento, 
        'sidebar': 'manage_equipments',
        'sidebarmain': 'system_equipments', 
    }
    return render(request,'pages/equipment/new_equipment.html', context)

@login_required
@admin_required
def save_new_equipment(request):     
    if request.method == 'POST':
        marca = MarcaEquipo.objects.get(id=request.POST['marca'])
        tipo = TipoEquipo.objects.get(id=request.POST['tipo'])
        faena = Faena.objects.get(id=request.POST['faena'])
        formulario = FormNuevoEquipamiento(data=request.POST)
        if formulario.is_valid():       
            equipo = NuevoEquipamiento(
                tipo = tipo,
                marca = marca,
                faena = faena,
                area = request.POST['area'],
                ultimaMantencion = request.POST['ultimaMantencion'],
                frecuencia = request.POST['frecuencia'],
                proximaMantencion = request.POST['proximaMantencion'],
                notasAdicionales = request.POST['notasAdicionales'],
                status = True,
                creador = request.user.first_name+" "+request.user.last_name,
            )
            equipo.save()
            notificacion_mantenedor_email(request,equipo,'Equipo','creado')
            return JsonResponse({'success': True})
    else:
        return redirect('new_equipment')

@login_required
@admin_required
def status_equipment(request):
    if request.method == 'POST': 
        equipo = NuevoEquipamiento.objects.get(id=request.POST['id'])
        if (equipo.status): 
            NuevoEquipamiento.objects.filter(id=request.POST['id']).update(status=False) 
            notificacion_mantenedor_email(request,equipo,'Equipo','deshabilitado')
            messages.success(request, 'Equipo Deshabilitado Correctamente')  
        else:
            NuevoEquipamiento.objects.filter(id=request.POST['id']).update(status=True)
            notificacion_mantenedor_email(request,equipo,'Equipo','habilitado')
            messages.success(request, 'Equipo Habilitado Correctamente') 
        return redirect('manage_equipments')
    else:
        messages.error(request, 'Error al Deshabilitar') 
        return redirect('manage_equipments')
    
@login_required
@admin_required
def edit_equipment(request):  
    try:
        request.session['edit_equipo_id'] = request.POST['equipo_id']            
    except MultiValueDictKeyError:
        request.session['edit_equipo_id'] = request.session['edit_equipo_id']
    equipo = NuevoEquipamiento.objects.get(id=request.session['edit_equipo_id'])
    ultimaFecha = formatear_fecha(equipo.ultimaMantencion)
    proximaFecha = formatear_fecha(equipo.proximaMantencion)

    context = {
        'formequipo':  FormNuevoEquipamiento(initial={
            'tipo': equipo.tipo,
            'marca': equipo.marca,
            'faena': equipo.faena,
            'area': equipo.area,
            'ultimaMantencion': ultimaFecha,
            'frecuencia': equipo.frecuencia,
            'proximaMantencion': proximaFecha,
            'notasAdicionales': equipo.notasAdicionales,
            },
            marca_disabled = True,
            tipo_disabled = True,
        ),
        'equipo_id': equipo.id,
    }
    return render(request,'pages/equipment/edit_equipment.html', context)

@login_required
@admin_required
def save_edit_equipment(request):     
    if request.method == 'POST':
        equipo = NuevoEquipamiento.objects.filter(id=request.POST['equipo_id'])
        faena = Faena.objects.get(id=request.POST['faena'])
        area = request.POST['area']
        ultimaMantencion = request.POST['ultimaMantencion']
        frecuencia = request.POST['frecuencia']
        proximaMantencion = request.POST['proximaMantencion']
        notasAdicionales = request.POST['notasAdicionales']
        NuevoEquipamiento.objects.filter(id=request.POST['equipo_id']).update(faena=faena)
        NuevoEquipamiento.objects.filter(id=request.POST['equipo_id']).update(area=area)
        NuevoEquipamiento.objects.filter(id=request.POST['equipo_id']).update(ultimaMantencion=ultimaMantencion)
        NuevoEquipamiento.objects.filter(id=request.POST['equipo_id']).update(frecuencia=frecuencia)
        NuevoEquipamiento.objects.filter(id=request.POST['equipo_id']).update(proximaMantencion=proximaMantencion)
        NuevoEquipamiento.objects.filter(id=request.POST['equipo_id']).update(notasAdicionales=notasAdicionales)
        notificacion_mantenedor_email(request,equipo,'Equipo','actualizado')
        return JsonResponse({'success': True})
    else:
        return redirect('edit_equipment')

def cargar_marcas_por_tipo(request):
    tipo_id = request.GET.get('tipo_id')
    if tipo_id:
        marcas = MarcaEquipo.objects.filter(tipo=tipo_id,status=True)
        data = [{'id': marca.id, 'nombre': marca.marca} for marca in marcas]
        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({}, status=400)
    
