import os
from django.conf import settings
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import (Genero, Ciudad, Nacionalidad, Ano, Marca, Modelo, Color, Tipo, Faena, TipoDocumentoFaena, EmpresaServicios, 
                    EmpresaTipoServicios, TipoFallaVehiculo, OcultarOpcionesVehiculo, CategoriaFallaVehiculo, TipoDocumentoFaenaGeneral,
                    TipoMaquinaria, MarcaMaquinaria, KitsMaquinaria, FallaMaquinaria, FechasImportantes, ReporteError, AyudaManuales,
                    Sondas, Sondajes, Diametros, TipoTerreno, Orientacion, DetalleControlHorario, Corona, Escareador, CantidadAgua,
                    Aditivos, Casing, Zapata, LargoBarra, Recomendacion, Perforistas, MaterialesSonda, MaterialesCaseta, Campana, Programa,
                    RecomendacionAjuste, RecomendacionFinal)
from .forms import (FormGenero, FormCiudad, FormNacionalidad, FormAno, FormMarca, FormModelo, FormColor,FormTipo, FormNuevaFaena, 
                    FormTipoDocumentoFaena, FormNuevaEmpresaServicios, FormEmpresaTipoServicios, FormTipoFallaVehiculo, 
                    FormOcultarOpcionesVehiculoAdicional, FormOcultarOpcionesVehiculoTecnica, FormOcultarOpcionesVehiculoDocumentacion, 
                    FormNuevaFechasImportantes, FormOcultarOpcionesVehiculoInterior, FormOcultarOpcionesVehiculoExterior, FormCategoriaFallaVehiculo, 
                    FormTipoDocumentoFaenaGeneral, FormTipoMaquinaria, FormMarcaMaquinaria, FormKitReparacion, FormFallaMaquinaria, 
                    FormMarcaMaquinariaSelect, FormReporteError, FormAyudaManuales, FormSeleccionSeccion, FormCampana, FormPrograma,
                    FormSondas, FormSondajes, FormDiametros, FormTipoTerreno, FormOrientacion, FormDetalleControlHorario, FormCorona, FormEscareador,
                    FormCantidadAgua, FormAditivos, FormCasing, FormZapata, FormLargoBarra, FormRecomendaciones, FormPerforista, 
                    FormMaterialesSonda, FormMaterialesCaseta, FormRecomendacionesAjuste, FormRecomendacionesFinal)
from user.models import UsuarioProfile, LicenciasUsuario, User
from vehicle.models import Vehiculo, NuevoKilometraje
from machine.models import Maquinaria, NuevoHorometro, KitsMaquinariaFaena
from maintenance.models import NuevaSolicitudMantenimiento
from django.utils import timezone
from django.utils.datastructures import MultiValueDictKeyError
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Count, OuterRef, Subquery, Q, F, IntegerField, ExpressionWrapper, Sum
from mining.models import VehiculoAsignado
import json
from django.shortcuts import get_object_or_404
from core.utils import procesar_fotografia_dos, ordenar_por_mes_inicial
from datetime import datetime
from messenger.views import notificacion_mantenedor_email, notificacion_admin_jefe_mantencion_email
from .decorators import sondaje_admin_or_base_datos_or_supervisor_required, admin_required
from core.utils import formatear_fecha
from django.utils.timezone import make_aware
from mining.models import VehiculoAsignado
from machine.models import Maquinaria
from equipment.models import NuevoEquipamiento

@login_required
def select(request):
    user = UsuarioProfile.objects.get(user=request.user)
    if user.seccionVehicular == 'Si' and user.seccionSondaje == 'No' and user.seccionPrevencion == 'No': 
        request.session['seccion'] = 'vehicular'
        return redirect('dashboard')
    if user.seccionSondaje == 'Si' and user.seccionVehicular == 'No' and user.seccionPrevencion == 'No':
        request.session['seccion'] = 'sondaje'
        return redirect('dashboardSondaje')
    if user.seccionPrevencion == 'Si' and user.seccionVehicular == 'No' and user.seccionSondaje == 'No':
        request.session['seccion'] = 'prevencion'
        return redirect('dashboardPrevencion')
    if user.seccionInventario == 'Si' and user.seccionInventario == 'No' and user.seccionSondaje == 'No':
        request.session['seccion'] = 'inventario'
        return redirect('dashboardInventario')
    if user.seccionPrevencion == 'No' and user.seccionVehicular == 'No' and user.seccionSondaje == 'No':
        context = {
            'mensajeuno': "Sin secciones asignadas",
            'mensajedos': "Contacte al Administrador",
            'valor': False,
        }
        return render(request, 'main/select.html', context)
    context = {
        'valor': True,
        'usuario': user,
        'formseleccionar': FormSeleccionSeccion(usuario_profile=user),
    }
    return render(request, 'main/select.html', context)

@login_required
def selectOption(request):
    if request.method == 'POST':
        if request.POST['seccion_select'] == 'vehicular':
            request.session['seccion'] = 'vehicular'
            return redirect('dashboard')
        if request.POST['seccion_select'] == 'sondaje':
            request.session['seccion'] = 'sondaje'
            return redirect('dashboardSondaje')
        if request.POST['seccion_select'] == 'prevencion':
            request.session['seccion'] = 'prevencion'
            return redirect('dashboardPrevencion')
        if request.POST['seccion_select'] == 'inventario':
            request.session['seccion'] = 'inventario'
            return redirect('dashboardInventario')
    else:
        return redirect('select')
    
@login_required
def dashboard(request): 
    detalle_tipo_vehiculo = VehiculoAsignado.objects.filter(status=True, vehiculo__status=True).values('faena__faena', 'vehiculo__tipo__tipo').annotate(cantidad=Count('vehiculo__tipo__tipo'))
    detalle_por_faena = {}
    for item in detalle_tipo_vehiculo:
        nombre_faena = item['faena__faena']
        tipo_vehiculo = item['vehiculo__tipo__tipo']
        cantidad_vehiculos = item['cantidad']
        
        if nombre_faena not in detalle_por_faena:
            detalle_por_faena[nombre_faena] = {
                'cantidad_total_vehiculos': 0,
                'detalle_por_tipo': {}
            }
        
        detalle_por_faena[nombre_faena]['cantidad_total_vehiculos'] += cantidad_vehiculos
        
        if tipo_vehiculo not in detalle_por_faena[nombre_faena]['detalle_por_tipo']:
            detalle_por_faena[nombre_faena]['detalle_por_tipo'][tipo_vehiculo] = 0
        
        detalle_por_faena[nombre_faena]['detalle_por_tipo'][tipo_vehiculo] += cantidad_vehiculos
        
    if 'SIN ASIGNAR' in detalle_por_faena:
        sin_asignar = detalle_por_faena.pop('SIN ASIGNAR')
        detalle_por_faena = {'SIN ASIGNAR': sin_asignar, **detalle_por_faena}

    detalle_por_faena_json = json.dumps(detalle_por_faena, indent=4)
    detalle_por_faena_dict = json.loads(detalle_por_faena_json)
    
    vehiculos = Vehiculo.objects.all()
    data_vehiculos = []
    for vehiculo in vehiculos:
        diferencias = vehiculo.calculate_days_difference()        
        for fecha_tipo, detalles in diferencias.items():
            if detalles['dias_diferencia'] < 120:
                data_vehiculos.append({
                    'placaPatente': vehiculo.placaPatente,
                    'tipo_fecha': fecha_tipo,
                    'dias_diferencia': detalles['dias_diferencia'],
                    'fecha_vencimiento': detalles['fecha_vencimiento'],
                    'tipo_vehiculo': vehiculo.tipo.tipo
                })
    # Ordenar los datos por 'dias_diferencia' en orden ascendente
    data_vehiculos.sort(key=lambda x: x['dias_diferencia'])

    today = timezone.now().date()
    data_arriendo = []
    # Recopilar datos y calcular diferencias de días
    for vehiculo in vehiculos:
        vehiculo_faena = VehiculoAsignado.objects.get(status=True, vehiculo=vehiculo)
        if vehiculo.fechaArriendoFinal:
            dias_diferencia = (vehiculo.fechaArriendoFinal.date() - today).days
            if dias_diferencia < 120:
                data_arriendo.append({
                    'placaPatente': vehiculo.placaPatente,
                    'dias_diferencia': dias_diferencia,
                    'fecha_arriendo_inicial': vehiculo.fechaArriendoInicial,
                    'fecha_arriendo_final': vehiculo.fechaArriendoFinal,
                    'tipo_vehiculo': vehiculo.tipo.tipo,
                    'faena': vehiculo_faena.faena,
                })

    # Ordenar los datos por 'dias_diferencia' en orden ascendente
    data_arriendo.sort(key=lambda x: x['dias_diferencia'])    
    
    usuarios_profiles = UsuarioProfile.objects.select_related('user').all().exclude(user_id=2)
    licencias_usuarios = LicenciasUsuario.objects.select_related('user').all().exclude(user_id=2)
    data_usuarios = []
    # Recopilar datos y calcular diferencias de días
    for profile in usuarios_profiles:
        fechas = {
            'Cédula Identidad (Vencimiento)': profile.fechaCedulaVencimiento,
        }
        for fecha_tipo, fecha_vencimiento in fechas.items():
            if fecha_vencimiento:
                dias_diferencia = (fecha_vencimiento.date() - today).days
                if dias_diferencia < 120:
                    data_usuarios.append({
                        'username': profile.user.username,
                        'first_name': profile.user.first_name,
                        'last_name': profile.user.last_name,
                        'faena': profile.faena.faena,
                        'tipo_fecha': fecha_tipo,
                        'dias_diferencia': dias_diferencia,
                        'fecha_vencimiento': fecha_vencimiento,
                    })
    
    for licencia in licencias_usuarios:
        usuario_profile = UsuarioProfile.objects.select_related('faena').filter(user=licencia.user).first()
        fechas = {
            'Licencia Conducir (Vencimiento)': licencia.fechaLicenciaVencimiento,
            'Licencia Interna (Vencimiento)': licencia.fechaLicenciaInternaVencimiento,
        }
        for fecha_tipo, fecha_vencimiento in fechas.items():
            if fecha_vencimiento:
                dias_diferencia = (fecha_vencimiento.date() - today).days
                if dias_diferencia < 120:
                    data_usuarios.append({
                        'username': licencia.user.username,
                        'first_name': licencia.user.first_name,
                        'last_name': licencia.user.last_name,
                        'faena': usuario_profile.faena.faena if usuario_profile and usuario_profile.faena else 'SIN ASIGNAR',
                        'tipo_fecha': fecha_tipo,
                        'dias_diferencia': dias_diferencia,
                        'fecha_vencimiento': fecha_vencimiento,
                    })
    # Ordenar los datos por 'dias_diferencia' en orden ascendente
    data_usuarios.sort(key=lambda x: x['dias_diferencia'])
    
    last_users = User.objects.all().exclude(username__in=['cconelli', '15.053.475-5']).order_by('-last_login')[:5]

    # Subconsulta para obtener el último registro de cada vehículo
    latest_kilometraje = NuevoKilometraje.objects.filter(
        vehiculo=OuterRef('vehiculo')
    ).order_by('-fechacreacion')

    # Consulta principal usando select_related para optimizar la relación ForeignKey
    ultimo_kilometraje_por_vehiculo = NuevoKilometraje.objects.filter(
        id=Subquery(latest_kilometraje.values('id')[:1])
    ).select_related('vehiculo')

    # Anotar los campos adicionales de InformacionTecnicaVehiculo
    ultimo_kilometraje_por_vehiculo = ultimo_kilometraje_por_vehiculo.annotate(
        frecuenciaMantenimiento=F('vehiculo__informaciontecnicavehiculo__frecuenciaMantenimiento'),
        proximoMantenimiento=F('vehiculo__informaciontecnicavehiculo__proximoMantenimiento'),
        proximoMantenimientoGrua=F('vehiculo__informaciontecnicavehiculo__proximoMantenimientoGrua'),
        kilometrosRestantes=F('vehiculo__informaciontecnicavehiculo__proximoMantenimiento') - F('kilometraje')
    ).order_by('kilometrosRestantes')
    
    # Subconsulta para obtener el último registro de cada maquinaria
    latest_horometro = NuevoHorometro.objects.filter(
        maquinaria=OuterRef('maquinaria')
    ).order_by('-fechacreacion')

    # Subconsulta para obtener el horometro cuando origen es "Mantención mayor"
    mantencion_mayor_horometro = NuevoHorometro.objects.filter(
        maquinaria=OuterRef('maquinaria'),
        origen='Mantención mayor'
    ).order_by('-fechacreacion').values('horometro')[:1]

    # Consulta principal usando select_related para optimizar la relación ForeignKey
    ultimo_horometro_por_maquinaria = NuevoHorometro.objects.filter(
        id=Subquery(latest_horometro.values('id')[:1])
    ).select_related('maquinaria')

    # Anotar el campo adicional de mantencionMayor y proximoMantenimientoMayor
    ultimo_horometro_por_maquinaria = ultimo_horometro_por_maquinaria.annotate(
        mantencionMayor=Subquery(mantencion_mayor_horometro),
        proximoMantenimientoMayor=ExpressionWrapper(F('maquinaria__frecuenciaMantenimiento') + Subquery(mantencion_mayor_horometro), output_field=IntegerField()),
        horasRestantes= ExpressionWrapper(F('proximoMantenimientoMayor') - F('horometro'), output_field=IntegerField()),
    )
    #ordenar fechas importantes
    mes_inicial = datetime.now().month
    fechas_importantes_ordenadas = ordenar_por_mes_inicial(mes_inicial)
    
    # Realiza la consulta con los filtros y ordenamiento
    data_solicitudes = NuevaSolicitudMantenimiento.objects.filter(status=True).exclude(Q(progreso='4') | Q(progreso='5')).order_by('-fechacreacion')

    request.session['seccion'] = 'vehicular'
    context = {
        'detalle_por_faena_json': detalle_por_faena_dict,
        'sidebar': 'dashboard',
        'fechavencimientodocumentacionvehiculos': data_vehiculos,
        'fechavencimientoarriendovehiculos': data_arriendo,
        'fechavencimientodocumentacionusuarios': data_usuarios,
        'last_users': last_users,
        'ultimo_kilometraje_por_vehiculo': ultimo_kilometraje_por_vehiculo,
        'ultimo_horometro_por_maquinaria': ultimo_horometro_por_maquinaria,
        'fechas_importantes': fechas_importantes_ordenadas,
        'mantenimientos_vehiculos': data_solicitudes,
    }
    return render(request,'main/homevehicular.html', context)

@login_required
def dashboardSondaje(request):
    request.session['seccion'] = 'sondaje'
    context = {
        'seccion': 'sondaje',
        'sidebar': 'dashboardSondaje',
    }
    return render(request, 'main/homesondaje.html', context)

@login_required
def dashboardPrevencion(request):
    request.session['seccion'] = 'prevencion'
    context = {
        'seccion': 'prevencion',
        'sidebar': 'dashboardPrevencion',
    }
    return render(request, 'main/homeprevencion.html', context)

@login_required
def dashboardInventario(request):
    request.session['seccion'] = 'inventario'
    context = {
        'seccion': 'inventario',
        'sidebar': 'dashboardInventario',
    }
    return render(request, 'main/homeinventario.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_genders(request): 
    storage = messages.get_messages(request)
    storage.used = True
    generos = list(Genero.objects.all().order_by('id'))   
    context = {
        'generos': generos,
        'sidebarsubmenu': 'manage_genders',
        'sidebarmenu': 'manage_users',
        'sidebarmain': 'manage_system',
    }
    return render(request,'pages/maintainer/manage_genders.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_gender(request):     
    context = {
        'formgenero': FormGenero, 
        'sidebarsubmenu': 'manage_genders',
        'sidebarmenu': 'manage_users',
        'sidebarmain': 'manage_system',        
    }
    return render(request,'pages/maintainer/new_gender.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_new_gender(request):     
    if request.method == 'POST':
        formulario = FormGenero(data=request.POST)
        if formulario.is_valid():       
            genero = Genero(
                genero = request.POST['genero'],
                status = True,
                creador = request.user.first_name+" "+request.user.last_name,
            )
            genero.save()
            notificacion_mantenedor_email(request,genero,'Generos','creado')  
            return JsonResponse({'success': True})
    else:
        return redirect('new_gender')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def status_gender(request):
    if request.method == 'POST': 
        genero = Genero.objects.get(id=request.POST['id'])
        if (genero.status): 
            Genero.objects.filter(id=request.POST['id']).update(status=False)
            notificacion_mantenedor_email(request,genero,'Generos','deshabilitado')  
            messages.success(request, 'Genero Deshabilitado Correctamente')  
        else:
            Genero.objects.filter(id=request.POST['id']).update(status=True)
            notificacion_mantenedor_email(request,genero,'Generos','habilitado')
            messages.success(request, 'Genero Habilitado Correctamente') 
        return redirect('manage_genders') 

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_cities(request): 
    storage = messages.get_messages(request)
    storage.used = True
    ciudades = list(Ciudad.objects.all().order_by('id'))   
    context = {
        'ciudades': ciudades,
        'sidebarsubmenu': 'manage_cities',
        'sidebarmenu': 'manage_users',
        'sidebarmain': 'manage_system',  
    }
    return render(request,'pages/maintainer/manage_cities.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_city(request):     
    context = {
        'formciudad': FormCiudad, 
        'sidebarsubmenu': 'manage_cities',
        'sidebarmenu': 'manage_users',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/new_city.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_new_city(request):     
    if request.method == 'POST':
        formulario = FormCiudad(data=request.POST)
        if formulario.is_valid():       
            ciudad = Ciudad(
                ciudad = request.POST['ciudad'],
                status = True,
                creador = request.user.first_name+" "+request.user.last_name,
            )
            ciudad.save()
            notificacion_mantenedor_email(request,ciudad,'Ciudades','creada')         
            return JsonResponse({'success': True})
    else:
        return redirect('new_city')

@login_required 
@sondaje_admin_or_base_datos_or_supervisor_required
def status_city(request):
    if request.method == 'POST': 
        ciudad = Ciudad.objects.get(id=request.POST['id'])
        if (ciudad.status): 
            Ciudad.objects.filter(id=request.POST['id']).update(status=False)
            notificacion_mantenedor_email(request,ciudad,'Ciudades','deshabilitada')  
            messages.success(request, 'Ciudad Deshabilitado Correctamente')  
        else:
            Ciudad.objects.filter(id=request.POST['id']).update(status=True)
            notificacion_mantenedor_email(request,ciudad,'Ciudades','habilitada')  
            messages.success(request, 'Ciudad Habilitado Correctamente') 
        return redirect('manage_cities') 

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_nationalities(request): 
    storage = messages.get_messages(request)
    storage.used = True
    nacionalidades = list(Nacionalidad.objects.all().order_by('id'))   
    context = {
        'nacionalidades': nacionalidades,
        'sidebarsubmenu': 'manage_nationalities',
        'sidebarmenu': 'manage_users',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/manage_nationalities.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_nationality(request):     
    context = {
        'formnacionalidad': FormNacionalidad, 
        'sidebarsubmenu': 'manage_nationalities',
        'sidebarmenu': 'manage_users',
        'sidebarmain': 'manage_system',         
    }
    return render(request,'pages/maintainer/new_nationality.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_new_nationality(request):     
    if request.method == 'POST':
        formulario = FormNacionalidad(data=request.POST)
        if formulario.is_valid():       
            nacionalidad = Nacionalidad(
                nacionalidad = request.POST['nacionalidad'],
                status = True,
                creador = request.user.first_name+" "+request.user.last_name,
            )
            nacionalidad.save()
            notificacion_mantenedor_email(request,nacionalidad,'Nacionalidades','creada')             
            return JsonResponse({'success': True})
    else:
        return redirect('new_nationality')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def status_nationality(request):
    if request.method == 'POST': 
        nacionalidad = Nacionalidad.objects.get(id=request.POST['id'])
        if (nacionalidad.status): 
            Nacionalidad.objects.filter(id=request.POST['id']).update(status=False)
            notificacion_mantenedor_email(request,nacionalidad,'Nacionalidades','deshabilitada')   
            messages.success(request, 'Nacionalidad Deshabilitado Correctamente')  
        else:
            Nacionalidad.objects.filter(id=request.POST['id']).update(status=True)
            notificacion_mantenedor_email(request,nacionalidad,'Nacionalidades','habilitada')   
            messages.success(request, 'Nacionalidad Habilitado Correctamente') 
        return redirect('manage_nationalities') 

@login_required
@admin_required
def manage_years(request): 
    storage = messages.get_messages(request)
    storage.used = True
    anos = list(Ano.objects.all().order_by('id'))   
    context = {
        'anos': anos,
        'sidebarsubmenu': 'manage_years',
        'sidebarmenu': 'manage_vehicles',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/manage_years.html', context)

@login_required
@admin_required
def new_year(request):     
    context = {
        'formano': FormAno,
        'sidebarsubmenu': 'manage_years',
        'sidebarmenu': 'manage_vehicles',
        'sidebarmain': 'manage_system',  
    }
    return render(request,'pages/maintainer/new_year.html', context)

@login_required
@admin_required
def save_new_year(request):     
    if request.method == 'POST':
        formulario = FormAno(data=request.POST)
        if formulario.is_valid():       
            ano = Ano(
                ano = request.POST['ano'],
                status = True,
                creador = request.user.first_name+" "+request.user.last_name,
            )
            ano.save()
            notificacion_mantenedor_email(request,ano,'Años','creado')            
            return JsonResponse({'success': True})
    else:
        return redirect('new_year')

@login_required
@admin_required
def status_year(request):
    if request.method == 'POST': 
        ano = Ano.objects.get(id=request.POST['id'])
        if (ano.status): 
            Ano.objects.filter(id=request.POST['id']).update(status=False)
            notificacion_mantenedor_email(request,ano,'Años','deshabilitado')  
            messages.success(request, 'Año Deshabilitado Correctamente')  
        else:
            Ano.objects.filter(id=request.POST['id']).update(status=True)
            notificacion_mantenedor_email(request,ano,'Años','habilitado')  
            messages.success(request, 'Año Habilitado Correctamente') 
        return redirect('manage_years') 

@login_required
@admin_required
def manage_brands(request): 
    storage = messages.get_messages(request)
    storage.used = True
    marcas = list(Marca.objects.all().order_by('id'))   
    context = {
        'marcas': marcas,
        'sidebarsubmenu': 'manage_brands',
        'sidebarmenu': 'manage_vehicles',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/manage_brands.html', context)

@login_required
@admin_required
def new_brand(request):     
    context = {
        'formmarca': FormMarca, 
        'sidebarsubmenu': 'manage_brands',
        'sidebarmenu': 'manage_vehicles',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/new_brand.html', context)

@login_required
@admin_required
def save_new_brand(request):     
    if request.method == 'POST':
        formulario = FormMarca(data=request.POST)
        if formulario.is_valid():       
            marca = Marca(
                marca = request.POST['marca'],
                status = True,
                creador = request.user.first_name+" "+request.user.last_name,
            )
            marca.save()
            notificacion_mantenedor_email(request,marca,'Marcas de vehículos','creada')
            return JsonResponse({'success': True})
    else:
        return redirect('new_brand')

@login_required
@admin_required
def status_brand(request):
    if request.method == 'POST': 
        marca = Marca.objects.get(id=request.POST['id'])
        if (marca.status): 
            Marca.objects.filter(id=request.POST['id']).update(status=False)
            notificacion_mantenedor_email(request,marca,'Marcas de vehículos','deshabilitada')
            messages.success(request, 'Marca Deshabilitada Correctamente')  
        else:
            Marca.objects.filter(id=request.POST['id']).update(status=True)
            notificacion_mantenedor_email(request,marca,'Marcas de vehículos','habilitada')
            messages.success(request, 'Marca Habilitada Correctamente') 
        return redirect('manage_brands') 

@login_required
@admin_required
def manage_models(request): 
    storage = messages.get_messages(request)
    storage.used = True
    modelos = list(Modelo.objects.all().order_by('id'))   
    context = {
        'modelos': modelos,
        'sidebarsubmenu': 'manage_models',
        'sidebarmenu': 'manage_vehicles',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/manage_models.html', context)

@login_required
@admin_required
def new_model(request):     
    context = {
        'formmodelo': FormModelo, 
        'sidebarsubmenu': 'manage_models',
        'sidebarmenu': 'manage_vehicles',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/new_model.html', context)

@login_required
@admin_required
def save_new_model(request):     
    if request.method == 'POST':
        formulario = FormModelo(data=request.POST)
        if formulario.is_valid():       
            modelo = Modelo(
                modelo = request.POST['modelo'],
                status = True,
                creador = request.user.first_name+" "+request.user.last_name,
            )
            modelo.save()
            notificacion_mantenedor_email(request,modelo,'Modelos de vehículos','creado')
            return JsonResponse({'success': True})
    else:
        return redirect('new_model')

@login_required
@admin_required
def status_model(request):
    if request.method == 'POST': 
        modelo = Modelo.objects.get(id=request.POST['id'])
        if (modelo.status): 
            Modelo.objects.filter(id=request.POST['id']).update(status=False)
            notificacion_mantenedor_email(request,modelo,'Modelos de vehículos','deshabilitado')
            messages.success(request, 'Modelo Deshabilitado Correctamente')  
        else:
            Modelo.objects.filter(id=request.POST['id']).update(status=True)
            notificacion_mantenedor_email(request,modelo,'Modelos de vehículos','habilitado')
            messages.success(request, 'Modelo Habilitado Correctamente') 
        return redirect('manage_models') 

@login_required
@admin_required
def manage_colours(request): 
    storage = messages.get_messages(request)
    storage.used = True
    colores = list(Color.objects.all().order_by('id'))   
    context = {
        'colores': colores,
        'sidebarsubmenu': 'manage_colours',
        'sidebarmenu': 'manage_vehicles',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/manage_colours.html', context)

@login_required
@admin_required
def new_colour(request):     
    context = {
        'formcolor': FormColor, 
        'sidebarsubmenu': 'manage_colours',
        'sidebarmenu': 'manage_vehicles',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/new_colour.html', context)

@login_required
@admin_required
def save_new_colour(request):     
    if request.method == 'POST':
        formulario = FormColor(data=request.POST)
        if formulario.is_valid():       
            color = Color(
                color = request.POST['color'],
                status = True,
                creador = request.user.first_name+" "+request.user.last_name,
            )
            color.save()
            notificacion_mantenedor_email(request,color,'Colores de vehículos','creado')
            return JsonResponse({'success': True})
    else:
        return redirect('new_colour')

@login_required
@admin_required
def status_colour(request):
    if request.method == 'POST': 
        color = Color.objects.get(id=request.POST['id'])
        if (color.status): 
            Color.objects.filter(id=request.POST['id']).update(status=False)
            notificacion_mantenedor_email(request,color,'Colores de vehículos','deshabilitado')
            messages.success(request, 'Color Deshabilitado Correctamente')  
        else:
            Color.objects.filter(id=request.POST['id']).update(status=True)
            notificacion_mantenedor_email(request,color,'Colores de vehículos','habilitado')
            messages.success(request, 'Color Habilitado Correctamente') 
        return redirect('manage_colours') 
    
@login_required
@admin_required
def manage_types(request): 
    storage = messages.get_messages(request)
    storage.used = True
    tipos = list(Tipo.objects.all().order_by('id'))   
    context = {
        'tipos': tipos,
        'sidebarsubmenu': 'manage_types',
        'sidebarmenu': 'manage_vehicles',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/manage_types.html', context)

@login_required
@admin_required
def new_type(request):     
    context = {
        'formtipo': FormTipo, 
        'sidebarsubmenu': 'manage_types',
        'sidebarmenu': 'manage_vehicles',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/new_type.html', context)

@login_required
@admin_required
def save_new_type(request):     
    if request.method == 'POST':
        formulario = FormTipo(data=request.POST)
        if formulario.is_valid():       
            tipo = Tipo(
                tipo = request.POST['tipo'],
                status = True,
                creador = request.user.first_name+" "+request.user.last_name,
            )
            tipo.save()
            notificacion_mantenedor_email(request,tipo,'Tipos de vehículos','creado')
            return JsonResponse({'success': True})
    else:
        return redirect('new_type')

@login_required
@admin_required
def status_type(request):
    if request.method == 'POST': 
        tipo = Tipo.objects.get(id=request.POST['id'])
        if (tipo.status): 
            Tipo.objects.filter(id=request.POST['id']).update(status=False)
            notificacion_mantenedor_email(request,tipo,'Tipos de vehículos','deshabilitado')
            messages.success(request, 'Tipo de vehículo Deshabilitado Correctamente')  
        else:
            Tipo.objects.filter(id=request.POST['id']).update(status=True)
            notificacion_mantenedor_email(request,tipo,'Tipos de vehículos','habilitado')
            messages.success(request, 'Tipo de vehículo Habilitado Correctamente') 
        return redirect('manage_types')

@login_required
@admin_required
def edit_type(request):  
    try:
        request.session['edit_tipo_id'] = request.POST['tipo_id']            
    except MultiValueDictKeyError:
        request.session['edit_tipo_id'] = request.session['edit_tipo_id']
    tipo = Tipo.objects.get(id=request.session['edit_tipo_id'])
    opciones = OcultarOpcionesVehiculo.objects.get(tipo_vehiculo=tipo.tipo)
    formocultaropcionesadicional = FormOcultarOpcionesVehiculoAdicional(instance=opciones)
    formocultaropcionestecnica = FormOcultarOpcionesVehiculoTecnica(instance=opciones)
    formocultaropcionesdocumentacion = FormOcultarOpcionesVehiculoDocumentacion(instance=opciones)
    formocultaropcionesinterior = FormOcultarOpcionesVehiculoInterior(instance=opciones)
    formocultaropcionesexterior = FormOcultarOpcionesVehiculoExterior(instance=opciones)
    context = {
        'formocultaropcionesadicional': formocultaropcionesadicional,
        'formocultaropcionestecnica': formocultaropcionestecnica,
        'formocultaropcionesdocumentacion': formocultaropcionesdocumentacion,
        'formocultaropcionesinterior': formocultaropcionesinterior,
        'formocultaropcionesexterior': formocultaropcionesexterior,
        'opciones': opciones,  
        'sidebarsubmenu': 'manage_types',
        'sidebarmenu': 'manage_vehicles',
        'sidebarmain': 'manage_system', 
    }
    
    return render(request,'pages/maintainer/edit_type.html', context)

@login_required
@admin_required
def save_edit_type(request):
    if request.method == 'POST':
        instance = get_object_or_404(OcultarOpcionesVehiculo, tipo_vehiculo=request.POST['tipo_vehiculo'])
        
        formadicional = FormOcultarOpcionesVehiculoAdicional(request.POST, instance=instance)
        formtecnica = FormOcultarOpcionesVehiculoTecnica(request.POST, instance=instance)
        formdocumentacion = FormOcultarOpcionesVehiculoDocumentacion(request.POST, instance=instance)
        forminterior = FormOcultarOpcionesVehiculoInterior(request.POST, instance=instance)
        formexterior = FormOcultarOpcionesVehiculoExterior(request.POST, instance=instance)
        
        if all([
            formadicional.is_valid(),
            formtecnica.is_valid(),
            formdocumentacion.is_valid(),
            forminterior.is_valid(),
            formexterior.is_valid()
        ]):
            formadicional.save()
            formtecnica.save()
            formdocumentacion.save()
            forminterior.save()
            formexterior.save()
            notificacion_mantenedor_email(request,request.POST['tipo_vehiculo'],'Ocultar opciones de vehículos','actualizada')
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'error': True})
    else:
        return redirect('edit_type')
    
@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_mining(request): 
    storage = messages.get_messages(request)
    storage.used = True
    faenas = list(Faena.objects.all().order_by('id'))   
    context = {
        'faenas': faenas,
        'sidebarsubmenu': 'manage_managemining',
        'sidebarmenu': 'manage_mining',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/manage_mining.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_mining(request):     
    context = {
        'formnuevafaena': FormNuevaFaena, 
        'sidebarsubmenu': 'manage_managemining',
        'sidebarmenu': 'manage_mining',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/new_mining.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_new_mining(request):     
    if request.method == 'POST':
        formulario = FormNuevaFaena(data=request.POST)
        if formulario.is_valid():       
            faena = Faena(
                faena = request.POST['faena'],
                descripcion = request.POST['descripcion'],
                status = True,
                creador = request.user.first_name+" "+request.user.last_name,
            )
            faena.save()
            notificacion_mantenedor_email(request,faena,'Faena','creada')
            return JsonResponse({'success': True})
    else:
        return redirect('new_mining')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def status_mining(request):
    if request.method == 'POST': 
        try:
            faena = Faena.objects.get(id=request.POST['id'])
            
            # --- VALIDACIÓN DE SEGURIDAD ---
            if (faena.status): 
                # Contamos activos asociados
                vehiculos = VehiculoAsignado.objects.filter(faena=faena, status=True).count()
                maquinarias = Maquinaria.objects.filter(faena=faena, status=True).count()
                equipos = NuevoEquipamiento.objects.filter(faena=faena, status=True).count()

                if vehiculos > 0 or maquinarias > 0 or equipos > 0:
                    detalles = []
                    if vehiculos > 0: detalles.append(f"{vehiculos} Vehículo(s)")
                    if maquinarias > 0: detalles.append(f"{maquinarias} Maquinaria(s)")
                    if equipos > 0: detalles.append(f"{equipos} Equipo(s)")
                    
                    msj = f"No se puede deshabilitar. Tiene asociado: {', '.join(detalles)}."
                    
                    # Retornamos JSON con error lógico (success=False)
                    return JsonResponse({'success': False, 'message': msj})

                # Si pasa, deshabilitamos
                Faena.objects.filter(id=request.POST['id']).update(status=False)
                #notificacion_mantenedor_email(request, faena, 'Faena', 'deshabilitada')
                return JsonResponse({'success': True, 'message': 'Faena Deshabilitada Correctamente'})
            else:
                # Habilitamos
                Faena.objects.filter(id=request.POST['id']).update(status=True)
                #notificacion_mantenedor_email(request, faena, 'Faena', 'habilitada')
                return JsonResponse({'success': True, 'message': 'Faena Habilitada Correctamente'})

        except Exception as e:
            return JsonResponse({'success': False, 'message': 'Error interno del servidor.'})
            
    return JsonResponse({'success': False, 'message': 'Método no permitido'})

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def edit_mining(request):  
    try:
        request.session['edit_faena_id'] = request.POST['faena_id']            
    except MultiValueDictKeyError:
        request.session['edit_faena_id'] = request.session['edit_faena_id']
    faena = Faena.objects.get(id=request.session['edit_faena_id'])
    context = {
        'formeditarfaena':  FormNuevaFaena(initial={
            'faena': faena.faena,
            'descripcion': faena.descripcion,              
            },
            faena_disabled = True,
        ),
        'faena_id': faena.id,  
        'sidebarsubmenu': 'manage_managemining',
        'sidebarmenu': 'manage_mining',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/edit_mining.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_mining(request):     
    if request.method == 'POST':
        faena = Faena.objects.get(id=request.POST['faena_id'])
        Faena.objects.filter(id=request.POST['faena_id']).update(descripcion=request.POST['descripcion'])
        notificacion_mantenedor_email(request,faena,'Faenas','actualizada')
        return JsonResponse({'success': True})
    else:
        return redirect('edit_mining')

@login_required
@admin_required
def manage_mining_documents(request): 
    storage = messages.get_messages(request)
    storage.used = True
    tipo_documentos = list(TipoDocumentoFaena.objects.all().order_by('fechacreacion'))  
    context = {
        'tipo_documentos': tipo_documentos,
        'sidebarsubmenu': 'manage_documentsmining',
        'sidebarmenu': 'manage_mining',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/manage_mining_documents.html', context)

@login_required
@admin_required
def new_mining_document(request):     
    context = {
        'formnuevodocumento': FormTipoDocumentoFaena, 
        'sidebarsubmenu': 'manage_documentsmining',
        'sidebarmenu': 'manage_mining',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/new_mining_document.html', context)

@login_required
@admin_required
def save_new_mining_document(request):
    if request.method == 'POST':
        try: 
            tipo_documento_faena = TipoDocumentoFaena.objects.get(documento=request.POST['documento'],faena=request.POST['faena'])
            return tipo_documento_faena
        except ObjectDoesNotExist:            
            faena = Faena.objects.get(pk=request.POST['faena'])
            formulario = FormTipoDocumentoFaena(data=request.POST)
            if formulario.is_valid():       
                tipo_documento = TipoDocumentoFaena(
                    faena = faena,
                    documento = request.POST['documento'],
                    status = True,
                    creador = request.user.first_name+" "+request.user.last_name,
                )
                tipo_documento.save()
                notificacion_mantenedor_email(request,tipo_documento,'Documentos Vehículos de Faenas','creado')
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        return redirect('manage_mining_documents')

@login_required
@admin_required
def status_mining_document(request):
    if request.method == 'POST': 
        tipo_documento = TipoDocumentoFaena.objects.get(id=request.POST['id'])
        if (tipo_documento.status): 
            TipoDocumentoFaena.objects.filter(id=request.POST['id']).update(status=False)
            notificacion_mantenedor_email(request,tipo_documento,'Documentos Vehículos de Faenas','deshabilitado')
            messages.success(request, 'Documento Deshabilitado Correctamente')  
        else:
            TipoDocumentoFaena.objects.filter(id=request.POST['id']).update(status=True)
            notificacion_mantenedor_email(request,tipo_documento,'Documentos Vehículos de Faenas','habilitado')
            messages.success(request, 'Documento Habilitado Correctamente') 
        return redirect('manage_mining_documents') 

@login_required
@admin_required
def manage_maintenance_companies(request): 
    storage = messages.get_messages(request)
    storage.used = True
    empresas = list(EmpresaServicios.objects.all().order_by('id'))   
    context = {
        'empresas': empresas,
        'sidebarsubmenu': 'manage_newcompanie',
        'sidebarmenu': 'manage_maintenance',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/manage_maintenance_companies.html', context)

@login_required
@admin_required
def new_maintenance_companie(request):     
    context = {
        'formnuevaempresa': FormNuevaEmpresaServicios, 
        'sidebarsubmenu': 'manage_newcompanie',
        'sidebarmenu': 'manage_maintenance',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/new_maintenance_companie.html', context)

@login_required
@admin_required
def save_new_maintenance_companie(request):     
    if request.method == 'POST':
        formulario = FormNuevaEmpresaServicios(data=request.POST)
        if formulario.is_valid():       
            empresa = EmpresaServicios(
                empresa = request.POST['empresa'],
                rut = request.POST['rut'],
                direccion = request.POST['direccion'],
                telefono = request.POST['telefono'],
                descripcion = request.POST['descripcion'],
                status = True,
                creador = request.user.first_name+" "+request.user.last_name,
            )
            empresa.save()
            notificacion_mantenedor_email(request,empresa,'Empresa de mantenimiento','creada')
            return JsonResponse({'success': True})
    else:
        return redirect('new_maintenance_companie')

@login_required
@admin_required
def status_maintenance_companie(request):
    if request.method == 'POST': 
        empresa = EmpresaServicios.objects.get(id=request.POST['id'])
        if (empresa.status): 
            EmpresaServicios.objects.filter(id=request.POST['id']).update(status=False)
            notificacion_mantenedor_email(request,empresa,'Empresa de mantenimiento','deshabilitada')
            messages.success(request, 'Empresa Deshabilitada Correctamente')  
        else:
            EmpresaServicios.objects.filter(id=request.POST['id']).update(status=True)
            notificacion_mantenedor_email(request,empresa,'Empresa de mantenimiento','habilitada')
            messages.success(request, 'Empresa Habilitada Correctamente') 
        return redirect('manage_maintenance_companies') 

@login_required
@admin_required
def edit_maintenance_companie(request):  
    try:
        request.session['edit_empresa_id'] = request.POST['empresa_id']            
    except MultiValueDictKeyError:
        request.session['edit_empresa_id'] = request.session['edit_empresa_id']
    empresa = EmpresaServicios.objects.get(id=request.session['edit_empresa_id'])
    context = {
        'formeditarempresa':  FormNuevaEmpresaServicios(initial={
            'empresa': empresa.empresa,
            'rut': empresa.rut,
            'telefono': empresa.telefono,
            'direccion': empresa.direccion,
            'descripcion': empresa.descripcion,              
            },
            empresa_disabled = True,
            rut_disabled = True,
        ),
        'empresa_id': empresa.id,  
        'sidebarsubmenu': 'manage_newcompanie',
        'sidebarmenu': 'manage_maintenance',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/edit_maintenance_companie.html', context)

@login_required
@admin_required
def save_edit_maintenance_companie(request):     
    if request.method == 'POST':
        empresa = EmpresaServicios.objects.get(id=request.POST['empresa_id'])
        EmpresaServicios.objects.filter(id=request.POST['empresa_id']).update(telefono=request.POST['telefono'])
        EmpresaServicios.objects.filter(id=request.POST['empresa_id']).update(direccion=request.POST['direccion'])
        EmpresaServicios.objects.filter(id=request.POST['empresa_id']).update(descripcion=request.POST['descripcion'])
        notificacion_mantenedor_email(request,empresa,'Empresa de mantenimiento','actualizada')
        return JsonResponse({'success': True})
    else:
        return redirect('edit_maintenance_companie')

@login_required
@admin_required
def manage_maintenance_services(request): 
    storage = messages.get_messages(request)
    storage.used = True
    servicios = list(EmpresaTipoServicios.objects.all().order_by('fechacreacion'))  
    context = {
        'servicios': servicios,
        'sidebarsubmenu': 'manage_maintenanceservices',
        'sidebarmenu': 'manage_maintenance',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/manage_maintenance_services.html', context)

@login_required
@admin_required
def new_maintenance_service(request):     
    context = {
        'formnuevoservicio': FormEmpresaTipoServicios, 
        'sidebarsubmenu': 'manage_maintenanceservices',
        'sidebarmenu': 'manage_maintenance',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/new_maintenance_service.html', context)

@login_required
@admin_required
def save_new_maintenance_service(request):
    if request.method == 'POST':
        try: 
            tipo_servicio = EmpresaTipoServicios.objects.get(servicio=request.POST['servicio'],empresa=request.POST['empresa'])
            return tipo_servicio
        except ObjectDoesNotExist:            
            empresa = EmpresaServicios.objects.get(pk=request.POST['empresa'])
            formulario = FormEmpresaTipoServicios(data=request.POST)
            if formulario.is_valid():       
                servicio_nuevo = EmpresaTipoServicios(
                    empresa = empresa,
                    servicio = request.POST['servicio'],
                    status = True,
                    creador = request.user.first_name+" "+request.user.last_name,
                )
                servicio_nuevo.save()
                notificacion_mantenedor_email(request,servicio_nuevo,'Servicio de mantenimiento','creado')
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        return redirect('manage_maintenance_services')

@login_required
@admin_required
def status_maintenance_service(request):
    if request.method == 'POST': 
        servicio = EmpresaTipoServicios.objects.get(id=request.POST['id'])
        if (servicio.status): 
            EmpresaTipoServicios.objects.filter(id=request.POST['id']).update(status=False)
            notificacion_mantenedor_email(request,servicio,'Servicio de mantenimiento','deshabilitado')
            messages.success(request, 'Servicio Deshabilitado Correctamente')  
        else:
            EmpresaTipoServicios.objects.filter(id=request.POST['id']).update(status=True)
            notificacion_mantenedor_email(request,servicio,'Servicio de mantenimiento','habilitado')
            messages.success(request, 'Servicio Habilitado Correctamente') 
        return redirect('manage_maintenance_services') 

@login_required
@admin_required
def manage_failures(request): 
    storage = messages.get_messages(request)
    storage.used = True
    fallas = list(TipoFallaVehiculo.objects.all().order_by('id'))   
    context = {
        'fallas': fallas,
        'sidebarsubsubmenu': 'manage_failures',
        'sidebarsubmenu': 'manage_failures',
        'sidebarmenu': 'manage_vehicles',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/manage_failures.html', context)

@login_required
@admin_required
def new_failure(request):     
    context = {
        'formfalla': FormTipoFallaVehiculo,
        'sidebarsubsubmenu': 'manage_failures',
        'sidebarsubmenu': 'manage_failures',
        'sidebarmenu': 'manage_vehicles',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/new_failure.html', context)

@login_required
@admin_required
def save_new_failure(request):     
    if request.method == 'POST':
        formulario = FormTipoFallaVehiculo(data=request.POST)
        categoria = CategoriaFallaVehiculo(pk=request.POST['categoria'])
        if formulario.is_valid():       
            falla = TipoFallaVehiculo(
                categoria = categoria,
                falla = request.POST['falla'],
                status = True,
                creador = request.user.first_name+" "+request.user.last_name,
            )
            falla.save()
            notificacion_mantenedor_email(request,falla,'Falla de vehículo','creada')
            return JsonResponse({'success': True})
    else:
        return redirect('new_failure')

@login_required
@admin_required
def status_failure(request):
    if request.method == 'POST': 
        falla = TipoFallaVehiculo.objects.get(id=request.POST['id'])
        if (falla.status): 
            TipoFallaVehiculo.objects.filter(id=request.POST['id']).update(status=False)
            notificacion_mantenedor_email(request,falla,'Falla de vehículo','deshabilitada')
            messages.success(request, 'Falla de Vehículo Deshabilitado Correctamente')  
        else:
            TipoFallaVehiculo.objects.filter(id=request.POST['id']).update(status=True)
            notificacion_mantenedor_email(request,falla,'Falla de vehículo','habilitada')
            messages.success(request, 'Falla de Vehículo Habilitado Correctamente') 
        return redirect('manage_failures') 

@login_required
@admin_required
def manage_categories_failures(request): 
    storage = messages.get_messages(request)
    storage.used = True
    categorias = list(CategoriaFallaVehiculo.objects.all().order_by('id'))   
    context = {
        'categorias': categorias,
        'sidebarsubsubmenu': 'manage_categories_failures',
        'sidebarsubmenu': 'manage_failures',
        'sidebarmenu': 'manage_vehicles',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/manage_categories_failures.html', context)

@login_required
@admin_required
def new_categories_failure(request):     
    context = {
        'formcategoria': FormCategoriaFallaVehiculo,
        'sidebarsubsubmenu': 'manage_categories_failures',
        'sidebarsubmenu': 'manage_failures',
        'sidebarmenu': 'manage_vehicles',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/new_categorie_failure.html', context)

@login_required
@admin_required
def save_new_categories_failure(request):     
    if request.method == 'POST':
        formulario = FormCategoriaFallaVehiculo(data=request.POST)
        if formulario.is_valid():       
            categoria = CategoriaFallaVehiculo(
                categoria = request.POST['categoria'],
                status = True,
                creador = request.user.first_name+" "+request.user.last_name,
            )
            categoria.save()
            notificacion_mantenedor_email(request,categoria,'Categoría de vehículo','creada')
            return JsonResponse({'success': True})
    else:
        return redirect('new_categories_failure')

@login_required
@admin_required
def status_categories_failure(request):
    if request.method == 'POST': 
        categoria = CategoriaFallaVehiculo.objects.get(id=request.POST['id'])
        if (categoria.status): 
            CategoriaFallaVehiculo.objects.filter(id=request.POST['id']).update(status=False)
            notificacion_mantenedor_email(request,categoria,'Categoría de vehículo','deshabilitada')
            messages.success(request, 'Categoría de Vehículo Deshabilitada Correctamente')  
        else:
            CategoriaFallaVehiculo.objects.filter(id=request.POST['id']).update(status=True)
            notificacion_mantenedor_email(request,categoria,'Categoria de vehículo','habilitada')
            messages.success(request, 'Categoría de Vehículo Habilitada Correctamente') 
        return redirect('manage_categories_failures') 

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_mining_documents_general(request): 
    storage = messages.get_messages(request)
    storage.used = True
    tipo_documentos = list(TipoDocumentoFaenaGeneral.objects.all().order_by('fechacreacion'))  
    context = {
        'tipo_documentos': tipo_documentos,
        'sidebarsubmenu': 'manage_documentsmining_general',
        'sidebarmenu': 'manage_mining',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/manage_mining_documents_general.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_mining_document_general(request):     
    context = {
        'formnuevodocumentogeneral': FormTipoDocumentoFaenaGeneral,
        'sidebarsubmenu': 'manage_documentsmining_general',
        'sidebarmenu': 'manage_mining',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/new_mining_document_general.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_new_mining_document_general(request):
    if request.method == 'POST':
        toggle_archivoDocumento = request.POST.get('toggle-archivoDocumento', 'no')
        archivo = procesar_fotografia_dos(toggle_archivoDocumento, 'archivoDocumento', 'base/no-imagen.png', request)
        try: 
            tipo_documento_faena_general = TipoDocumentoFaenaGeneral.objects.get(nombredocumento=request.POST['nombredocumento'],faena=request.POST['faena'])
            return tipo_documento_faena_general
        except ObjectDoesNotExist:            
            faena = Faena.objects.get(pk=request.POST['faena'])
            formulario = FormTipoDocumentoFaenaGeneral(data=request.POST)
            if formulario.is_valid():       
                tipo_documento_general = TipoDocumentoFaenaGeneral(
                    faena = faena,
                    nombredocumento = request.POST['nombredocumento'],
                    archivodocumento = archivo,
                    status = True,
                    creador = request.user.first_name+" "+request.user.last_name,
                )
                tipo_documento_general.save()
                notificacion_admin_jefe_mantencion_email(request,tipo_documento_general,'Tipo documento general','creado')
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        messages.error(request, 'Error en la Acción')
        return redirect('manage_mining_documents_general')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def status_mining_document_general(request):
    if request.method == 'POST': 
        tipo_documento = TipoDocumentoFaenaGeneral.objects.get(id=request.POST['id'])
        if (tipo_documento.status): 
            TipoDocumentoFaenaGeneral.objects.filter(id=request.POST['id']).update(status=False)
            notificacion_admin_jefe_mantencion_email(request,tipo_documento,'Tipo documento general','deshabilitado')
            messages.success(request, 'Documento Deshabilitado Correctamente')  
        else:
            TipoDocumentoFaenaGeneral.objects.filter(id=request.POST['id']).update(status=True)
            notificacion_admin_jefe_mantencion_email(request,tipo_documento,'Tipo documento general','habilitado')
            messages.success(request, 'Documento Habilitado Correctamente') 
        return redirect('manage_mining_documents_general')
    else:
        messages.error(request, 'Error en la Acción') 
        return redirect('manage_mining_documents_general') 

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def edit_mining_document_general(request):  
    try:
        request.session['edit_document_general_id'] = request.POST['documento_id']            
    except MultiValueDictKeyError:
        request.session['edit_document_general_id'] = request.session['edit_document_general_id']
    documento = TipoDocumentoFaenaGeneral.objects.get(id=request.session['edit_document_general_id'])
    urlDocumento = documento.archivodocumento
    if urlDocumento.url.lower().endswith((".jpg", ".jpeg", ".png")):
        extensionDocumento = "imagen"
    elif urlDocumento.url.lower().endswith((".pdf")):
        extensionDocumento = "pdf"
    else:
        extensionDocumento = "otro"
    context = {
        'formeditardocumento':  FormTipoDocumentoFaenaGeneral(initial={
            'faena': documento.faena,
            'nombredocumento': documento.nombredocumento,
            },
            faena_disabled = True,
            nombredocumento_disabled = True,
        ),
        'documento_id': documento.id,
        'archivodocumento': documento.archivodocumento,
        'extensionDocumento': extensionDocumento,
        'sidebarsubmenu': 'manage_documentsmining_general',
        'sidebarmenu': 'manage_mining',
        'sidebarmain': 'manage_system',  
    }
    return render(request,'pages/maintainer/edit_mining_document_general.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_mining_document_general(request):     
    if request.method == 'POST':
        documento = TipoDocumentoFaenaGeneral.objects.get(id=request.POST['documento_id'])
        toggle_Documento = request.POST.get('toggle-archivoDocumento', 'no')
        archivo = procesar_fotografia_dos(toggle_Documento, 'archivoDocumento','base/no-imagen.png', request)
        documento.archivodocumento = archivo
        documento.save()
        notificacion_admin_jefe_mantencion_email(request,documento,'Tipo documento general','actualizado')
        return JsonResponse({'success': True})
    else:
        return redirect('edit_mining_document_general')

@login_required
@admin_required
def manage_types_machines(request): 
    storage = messages.get_messages(request)
    storage.used = True
    tipos = list(TipoMaquinaria.objects.all().order_by('id'))   
    context = {
        'tiposmaquinas': tipos,
        'sidebarsubmenu': 'manage_managetypemachine',
        'sidebarmenu': 'manage_machine',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/manage_types_machine.html', context)

@login_required
@admin_required
def new_type_machine(request):     
    context = {
        'formnuevotipomaquinaria': FormTipoMaquinaria, 
        'sidebarsubmenu': 'manage_managetypemachine',
        'sidebarmenu': 'manage_machine',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/new_type_machine.html', context)

@login_required
@admin_required
def save_new_type_machine(request):     
    if request.method == 'POST':
        formulario = FormTipoMaquinaria(data=request.POST)
        if formulario.is_valid():       
            tipo = TipoMaquinaria(
                tipo = request.POST['tipo'],
                status = True,
                creador = request.user.first_name+" "+request.user.last_name,
            )
            tipo.save()
            notificacion_mantenedor_email(request,tipo,'Tipo maquinaria','creada')
            return JsonResponse({'success': True})
    else:
        return redirect('new_type_machine')

@login_required
@admin_required
def status_type_machine(request):
    if request.method == 'POST': 
        tipo = TipoMaquinaria.objects.get(id=request.POST['id'])
        if (tipo.status): 
            TipoMaquinaria.objects.filter(id=request.POST['id']).update(status=False)
            notificacion_mantenedor_email(request,tipo,'Tipo maquinaria','deshabilitada')
            messages.success(request, 'Tipo Maquinaria Deshabilitada Correctamente')  
        else:
            TipoMaquinaria.objects.filter(id=request.POST['id']).update(status=True)
            notificacion_mantenedor_email(request,tipo,'Tipo maquinaria','habilitada')
            messages.success(request, 'Tipo Maquinaria Habilitado Correctamente') 
        return redirect('manage_types_machines')
    else:
        messages.error(request, 'Error al Deshabilitar') 
        return redirect('manage_types_machines')

@login_required
@admin_required
def manage_brands_machines(request): 
    storage = messages.get_messages(request)
    storage.used = True
    marcas = list(MarcaMaquinaria.objects.all().order_by('id'))   
    context = {
        'marcasmaquinas': marcas,
        'sidebarsubmenu': 'manage_managebrandmachine',
        'sidebarmenu': 'manage_machine',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/manage_brands_machine.html', context)

@login_required
@admin_required
def new_brand_machine(request):     
    context = {
        'formmarcamaquinaria': FormMarcaMaquinaria, 
        'sidebarsubmenu': 'manage_managebrandmachine',
        'sidebarmenu': 'manage_machine',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/new_brand_machine.html', context)

@login_required
@admin_required
def save_new_brand_machine(request):     
    if request.method == 'POST':
        tipo = TipoMaquinaria.objects.get(id=request.POST['tipo'])
        formulario = FormMarcaMaquinaria(data=request.POST)
        if formulario.is_valid():       
            marca = MarcaMaquinaria(
                tipo = tipo,
                marca = request.POST['marca'],
                status = True,
                creador = request.user.first_name+" "+request.user.last_name,
            )
            marca.save()
            notificacion_mantenedor_email(request,marca,'Marca maquinaria','creada')
            return JsonResponse({'success': True})
    else:
        return redirect('new_brand_machine')

@login_required
@admin_required
def status_brand_machine(request):
    if request.method == 'POST': 
        marca = MarcaMaquinaria.objects.get(id=request.POST['id'])
        if (marca.status): 
            MarcaMaquinaria.objects.filter(id=request.POST['id']).update(status=False)
            notificacion_mantenedor_email(request,marca,'Marca maquinaria','deshabilitada')
            messages.success(request, 'Marca Maquinaria Deshabilitada Correctamente')  
        else:
            MarcaMaquinaria.objects.filter(id=request.POST['id']).update(status=True)
            notificacion_mantenedor_email(request,marca,'Marca maquinaria','habilitada')
            messages.success(request, 'Marca Maquinaria Habilitado Correctamente') 
        return redirect('manage_brands_machines')
    else:
        messages.error(request, 'Error al Deshabilitar') 
        return redirect('manage_brands_machines')

@login_required
@admin_required
def manage_kits_repairs(request): 
    storage = messages.get_messages(request)
    storage.used = True
    kits = list(KitsMaquinaria.objects.all().order_by('id'))   
    context = {
        'kitsreparacion': kits,
        'sidebarsubmenu': 'manage_managekitmachine',
        'sidebarmenu': 'manage_machine',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/manage_kits_repair.html', context)

@login_required
@admin_required
def new_kit_repair(request):     
    context = {
        'formkitreparacion': FormKitReparacion, 
        'sidebarsubmenu': 'manage_managekitmachine',
        'sidebarmenu': 'manage_machine',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/new_kit_repair.html', context)

@login_required
@admin_required
def save_new_kit_repair(request):     
    if request.method == 'POST':
        marca = MarcaMaquinaria.objects.get(id=request.POST['marcaMaquina'])
        formulario = FormKitReparacion(data=request.POST)
        if formulario.is_valid():       
            kits = KitsMaquinaria(
                marcaMaquina = marca,
                nombreKit = request.POST['nombreKit'],
                stockMinimo = request.POST['stockMinimo'],
                stockMaximo = request.POST['stockMaximo'],
                status = True,
                creador = request.user.first_name+" "+request.user.last_name,
            )
            kits.save()
            notificacion_mantenedor_email(request,kits,'Kit de reparación','creado')
            return JsonResponse({'success': True})
    else:
        return redirect('new_kit_repair')

@login_required
@admin_required
def status_kit_repair(request):
    if request.method == 'POST': 
        try:
            # Se incorpora manejo de excepciones para prevenir errores de servidor (500) y gestionar fallos controlados.
            kit = KitsMaquinaria.objects.get(id=request.POST['id'])
            
            if kit.status: 
                KitsMaquinaria.objects.filter(id=request.POST['id']).update(status=False) 
       
                notificacion_mantenedor_email(request, kit, 'Kit de reparación', 'deshabilitado')
                messages.success(request, 'Kit de Reparación Deshabilitado Correctamente')  
            else:
                KitsMaquinaria.objects.filter(id=request.POST['id']).update(status=True)
                
                notificacion_mantenedor_email(request, kit, 'Kit de reparación', 'habilitado')
                messages.success(request, 'Kit de Reparación Habilitado Correctamente') 
            
            return redirect('manage_kits_repairs')
            
        except Exception as e:
            print(e)
            messages.error(request, 'Error al cambiar estado') 
            return redirect('manage_kits_repairs')
    else:
        messages.error(request, 'Error en la Acción') 
        return redirect('manage_kits_repairs')
    
@login_required
@admin_required
def edit_kit_repair(request):  
    try:
        request.session['edit_kit_repair_id'] = request.POST['kit_id']            
    except MultiValueDictKeyError:
        request.session['edit_kit_repair_id'] = request.session['edit_kit_repair_id']
    kit = KitsMaquinaria.objects.get(id=request.session['edit_kit_repair_id'])

    context = {
        'formkitreparacion':  FormKitReparacion(initial={
            'marcaMaquina': kit.marcaMaquina,
            'nombreKit': kit.nombreKit,
            'stockMinimo': kit.stockMinimo,
            'stockMaximo': kit.stockMaximo,
            },
            marcaMaquina_disabled = True,
            nombreKit_disabled = True,
        ),
        'kit_id': kit.id,
    }
    return render(request,'pages/maintainer/edit_kit_repair.html', context)

@login_required
@admin_required
def save_edit_kit_repair(request):     
    if request.method == 'POST':
        kit = KitsMaquinaria.objects.filter(id=request.POST['kit_id'])
        minimo = int(request.POST['stockMinimo'])
        maximo = int(request.POST['stockMaximo'])
        if minimo < 1 or maximo < 1:
            return JsonResponse({'error': 'Los valores no deben ser menor a 1'})
        else:
            if minimo < maximo:
                KitsMaquinaria.objects.filter(id=request.POST['kit_id']).update(stockMinimo=minimo)
                KitsMaquinaria.objects.filter(id=request.POST['kit_id']).update(stockMaximo=maximo)
                notificacion_mantenedor_email(request,kit,'Kit de reparación','actualizado')
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'error': 'El valor minimo no puede ser mayor que el valor máximo o iguales'})
            
    else:
        return redirect('edit_kit_repair')

@login_required
@admin_required
def manage_failures_machines(request): 
    storage = messages.get_messages(request)
    storage.used = True
    fallas = list(FallaMaquinaria.objects.all().order_by('id'))   
    context = {
        'fallasmaquinas': fallas,
        'sidebarsubmenu': 'manage_managefailuremachine',
        'sidebarmenu': 'manage_machine',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/manage_failures_machine.html', context)

@login_required
@admin_required
def new_failure_machine(request):
    context = {
        'formmarcasmaquinaria': FormMarcaMaquinariaSelect,
        'formfallamaquinaria': FormFallaMaquinaria, 
        'sidebarsubmenu': 'manage_managefailuremachine',
        'sidebarmenu': 'manage_machine',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/new_failure_machine.html', context)

@login_required
def save_new_failure_machine(request):     
    if request.method == 'POST':
        kit = KitsMaquinaria.objects.get(id=request.POST['kitMaquinaria'])
        formulario = FormFallaMaquinaria(data=request.POST)
        if formulario.is_valid():       
            falla = FallaMaquinaria(
                kitMaquinaria = kit,
                falla = request.POST['falla'],
                status = True,
                creador = request.user.first_name+" "+request.user.last_name,
            )
            falla.save()
            notificacion_mantenedor_email(request,falla,'Falla maquinaria','creada')
            return JsonResponse({'success': True})
    else:
        return redirect('new_failure_machine')

@login_required
@admin_required
def status_failure_machine(request):
    if request.method == 'POST': 
        falla = FallaMaquinaria.objects.get(id=request.POST['id'])
        if (falla.status): 
            FallaMaquinaria.objects.filter(id=request.POST['id']).update(status=False)
            notificacion_mantenedor_email(request,falla,'Falla maquinaria','deshabilitada')
            messages.success(request, 'Falla Maquinaria Deshabilitada Correctamente')  
        else:
            FallaMaquinaria.objects.filter(id=request.POST['id']).update(status=True)
            notificacion_mantenedor_email(request,falla,'Falla maquinaria','habilitada')
            messages.success(request, 'Falla Maquinaria Habilitado Correctamente') 
        return redirect('manage_failures_machines')
    else:
        messages.error(request, 'Error al Deshabilitar') 
        return redirect('manage_failures_machines')
    
def cargar_kits_por_marca(request):
    marca_id = request.GET.get('marca_id')
    if marca_id:
        kits = KitsMaquinaria.objects.filter(marcaMaquina_id=marca_id,status=True)
        data = [{'id': kit.id, 'nombre': kit.nombreKit} for kit in kits]
        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({}, status=400)
    
@login_required
@admin_required
def new_important_dates(request):
    context = {
        'formnuevafecha': FormNuevaFechasImportantes,
        'sidebarsubmenu': 'manage_important_dates',
        'sidebarmenu': 'manage_vehicles',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/new_important_dates.html', context)

@login_required
def save_new_important_dates(request):
    if request.method == 'POST':
        formulario = FormNuevaFechasImportantes(data=request.POST)
        if formulario.is_valid():       
            registro = FechasImportantes(
                descripcion = request.POST['descripcion'],
                fechaVencimiento = request.POST['fechaVencimiento'],
                creador = request.user.first_name+" "+request.user.last_name,
                status = True,
            )
            registro.save()
            notificacion_mantenedor_email(request,registro,'Fecha importante','creada')
            return JsonResponse({'success': True})
    else:
        return redirect('new_important_dates')
    
@login_required
@admin_required
def manage_important_dates(request): 
    storage = messages.get_messages(request)
    storage.used = True
    dates = list(FechasImportantes.objects.all().order_by('id'))   
    context = {
        'fechasimportantes': dates,
        'sidebarsubmenu': 'manage_important_dates',
        'sidebarmenu': 'manage_vehicles',
        'sidebarmain': 'manage_system',  
    }
    return render(request,'pages/maintainer/manage_important_dates.html', context)

@login_required
@admin_required
def status_important_dates(request):
    if request.method == 'POST': 
        fecha = FechasImportantes.objects.get(id=request.POST['id'])
        if (fecha.status): 
            FechasImportantes.objects.filter(id=request.POST['id']).update(status=False)
            notificacion_mantenedor_email(request,fecha,'Fecha importante','deshabilitada')
            messages.success(request, 'Fecha Deshabilitada Correctamente')  
        else:
            FechasImportantes.objects.filter(id=request.POST['id']).update(status=True)
            notificacion_mantenedor_email(request,fecha,'Fecha importante','habilitada')
            messages.success(request, 'Fecha Habilitado Correctamente') 
        return redirect('manage_important_dates') 

@login_required
@admin_required
def edit_important_dates(request):  
    try:
        request.session['edit_fecha_id'] = request.POST['fecha_id']            
    except MultiValueDictKeyError:
        request.session['edit_fecha_id'] = request.session['edit_fecha_id']
    fecha = FechasImportantes.objects.get(id=request.session['edit_fecha_id'])
    formFecha = FormNuevaFechasImportantes(instance=fecha)
    context = {
        'id_fecha': fecha.id,
        'formnuevafecha': formFecha,
        'sidebarsubmenu': 'manage_important_dates',
        'sidebarmenu': 'manage_vehicles',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/edit_important_dates.html', context)

@login_required
@admin_required
def save_edit_important_dates(request):
    if request.method == 'POST':
        instance = get_object_or_404(FechasImportantes, id=request.POST['id_fecha'])
        formFecha = FormNuevaFechasImportantes(request.POST, instance=instance)
        if all([
            formFecha.is_valid()
        ]):
            formFecha.save()
            notificacion_mantenedor_email(request,formFecha,'Fecha importante','actualizada')
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'error': True})
    else:
        return redirect('edit_important_dates')
    
@login_required
@admin_required
def manage_report_error(request):
    storage = messages.get_messages(request)
    storage.used = True
    report_errors = list(ReporteError.objects.all().order_by('fechacreacion'))   
    context = {
        'errores':report_errors,
        'sidebarmain': 'system_report_error',  
    }
    return render(request,'pages/users/manage_report_errors.html', context)

@login_required    
def new_report_error(request):
    context = {
        'formnuevoreporte': FormReporteError,   
        'sidebar': 'dashboard',
    }
    return render(request,'pages/users/new_report_error.html', context)

@login_required
def save_new_report_error(request):
    if request.method == 'POST':
        registro = ReporteError(
            descripcion = request.POST['descripcion'],
            detalle = request.POST['detalle'],
            creador = request.user.first_name+" "+request.user.last_name,
            status = True,
        )
        registro.save()             
        return JsonResponse({'success': True})
    else:
        return redirect('new_report_error')

@login_required
@admin_required
def mostrar_reporte_error(request, id):
    registro = ReporteError.objects.get(id=id)
    context = {
        'registro': registro,
        'sidebarmain': 'system_report_error',
    }
    return render(request,'pages/users/mostrarregistro.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_help_manuals(request): 
    storage = messages.get_messages(request)
    storage.used = True
    documentos = list(AyudaManuales.objects.all().order_by('-fechacreacion'))  
    context = {
        'documentos': documentos,
        'sidebarmenu': 'manage_ayuda_manuales',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/manage_help_manuals.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_help_manuals(request):     
    context = {
        'formnuevo': FormAyudaManuales,
        'sidebarmenu': 'manage_ayuda_manuales',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/new_help_manuals.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_new_help_manuals(request):
    if request.method == 'POST':
        toggle_archivoDocumento = request.POST.get('toggle-archivoDocumento', 'no')
        archivo = procesar_fotografia_dos(toggle_archivoDocumento, 'archivoDocumento', 'base/no-imagen.png', request)
        try: 
            documento_ayuda = AyudaManuales.objects.get(nombredocumento=request.POST['nombredocumento'],seccion=request.POST['seccion'])
            return documento_ayuda
        except ObjectDoesNotExist:            
            formulario = FormAyudaManuales(data=request.POST)
            if formulario.is_valid():       
                documento = AyudaManuales(
                    seccion = request.POST['seccion'],
                    nombredocumento = request.POST['nombredocumento'],
                    archivodocumento = archivo,
                    status = True,
                    creador = request.user.first_name+" "+request.user.last_name,
                )
                documento.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        messages.error(request, 'Error en la Acción')
        return redirect('manage_help_manuals')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def status_help_manuals(request):
    if request.method == 'POST': 
        tipo_documento = AyudaManuales.objects.get(id=request.POST['id'])
        if (tipo_documento.status): 
            AyudaManuales.objects.filter(id=request.POST['id']).update(status=False)
            messages.success(request, 'Documento Deshabilitado Correctamente')  
        else:
            AyudaManuales.objects.filter(id=request.POST['id']).update(status=True)
            messages.success(request, 'Documento Habilitado Correctamente') 
        return redirect('manage_help_manuals')
    else:
        messages.error(request, 'Error en la Acción') 
        return redirect('manage_help_manuals') 

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def edit_help_manuals(request):  
    try:
        request.session['edit_document_general_id'] = request.POST['documento_id']            
    except MultiValueDictKeyError:
        request.session['edit_document_general_id'] = request.session['edit_document_general_id']
    documento = AyudaManuales.objects.get(id=request.session['edit_document_general_id'])
    urlDocumento = documento.archivodocumento
    if urlDocumento.url.lower().endswith((".jpg", ".jpeg", ".png")):
        extensionDocumento = "imagen"
    elif urlDocumento.url.lower().endswith((".pdf")):
        extensionDocumento = "pdf"
    else:
        extensionDocumento = "otro"
    context = {
        'formeditardocumento':  FormAyudaManuales(initial={
            'seccion': documento.seccion,
            'nombredocumento': documento.nombredocumento,
            },
        ),
        'documento_id': documento.id,
        'archivodocumento': documento.archivodocumento,
        'extensionDocumento': extensionDocumento,
        'sidebarmenu': 'manage_ayuda_manuales',
        'sidebarmain': 'manage_system',  
    }
    return render(request,'pages/maintainer/edit_help_manuals.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_help_manuals(request):     
    if request.method == 'POST':
        AyudaManuales.objects.filter(id=request.POST['documento_id']).update(seccion=request.POST['seccion'],nombredocumento=request.POST['nombredocumento'])
        documento = AyudaManuales.objects.get(id=request.POST['documento_id'])
        toggle_Documento = request.POST.get('toggle-archivoDocumento', 'no')
        archivo = procesar_fotografia_dos(toggle_Documento, 'archivoDocumento','base/no-imagen.png', request)
        documento.archivodocumento = archivo
        documento.save() 
        return JsonResponse({'success': True})
    else:
        return redirect('edit_help_manuals')

@login_required
def view_help_manuals(request): 
    storage = messages.get_messages(request)
    storage.used = True
    documentos = list(AyudaManuales.objects.all().order_by('-fechacreacion'))  
    context = {
        'documentos': documentos,
        'sidebar': 'dashboard', 
    }
    return render(request,'pages/users/manage_help_manuals.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_probe(request): 
    lista = list(Sondas.objects.all().order_by('sonda'))  
    context = {
        'documentos': lista,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_sonda',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/manage_probe.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_probe(request):     
    context = {
        'formnuevo': FormSondas,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_sonda',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/new_probe.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_new_probe(request):
    if request.method == 'POST':
        try: 
            sonda = Sondas.objects.get(sonda=request.POST['sonda'])
            return sonda
        except ObjectDoesNotExist:            
            formulario = FormSondas(data=request.POST)
            if formulario.is_valid():       
                documento = Sondas(
                    sonda = request.POST['sonda'],
                    status = True,
                    creador = request.user.first_name+" "+request.user.last_name,
                )
                documento.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        messages.error(request, 'Error en la Acción')
        return redirect('manage_probe')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def status_probe(request):
    if request.method == 'POST': 
        sonda = Sondas.objects.get(id=request.POST['id'])
        if (sonda.status): 
            Sondas.objects.filter(id=request.POST['id']).update(status=False)
            messages.success(request, 'Sonda Deshabilitada Correctamente')  
        else:
            Sondas.objects.filter(id=request.POST['id']).update(status=True)
            messages.success(request, 'Sonda Habilitada Correctamente') 
        return redirect('manage_probe')
    else:
        messages.error(request, 'Error en la Acción') 
        return redirect('manage_probe') 

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def edit_probe(request):  
    try:
        request.session['edit_id'] = request.POST['id']            
    except MultiValueDictKeyError:
        request.session['edit_id'] = request.session['edit_id']
    documento = Sondas.objects.get(id=request.session['edit_id'])
    context = {
        'formeditar':  FormSondas(initial={
            'sonda': documento.sonda,
            },
        ),
        'documento_id': documento.id,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_sonda',
        'sidebarmain': 'manage_system',  
    }
    return render(request,'pages/maintainer/drilling/edit_probe.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_probe(request):     
    if request.method == 'POST':
        Sondas.objects.filter(id=request.POST['id']).update(sonda=request.POST['sonda'])
        return JsonResponse({'success': True})
    else:
        return redirect('edit_probe')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_aditivos(request): 
    lista = list(Aditivos.objects.all().order_by('aditivo'))  
    context = {
        'documentos': lista,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_aditivo',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/manage_aditivos.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_aditivos(request):     
    context = {
        'formnuevo': FormAditivos,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_aditivo',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/new_aditivos.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_new_aditivos(request):
    if request.method == 'POST':
        try: 
            aditivo = Aditivos.objects.get(aditivo=request.POST['aditivo'])
            return aditivo
        except ObjectDoesNotExist:            
            formulario = FormAditivos(data=request.POST)
            if formulario.is_valid():       
                documento = Aditivos(
                    aditivo = request.POST['aditivo'],
                    status = True,
                    creador = request.user.first_name+" "+request.user.last_name,
                )
                documento.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        messages.error(request, 'Error en la Acción')
        return redirect('manage_aditivos')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def status_aditivos(request):
    if request.method == 'POST': 
        aditivo = Aditivos.objects.get(id=request.POST['id'])
        if (aditivo.status): 
            Aditivos.objects.filter(id=request.POST['id']).update(status=False)
            messages.success(request, 'Aditivo Deshabilitado Correctamente')  
        else:
            Aditivos.objects.filter(id=request.POST['id']).update(status=True)
            messages.success(request, 'Aditivo Habilitado Correctamente') 
        return redirect('manage_aditivos')
    else:
        messages.error(request, 'Error en la Acción') 
        return redirect('manage_aditivos') 

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def edit_aditivos(request):  
    try:
        request.session['edit_id'] = request.POST['id']            
    except MultiValueDictKeyError:
        request.session['edit_id'] = request.session['edit_id']
    documento = Aditivos.objects.get(id=request.session['edit_id'])
    context = {
        'formeditar':  FormAditivos(initial={
            'aditivo': documento.aditivo,
            },
        ),
        'documento_id': documento.id,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_aditivo',
        'sidebarmain': 'manage_system',  
    }
    return render(request,'pages/maintainer/drilling/edit_aditivos.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_aditivos(request):     
    if request.method == 'POST':
        Aditivos.objects.filter(id=request.POST['id']).update(aditivo=request.POST['aditivo'])
        return JsonResponse({'success': True})
    else:
        return redirect('edit_aditivos')
    
@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_cantidadAgua(request): 
    lista = list(CantidadAgua.objects.all().order_by('cantidadAgua'))  
    context = {
        'documentos': lista,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_cantidadAgua',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/manage_cantidadAgua.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_cantidadAgua(request):     
    context = {
        'formnuevo': FormCantidadAgua,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_cantidadAgua',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/new_cantidadAgua.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_new_cantidadAgua(request):
    if request.method == 'POST':
        try: 
            cantidadAgua = CantidadAgua.objects.get(cantidadAgua=request.POST['cantidadAgua'])
            return cantidadAgua
        except ObjectDoesNotExist:            
            formulario = FormCantidadAgua(data=request.POST)
            if formulario.is_valid():       
                documento = CantidadAgua(
                    cantidadAgua = request.POST['cantidadAgua'],
                    status = True,
                    creador = request.user.first_name+" "+request.user.last_name,
                )
                documento.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        messages.error(request, 'Error en la Acción')
        return redirect('manage_cantidadAgua')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def status_cantidadAgua(request):
    if request.method == 'POST': 
        cantidadAgua = CantidadAgua.objects.get(id=request.POST['id'])
        if (cantidadAgua.status): 
            CantidadAgua.objects.filter(id=request.POST['id']).update(status=False)
            messages.success(request, 'Cantidad Agua Deshabilitada Correctamente')  
        else:
            CantidadAgua.objects.filter(id=request.POST['id']).update(status=True)
            messages.success(request, 'Cantidad Agua Habilitada Correctamente') 
        return redirect('manage_cantidadAgua')
    else:
        messages.error(request, 'Error en la Acción') 
        return redirect('manage_cantidadAgua') 

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def edit_cantidadAgua(request):  
    try:
        request.session['edit_id'] = request.POST['id']            
    except MultiValueDictKeyError:
        request.session['edit_id'] = request.session['edit_id']
    documento = CantidadAgua.objects.get(id=request.session['edit_id'])
    context = {
        'formeditar':  FormCantidadAgua(initial={
            'cantidadAgua': documento.cantidadAgua,
            },
        ),
        'documento_id': documento.id,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_cantidadAgua',
        'sidebarmain': 'manage_system',  
    }
    return render(request,'pages/maintainer/drilling/edit_cantidadAgua.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_cantidadAgua(request):     
    if request.method == 'POST':
        CantidadAgua.objects.filter(id=request.POST['id']).update(cantidadAgua=request.POST['cantidadAgua'])
        return JsonResponse({'success': True})
    else:
        return redirect('edit_cantidadAgua')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_casing(request): 
    lista = list(Casing.objects.all().order_by('casing'))  
    context = {
        'documentos': lista,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_casing',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/manage_casing.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_casing(request):     
    context = {
        'formnuevo': FormCasing,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_casing',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/new_casing.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_new_casing(request):
    if request.method == 'POST':
        try: 
            casing = Casing.objects.get(casing=request.POST['casing'])
            return casing
        except ObjectDoesNotExist:            
            formulario = FormCasing(data=request.POST)
            if formulario.is_valid():       
                documento = Casing(
                    casing = request.POST['casing'],
                    status = True,
                    creador = request.user.first_name+" "+request.user.last_name,
                )
                documento.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        messages.error(request, 'Error en la Acción')
        return redirect('manage_casing')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def status_casing(request):
    if request.method == 'POST': 
        casing = Casing.objects.get(id=request.POST['id'])
        if (casing.status): 
            Casing.objects.filter(id=request.POST['id']).update(status=False)
            messages.success(request, 'Casing Deshabilitado Correctamente')  
        else:
            Casing.objects.filter(id=request.POST['id']).update(status=True)
            messages.success(request, 'Casing Habilitado Correctamente') 
        return redirect('manage_casing')
    else:
        messages.error(request, 'Error en la Acción') 
        return redirect('manage_casing') 

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def edit_casing(request):  
    try:
        request.session['edit_id'] = request.POST['id']            
    except MultiValueDictKeyError:
        request.session['edit_id'] = request.session['edit_id']
    documento = Casing.objects.get(id=request.session['edit_id'])
    context = {
        'formeditar':  FormCasing(initial={
            'casing': documento.casing,
            },
        ),
        'documento_id': documento.id,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_casing',
        'sidebarmain': 'manage_system',  
    }
    return render(request,'pages/maintainer/drilling/edit_casing.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_casing(request):     
    if request.method == 'POST':
        Casing.objects.filter(id=request.POST['id']).update(casing=request.POST['casing'])
        return JsonResponse({'success': True})
    else:
        return redirect('edit_casing')
    
@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_corona(request): 
    lista = list(Corona.objects.all().order_by('corona'))  
    context = {
        'documentos': lista,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_corona',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/manage_corona.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_corona(request):     
    context = {
        'formnuevo': FormCorona,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_corona',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/new_corona.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_new_corona(request):
    if request.method == 'POST':
        try: 
            corona = Corona.objects.get(corona=request.POST['corona'])
            return corona
        except ObjectDoesNotExist:            
            formulario = FormCorona(data=request.POST)
            if formulario.is_valid():       
                documento = Corona(
                    corona = request.POST['corona'],
                    status = True,
                    creador = request.user.first_name+" "+request.user.last_name,
                )
                documento.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        messages.error(request, 'Error en la Acción')
        return redirect('manage_corona')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def status_corona(request):
    if request.method == 'POST': 
        corona = Corona.objects.get(id=request.POST['id'])
        if (corona.status): 
            Corona.objects.filter(id=request.POST['id']).update(status=False)
            messages.success(request, 'Corona Deshabilitada Correctamente')  
        else:
            Corona.objects.filter(id=request.POST['id']).update(status=True)
            messages.success(request, 'Corona Habilitada Correctamente') 
        return redirect('manage_corona')
    else:
        messages.error(request, 'Error en la Acción') 
        return redirect('manage_corona') 

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def edit_corona(request):  
    try:
        request.session['edit_id'] = request.POST['id']            
    except MultiValueDictKeyError:
        request.session['edit_id'] = request.session['edit_id']
    documento = Corona.objects.get(id=request.session['edit_id'])
    context = {
        'formeditar':  FormCorona(initial={
            'corona': documento.corona,
            },
        ),
        'documento_id': documento.id,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_corona',
        'sidebarmain': 'manage_system',  
    }
    return render(request,'pages/maintainer/drilling/edit_corona.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_corona(request):     
    if request.method == 'POST':
        Corona.objects.filter(id=request.POST['id']).update(corona=request.POST['corona'])
        return JsonResponse({'success': True})
    else:
        return redirect('edit_corona')
    
@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_details(request): 
    lista = list(DetalleControlHorario.objects.all().order_by('detalle'))  
    context = {
        'documentos': lista,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_detalle',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/manage_details.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_details(request):     
    context = {
        'formnuevo': FormDetalleControlHorario,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_detalle',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/new_details.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_new_details(request):
    if request.method == 'POST':
        try: 
            detalle = DetalleControlHorario.objects.get(detalle=request.POST['detalle'])
            return detalle
        except ObjectDoesNotExist:            
            formulario = FormDetalleControlHorario(data=request.POST)
            if formulario.is_valid():       
                documento = DetalleControlHorario(
                    detalle = request.POST['detalle'],
                    status = True,
                    creador = request.user.first_name+" "+request.user.last_name,
                )
                documento.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        messages.error(request, 'Error en la Acción')
        return redirect('manage_details')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def status_details(request):
    if request.method == 'POST': 
        detalle = DetalleControlHorario.objects.get(id=request.POST['id'])
        if (detalle.status): 
            DetalleControlHorario.objects.filter(id=request.POST['id']).update(status=False)
            messages.success(request, 'Detalle Deshabilitada Correctamente')  
        else:
            DetalleControlHorario.objects.filter(id=request.POST['id']).update(status=True)
            messages.success(request, 'Detalle Habilitada Correctamente') 
        return redirect('manage_details')
    else:
        messages.error(request, 'Error en la Acción') 
        return redirect('manage_details') 

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def edit_details(request):  
    try:
        request.session['edit_id'] = request.POST['id']            
    except MultiValueDictKeyError:
        request.session['edit_id'] = request.session['edit_id']
    documento = DetalleControlHorario.objects.get(id=request.session['edit_id'])
    context = {
        'formeditar':  FormDetalleControlHorario(initial={
            'detalle': documento.detalle,
            },
        ),
        'documento_id': documento.id,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_detalle',
        'sidebarmain': 'manage_system',  
    }
    return render(request,'pages/maintainer/drilling/edit_details.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_details(request):     
    if request.method == 'POST':
        DetalleControlHorario.objects.filter(id=request.POST['id']).update(detalle=request.POST['detalle'])
        return JsonResponse({'success': True})
    else:
        return redirect('edit_details')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_diameter(request): 
    lista = list(Diametros.objects.all().order_by('diametro'))  
    context = {
        'documentos': lista,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_diametro',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/manage_diameter.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_diameter(request):     
    context = {
        'formnuevo': FormDiametros,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_diametro',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/new_diameter.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_new_diameter(request):
    if request.method == 'POST':
        try: 
            diametro = Diametros.objects.get(diametro=request.POST['diametro'])
            return diametro
        except ObjectDoesNotExist:            
            formulario = FormDiametros(data=request.POST)
            if formulario.is_valid():       
                documento = Diametros(
                    diametro = request.POST['diametro'],
                    status = True,
                    creador = request.user.first_name+" "+request.user.last_name,
                )
                documento.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        messages.error(request, 'Error en la Acción')
        return redirect('manage_diameter')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def status_diameter(request):
    if request.method == 'POST': 
        diametro = Diametros.objects.get(id=request.POST['id'])
        if (diametro.status): 
            Diametros.objects.filter(id=request.POST['id']).update(status=False)
            messages.success(request, 'Diametro Deshabilitada Correctamente')  
        else:
            Diametros.objects.filter(id=request.POST['id']).update(status=True)
            messages.success(request, 'Diametro Habilitada Correctamente') 
        return redirect('manage_diameter')
    else:
        messages.error(request, 'Error en la Acción') 
        return redirect('manage_diameter') 

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def edit_diameter(request):  
    try:
        request.session['edit_id'] = request.POST['id']            
    except MultiValueDictKeyError:
        request.session['edit_id'] = request.session['edit_id']
    documento = Diametros.objects.get(id=request.session['edit_id'])
    context = {
        'formeditar':  FormDiametros(initial={
            'diametro': documento.diametro,
            },
        ),
        'documento_id': documento.id,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_diametro',
        'sidebarmain': 'manage_system',  
    }
    return render(request,'pages/maintainer/drilling/edit_diameter.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_diameter(request):     
    if request.method == 'POST':
        Diametros.objects.filter(id=request.POST['id']).update(diametro=request.POST['diametro'])
        return JsonResponse({'success': True})
    else:
        return redirect('edit_diameter')
    
@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_drilling(request): 
    lista = list(Sondajes.objects.all().order_by('sondaje'))  
    context = {
        'documentos': lista,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_sondaje',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/manage_drilling.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_drilling(request):     
    context = {
        'formnuevo': FormSondajes,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_sondaje',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/new_drilling.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_new_drilling(request):
    if request.method == 'POST':
        faena = Faena.objects.get(id=request.POST['faena'])
        try: 
            sondaje = Sondajes.objects.get(sondaje=request.POST['sondaje'])
            return sondaje
        except ObjectDoesNotExist:
            formulario = FormSondajes(data=request.POST)
            if formulario.is_valid():       
                documento = Sondajes(
                    faena = faena,
                    sondaje = request.POST['sondaje'],
                    status = True,
                    creador = request.user.first_name+" "+request.user.last_name,
                )
                documento.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        messages.error(request, 'Error en la Acción')
        return redirect('manage_drilling')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def status_drilling(request):
    if request.method == 'POST': 
        sondaje = Sondajes.objects.get(id=request.POST['id'])
        if (sondaje.status): 
            Sondajes.objects.filter(id=request.POST['id']).update(status=False)
            messages.success(request, 'Sondaje Deshabilitado Correctamente')  
        else:
            Sondajes.objects.filter(id=request.POST['id']).update(status=True)
            messages.success(request, 'Sondaje Habilitado Correctamente') 
        return redirect('manage_drilling')
    else:
        messages.error(request, 'Error en la Acción') 
        return redirect('manage_drilling') 

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def edit_drilling(request):  
    try:
        request.session['edit_id'] = request.POST['id']            
    except MultiValueDictKeyError:
        request.session['edit_id'] = request.session['edit_id']
    documento = Sondajes.objects.get(id=request.session['edit_id'])
    context = {
        'formeditar':  FormSondajes(initial={
            'faena': documento.faena,
            'sondaje': documento.sondaje,
            },
        ),
        'documento_id': documento.id,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_sondaje',
        'sidebarmain': 'manage_system',  
    }
    return render(request,'pages/maintainer/drilling/edit_drilling.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_drilling(request):     
    if request.method == 'POST':
        Sondajes.objects.filter(id=request.POST['id']).update(faena=request.POST['faena'],sondaje=request.POST['sondaje'])
        return JsonResponse({'success': True})
    else:
        return redirect('edit_drilling')
    
@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_escareador(request): 
    lista = list(Escareador.objects.all().order_by('escareador'))  
    context = {
        'documentos': lista,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_escareador',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/manage_escareador.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_escareador(request):     
    context = {
        'formnuevo': FormEscareador,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_escareador',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/new_escareador.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_new_escareador(request):
    if request.method == 'POST':
        try: 
            escareador = Escareador.objects.get(escareador=request.POST['escareador'])
            return escareador
        except ObjectDoesNotExist:            
            formulario = FormEscareador(data=request.POST)
            if formulario.is_valid():       
                documento = Escareador(
                    escareador = request.POST['escareador'],
                    status = True,
                    creador = request.user.first_name+" "+request.user.last_name,
                )
                documento.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        messages.error(request, 'Error en la Acción')
        return redirect('manage_escareador')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def status_escareador(request):
    if request.method == 'POST': 
        escareador = Escareador.objects.get(id=request.POST['id'])
        if (escareador.status): 
            Escareador.objects.filter(id=request.POST['id']).update(status=False)
            messages.success(request, 'Escareador Deshabilitado Correctamente')  
        else:
            Escareador.objects.filter(id=request.POST['id']).update(status=True)
            messages.success(request, 'Escareador Habilitado Correctamente') 
        return redirect('manage_escareador')
    else:
        messages.error(request, 'Error en la Acción') 
        return redirect('manage_escareador') 

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def edit_escareador(request):  
    try:
        request.session['edit_id'] = request.POST['id']            
    except MultiValueDictKeyError:
        request.session['edit_id'] = request.session['edit_id']
    documento = Escareador.objects.get(id=request.session['edit_id'])
    context = {
        'formeditar':  FormEscareador(initial={
            'escareador': documento.escareador,
            },
        ),
        'documento_id': documento.id,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_escareador',
        'sidebarmain': 'manage_system',  
    }
    return render(request,'pages/maintainer/drilling/edit_escareador.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_escareador(request):     
    if request.method == 'POST':
        Escareador.objects.filter(id=request.POST['id']).update(escareador=request.POST['escareador'])
        return JsonResponse({'success': True})
    else:
        return redirect('edit_escareador')
    
@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_largoBarra(request): 
    lista = list(LargoBarra.objects.all().order_by('largoBarra'))  
    context = {
        'documentos': lista,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_largoBarra',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/manage_largoBarra.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_largoBarra(request):     
    context = {
        'formnuevo': FormLargoBarra,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_largoBarra',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/new_largoBarra.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_new_largoBarra(request):
    if request.method == 'POST':
        try: 
            largoBarra = LargoBarra.objects.get(largoBarra=request.POST['largoBarra'])
            return largoBarra
        except ObjectDoesNotExist:            
            formulario = FormLargoBarra(data=request.POST)
            if formulario.is_valid():       
                documento = LargoBarra(
                    largoBarra = request.POST['largoBarra'],
                    status = True,
                    creador = request.user.first_name+" "+request.user.last_name,
                )
                documento.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        messages.error(request, 'Error en la Acción')
        return redirect('manage_largoBarra')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def status_largoBarra(request):
    if request.method == 'POST': 
        largoBarra = LargoBarra.objects.get(id=request.POST['id'])
        if (largoBarra.status): 
            LargoBarra.objects.filter(id=request.POST['id']).update(status=False)
            messages.success(request, 'Largo Barra Deshabilitada Correctamente')  
        else:
            LargoBarra.objects.filter(id=request.POST['id']).update(status=True)
            messages.success(request, 'Largo Barra Habilitada Correctamente') 
        return redirect('manage_largoBarra')
    else:
        messages.error(request, 'Error en la Acción') 
        return redirect('manage_largoBarra') 

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def edit_largoBarra(request):  
    try:
        request.session['edit_id'] = request.POST['id']            
    except MultiValueDictKeyError:
        request.session['edit_id'] = request.session['edit_id']
    documento = LargoBarra.objects.get(id=request.session['edit_id'])
    context = {
        'formeditar':  FormLargoBarra(initial={
            'largoBarra': documento.largoBarra,
            },
        ),
        'documento_id': documento.id,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_largoBarra',
        'sidebarmain': 'manage_system',  
    }
    return render(request,'pages/maintainer/drilling/edit_largoBarra.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_largoBarra(request):     
    if request.method == 'POST':
        LargoBarra.objects.filter(id=request.POST['id']).update(largoBarra=request.POST['largoBarra'])
        return JsonResponse({'success': True})
    else:
        return redirect('edit_largoBarra')
    
@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_orientation(request): 
    lista = list(Orientacion.objects.all().order_by('orientacion'))  
    context = {
        'documentos': lista,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_orientacion',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/manage_orientation.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_orientation(request):     
    context = {
        'formnuevo': FormOrientacion,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_orientacion',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/new_orientation.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_new_orientation(request):
    if request.method == 'POST':
        try: 
            orientacion = Orientacion.objects.get(orientacion=request.POST['orientacion'])
            return orientacion
        except ObjectDoesNotExist:            
            formulario = FormOrientacion(data=request.POST)
            if formulario.is_valid():       
                documento = Orientacion(
                    orientacion = request.POST['orientacion'],
                    status = True,
                    creador = request.user.first_name+" "+request.user.last_name,
                )
                documento.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        messages.error(request, 'Error en la Acción')
        return redirect('manage_orientation')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def status_orientation(request):
    if request.method == 'POST': 
        orientacion = Orientacion.objects.get(id=request.POST['id'])
        if (orientacion.status): 
            Orientacion.objects.filter(id=request.POST['id']).update(status=False)
            messages.success(request, 'Orientación Deshabilitada Correctamente')  
        else:
            Orientacion.objects.filter(id=request.POST['id']).update(status=True)
            messages.success(request, 'Orientación Habilitada Correctamente') 
        return redirect('manage_orientation')
    else:
        messages.error(request, 'Error en la Acción') 
        return redirect('manage_orientation') 

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def edit_orientation(request):  
    try:
        request.session['edit_id'] = request.POST['id']            
    except MultiValueDictKeyError:
        request.session['edit_id'] = request.session['edit_id']
    documento = Orientacion.objects.get(id=request.session['edit_id'])
    context = {
        'formeditar':  FormOrientacion(initial={
            'orientacion': documento.orientacion,
            },
        ),
        'documento_id': documento.id,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_orientacion',
        'sidebarmain': 'manage_system',  
    }
    return render(request,'pages/maintainer/drilling/edit_orientation.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_orientation(request):     
    if request.method == 'POST':
        Orientacion.objects.filter(id=request.POST['id']).update(orientacion=request.POST['orientacion'])
        return JsonResponse({'success': True})
    else:
        return redirect('edit_orientation')
    
@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_tipoTerreno(request): 
    lista = list(TipoTerreno.objects.all().order_by('tipoTerreno'))  
    context = {
        'documentos': lista,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_tipoTerreno',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/manage_tipoTerreno.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_tipoTerreno(request):     
    context = {
        'formnuevo': FormTipoTerreno,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_tipoTerreno',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/new_tipoTerreno.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_new_tipoTerreno(request):
    if request.method == 'POST':
        try: 
            tipoTerreno = TipoTerreno.objects.get(tipoTerreno=request.POST['tipoTerreno'])
            return tipoTerreno
        except ObjectDoesNotExist:            
            formulario = FormTipoTerreno(data=request.POST)
            if formulario.is_valid():       
                documento = TipoTerreno(
                    tipoTerreno = request.POST['tipoTerreno'],
                    status = True,
                    creador = request.user.first_name+" "+request.user.last_name,
                )
                documento.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        messages.error(request, 'Error en la Acción')
        return redirect('manage_tipoTerreno')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def status_tipoTerreno(request):
    if request.method == 'POST': 
        tipoTerreno = TipoTerreno.objects.get(id=request.POST['id'])
        if (tipoTerreno.status): 
            TipoTerreno.objects.filter(id=request.POST['id']).update(status=False)
            messages.success(request, 'Tipo Terreno Deshabilitada Correctamente')  
        else:
            TipoTerreno.objects.filter(id=request.POST['id']).update(status=True)
            messages.success(request, 'Tipo Terreno Habilitada Correctamente') 
        return redirect('manage_tipoTerreno')
    else:
        messages.error(request, 'Error en la Acción') 
        return redirect('manage_tipoTerreno') 

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def edit_tipoTerreno(request):  
    try:
        request.session['edit_id'] = request.POST['id']            
    except MultiValueDictKeyError:
        request.session['edit_id'] = request.session['edit_id']
    documento = TipoTerreno.objects.get(id=request.session['edit_id'])
    context = {
        'formeditar':  FormTipoTerreno(initial={
            'tipoTerreno': documento.tipoTerreno,
            },
        ),
        'documento_id': documento.id,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_tipoTerreno',
        'sidebarmain': 'manage_system',  
    }
    return render(request,'pages/maintainer/drilling/edit_tipoTerreno.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_tipoTerreno(request):     
    if request.method == 'POST':
        TipoTerreno.objects.filter(id=request.POST['id']).update(tipoTerreno=request.POST['tipoTerreno'])
        return JsonResponse({'success': True})
    else:
        return redirect('edit_tipoTerreno')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_zapata(request): 
    lista = list(Zapata.objects.all().order_by('zapata'))  
    context = {
        'documentos': lista,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_zapata',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/manage_zapata.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_zapata(request):     
    context = {
        'formnuevo': FormZapata,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_zapata',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/new_zapata.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_new_zapata(request):
    if request.method == 'POST':
        try: 
            zapata = Zapata.objects.get(zapata=request.POST['zapata'])
            return zapata
        except ObjectDoesNotExist:            
            formulario = FormZapata(data=request.POST)
            if formulario.is_valid():       
                documento = Zapata(
                    zapata = request.POST['zapata'],
                    status = True,
                    creador = request.user.first_name+" "+request.user.last_name,
                )
                documento.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        messages.error(request, 'Error en la Acción')
        return redirect('manage_zapata')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def status_zapata(request):
    if request.method == 'POST': 
        zapata = Zapata.objects.get(id=request.POST['id'])
        if (zapata.status): 
            Zapata.objects.filter(id=request.POST['id']).update(status=False)
            messages.success(request, 'Zapata Deshabilitada Correctamente')  
        else:
            Zapata.objects.filter(id=request.POST['id']).update(status=True)
            messages.success(request, 'Zapata Habilitada Correctamente') 
        return redirect('manage_zapata')
    else:
        messages.error(request, 'Error en la Acción') 
        return redirect('manage_zapata') 

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def edit_zapata(request):  
    try:
        request.session['edit_id'] = request.POST['id']            
    except MultiValueDictKeyError:
        request.session['edit_id'] = request.session['edit_id']
    documento = Zapata.objects.get(id=request.session['edit_id'])
    context = {
        'formeditar':  FormZapata(initial={
            'zapata': documento.zapata,
            },
        ),
        'documento_id': documento.id,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_zapata',
        'sidebarmain': 'manage_system',  
    }
    return render(request,'pages/maintainer/drilling/edit_zapata.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_zapata(request):     
    if request.method == 'POST':
        Zapata.objects.filter(id=request.POST['id']).update(zapata=request.POST['zapata'])
        return JsonResponse({'success': True})
    else:
        return redirect('edit_zapata')
    
@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_perforista(request): 
    lista = list(Perforistas.objects.all().order_by('perforista'))  
    context = {
        'documentos': lista,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_perforista',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/manage_perforista.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_perforista(request):     
    context = {
        'formnuevo': FormPerforista,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_perforista',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/new_perforista.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_new_perforista(request):
    if request.method == 'POST':
        try: 
            perforista = Perforistas.objects.get(perforista=request.POST['perforista'])
            return perforista
        except ObjectDoesNotExist:            
            formulario = FormPerforista(data=request.POST)
            if formulario.is_valid():       
                documento = Perforistas(
                    perforista = request.POST['perforista'],
                    status = True,
                    creador = request.user.first_name+" "+request.user.last_name,
                )
                documento.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        messages.error(request, 'Error en la Acción')
        return redirect('manage_perforista')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def status_perforista(request):
    if request.method == 'POST': 
        perforista = Perforistas.objects.get(id=request.POST['id'])
        if (perforista.status): 
            Perforistas.objects.filter(id=request.POST['id']).update(status=False)
            messages.success(request, 'Perforista Deshabilitado Correctamente')  
        else:
            Perforistas.objects.filter(id=request.POST['id']).update(status=True)
            messages.success(request, 'Perforista Habilitado Correctamente') 
        return redirect('manage_perforista')
    else:
        messages.error(request, 'Error en la Acción') 
        return redirect('manage_perforista') 

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def edit_perforista(request):  
    try:
        request.session['edit_id'] = request.POST['id']            
    except MultiValueDictKeyError:
        request.session['edit_id'] = request.session['edit_id']
    documento = Perforistas.objects.get(id=request.session['edit_id'])
    context = {
        'formeditar':  FormPerforista(initial={
            'perforista': documento.perforista,
            },
        ),
        'documento_id': documento.id,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_perforista',
        'sidebarmain': 'manage_system',  
    }
    return render(request,'pages/maintainer/drilling/edit_perforista.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_perforista(request):     
    if request.method == 'POST':
        Perforistas.objects.filter(id=request.POST['id']).update(perforista=request.POST['perforista'])
        return JsonResponse({'success': True})
    else:
        return redirect('edit_perforista')
    
@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_recomendaciones(request):
    lista = Recomendacion.objects.all().order_by('-fecha_inicio')
    
    for recomendacion in lista:
        recomendacion.este = str(recomendacion.este).rstrip('0').rstrip('.') if recomendacion.este else None
        recomendacion.norte = str(recomendacion.norte).rstrip('0').rstrip('.') if recomendacion.norte else None
        recomendacion.cota = str(recomendacion.cota).rstrip('0').rstrip('.') if recomendacion.cota else None
        recomendacion.largo_real = int(recomendacion.largo_real) if recomendacion.largo_real == 0 else recomendacion.largo_real
    
    context = {
        'documentos': lista,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_recomendacion',
        'sidebarmain': 'manage_system', 
    }
    return render(request, 'pages/maintainer/drilling/manage_recomendacion.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_recomendacion(request):     
    context = {
        'formnuevo': FormRecomendaciones,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_recomendacion',
        'sidebarmain': 'manage_system',
    }
    return render(request,'pages/maintainer/drilling/new_recomendacion.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_new_recomendacion(request):
    if request.method == 'POST':
        # Validación de nombre duplicado (Existente)
        if Recomendacion.objects.filter(recomendacion=request.POST.get('recomendacion')).exists():
            return JsonResponse({'success': False, 'message': 'La recomendación ya existe.'})

        formulario = FormRecomendaciones(data=request.POST)
        if formulario.is_valid():
            try:
                sonda_id = request.POST.get('sonda')
                sonda = Sondas.objects.get(id=sonda_id)

                azimut = request.POST.get('azimut')
                azimut = int(azimut) if azimut and azimut.strip() != "" else None

                if azimut is not None and (azimut < 0 or azimut > 360):
                    return JsonResponse({'success': False, 'message': 'El azimut debe estar entre 0 y 360.'})
                
                campana = Campana.objects.get(id=request.POST['campana'])
                programa = Programa.objects.get(id=request.POST['programa'])
                
                # Obtener el largo que se intenta guardar
                largo_programado_solicitado = float(request.POST.get('largo_programado')) if request.POST.get('largo_programado') else 0.0

                # Calcular cuántos metros ya se han usado en este programa
                metros_usados = Recomendacion.objects.filter(
                    programa=programa,
                    status=True
                ).aggregate(total=Sum('largo_programado'))['total'] or 0

                # Calcular disponible
                metros_disponibles = float(programa.metros) - float(metros_usados)

                # Validar Metros
                if largo_programado_solicitado > metros_disponibles:
                     return JsonResponse({
                        'success': False, 
                        'message': f'El largo programado excede el disponible del programa. Disponibles: {metros_disponibles:.2f} mts.'
                    })

                Recomendacion.objects.create(
                    campana=campana,
                    programa=programa,
                    recomendacion=request.POST['recomendacion'],
                    pozo=request.POST.get('pozo'),
                    sonda=sonda,
                    fecha_inicio=request.POST.get('fecha_inicio'),
                    sector=request.POST.get('sector'),
                    azimut=azimut,
                    inclinacion=float(request.POST.get('inclinacion')) if request.POST.get('inclinacion') else None,
                    largo_programado=largo_programado_solicitado,
                    largo_real=0,
                    este=float(request.POST.get('este')) if request.POST.get('este') else None,
                    norte=float(request.POST.get('norte')) if request.POST.get('norte') else None,
                    cota=float(request.POST.get('cota')) if request.POST.get('cota') else None,
                    manteo=float(request.POST.get('manteo')) if request.POST.get('manteo') else None,
                    estado=request.POST.get('estado'),
                    status=True,
                    creador=f"{request.user.first_name} {request.user.last_name}",
                )
                return JsonResponse({'success': True, 'message': 'Recomendación creada con éxito.'})

            except Sondas.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'La sonda seleccionada no existe.'})
            except ValueError:
                return JsonResponse({'success': False, 'message': 'Error en la conversión de datos numéricos.'})
            except Programa.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'El programa seleccionado no existe.'})
        else:
            # --- MEJORA EN EL REPORTE DE ERRORES ---
            for field, errors in formulario.errors.items():
                # Obtener nombre amigable del campo
                label = field
                if field == '__all__':
                    label = 'General'
                elif field in formulario.fields:
                    label = formulario.fields[field].label or field.capitalize()
                
                for error in errors:
                    # Detección específica de Sonda Ocupada
                    if field == 'sonda':
                        sonda_id = request.POST.get('sonda')
                        if sonda_id:
                             # Verificamos si está ocupada en BD (Activa y no Abortada/Finalizada)
                             # 1: Abortado, 4: Finalizado
                             esta_ocupada = Recomendacion.objects.filter(
                                 status=True, 
                                 sonda_id=sonda_id
                             ).exclude(estado__in=['1', '4', 1, 4]).exists()
                             
                             if esta_ocupada:
                                 error = "La sonda seleccionada ya se encuentra ocupada en otra recomendación activa."

                    

            return JsonResponse({'success': False, 'message': error})

    else:
        messages.error(request, 'Error en la Acción')
        return redirect('manage_recomendacion')
@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def status_recomendacion(request):
    if request.method == 'POST': 
        recomendacion = Recomendacion.objects.get(id=request.POST['id'])
        if (recomendacion.status): 
            Recomendacion.objects.filter(id=request.POST['id']).update(status=False)
            messages.success(request, 'Recomendación Terminada Correctamente')  
        else:
            Recomendacion.objects.filter(id=request.POST['id']).update(status=True)
            messages.success(request, 'Recomendación Activa Correctamente') 
        return redirect('manage_recomendacion')
    else:
        messages.error(request, 'Error en la Acción') 
        return redirect('manage_recomendacion')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def edit_recomendacion(request):  
    # Obtener o mantener el ID de la recomendación a editar
    if request.method == "POST":
        try:
            request.session['edit_id'] = request.POST['id']
        except MultiValueDictKeyError:
            if 'edit_id' not in request.session:
                return render(request, 'pages/maintainer/drilling/edit_recomendacion.html', {'error': 'No se encontró un ID válido.'})

    documento = Recomendacion.objects.get(id=request.session['edit_id'])
    try:
        recomendacionAjuste = RecomendacionAjuste.objects.get(recomendacionAjuste=documento)
        azimut_ajuste = recomendacionAjuste.azimutAjuste
        este_ajuste = recomendacionAjuste.esteAjuste
        norte_ajuste = recomendacionAjuste.norteAjuste
        cota_ajuste = recomendacionAjuste.cotaAjuste
        manteo_ajuste = recomendacionAjuste.manteoAjuste
    except RecomendacionAjuste.DoesNotExist:
        recomendacionAjuste = None
        azimut_ajuste = None
        este_ajuste = None
        norte_ajuste = None
        cota_ajuste = None
        manteo_ajuste = None
    try:
        recomendacionFinal = RecomendacionFinal.objects.get(recomendacionFinal=documento)
        este_final = recomendacionFinal.esteFinal
        norte_final = recomendacionFinal.norteFinal
        cota_final = recomendacionFinal.cotaFinal
        fecha_final = formatear_fecha(recomendacionFinal.fechaFinal)
    except RecomendacionFinal.DoesNotExist:
        recomendacionFinal = None
        este_final = None
        norte_final = None
        cota_final = None
        fecha_final = None

    # Manejo de la fecha de inicio
    if documento.fecha_inicio:
        fecha_inicio_formateada = make_aware(documento.fecha_inicio) if documento.fecha_inicio.tzinfo is None else documento.fecha_inicio
        fecha_inicio_str = fecha_inicio_formateada.strftime('%Y-%m-%d')
    else:
        fecha_inicio_str = ""

    # Formateo de los valores opcionales (evita errores si están en `None`)
    este_formateado = str(documento.este).rstrip('0').rstrip('.') if documento.este is not None else ""
    norte_formateado = str(documento.norte).rstrip('0').rstrip('.') if documento.norte is not None else ""
    cota_formateada = str(documento.cota).rstrip('0').rstrip('.') if documento.cota is not None else ""

    # Contexto con los datos formateados
    context = {
        'formeditar': FormRecomendaciones(instance=documento,initial={
            'campana': documento.campana,
            'programa': documento.programa,
            'recomendacion': documento.recomendacion,
            'pozo': documento.pozo,
            'sonda': documento.sonda,
            'fecha_inicio': fecha_inicio_str,
            'sector': documento.sector,
            'azimut': documento.azimut if documento.azimut is not None else "",
            'inclinacion': documento.inclinacion,
            'largo_programado': documento.largo_programado if documento.largo_programado is not None else "",
            'largo_real': 0,  # Siempre se mantiene como 0
            'este': este_formateado,
            'norte': norte_formateado,
            'cota': cota_formateada,
            'manteo': documento.manteo,
            'estado': documento.estado,
            },
            campana_disabled = True,
            programa_disabled = True,
        ),
        'formeditarajuste': FormRecomendacionesAjuste(initial={
            'azimutAjuste': azimut_ajuste,
            'esteAjuste': este_ajuste,
            'norteAjuste': norte_ajuste,
            'cotaAjuste': cota_ajuste,
            'manteoAjuste': manteo_ajuste,
            },
        ),
        'formeditarfinal': FormRecomendacionesFinal(initial={
            'esteFinal': este_final,
            'norteFinal': norte_final,
            'cotaFinal': cota_final,
            'fechaFinal': fecha_final,
            },
        ),
        'documento_id': documento.id,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_recomendacion',
        'sidebarmain': 'manage_system',
    }
    return render(request, 'pages/maintainer/drilling/edit_recomendacion.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_recomendacion(request):     
    if request.method == 'POST':
        try:
            recomendacion_id = request.POST.get('id')
            recomendacion = Recomendacion.objects.get(id=recomendacion_id)

            # Manejo seguro de la fecha
            fecha_inicio_raw = request.POST.get('fecha_inicio')
            fecha_inicio_aware = None
            if fecha_inicio_raw:
                try:
                    fecha_inicio_aware = make_aware(datetime.strptime(fecha_inicio_raw, '%Y-%m-%d'))
                except ValueError:
                    return JsonResponse({'success': False, 'message': 'Formato de fecha inválido.'})

            # Validación y conversión de valores numéricos
            azimut = request.POST.get('azimut')
            azimut = int(azimut) if azimut and azimut.strip() != "" else None
            if azimut is not None and (azimut < 0 or azimut > 360):
                return JsonResponse({'success': False, 'message': 'El azimut debe estar entre 0 y 360.'})

            inclinacion = request.POST.get('inclinacion')
            inclinacion = float(inclinacion) if inclinacion else None

            largo_programado = request.POST.get('largo_programado')
            largo_programado = float(largo_programado) if largo_programado else None

            largo_real = request.POST.get('largo_real')
            largo_real = float(largo_real) if largo_real else 0  # Siempre aseguramos que sea 0 si está vacío

            este = request.POST.get('este')
            este = float(este) if este else None

            norte = request.POST.get('norte')
            norte = float(norte) if norte else None

            cota = request.POST.get('cota')
            cota = float(cota) if cota else None
            
            manteo = request.POST.get('manteo')
            manteo = float(manteo) if manteo else None

            # Validación de la sonda
            sonda_id = request.POST.get('sonda')
            try:
                sonda = Sondas.objects.get(id=sonda_id)
            except Sondas.DoesNotExist:
                return JsonResponse({'success': False, 'message': 'La sonda seleccionada no existe.'})

            # Actualización en una sola consulta
            Recomendacion.objects.filter(id=recomendacion_id).update(
                recomendacion=request.POST.get('recomendacion'),
                pozo=request.POST.get('pozo'),
                sonda=sonda,
                fecha_inicio=fecha_inicio_aware,
                sector=request.POST.get('sector'),
                azimut=azimut,
                inclinacion=inclinacion,
                largo_programado=largo_programado,
                largo_real=largo_real,
                este=este,
                norte=norte,
                cota=cota,
                manteo=manteo,
                estado=request.POST.get('estado'),
                fechaUpdateEstado=datetime.now(),
            )
            return JsonResponse({'success': True, 'message': 'Recomendación actualizada con éxito.'})
        except Recomendacion.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'La recomendación no existe.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error inesperado: {str(e)}'})
    else:
        return redirect('edit_recomendacion')
    
@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_recomendacion_ajuste(request):
    if request.method == 'POST':
        recomendacion_id = request.POST.get('id')
        recomendacion = Recomendacion.objects.get(id=recomendacion_id)
        RecomendacionAjuste.objects.update_or_create(
            recomendacionAjuste=recomendacion,
            defaults={
                'azimutAjuste': request.POST.get('azimutAjuste'),
                'esteAjuste': request.POST.get('esteAjuste'),
                'norteAjuste': request.POST.get('norteAjuste'),
                'cotaAjuste': request.POST.get('cotaAjuste'),
                'manteoAjuste': request.POST.get('manteoAjuste'),
                'statusAjuste': True,
            }
        )
        return JsonResponse({'success': True, 'message': 'Recomendación actualizada con éxito.'})
    else:
        return redirect('edit_recomendacion')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_recomendacion_final(request):
    if request.method == 'POST':
        recomendacion_id = request.POST.get('id')
        recomendacion = Recomendacion.objects.get(id=recomendacion_id)
        RecomendacionFinal.objects.update_or_create(
            recomendacionFinal=recomendacion,
            defaults={
                'esteFinal': request.POST.get('esteFinal'),
                'norteFinal': request.POST.get('norteFinal'),
                'cotaFinal': request.POST.get('cotaFinal'),
                'fechaFinal': request.POST.get('fechaFinal'),
                'statusFinal': True,
            }
        )
        return JsonResponse({'success': True, 'message': 'Recomendación actualizada con éxito.'})
    else:
        return redirect('edit_recomendacion')
    
@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def update_estado_recomendacion(request):
    try:
        recomendacion_id = request.POST.get('id')
        nuevo_estado = request.POST.get('estado')
        
        recomendacion = Recomendacion.objects.get(id=recomendacion_id)
        recomendacion.estado = nuevo_estado
        
        # Opcional: Si el estado es "finalizado" o "abortado", ¿se debe considerar el status=False?
        # Por ahora solo actualizamos el campo 'estado' como pediste.
        recomendacion.save()
        
        return JsonResponse({'success': True, 'message': 'Estado actualizado correctamente.'})
    except Recomendacion.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Recomendación no encontrada.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})
    
def cargar_programas_por_campana(request):
    campana_id = request.GET.get('campana_id')
    if campana_id:
        programas = Programa.objects.filter(campana=campana_id,status=True)
        data = [{'id': programa.id, 'programa': programa.programa} for programa in programas]
        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({}, status=400)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_materiales_sonda(request): 
    lista = list(MaterialesSonda.objects.all().order_by('material'))  
    context = {
        'documentos': lista,
        'sidebarmenu': 'manage_materiales',
        'sidebarsubmenu': 'manage_materiales_sonda',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/checklist/manage_materiales_sonda.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_materiales_sonda(request):     
    context = {
        'formnuevo': FormMaterialesSonda,
        'sidebarmenu': 'manage_materiales',
        'sidebarsubmenu': 'manage_materiales_sonda',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/checklist/new_materiales_sonda.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_new_materiales_sonda(request):
    if request.method == 'POST':
        try: 
            materiales = MaterialesSonda.objects.get(material=request.POST['material'])
            return materiales
        except ObjectDoesNotExist:            
            formulario = FormMaterialesSonda(data=request.POST)
            if formulario.is_valid():       
                documento = MaterialesSonda(
                    material = request.POST['material'],
                    status = True,
                    creador = request.user.first_name+" "+request.user.last_name,
                )
                documento.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        messages.error(request, 'Error en la Acción')
        return redirect('manage_materiales_sonda')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def status_materiales_sonda(request):
    if request.method == 'POST': 
        materiales = MaterialesSonda.objects.get(id=request.POST['id'])
        if (materiales.status): 
            MaterialesSonda.objects.filter(id=request.POST['id']).update(status=False)
            messages.success(request, 'Material Deshabilitado Correctamente')  
        else:
            MaterialesSonda.objects.filter(id=request.POST['id']).update(status=True)
            messages.success(request, 'Material Habilitado Correctamente') 
        return redirect('manage_materiales_sonda')
    else:
        messages.error(request, 'Error en la Acción') 
        return redirect('manage_perforista') 

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def edit_materiales_sonda(request):  
    try:
        request.session['edit_id'] = request.POST['id']            
    except MultiValueDictKeyError:
        request.session['edit_id'] = request.session['edit_id']
    documento = MaterialesSonda.objects.get(id=request.session['edit_id'])
    context = {
        'formeditar':  FormMaterialesSonda(initial={
            'material': documento.material,
            },
        ),
        'documento_id': documento.id,
        'sidebarmenu': 'manage_materiales',
        'sidebarsubmenu': 'manage_materiales_sonda',
        'sidebarmain': 'manage_system',  
    }
    return render(request,'pages/maintainer/checklist/edit_materiales_sonda.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_materiales_sonda(request):     
    if request.method == 'POST':
        MaterialesSonda.objects.filter(id=request.POST['id']).update(material=request.POST['material'])
        return JsonResponse({'success': True})
    else:
        return redirect('edit_materiales_sonda')
    
@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_materiales_caseta(request): 
    lista = list(MaterialesCaseta.objects.all().order_by('material'))  
    context = {
        'documentos': lista,
        'sidebarmenu': 'manage_materiales',
        'sidebarsubmenu': 'manage_materiales_caseta',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/checklist/manage_materiales_caseta.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_materiales_caseta(request):     
    context = {
        'formnuevo': FormMaterialesCaseta,
        'sidebarmenu': 'manage_materiales',
        'sidebarsubmenu': 'manage_materiales_caseta',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/checklist/new_materiales_caseta.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_new_materiales_caseta(request):
    if request.method == 'POST':
        try: 
            material = MaterialesCaseta.objects.get(material=request.POST['material'])
            return material
        except ObjectDoesNotExist:            
            formulario = FormMaterialesCaseta(data=request.POST)
            if formulario.is_valid():       
                documento = MaterialesCaseta(
                    material = request.POST['material'],
                    status = True,
                    creador = request.user.first_name+" "+request.user.last_name,
                )
                documento.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        messages.error(request, 'Error en la Acción')
        return redirect('manage_materiales_caseta')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def status_materiales_caseta(request):
    if request.method == 'POST': 
        materiales = MaterialesCaseta.objects.get(id=request.POST['id'])
        if (materiales.status): 
            MaterialesCaseta.objects.filter(id=request.POST['id']).update(status=False)
            messages.success(request, 'Material Deshabilitado Correctamente')  
        else:
            MaterialesCaseta.objects.filter(id=request.POST['id']).update(status=True)
            messages.success(request, 'Material Habilitado Correctamente') 
        return redirect('manage_materiales_caseta')
    else:
        messages.error(request, 'Error en la Acción') 
        return redirect('manage_materiales_caseta') 

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def edit_materiales_caseta(request):
    try:
        request.session['edit_id'] = request.POST['id']            
    except MultiValueDictKeyError:
        request.session['edit_id'] = request.session['edit_id']
    documento = MaterialesCaseta.objects.get(id=request.session['edit_id'])
    context = {
        'formeditar':  FormMaterialesCaseta(initial={
            'material': documento.material,
            },
        ),
        'documento_id': documento.id,
        'sidebarmenu': 'manage_materiales',
        'sidebarsubmenu': 'manage_materiales_caseta',
        'sidebarmain': 'manage_system',  
    }
    return render(request,'pages/maintainer/checklist/edit_materiales_caseta.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_materiales_caseta(request):     
    if request.method == 'POST':
        MaterialesCaseta.objects.filter(id=request.POST['id']).update(material=request.POST['material'])
        return JsonResponse({'success': True})
    else:
        return redirect('edit_materiales_caseta')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_campanas(request): 
    lista = list(Campana.objects.all().order_by('campana'))  
    context = {
        'campanas': lista,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_campanas',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/manage_campanas.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_campana(request):     
    context = {
        'formnuevo': FormCampana,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_campanas',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/new_campana.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_new_campana(request):
    if request.method == 'POST':
        faena = Faena.objects.get(id=request.POST['faena'])
        try: 
            campana = Campana.objects.get(campana=request.POST['campana'])
            return campana
        except ObjectDoesNotExist:            
            formulario = FormCampana(data=request.POST)
            if formulario.is_valid():       
                documento = Campana(
                    campana = request.POST['campana'],
                    faena = faena,
                    metros = request.POST['metros'],
                    anoInicial = request.POST['anoInicial'],
                    anoFinal = request.POST['anoFinal'],
                    status = True,
                    creador = request.user.first_name+" "+request.user.last_name,
                )
                documento.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        messages.error(request, 'Error en la Acción')
        return redirect('manage_campanas')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def status_campana(request):
    if request.method == 'POST': 
        campana = Campana.objects.get(id=request.POST['id'])
        if (campana.status): 
            Campana.objects.filter(id=request.POST['id']).update(status=False)
            messages.success(request, 'Campaña Deshabilitada Correctamente')  
        else:
            Campana.objects.filter(id=request.POST['id']).update(status=True)
            messages.success(request, 'Campaña Habilitada Correctamente') 
        return redirect('manage_campanas')
    else:
        messages.error(request, 'Error en la Acción') 
        return redirect('manage_campanas') 

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def edit_campana(request):
    try:
        request.session['edit_id'] = request.POST['id']            
    except MultiValueDictKeyError:
        request.session['edit_id'] = request.session['edit_id']
    documento = Campana.objects.get(id=request.session['edit_id'])
    context = {
        'formeditar':  FormCampana(initial={
            'campana': documento.campana,
            'faena': documento.faena,
            'anoInicial': documento.anoInicial,
            'anoFinal': documento.anoFinal,
            'metros': documento.metros,
            },
        ),
        'documento_id': documento.id,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_campanas',
        'sidebarmain': 'manage_system',  
    }
    return render(request,'pages/maintainer/drilling/edit_campana.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_campana(request):     
    if request.method == 'POST':
        Campana.objects.filter(id=request.POST['id']).update(campana=request.POST['campana'])
        Campana.objects.filter(id=request.POST['id']).update(faena=request.POST['faena'])
        Campana.objects.filter(id=request.POST['id']).update(metros=request.POST['metros'])
        Campana.objects.filter(id=request.POST['id']).update(anoInicial=request.POST['anoInicial'])
        Campana.objects.filter(id=request.POST['id']).update(anoFinal=request.POST['anoFinal'])
        return JsonResponse({'success': True})
    else:
        return redirect('edit_campana')
    
@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_programas(request): 
    lista = list(Programa.objects.all().order_by('programa'))  
    context = {
        'programas': lista,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_programas',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/manage_programas.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def new_programa(request):     
    context = {
        'formnuevo': FormPrograma,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_programas',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/maintainer/drilling/new_programa.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_new_programa(request):
    if request.method == 'POST':
        try: 
            
            programa = Programa.objects.get(
                programa=request.POST['programa'], 
                campana_id=request.POST['campana']
            )
            
            return JsonResponse({'success': False, 'message': 'El nombre del programa ya existe en esta campaña.'})
        except ObjectDoesNotExist:            
            formulario = FormPrograma(data=request.POST)
            if formulario.is_valid():
                # 1. Obtener datos
                campana = Campana.objects.get(id=request.POST['campana'])
                metros_nuevos = int(request.POST['metros'])

                # 2. Calcular metros ya utilizados en esta campaña por otros programas activos
                metros_usados = Programa.objects.filter(
                    campana=campana, 
                    status=True
                ).aggregate(total=Sum('metros'))['total'] or 0

                # 3. Validar (AHORA CON 30% DE MARGEN EXTRA)
                
                # Calculamos el límite real (Los metros oficiales + 30%)
                limite_con_bono = campana.metros * 1.30  
                
                # Calculamos cuánto tendríamos en total si sumamos este nuevo programa
                total_proyectado = metros_usados + metros_nuevos

                # Si nos pasamos incluso del bono del 30%, lanzamos error
                if total_proyectado > limite_con_bono:
                    # Calculamos cuánto queda realmente para mostrarlo en el mensaje
                    disponible_real = limite_con_bono - metros_usados
                    
                    return JsonResponse({
                        'success': False, 
                        'message': f'Excede el límite (incluyendo el 30% extra). Disponibles: {int(disponible_real)} mts.'
                    })

                # 4. Guardar si pasa la validación
                documento = Programa(
                    campana = campana,
                    programa = request.POST['programa'],
                    metros = metros_nuevos,
                    status = True,
                    creador = request.user.first_name+" "+request.user.last_name,
                )
                documento.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        messages.error(request, 'Error en la Acción')
        return redirect('manage_programas')

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def status_programa(request):
    if request.method == 'POST': 
        programa = Programa.objects.get(id=request.POST['id'])
        if (programa.status): 
            Programa.objects.filter(id=request.POST['id']).update(status=False)
            messages.success(request, 'Programa Deshabilitado Correctamente')  
        else:
            Programa.objects.filter(id=request.POST['id']).update(status=True)
            messages.success(request, 'Programa Habilitado Correctamente') 
        return redirect('manage_programas')
    else:
        messages.error(request, 'Error en la Acción') 
        return redirect('manage_programas') 

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def edit_programa(request):
    try:
        request.session['edit_id'] = request.POST['id']            
    except MultiValueDictKeyError:
        request.session['edit_id'] = request.session['edit_id']
    documento = Programa.objects.get(id=request.session['edit_id'])
    context = {
        'formeditar':  FormPrograma(initial={
            'campana': documento.campana,
            'programa': documento.programa,
            'metros': documento.metros,
            },
        ),
        'documento_id': documento.id,
        'sidebarmenu': 'manage_drilling',
        'sidebarsubmenu': 'manage_programas',
        'sidebarmain': 'manage_system',  
    }
    return render(request,'pages/maintainer/drilling/edit_programa.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_programa(request):     
    if request.method == 'POST':
        # 1. Obtener datos
        programa_id = request.POST['id']
        campana_id = request.POST['campana']
        metros_nuevos = int(request.POST['metros'])
        nombre_programa = request.POST['programa']

        campana = Campana.objects.get(id=campana_id)

        # 2. Calcular metros usados por OTROS programas en esta campaña (excluyendo el actual)
        metros_usados = Programa.objects.filter(
            campana=campana, 
            status=True
        ).exclude(id=programa_id).aggregate(total=Sum('metros'))['total'] or 0

        # 3. Validar
        metros_disponibles = campana.metros - metros_usados
        if metros_nuevos > metros_disponibles:
            return JsonResponse({
                'success': False, 
                'message': f'Error: La campaña tiene {metros_disponibles} mts disponibles. Intentas asignar {metros_nuevos} mts.'
            })

        # 4. Actualizar (Optimizado en una sola consulta)
        Programa.objects.filter(id=programa_id).update(
            campana=campana,
            programa=nombre_programa,
            metros=metros_nuevos
        )
        return JsonResponse({'success': True})
    else:
        return redirect('edit_programa')
   

def error_400(request, exception):
    template = 'errors/400_logged_in.html' if request.user.is_authenticated else 'errors/400.html'
    return render(request, template, status=400)

def error_403(request, exception):
    template = 'errors/403_logged_in.html' if request.user.is_authenticated else 'errors/403.html'
    return render(request, template, status=403)

def error_404(request, exception):
    template = 'errors/404_logged_in.html' if request.user.is_authenticated else 'errors/404.html'
    return render(request, template, status=404)

def error_413(request, exception):
    template = 'errors/413_logged_in.html' if request.user.is_authenticated else 'errors/413.html'
    return render(request, template, status=413)

def error_500(request):
    template = 'errors/500_logged_in.html' if request.user.is_authenticated else 'errors/500.html'
    return render(request, template, status=500)
