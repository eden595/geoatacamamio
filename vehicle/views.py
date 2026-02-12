from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.datastructures import MultiValueDictKeyError
from django.http import JsonResponse
from django.core import serializers
from django.template.loader import get_template, render_to_string
from xhtml2pdf import pisa
from threading import Thread
from rut_chile import rut_chile
import datetime
from .forms import (FormNuevoVehiculo, FormInformacionTecnica, FormInfraccionesVehiculo, FormNuevoKilometraje, FormNuevaFuelCards, FormMarcaSomnolencia,
                    FormModeloSomnolencia, FormAyudaTecnicaVehiculo)
from .models import (Vehiculo, DocumentacionesVehiculo, InformacionTecnicaVehiculo, InfraccionesVehiculo, NuevoKilometraje, NuevaTarjetaCombustible,
                    MarcaSomnolencia, ModeloSomnolencia, AyudaTecnicaVehiculo)
from mining.models import VehiculoAsignado
from maintenance.models import NuevaSolicitudMantenimiento
from core.choices import progreso, tipocombustible, tipodocumento
from core.utils import procesar_fotografia, validar_campo_vacio, formatear_fecha, extension_archivo, check_and_convert_pdf
from core.models import Tipo, Ano, Marca, Modelo, Color, Faena, OcultarOpcionesVehiculo
from user.models import UsuarioProfile
from django.core.exceptions import ObjectDoesNotExist
import os
from django.conf import settings
from messenger.views import notificacion_vehiculos_email, notificacion_mantenedor_email
from core.decorators import admin_or_jefe_mantencion_or_supervisor_required, admin_required
from django.utils import timezone
from django.db.models import Q, F
from django.middleware.csrf import get_token
from django.urls import reverse

@login_required
@admin_required
def new_vehicle(request): 
    context = {
        'formnuevovehiculo': FormNuevoVehiculo,   
        'sidebar': 'manage_vehicles',
        'sidebarmain': 'system_vehicles',
    }
    return render(request,'pages/vehicle/new_vehicle.html', context)

@login_required
@admin_or_jefe_mantencion_or_supervisor_required
def manage_vehicles(request):
    usuario = UsuarioProfile.objects.get(user=request.user.id)

    # --- LÓGICA SERVER-SIDE (AJAX) ---
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        
        # 1. Parámetros
        draw = int(request.GET.get('draw', 1))
        start = int(request.GET.get('start', 0))
        length = int(request.GET.get('length', 10))
        search_value = request.GET.get('search[value]', '')
        
        estado_param = request.GET.get('estado')
        es_habilitado = True if estado_param == 'true' else False
        
        order_column_index = int(request.GET.get('order[0][column]', 0))
        order_direction = request.GET.get('order[0][dir]', 'desc')

        # 2. Query
        base_queryset = VehiculoAsignado.objects.filter(
            status=True,
            vehiculo__status=es_habilitado
        ).select_related('vehiculo', 'vehiculo__tipo', 'vehiculo__marca', 'vehiculo__modelo', 'faena')

        if usuario.faena.faena != "SIN ASIGNAR":
            base_queryset = base_queryset.filter(faena=usuario.faena)

        # 3. Búsqueda
        if search_value:
            base_queryset = base_queryset.filter(
                Q(vehiculo__placaPatente__icontains=search_value) |
                Q(vehiculo__tipo__tipo__icontains=search_value) |
                Q(vehiculo__marca__marca__icontains=search_value) |
                Q(vehiculo__modelo__modelo__icontains=search_value) |
                Q(faena__faena__icontains=search_value)
            )

        # 4. Ordenamiento
        if es_habilitado:
            # Habilitados: 0:Expander, 1:%, 2:Patente, 3:Tipo, 4:Marca, 5:Modelo, 6:Faena, 7:Estado, 8:Acciones
            column_mapping = {
                1: 'vehiculo__completado',
                2: 'vehiculo__placaPatente',
                3: 'vehiculo__tipo__tipo',
                4: 'vehiculo__marca__marca',
                5: 'vehiculo__modelo__modelo',
                6: 'faena__faena',
                7: 'vehiculo__status'
            }
        else:
            # Deshabilitados: 0:Expander, 1:%, 2:Patente, 3:Tipo, 4:Marca, 5:Modelo, 6:Estado, 7:Acciones
            column_mapping = {
                1: 'vehiculo__completado',
                2: 'vehiculo__placaPatente',
                3: 'vehiculo__tipo__tipo',
                4: 'vehiculo__marca__marca',
                5: 'vehiculo__modelo__modelo',
                6: 'vehiculo__status'
            }

        col_name = column_mapping.get(order_column_index)
        if col_name:
            if order_direction == 'desc':
                base_queryset = base_queryset.order_by(f'-{col_name}')
            else:
                base_queryset = base_queryset.order_by(col_name)
        else:
            base_queryset = base_queryset.order_by('-fechacreacion')

        # 5. Data
        total_records = base_queryset.count()
        records_filtered = total_records 
        page_items = base_queryset[start:start+length]

        data = []
        csrf_token = get_token(request)
        
        url_edit = reverse('edit_vehicle_profile')
        url_status = reverse('status_vehicle')
        try: url_assign = reverse('edit_vehicle_mining')
        except: url_assign = "#"

        for asignacion in page_items:
            vehiculo = asignacion.vehiculo
            
            # Badge
            pct = vehiculo.completado or 0
            badge_cls = 'success' if pct > 80 else 'danger' if pct < 50 else 'warning'
            badge_html = f'<div class="btn btn-{badge_cls}" style="cursor:default; width:100%">{pct}%</div>'

            # Botones
            btns = '<div class="form-inline-btn" style="display:flex; gap:3px;">'
            btns += f'''<form action="{url_edit}" method="POST"><input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}"><input type="hidden" name="placaPatente" value="{vehiculo.placaPatente}"><button type="submit" class="btn btn-info btn-size-edit">Editar</button></form>'''
            
            if es_habilitado:
                btns += f'''<form action="{url_assign}" method="POST"><input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}"><input type="hidden" name="placaPatente" value="{vehiculo.placaPatente}"><button type="submit" class="btn btn-success btn-size-edit">Asignar</button></form>'''
            
            btns += f'''<form class="vehicle-form" id="form-{vehiculo.placaPatente}" method="POST"><input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}"><input type="hidden" name="placaPatente" value="{vehiculo.placaPatente}"><button type="submit" class="btn btn-warning btn-size-edit">Pdf</button></form>'''
            
            if request.user.role == "ADMINISTRADOR":
                st_cls = 'danger' if vehiculo.status else 'primary'
                st_txt = 'Deshabilitar' if vehiculo.status else 'Habilitar'
                btns += f'''<form class="status-form" action="{url_status}" method="POST"><input type="hidden" name="csrfmiddlewaretoken" value="{csrf_token}"><input type="hidden" name="id" value="{vehiculo.id}"><button type="submit" class="btn btn-{st_cls} btn-size-adm">{st_txt}</button></form>'''
            
            btns += '</div>'

            row = {
                "porcentaje": badge_html,
                "patente": vehiculo.placaPatente,
                "tipo": vehiculo.tipo.tipo if vehiculo.tipo else "",
                "marca": vehiculo.marca.marca if vehiculo.marca else "",
                "modelo": vehiculo.modelo.modelo if vehiculo.modelo else "",
                "estado": "Habilitado" if vehiculo.status else "Deshabilitado",
                "acciones": btns
            }
            if es_habilitado:
                row["faena"] = asignacion.faena.faena

            data.append(row)

        return JsonResponse({
            "draw": draw,
            "recordsTotal": total_records,
            "recordsFiltered": records_filtered,
            "data": data
        })

    # Carga Normal
    context = {
        'sidebar': 'manage_vehicles',
        'sidebarmain': 'system_vehicles',  
    }
    return render(request,'pages/vehicle/manage_vehicles.html', context)

@login_required
@admin_required
def save_new_vehicle(request): 
    if request.method == 'POST':    
        tipo_instancia = Tipo.objects.get(pk=request.POST['tipo'])    
        ano_instancia = Ano.objects.get(pk=request.POST['ano'])  
        marca_instancia = Marca.objects.get(pk=request.POST['marca'])  
        modelo_instancia = Modelo.objects.get(pk=request.POST['modelo'])  
        color_instancia = Color.objects.get(pk=request.POST['color'])  
        formulario = FormNuevoVehiculo(data=request.POST)
        placaPatente = request.POST['placaPatente'].upper()
        fechaAdquisicion = validar_campo_vacio('fechaAdquisicion',request)
        if rut_chile.is_valid_rut(request.POST['rutPropietario']):
            if formulario.is_valid():               
                vehiculo = Vehiculo(
                    placaPatente = placaPatente,
                    fechaAdquisicion = fechaAdquisicion,
                    tenencia = request.POST['tenencia'],
                    nombrePropietario = request.POST['nombrePropietario'],
                    rutPropietario = request.POST['rutPropietario'],
                    domicilio = request.POST['domicilio'],
                    tipo = tipo_instancia,
                    ano = ano_instancia,
                    marca = marca_instancia,
                    modelo = modelo_instancia,
                    numeroMotor = request.POST['numeroMotor'],
                    numeroChasis = request.POST['numeroChasis'],
                    numeroVin = request.POST['numeroVin'],
                    color = color_instancia,
                    fechaVencimientoPermisoCirculacion = request.POST['fechaVencimientoPermisoCirculacion'],
                    fechaVencimientoRevisionTecnica = request.POST['fechaVencimientoRevisionTecnica'],
                    fechaVencimientoSeguroObligatorio = request.POST['fechaVencimientoSeguroObligatorio'],
                    #fechaInstalacionGps = fechaInstalacionGps,
                    status = True,
                )    
                vehiculo.save()
                
                #crea el vehiculo y le asigna la faena "SIN ASIGNAR"
                fecha_hoy = datetime.date.today().strftime('%Y-%m-%d')
                vehiculo_faena = Vehiculo.objects.get(placaPatente=placaPatente)
                faena = Faena.objects.get(faena='SIN ASIGNAR')
                vehiculo_actual = VehiculoAsignado(
                    vehiculo = vehiculo_faena,
                    faena = faena,
                    faenaAnterior = "SIN ASIGNAR",
                    creador = request.user.first_name+' ' +request.user.last_name,
                    fechaInicial = fecha_hoy,
                    status = True,
                )
                vehiculo_actual.save()                  
                
                notificacion_vehiculos_email(request, vehiculo_faena, "creado")
                messages.success(request, 'Vehículo Creado Correctamente', extra_tags='Recuerda completar la documentación')
                return redirect('manage_vehicles')          
            else:                
                messages.error(request, 'Error en el Formulario', extra_tags='Vuelva a Intentarlo')
                context = {
                    'formnuevovehiculo': formulario,       
                    'sidebar': 'manage_vehicles',
                    'sidebarmain': 'system_vehicles',     
                }         
                return render(request,'pages/vehicle/new_vehicle.html',context)
        else: 
            messages.error(request, "Rut incorrecto", extra_tags='Vuelva a intentarlo')
            context = {
                    'formnuevovehiculo': formulario,       
                    'sidebar': 'manage_vehicles',
                    'sidebarmain': 'system_vehicles',     
                }         
            return render(request,'pages/vehicle/new_vehicle.html',context)             
    else:
        return redirect('new_vehicle')

@login_required
@admin_required
def status_vehicle(request):
    if request.method == 'POST': 
        try:
            # Obtenemos el vehículo por ID
            vehiculo_id = request.POST.get('id')
            vehiculo = Vehiculo.objects.get(id=vehiculo_id)
            
            # Si el vehículo está ACTIVO y se quiere DESHABILITAR
            if (vehiculo.status):
                # Buscamos la asignación activa actual
                asignacion_activa = VehiculoAsignado.objects.filter(vehiculo=vehiculo, status=True).last()
                
                # VALIDACIÓN: Si tiene asignación Y esa asignación NO es "SIN ASIGNAR"
                if asignacion_activa and asignacion_activa.faena.faena != "SIN ASIGNAR":
                    return JsonResponse({
                        'success': False, 
                        'message': f'No se puede deshabilitar. El vehículo está operando en: {asignacion_activa.faena.faena}. Debe desasignarlo primero.'
                    })

                # Si pasa la validación (está en SIN ASIGNAR o no tiene asignación), deshabilitamos
                Vehiculo.objects.filter(id=vehiculo_id).update(status=False)
                #notificacion_vehiculos_email(request, vehiculo, "deshabilitado")
                return JsonResponse({'success': True, 'message': 'Vehículo Deshabilitado Correctamente'})
            
            else:            
                # Si está deshabilitado, lo HABILITAMOS
                Vehiculo.objects.filter(id=vehiculo_id).update(status=True) 
                #notificacion_vehiculos_email(request, vehiculo, "habilitado")
                return JsonResponse({'success': True, 'message': 'Vehículo Habilitado Correctamente'})
                
        except Vehiculo.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'El vehículo no existe.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': f'Error interno: {str(e)}'})
            
    return JsonResponse({'success': False, 'message': 'Método no permitido'})

@login_required
@admin_or_jefe_mantencion_or_supervisor_required
def edit_vehicle_profile(request):
        try:
            request.session['edit_placaPatente'] = request.POST['placaPatente']            
        except MultiValueDictKeyError:
            request.session['edit_placaPatente'] = request.session['edit_placaPatente']
        vehiculo = Vehiculo.objects.get(placaPatente=request.session['edit_placaPatente'])
        vehiculoDocumentacion = DocumentacionesVehiculo.objects.get(vehiculo_id=vehiculo.id)
        vehiculoInformacion = InformacionTecnicaVehiculo.objects.get(vehiculo_id=vehiculo.id)
        infracciones = InfraccionesVehiculo.objects.filter(vehiculo=vehiculo).order_by('-fechaInfraccion')
        solicitudesMantenimiento = NuevaSolicitudMantenimiento.objects.filter(vehiculo=vehiculo).order_by('-fechacreacion')
        tipo_actual = Tipo.objects.filter(tipo=vehiculo.tipo)
        marca_actual = Marca.objects.filter(marca=vehiculo.marca)
        modelo_actual = Modelo.objects.filter(modelo=vehiculo.modelo)
        ano_actual = Ano.objects.filter(ano=vehiculo.ano)
        color_actual = Color.objects.filter(color=vehiculo.color)
        ####### procesa y elimina la fotografia actual y la reemplaza por la default (si corresponde)
        urlFotografiaPadron = vehiculoDocumentacion.fotografiaPadron
        urlFotografiaPermisoCirculacion = vehiculoDocumentacion.fotografiaPermisoCirculacion
        urlFotografiaRevisionTecnica = vehiculoDocumentacion.fotografiaRevisionTecnica
        urlFotografiaRevisionTecnicaGases = vehiculoDocumentacion.fotografiaRevisionTecnicaGases
        urlFotografiaSeguroObligatorio = vehiculoDocumentacion.fotografiaSeguroObligatorio
        urlFotografiaCertificadoGps = vehiculoDocumentacion.fotografiaCertificadoGps
        urlFotografiaCertificadoMantencion = vehiculoDocumentacion.fotografiaCertificadoMantencion
        urlFotografiaCertificadoOperatividad = vehiculoDocumentacion.fotografiaCertificadoOperatividad
        urlFotografiaCertificadoGrua = vehiculoDocumentacion.fotografiaCertificadoGrua
        urlFotografiaFacturaCompra = vehiculoDocumentacion.fotografiaFacturaCompra
        urlFotografiaSeguroAutomotriz = vehiculoDocumentacion.fotografiaSeguroAutomotriz
        urlFotografiaCertificadoLamina = vehiculoDocumentacion.fotografiaCertificadoLamina
        urlFotografiaCertificadoBarraAntiVuelco = vehiculoDocumentacion.fotografiaCertificadoBarraAntiVuelco
        urlFotografiaDocumentacionMiniBus = vehiculoDocumentacion.fotografiaDocumentacionMiniBus
        urlFotografiaCertificadoVarios = vehiculoDocumentacion.fotografiaCertificadoVarios
        urlFotografiaExteriorFrontis = vehiculoDocumentacion.fotografiaExteriorFrontis
        urlFotografiaExteriorAtras = vehiculoDocumentacion.fotografiaExteriorAtras
        urlFotografiaExteriorPiloto = vehiculoDocumentacion.fotografiaExteriorPiloto
        urlFotografiaExteriorCopiloto = vehiculoDocumentacion.fotografiaExteriorCopiloto
        urlFotografiaInteriorTablero = vehiculoDocumentacion.fotografiaInteriorTablero
        urlFotografiaInteriorCopiloto = vehiculoDocumentacion.fotografiaInteriorCopiloto
        urlFotografiaInteriorAtrasPiloto = vehiculoDocumentacion.fotografiaInteriorAtrasPiloto
        urlFotografiaInteriorAtrasCopiloto = vehiculoDocumentacion.fotografiaInteriorAtrasCopiloto
        ####### recupera el tipo de archivo segun su extension
        extensionFotografiaPadron = extension_archivo(urlFotografiaPadron)
        extensionFotografiaPermisoCirculacion = extension_archivo(urlFotografiaPermisoCirculacion)
        extensionFotografiaRevisionTecnica = extension_archivo(urlFotografiaRevisionTecnica)
        extensionFotografiaRevisionTecnicaGases = extension_archivo(urlFotografiaRevisionTecnicaGases)
        extensionFotografiaSeguroObligatorio = extension_archivo(urlFotografiaSeguroObligatorio)
        extensionFotografiaCertificadoGps = extension_archivo(urlFotografiaCertificadoGps)
        extensionFotografiaCertificadoMantencion = extension_archivo(urlFotografiaCertificadoMantencion)
        extensionFotografiaCertificadoOperatividad = extension_archivo(urlFotografiaCertificadoOperatividad)
        extensionFotografiaCertificadoGrua = extension_archivo(urlFotografiaCertificadoGrua)
        extensionFotografiaFacturaCompra = extension_archivo(urlFotografiaFacturaCompra)
        extensionFotografiaSeguroAutomotriz = extension_archivo(urlFotografiaSeguroAutomotriz)
        extensionFotografiaCertificadoLamina = extension_archivo(urlFotografiaCertificadoLamina)
        extensionFotografiaCertificadoBarraAntiVuelco = extension_archivo(urlFotografiaCertificadoBarraAntiVuelco)
        extensionFotografiaDocumentacionMiniBus = extension_archivo(urlFotografiaDocumentacionMiniBus)
        extensionFotografiaCertificadoVarios = extension_archivo(urlFotografiaCertificadoVarios)
        extensionFotografiaExteriorFrontis = extension_archivo(urlFotografiaExteriorFrontis)
        extensionFotografiaExteriorAtras = extension_archivo(urlFotografiaExteriorAtras)
        extensionFotografiaExteriorPiloto = extension_archivo(urlFotografiaExteriorPiloto)
        extensionFotografiaExteriorCopiloto = extension_archivo(urlFotografiaExteriorCopiloto)
        extensionFotografiaInteriorTablero = extension_archivo(urlFotografiaInteriorTablero)
        extensionFotografiaInteriorCopiloto = extension_archivo(urlFotografiaInteriorCopiloto)
        extensionFotografiaInteriorAtrasPiloto = extension_archivo(urlFotografiaInteriorAtrasPiloto)
        extensionFotografiaInteriorAtrasCopiloto = extension_archivo(urlFotografiaInteriorAtrasCopiloto)
        ####### formatea fecha para enviarlas al template
        fecha_adquisicion = formatear_fecha(vehiculo.fechaAdquisicion)
        fecha_arriendo_inicial = formatear_fecha(vehiculo.fechaArriendoInicial)
        fecha_arriendo_final = formatear_fecha(vehiculo.fechaArriendoFinal)
        fecha_vencimiento_permiso_circulacion = formatear_fecha(vehiculo.fechaVencimientoPermisoCirculacion)
        fecha_vencimiento_revision_tecnica = formatear_fecha(vehiculo.fechaVencimientoRevisionTecnica)
        fecha_vencimiento_seguro_obligatorio = formatear_fecha(vehiculo.fechaVencimientoSeguroObligatorio)
        fecha_instalacion_gps = formatear_fecha(vehiculo.fechaInstalacionGps)
        fecha_vencimiento_lamina = formatear_fecha(vehiculo.fechaVencimientoLamina)
        fecha_vencimiento_transporte_privado = formatear_fecha(vehiculo.fechaVencimientoTransportePrivado)
        fecha_instalacion_barraantivuelco = formatear_fecha(vehiculo.fechaInstalacionBarraAntiVuelco)
        fecha_certificado_operatividad = formatear_fecha(vehiculo.fechaCertificadoOperatividad)
        fecha_certificado_mantencion = formatear_fecha(vehiculo.fechaCertificadoMantencion)
        fecha_certificado_grua = formatear_fecha(vehiculo.fechaCertificadoGrua)
        
        kilometrajes = NuevoKilometraje.objects.filter(vehiculo=vehiculo).order_by('-fechacreacion')
        try:
            tarjeta_combustible = NuevaTarjetaCombustible.objects.get(vehiculo=vehiculo, actual=True)
            tarjeta = tarjeta_combustible.numeroTarjeta
        except NuevaTarjetaCombustible.DoesNotExist:
            tarjeta = "Sin Tarjeta"
            
        ocultar_fechaAdquisicion = False
        ocultar_fechaArriendoInicial = False
        ocultar_fechaArriendoFinal = False
        
        try:
            modeloDispositivo = AyudaTecnicaVehiculo.objects.get(vehiculo=vehiculo)
            dispositivo = modeloDispositivo.dispositivo
            proveedor = modeloDispositivo.proveedor
        except AyudaTecnicaVehiculo.DoesNotExist:
            dispositivo = None
            proveedor = None
        
        ####### context        
        context = {
            'numero_placaPatente': vehiculo.placaPatente,
            'sidebar': 'manage_vehicles',
            'sidebarmain': 'system_vehicles',
            'vehiculo': vehiculo,
            'infracciones': infracciones,
            'kilometrajes': kilometrajes,
            'forminfracciones': FormInfraccionesVehiculo,
            'solicitudesMantenimiento': solicitudesMantenimiento,
            'choicesprogreso': progreso,
            'formnuevovehiculo': FormNuevoVehiculo(initial={
                'placaPatente': vehiculo.placaPatente,
                'tenencia': vehiculo.tenencia,
                'fechaAdquisicion': fecha_adquisicion,
                'fechaArriendoInicial': fecha_arriendo_inicial,
                'fechaArriendoFinal': fecha_arriendo_final,
                'nombrePropietario': vehiculo.nombrePropietario,
                'rutPropietario': vehiculo.rutPropietario,
                'domicilio': vehiculo.domicilio,
                'tipo': vehiculo.tipo,
                'ano': vehiculo.ano,
                'marca': vehiculo.marca,
                'modelo': vehiculo.modelo,
                'numeroMotor': vehiculo.numeroMotor,
                'numeroChasis': vehiculo.numeroChasis,
                'numeroVin': vehiculo.numeroVin,
                'color': vehiculo.color,
                'fechaVencimientoPermisoCirculacion': fecha_vencimiento_permiso_circulacion,
                'fechaVencimientoRevisionTecnica': fecha_vencimiento_revision_tecnica,
                'fechaVencimientoSeguroObligatorio': fecha_vencimiento_seguro_obligatorio,
                'fechaInstalacionGps': fecha_instalacion_gps,
                'fechaVencimientoLamina': fecha_vencimiento_lamina,
                'fechaVencimientoTransportePrivado': fecha_vencimiento_transporte_privado,
                'fechaInstalacionBarraAntiVuelco': fecha_instalacion_barraantivuelco,
                'fechaCertificadoOperatividad': fecha_certificado_operatividad,
                'fechaCertificadoMantencion': fecha_certificado_mantencion,
                'fechaCertificadoGrua': fecha_certificado_grua,
                'tieneTag': vehiculo.tieneTag,
                'tarjetaCombustible': tarjeta,
                },
                placaPatente_disabled=True,
                tipo_actual=tipo_actual,
                marca_actual=marca_actual,
                modelo_actual=modelo_actual,
                ano_actual=ano_actual,
                color_actual=color_actual,
                ocultar_fechaAdquisicion = ocultar_fechaAdquisicion,
                ocultar_fechaArriendoInicial = ocultar_fechaArriendoInicial,
                ocultar_fechaArriendoFinal = ocultar_fechaArriendoFinal,
                ocultar_fechaInstalacionGps = False,
                ocultar_fechaVencimientoLamina = False,
                ocultar_fechaVencimientoTransportePrivado = False,
                ocultar_fechaInstalacionBarraAntiVuelco= False,
                ocultar_fechaCertificadoOperatividad = False,
                ocultar_fechaCertificadoMantencion = False,
                ocultar_fechaCertificadoGrua = False,
                ocultar_tieneTag = False,
                ocultar_tarjetaCombustible = False,
            ),    
            'forminformaciontecnicavehiculo': FormInformacionTecnica(initial={
                'tipoTraccion': vehiculoInformacion.tipoTraccion,
                'pesoBrutoVehicular': vehiculoInformacion.pesoBrutoVehicular,
                'capacidadCarga': vehiculoInformacion.capacidadCarga,
                'tipoNeumatico': vehiculoInformacion.tipoNeumatico,
                'tipoAceiteMotor': vehiculoInformacion.tipoAceiteMotor,
                'tipoRefrigeranteMotor': vehiculoInformacion.tipoRefrigeranteMotor,
                'tipoFiltroAireMotor': vehiculoInformacion.tipoFiltroAireMotor,
                'tipoFiltroCombustible': vehiculoInformacion.tipoFiltroCombustible,
                'frecuenciaMantenimiento': vehiculoInformacion.frecuenciaMantenimiento,
                'proximoMantenimiento': vehiculoInformacion.proximoMantenimiento,
                'proximoMantenimientoGrua': vehiculoInformacion.proximoMantenimientoGrua,
                }
            ),
            'formayudatecnicavehiculo': FormAyudaTecnicaVehiculo(initial={
                'dispositivo': dispositivo,
                'proveedor': proveedor,
                }
            ),
            'fotografiaPadron': vehiculoDocumentacion.fotografiaPadron,
            'fotografiaPermisoCirculacion': vehiculoDocumentacion.fotografiaPermisoCirculacion,
            'fotografiaRevisionTecnica': vehiculoDocumentacion.fotografiaRevisionTecnica,
            'fotografiaRevisionTecnicaGases': vehiculoDocumentacion.fotografiaRevisionTecnicaGases,
            'fotografiaSeguroObligatorio': vehiculoDocumentacion.fotografiaSeguroObligatorio,
            'fotografiaCertificadoGps': vehiculoDocumentacion.fotografiaCertificadoGps,
            'fotografiaCertificadoMantencion': vehiculoDocumentacion.fotografiaCertificadoMantencion,
            'fotografiaCertificadoOperatividad': vehiculoDocumentacion.fotografiaCertificadoOperatividad,
            'fotografiaCertificadoGrua': vehiculoDocumentacion.fotografiaCertificadoGrua,
            'fotografiaFacturaCompra': vehiculoDocumentacion.fotografiaFacturaCompra,
            'fotografiaSeguroAutomotriz': vehiculoDocumentacion.fotografiaSeguroAutomotriz,
            'fotografiaCertificadoLamina': vehiculoDocumentacion.fotografiaCertificadoLamina,
            'fotografiaCertificadoBarraAntiVuelco': vehiculoDocumentacion.fotografiaCertificadoBarraAntiVuelco,
            'fotografiaDocumentacionMiniBus': vehiculoDocumentacion.fotografiaDocumentacionMiniBus,  
            'fotografiaCertificadoVarios': vehiculoDocumentacion.fotografiaCertificadoVarios,
            'fotografiaExteriorFrontis': vehiculoDocumentacion.fotografiaExteriorFrontis,
            'fotografiaExteriorAtras': vehiculoDocumentacion.fotografiaExteriorAtras,
            'fotografiaExteriorPiloto': vehiculoDocumentacion.fotografiaExteriorPiloto,
            'fotografiaExteriorCopiloto': vehiculoDocumentacion.fotografiaExteriorCopiloto,
            'fotografiaInteriorTablero': vehiculoDocumentacion.fotografiaInteriorTablero,
            'fotografiaInteriorCopiloto': vehiculoDocumentacion.fotografiaInteriorCopiloto,
            'fotografiaInteriorAtrasPiloto': vehiculoDocumentacion.fotografiaInteriorAtrasPiloto,
            'fotografiaInteriorAtrasCopiloto': vehiculoDocumentacion.fotografiaInteriorAtrasCopiloto,
            'extensionFotografiaPadron': extensionFotografiaPadron,
            'extensionFotografiaPermisoCirculacion': extensionFotografiaPermisoCirculacion,
            'extensionFotografiaRevisionTecnica': extensionFotografiaRevisionTecnica,
            'extensionFotografiaRevisionTecnicaGases': extensionFotografiaRevisionTecnicaGases,
            'extensionFotografiaSeguroObligatorio': extensionFotografiaSeguroObligatorio,
            'extensionFotografiaCertificadoGps': extensionFotografiaCertificadoGps,
            'extensionFotografiaCertificadoMantencion': extensionFotografiaCertificadoMantencion,
            'extensionFotografiaCertificadoOperatividad': extensionFotografiaCertificadoOperatividad,
            'extensionFotografiaCertificadoGrua': extensionFotografiaCertificadoGrua,
            'extensionFotografiaFacturaCompra': extensionFotografiaFacturaCompra,
            'extensionFotografiaSeguroAutomotriz': extensionFotografiaSeguroAutomotriz,
            'extensionFotografiaCertificadoLamina': extensionFotografiaCertificadoLamina,
            'extensionFotografiaCertificadoBarraAntiVuelco': extensionFotografiaCertificadoBarraAntiVuelco,
            'extensionFotografiaDocumentacionMiniBus': extensionFotografiaDocumentacionMiniBus,
            'extensionFotografiaCertificadoVarios': extensionFotografiaCertificadoVarios,
            'extensionFotografiaExteriorFrontis': extensionFotografiaExteriorFrontis,
            'extensionFotografiaExteriorAtras': extensionFotografiaExteriorAtras,
            'extensionFotografiaExteriorPiloto': extensionFotografiaExteriorPiloto,
            'extensionFotografiaExteriorCopiloto': extensionFotografiaExteriorCopiloto,
            'extensionFotografiaInteriorTablero': extensionFotografiaInteriorTablero,
            'extensionFotografiaInteriorCopiloto': extensionFotografiaInteriorCopiloto,
            'extensionFotografiaInteriorAtrasPiloto': extensionFotografiaInteriorAtrasPiloto,
            'extensionFotografiaInteriorAtrasCopiloto': extensionFotografiaInteriorAtrasCopiloto,            
        }
        return render(request,'pages/vehicle/edit_vehicle_profile.html', context)

@login_required
@admin_or_jefe_mantencion_or_supervisor_required
def save_edit_vehicle_profile(request):  
    if request.method == 'POST':
        fechaAdquisicion = validar_campo_vacio('fechaAdquisicion',request)
        fechaArriendoInicial = validar_campo_vacio('fechaArriendoInicial',request)
        fechaArriendoFinal = validar_campo_vacio('fechaArriendoFinal',request)
        fechaInstalacionGps  = validar_campo_vacio('fechaInstalacionGps',request)
        fechaCertificadoMantencion = validar_campo_vacio('fechaCertificadoMantencion',request)
        fechaCertificadoOperatividad = validar_campo_vacio('fechaCertificadoOperatividad',request)
        fechaCertificadoGrua = validar_campo_vacio('fechaCertificadoGrua',request)
        fechaVencimientoLamina = validar_campo_vacio('fechaVencimientoLamina',request)
        fechaVencimientoTransportePrivado = validar_campo_vacio('fechaVencimientoTransportePrivado',request)
        fechaInstalacionBarraAntiVuelco = validar_campo_vacio('fechaInstalacionBarraAntiVuelco',request)
        tieneTag = validar_campo_vacio('tieneTag',request)
        tarjetaCombustible = validar_campo_vacio('tarjetaCombustible',request)
        pesoBrutoVehicular = validar_campo_vacio('pesoBrutoVehicular',request)
        capacidadCarga =  validar_campo_vacio('capacidadCarga',request)
        tipoNeumatico =  validar_campo_vacio('tipoNeumatico',request)
        tipoAceiteMotor =  validar_campo_vacio('tipoAceiteMotor',request)
        tipoRefrigeranteMotor =  validar_campo_vacio('tipoRefrigeranteMotor',request)
        tipoFiltroAireMotor =  validar_campo_vacio('tipoFiltroAireMotor',request)
        tipoFiltroCombustible =  validar_campo_vacio('tipoFiltroCombustible',request)
        frecuenciaMantenimiento =  validar_campo_vacio('frecuenciaMantenimiento',request)
        proximoMantenimiento =  validar_campo_vacio('proximoMantenimiento',request)
        proximoMantenimientoGrua =  validar_campo_vacio('proximoMantenimientoGrua',request)
            
        if rut_chile.is_valid_rut(request.POST['rutPropietario']):
                vehicle_update_fields = {
                    'tenencia': request.POST['tenencia'],
                    'fechaAdquisicion': fechaAdquisicion,
                    'fechaArriendoInicial': fechaArriendoInicial,
                    'fechaArriendoFinal': fechaArriendoFinal,
                    'nombrePropietario': request.POST['nombrePropietario'],
                    'rutPropietario': request.POST['rutPropietario'],
                    'domicilio': request.POST['domicilio'],
                    'tipo': request.POST['tipo'],
                    'ano': request.POST['ano'],
                    'marca': request.POST['marca'],
                    'modelo': request.POST['modelo'],
                    'numeroMotor': request.POST['numeroMotor'],
                    'numeroChasis': request.POST['numeroChasis'],
                    'numeroVin': request.POST['numeroVin'],
                    'color': request.POST['color'],
                    'fechaVencimientoPermisoCirculacion': request.POST['fechaVencimientoPermisoCirculacion'],
                    'fechaVencimientoRevisionTecnica': request.POST['fechaVencimientoRevisionTecnica'],
                    'fechaVencimientoSeguroObligatorio': request.POST['fechaVencimientoSeguroObligatorio'],
                    'fechaInstalacionGps': fechaInstalacionGps,
                    'fechaCertificadoMantencion': fechaCertificadoMantencion,
                    'fechaCertificadoOperatividad': fechaCertificadoOperatividad,
                    'fechaCertificadoGrua': fechaCertificadoGrua,
                    'fechaVencimientoLamina': fechaVencimientoLamina,
                    'fechaVencimientoTransportePrivado': fechaVencimientoTransportePrivado,
                    'fechaInstalacionBarraAntiVuelco': fechaInstalacionBarraAntiVuelco,
                    'tieneTag': tieneTag,
                    'tarjetaCombustible': tarjetaCombustible
                }
                Vehiculo.objects.filter(placaPatente=request.POST['numero_placaPatente']).update(**vehicle_update_fields)
                
                vehiculo = Vehiculo.objects.get(placaPatente=request.POST['numero_placaPatente'])
                
                InformacionTecnicaVehiculo.objects.filter(vehiculo=vehiculo).update(
                    tipoTraccion=request.POST['tipoTraccion'],
                    pesoBrutoVehicular=pesoBrutoVehicular,
                    capacidadCarga=capacidadCarga,
                    tipoNeumatico=tipoNeumatico,
                    tipoAceiteMotor=tipoAceiteMotor,
                    tipoRefrigeranteMotor=tipoRefrigeranteMotor,
                    tipoFiltroAireMotor=tipoFiltroAireMotor,
                    tipoFiltroCombustible=tipoFiltroCombustible,
                    frecuenciaMantenimiento=frecuenciaMantenimiento,
                    proximoMantenimiento=proximoMantenimiento,
                    proximoMantenimientoGrua=proximoMantenimientoGrua,
                )
                
                try:
                    proveedor_id = request.POST.get('proveedor')  # Obtiene el ID del proveedor o None si no viene
                    if proveedor_id:
                        try:
                            proveedor = MarcaSomnolencia.objects.get(id=proveedor_id)
                        except MarcaSomnolencia.DoesNotExist:
                            print(f"Error: El proveedor con ID {proveedor_id} no existe.")
                            proveedor = None
                    else:
                        proveedor = None  # Si no se envió proveedor, asigna None
                    # Convertir el dispositivo a booleano
                    dispositivo = request.POST.get('dispositivo') == 'true'
                    # Si el dispositivo es False, el proveedor debe ser None
                    if not dispositivo:
                        proveedor = None
                    AyudaTecnicaVehiculo.objects.update_or_create(
                        vehiculo=vehiculo,
                        defaults={
                            "dispositivo": dispositivo,
                            "proveedor": proveedor,
                            "creador": f"{request.user.first_name} {request.user.last_name}",
                            "status": True
                        }
                    )

                except Exception as e:
                    print(f"Error en la actualización o creación: {e}")


                
                documentacionVehiculo = DocumentacionesVehiculo.objects.get(vehiculo_id=vehiculo.id)                  
                toggle_padron = request.POST.get('toggle-Padron', 'no')
                procesar_fotografia(documentacionVehiculo, toggle_padron, 'fotografiaPadron','documentacion_vehiculo/no-imagen.png', request)                
                toggle_permiso_circulacion = request.POST.get('toggle-PermisoCirculacion', 'no')
                procesar_fotografia(documentacionVehiculo, toggle_permiso_circulacion, 'fotografiaPermisoCirculacion','documentacion_vehiculo/no-imagen.png', request)                
                toggle_RevisionTecnica = request.POST.get('toggle-RevisionTecnica', 'no')
                procesar_fotografia(documentacionVehiculo, toggle_RevisionTecnica, 'fotografiaRevisionTecnica','documentacion_vehiculo/no-imagen.png', request)                
                toggle_RevisionTecnicaGases = request.POST.get('toggle-RevisionTecnicaGases', 'no')
                procesar_fotografia(documentacionVehiculo, toggle_RevisionTecnicaGases, 'fotografiaRevisionTecnicaGases','documentacion_vehiculo/no-imagen.png', request)                
                toggle_SeguroObligatorio = request.POST.get('toggle-SeguroObligatorio', 'no')
                procesar_fotografia(documentacionVehiculo, toggle_SeguroObligatorio, 'fotografiaSeguroObligatorio','documentacion_vehiculo/no-imagen.png', request)                
                toggle_CertificadoGps = request.POST.get('toggle-CertificadoGps', 'no')
                procesar_fotografia(documentacionVehiculo, toggle_CertificadoGps, 'fotografiaCertificadoGps','documentacion_vehiculo/no-imagen.png', request)    
                
                toggle_CertificadoMantencion = request.POST.get('toggle-CertificadoMantencion', 'no')
                procesar_fotografia(documentacionVehiculo, toggle_CertificadoMantencion, 'fotografiaCertificadoMantencion','documentacion_vehiculo/no-imagen.png', request)
                toggle_CertificadoOperatividad = request.POST.get('toggle-CertificadoOperatividad', 'no')
                procesar_fotografia(documentacionVehiculo, toggle_CertificadoOperatividad, 'fotografiaCertificadoOperatividad','documentacion_vehiculo/no-imagen.png', request)    
                toggle_CertificadoGrua = request.POST.get('toggle-CertificadoGrua', 'no')
                procesar_fotografia(documentacionVehiculo, toggle_CertificadoGrua, 'fotografiaCertificadoGrua','documentacion_vehiculo/no-imagen.png', request) 
                toggle_FacturaCompra = request.POST.get('toggle-FacturaCompra', 'no')
                procesar_fotografia(documentacionVehiculo, toggle_FacturaCompra, 'fotografiaFacturaCompra','documentacion_vehiculo/no-imagen.png', request)                
                toggle_SeguroAutomotriz = request.POST.get('toggle-SeguroAutomotriz', 'no')
                procesar_fotografia(documentacionVehiculo, toggle_SeguroAutomotriz, 'fotografiaSeguroAutomotriz','documentacion_vehiculo/no-imagen.png', request)                
                toggle_CertificadoLamina = request.POST.get('toggle-CertificadoLamina', 'no')
                procesar_fotografia(documentacionVehiculo, toggle_CertificadoLamina, 'fotografiaCertificadoLamina','documentacion_vehiculo/no-imagen.png', request)                
                toggle_CertificadoBarraAntiVuelco = request.POST.get('toggle-CertificadoBarraAntiVuelco', 'no')
                procesar_fotografia(documentacionVehiculo, toggle_CertificadoBarraAntiVuelco, 'fotografiaCertificadoBarraAntiVuelco','documentacion_vehiculo/no-imagen.png', request)                
                toggle_DocumentacionMiniBus = request.POST.get('toggle-DocumentacionMiniBus', 'no')
                procesar_fotografia(documentacionVehiculo, toggle_DocumentacionMiniBus, 'fotografiaDocumentacionMiniBus','documentacion_vehiculo/no-imagen.png', request)  
                toggle_CertificadoVarios = request.POST.get('toggle-CertificadoVarios', 'no')
                procesar_fotografia(documentacionVehiculo, toggle_CertificadoVarios, 'fotografiaCertificadoVarios','documentacion_vehiculo/no-imagen.png', request)                
                toggle_InteriorTablero = request.POST.get('toggle-InteriorTablero', 'no')
                procesar_fotografia(documentacionVehiculo, toggle_InteriorTablero, 'fotografiaInteriorTablero','documentacion_vehiculo/no-imagen-vehiculo.png', request)                
                toggle_InteriorCopiloto = request.POST.get('toggle-InteriorCopiloto', 'no')
                procesar_fotografia(documentacionVehiculo, toggle_InteriorCopiloto, 'fotografiaInteriorCopiloto','documentacion_vehiculo/no-imagen-vehiculo.png', request)                
                toggle_InteriorAtrasPiloto = request.POST.get('toggle-InteriorAtrasPiloto', 'no')
                procesar_fotografia(documentacionVehiculo, toggle_InteriorAtrasPiloto, 'fotografiaInteriorAtrasPiloto','documentacion_vehiculo/no-imagen-vehiculo.png', request)                
                toggle_InteriorAtrasCopiloto = request.POST.get('toggle-InteriorAtrasCopiloto', 'no')
                procesar_fotografia(documentacionVehiculo, toggle_InteriorAtrasCopiloto, 'fotografiaInteriorAtrasCopiloto','documentacion_vehiculo/no-imagen-vehiculo.png', request)                
                toggle_ExteriorFrontis = request.POST.get('toggle-ExteriorFrontis', 'no')
                procesar_fotografia(documentacionVehiculo, toggle_ExteriorFrontis, 'fotografiaExteriorFrontis','documentacion_vehiculo/no-imagen-vehiculo.png', request)                
                toggle_ExteriorAtras = request.POST.get('toggle-ExteriorAtras', 'no')
                procesar_fotografia(documentacionVehiculo, toggle_ExteriorAtras, 'fotografiaExteriorAtras','documentacion_vehiculo/no-imagen-vehiculo.png', request)                
                toggle_ExteriorPiloto = request.POST.get('toggle-ExteriorPiloto', 'no')
                procesar_fotografia(documentacionVehiculo, toggle_ExteriorPiloto, 'fotografiaExteriorPiloto','documentacion_vehiculo/no-imagen-vehiculo.png', request)                
                toggle_ExteriorCopiloto = request.POST.get('toggle-ExteriorCopiloto', 'no')
                procesar_fotografia(documentacionVehiculo, toggle_ExteriorCopiloto, 'fotografiaExteriorCopiloto','documentacion_vehiculo/no-imagen-vehiculo.png', request)
                
                documentacionVehiculo.save()
                
                informacionTecnicaVehiculo = InformacionTecnicaVehiculo.objects.get(vehiculo_id=vehiculo.id)   
                
                campos_completos_vehiculo, total_campos_vehiculo = vehiculo.calcular_completitud_vehiculo()
                campos_completos_informacion, total_campos_informacion = informacionTecnicaVehiculo.calcular_completitud_informacion_tecnica()
                campos_completos_documentacion, total_campos_documentacion = documentacionVehiculo.calcular_completitud_documentaciones()
                
                campos_completos = 16 + campos_completos_vehiculo + campos_completos_informacion + campos_completos_documentacion
                total_campos = 16 + total_campos_vehiculo + total_campos_informacion + total_campos_documentacion
                porcentaje_completitud = (campos_completos / total_campos) * 100
                Vehiculo.objects.filter(placaPatente=request.POST['numero_placaPatente']).update(completado=porcentaje_completitud)
                
                notificacion_vehiculos_email(request, vehiculo, "actualizado")
                messages.success(request, 'Datos Actualizados Correctamente') 
                return redirect('manage_vehicles') 
        else: 
            messages.error(request, "Rut incorrecto", extra_tags='Vuelva a intentarlo')
            context = {      
                    'sidebar': 'manage_vehicles',
                    'sidebarmain': 'system_vehicles',     
                }         
            return render(request,'pages/vehicle/edit_vehicle_profile.html', context)        

@login_required
@admin_or_jefe_mantencion_or_supervisor_required
def hide_options_vehicle(request):
    if request.method == 'POST':
        tipo = request.POST['tipo_vehiculo']
        opciones = OcultarOpcionesVehiculo.objects.get(tipo_vehiculo=tipo)
        opciones_dict = serializers.serialize('python', [opciones])[0]['fields']      
        data = {
            'opciones': opciones_dict,
        }
        return JsonResponse(data)
    else:
        return JsonResponse({'error': 'Solicitud no válida'}, status=400)

@login_required
@admin_required
def save_penalty(request):
    if request.method == 'POST':
        vehiculo = Vehiculo.objects.get(placaPatente=request.POST['patente'])
        infraccion = InfraccionesVehiculo(
            vehiculo = vehiculo,
            fechaInfraccion = request.POST['fecha'],
            ciudadInfraccion = request.POST['ciudad'], 
            infraccion = request.POST['infraccion'],
            estadoPagoInfraccion = request.POST['estado'],
            valorInfraccion = request.POST['valor'],            
        )
        infraccion.save()
        return JsonResponse({'success': 'Multa Creada'}, status=200)
    else:
        return JsonResponse({'error': 'Solicitud no válida'}, status=400)

@login_required    
def new_kilometraje_register(request):
    usuario = UsuarioProfile.objects.get(user=request.user.id)
    if usuario.faena.faena == "SIN ASIGNAR":
        vehiculos = Vehiculo.objects.filter(status=True).exclude(tipo=7).order_by('-placaPatente')
    else:
        asignados = VehiculoAsignado.objects.filter(faena=usuario.faena, status=True).exclude(vehiculo__tipo=7).order_by('-vehiculo')
        vehiculos = [asignado.vehiculo for asignado in asignados]
    context = {
        'formnuevokilometraje': FormNuevoKilometraje(vehiculos=vehiculos),   
        'sidebar': 'new_kilometraje_register',
        'sidebarmain': 'system_vehicles',
    }
    return render(request,'pages/vehicle/new_kilometraje.html', context)

@login_required
def save_new_kilometraje_register(request):
    if request.method == 'POST':
        #formulario = FormNuevoKilometraje(data=request.POST)
        vehiculo = Vehiculo.objects.get(id= request.POST['vehiculo'])   
        registro = NuevoKilometraje(
            vehiculo = vehiculo,
            kilometraje = request.POST['kilometraje'],
            creador = request.user.first_name+" "+request.user.last_name,
            origen = "Formulario"
        )
        registro.save()             
        return JsonResponse({'success': True})
    else:
        return redirect('new_kilometraje_register')

@login_required
def vehicle_pdf_view(request):
    if request.method == 'POST':
        vehiculo = get_object_or_404(Vehiculo, placaPatente=request.POST['placaPatente'])
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
                return JsonResponse({'error': 'Error al generar el PDF'})

        pdf_url = os.path.join(settings.MEDIA_URL, 'pdfs_temp', filename)
        return JsonResponse({'pdf_url': pdf_url, 'message': 'Documento creado con éxito'})
    else:
        return redirect('manage_vehicles')

@login_required
@admin_required
def report_vehicles_kilometrajes(request): 
    context = {
        'sidebar': 'report_vehicles_kilometrajes',
        'sidebarmain': 'system_report_vehicles',
    }
    return render(request,'pages/vehicle/report/report_vehicles_kilometrajes.html', context)

@login_required
@admin_required
def report_vehicles_general(request): 
    context = {
        'sidebar': 'report_vehicles_general',
        'sidebarmain': 'system_report_vehicles',
    }
    return render(request,'pages/vehicle/report/report_vehicles_general.html', context)

@login_required
@admin_required
def report_vehicles_faenas(request): 
    context = {
        'sidebar': 'report_vehicles_faenas',
        'sidebarmain': 'system_report_vehicles',
    }
    return render(request,'pages/vehicle/report/report_vehicles_faenas.html', context)

@login_required
@admin_required
def report_vehicles_camionetas_ano(request): 
    context = {
        'sidebar': 'report_vehicles_camionetas_ano',
        'sidebarmain': 'system_report_vehicles',
    }
    return render(request,'pages/vehicle/report/report_vehicles_camionetas_ano.html', context)

@login_required
@admin_required
def report_vehicles_camionetas_faenas(request): 
    context = {
        'sidebar': 'report_vehicles_camionetas_faenas',
        'sidebarmain': 'system_report_vehicles',
    }
    return render(request,'pages/vehicle/report/report_vehicles_camionetas_faenas.html', context)

@login_required
@admin_or_jefe_mantencion_or_supervisor_required
def manage_fuel_cards(request):
    usuario = UsuarioProfile.objects.get(user=request.user.id)
    
    if usuario.faena.faena == "SIN ASIGNAR":
        tarjeta = list(NuevaTarjetaCombustible.objects.filter(actual=True).order_by('-fechacreacion'))
    else:
        tarjeta = list(NuevaTarjetaCombustible.objects.filter(faena=usuario.faena, actual=True).order_by('-fechacreacion')) 

    completados = Vehiculo.objects.all()

    context = {
        'tarjetas': tarjeta,  # 🔹 Solo tarjetas actuales
        'porcentajes': completados,
        'sidebar': 'manage_fuel_cards',
        'sidebarmain': 'system_vehicles',  
    }
    return render(request, 'pages/vehicle/manage_fuel_cards.html', context)

@login_required
@admin_required
def new_fuel_cards(request):

    form = FormNuevaFuelCards(user=request.user)  # 🔹 Pasamos el usuario al formulario
     
    context = {
        'formnuevafuelcards': form,
        'sidebar': 'manage_fuel_cards',
        'sidebarmain': 'system_vehicles',
    }
    return render(request,'pages/vehicle/new_fuel_cards.html', context)

def cargar_informacion_vehiculo(request):
    vehiculo_id = request.GET.get('vehiculo_id')
    vehiculo = Vehiculo.objects.get(id=vehiculo_id)
    faena = VehiculoAsignado.objects.get(vehiculo=vehiculo, status=True)
    data = {
        'faena': faena.faena.faena,
        'placaPatente': vehiculo.placaPatente,
        'tipoVehiculo': vehiculo.tipo.tipo,
        'nombrePropietario': vehiculo.nombrePropietario,
        'rutPropietario': vehiculo.rutPropietario,
    }
    return JsonResponse(data, safe=False)

@login_required
@admin_required
def save_new_fuel_cards(request): 
    if request.method == 'POST':
        vehiculo = Vehiculo.objects.get(id=request.POST['vehiculo'])
        # Obtener el vehículo
        vehiculo_id = int(request.POST['vehiculo'])  
        vehiculo = get_object_or_404(Vehiculo, id=vehiculo_id)
        # Verificar si ya existe una tarjeta para este vehículo
        if NuevaTarjetaCombustible.objects.filter(vehiculo=vehiculo).exists():
            return JsonResponse({'success': False, 'error': 'Este vehículo ya tiene una tarjeta registrada.'}, status=400)
        form = FormNuevaFuelCards(request.POST)
        if form.is_valid():
            nueva_tarjeta = form.save(commit=False)
            nueva_tarjeta.patente = vehiculo.placaPatente
            nueva_tarjeta.actual = True
            nueva_tarjeta.status = True
            nueva_tarjeta.creador = request.user.first_name+" "+request.user.last_name
            nueva_tarjeta.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)         
    else:
        return redirect('new_fuel_cards')

@login_required 
@admin_required
def status_fuel_cards(request):
    if request.method == 'POST': 
        tarjeta = NuevaTarjetaCombustible.objects.get(id=request.POST['id'])
        if (tarjeta.status): 
            NuevaTarjetaCombustible.objects.filter(id=request.POST['id']).update(status=False)
            notificacion_mantenedor_email(request,tarjeta,'secciones','deshabilitada')  
            messages.success(request, 'seccion Deshabilitado Correctamente')  
        else:
            NuevaTarjetaCombustible.objects.filter(id=request.POST['id']).update(status=True)
            notificacion_mantenedor_email(request,tarjeta,'secciones','habilitada')  
            messages.success(request, 'seccion Habilitado Correctamente') 
        return redirect('manage_fuel_cards')

@login_required
@admin_or_jefe_mantencion_or_supervisor_required
def edit_fuel_card(request, card_id):
    try:
        tarjeta = NuevaTarjetaCombustible.objects.get(id=card_id)
    except NuevaTarjetaCombustible.DoesNotExist:
        return redirect('manage_fuel_cards')

    form = FormNuevaFuelCards(instance=tarjeta)

    # 🔹 Obtener historial de tarjetas de la misma patente, excluyendo la actual

    historial_tarjetas = NuevaTarjetaCombustible.objects.filter(patente=tarjeta.patente).order_by('-fechacreacion')
    context = {
        'form': form,
        'tarjeta': tarjeta,
        'historial_tarjetas': historial_tarjetas,  # 🔹 Historial filtrado
    }

    return render(request, 'pages/vehicle/edit_fuel_card.html', context)

@login_required
@admin_or_jefe_mantencion_or_supervisor_required
def save_edit_fuel_card(request, card_id):
    try:
        tarjeta_actual = NuevaTarjetaCombustible.objects.get(id=card_id)
    except NuevaTarjetaCombustible.DoesNotExist:
        return JsonResponse({'success': False, 'error': "La tarjeta de combustible no existe."}, status=404)

    if request.method == 'POST':
        form = FormNuevaFuelCards(request.POST)
        if form.is_valid():
            # 🔹 Desactivar el registro actual (pasarlo a historial)
            tarjeta_actual.actual = False
            tarjeta_actual.save()

            # 🔹 Crear un nuevo registro con los datos editados y `actual=True`
            vehiculo = Vehiculo.objects.get(id=request.POST['vehiculo'])
            nueva_tarjeta = form.save(commit=False)
            nueva_tarjeta.patente = vehiculo.placaPatente
            nueva_tarjeta.actual = True
            nueva_tarjeta.status = True
            nueva_tarjeta.creador = request.user.first_name+" "+request.user.last_name
            nueva_tarjeta.save()
            Vehiculo.objects.filter(id=request.POST['vehiculo']).update(tarjetaCombustible=request.POST['numeroTarjeta'])

            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)

    return redirect('edit_fuel_card', card_id=card_id)

@login_required
def fuel_cards_pdf_view(request):
    if request.method == 'POST':
        tarjeta = get_object_or_404(NuevaTarjetaCombustible, id=request.POST['id']) 
        current_datetime = datetime.datetime.now()
        context = {
            'tarjeta': tarjeta,
            'user_role': request.user.role,
            'current_datetime': current_datetime,
        }
        template_path = 'pages/pdfs/card_pdf_template.html'
        template = get_template(template_path)
        html = template.render(context)
        filename = f'{tarjeta.patente}-{current_datetime.strftime("%Y%m%d_%H%M%S")}.pdf'
        pdf_path = os.path.join(settings.MEDIA_ROOT, 'pdfs_cards_temp', filename)
        os.makedirs(os.path.dirname(pdf_path), exist_ok=True)

        with open(pdf_path, 'wb') as pdf_file:
            pisa_status = pisa.CreatePDF(html, dest=pdf_file)
            if pisa_status.err:
                return JsonResponse({'error': 'Error al generar el PDF'})

        pdf_url = os.path.join(settings.MEDIA_URL, 'pdfs_cards_temp', filename)
        return JsonResponse({'pdf_url': pdf_url, 'message': 'Documento creado con éxito'})
    else:
        return redirect('manage_fuel_cards')

@login_required
def manage_brand_sleepiness(request): 
    lista = list(MarcaSomnolencia.objects.all().order_by('marca'))  
    context = {
        'dispositivos': lista,
        'sidebarmenu': 'manage_vehicles',
        'sidebarsubmenu': 'manage_sleepiness',
        'sidebarsubsubmenu': 'manage_brand_sleepiness',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/vehicle/manage_brand_sleepiness.html', context)

@login_required
def new_brand_sleepiness(request):     
    context = {
        'formnuevamarca': FormMarcaSomnolencia,
        'sidebarmenu': 'manage_vehicles',
        'sidebarsubmenu': 'manage_sleepiness',
        'sidebarsubsubmenu': 'manage_brand_sleepiness',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/vehicle/new_brand_sleepiness.html', context)

@login_required
def save_new_brand_sleepiness(request):
    if request.method == 'POST':
        try: 
            marca = MarcaSomnolencia.objects.get(marca=request.POST['marca'])
            return marca
        except ObjectDoesNotExist:            
            formulario = FormMarcaSomnolencia(data=request.POST)
            if formulario.is_valid():       
                documento = MarcaSomnolencia(
                    marca = request.POST['marca'],
                    status = True,
                    creador = request.user.first_name+" "+request.user.last_name,
                )
                documento.save()
                return JsonResponse({'success': True})
            else:
                return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        messages.error(request, 'Error en la Acción')
        return redirect('manage_brand_sleepiness')

@login_required
def status_brand_sleepiness(request):
    if request.method == 'POST': 
        marca = MarcaSomnolencia.objects.get(id=request.POST['id'])
        if (marca.status): 
            MarcaSomnolencia.objects.filter(id=request.POST['id']).update(status=False)
            messages.success(request, 'Proveedor de Equipo Deshabilitado Correctamente')  
        else:
            MarcaSomnolencia.objects.filter(id=request.POST['id']).update(status=True)
            messages.success(request, 'Proveedor de Equipo Habilitado Correctamente') 
        return redirect('manage_brand_sleepiness')
    else:
        messages.error(request, 'Error en la Acción') 
        return redirect('manage_brand_sleepiness') 

@login_required
def edit_brand_sleepiness(request):  
    try:
        request.session['edit_id'] = request.POST['id']            
    except MultiValueDictKeyError:
        request.session['edit_id'] = request.session['edit_id']
    documento = MarcaSomnolencia.objects.get(id=request.session['edit_id'])
    context = {
        'formeditar':  FormMarcaSomnolencia(initial={
            'marca': documento.marca,
            },
        ),
        'documento_id': documento.id,
        'sidebarmenu': 'manage_vehicles',
        'sidebarsubmenu': 'manage_sleepiness',
        'sidebarsubsubmenu': 'manage_brand_sleepiness',
        'sidebarmain': 'manage_system',  
    }
    return render(request,'pages/vehicle/edit_brand_sleepiness.html', context)

@login_required
def save_edit_brand_sleepiness(request):     
    if request.method == 'POST':
        MarcaSomnolencia.objects.filter(id=request.POST['id']).update(marca=request.POST['marca'])
        return JsonResponse({'success': True})
    else:
        return redirect('edit_brand_sleepiness')

@login_required
def manage_model_sleepiness(request): 
    lista = list(ModeloSomnolencia.objects.all().order_by('marca'))  
    context = {
        'dispositivos': lista,
        'sidebarmenu': 'manage_vehicles',
        'sidebarsubmenu': 'manage_sleepiness',
        'sidebarsubsubmenu': 'manage_model_sleepiness',
        'sidebarmain': 'manage_system', 
    }
    return render(request,'pages/vehicle/manage_model_sleepiness.html', context)

@login_required
def new_model_sleepiness(request):     
    context = {
        'formnuevomodelo': FormModeloSomnolencia,
        'sidebarmenu': 'manage_vehicles',
        'sidebarsubmenu': 'manage_sleepiness',
        'sidebarsubsubmenu': 'manage_model_sleepiness',
        'sidebarmain': 'manage_system',
    }
    return render(request,'pages/vehicle/new_model_sleepiness.html', context)

@login_required
def save_new_model_sleepiness(request):
    if request.method == 'POST':
        marca = MarcaSomnolencia.objects.get(id=request.POST['marca'])
        formulario = FormModeloSomnolencia(data=request.POST)
        if formulario.is_valid():       
            documento = ModeloSomnolencia(
                marca = marca,
                modelo = request.POST['modelo'],
                status = True,
                creador = request.user.first_name+" "+request.user.last_name,
            )
            documento.save()
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        messages.error(request, 'Error en la Acción')
        return redirect('manage_model_sleepiness')

@login_required
def status_model_sleepiness(request):
    if request.method == 'POST': 
        modelo = ModeloSomnolencia.objects.get(id=request.POST['id'])
        if (modelo.status): 
            ModeloSomnolencia.objects.filter(id=request.POST['id']).update(status=False)
            messages.success(request, 'Modelo Somnolencia Deshabilitada Correctamente')  
        else:
            ModeloSomnolencia.objects.filter(id=request.POST['id']).update(status=True)
            messages.success(request, 'Modelo Somnolencia Habilitada Correctamente') 
        return redirect('manage_model_sleepiness')
    else:
        messages.error(request, 'Error en la Acción') 
        return redirect('manage_model_sleepiness') 

@login_required
def edit_model_sleepiness(request):  
    try:
        request.session['edit_id'] = request.POST['id']            
    except MultiValueDictKeyError:
        request.session['edit_id'] = request.session['edit_id']
    documento = ModeloSomnolencia.objects.get(id=request.session['edit_id'])
    context = {
        'formeditar':  FormModeloSomnolencia(initial={
            'zapata': documento.zapata,
            },
        ),
        'documento_id': documento.id,
        'sidebarmenu': 'manage_vehicles',
        'sidebarsubmenu': 'manage_sleepiness',
        'sidebarsubsubmenu': 'manage_model_sleepiness',
        'sidebarmain': 'manage_system',  
    }
    return render(request,'pages/vehicle/edit_model_sleepiness.html', context)

@login_required
def save_edit_model_sleepiness(request):     
    if request.method == 'POST':
        ModeloSomnolencia.objects.filter(id=request.POST['id']).update(modelo=request.POST['modelo'])
        return JsonResponse({'success': True})
    else:
        return redirect('edit_model_sleepiness')

@login_required
@admin_or_jefe_mantencion_or_supervisor_required
def manage_vehicles_por_faena(request):
    usuario = UsuarioProfile.objects.get(user=request.user.id)
    faena_data = Faena.objects.get(faena=request.POST['faena'])
    if usuario.faena.faena == "SIN ASIGNAR":
        vehiculos = list(VehiculoAsignado.objects.filter(faena=faena_data, status=True).order_by('-fechacreacion'))
        #completados = Vehiculo.objects.filter(status=True)
        completados = Vehiculo.objects.all()
    else:
        vehiculos = list(VehiculoAsignado.objects.filter(faena__in=[usuario.faena, faena_data], status=True).order_by('-fechacreacion'))

        #completados = Vehiculo.objects.filter(status=True)
        completados = Vehiculo.objects.all()

    context = {
        'vehiculos': vehiculos,
        'porcentajes': completados,
        'sidebar': 'manage_vehicles',
        'sidebarmain': 'system_vehicles',  
    }
    return render(request,'pages/vehicle/manage_vehicles.html', context)

@login_required
@admin_or_jefe_mantencion_or_supervisor_required
def manage_vehicles_por_tipo(request):
    usuario = UsuarioProfile.objects.get(user=request.user.id)
    faena_data = Faena.objects.get(faena=request.POST['faena'])
    tipo_data = Tipo.objects.get(tipo=request.POST['tipo'])
    if usuario.faena.faena == "SIN ASIGNAR":
        vehiculos = list(VehiculoAsignado.objects.filter(faena=faena_data, vehiculo__tipo=tipo_data, status=True).order_by('-fechacreacion'))
        #completados = Vehiculo.objects.filter(status=True)
        completados = Vehiculo.objects.all()
    else:
        vehiculos = list(VehiculoAsignado.objects.filter(faena__in=[usuario.faena, faena_data], vehiculo__tipo=tipo_data, status=True).order_by('-fechacreacion')) 
        #completados = Vehiculo.objects.filter(status=True)
        completados = Vehiculo.objects.all()

    context = {
        'vehiculos': vehiculos,
        'porcentajes': completados,
        'sidebar': 'manage_vehicles',
        'sidebarmain': 'system_vehicles',  
    }
    return render(request,'pages/vehicle/manage_vehicles.html', context)

@login_required
@admin_required
def update_penalty(request):
    if request.method == 'POST':
        try:
            infraccion_id = request.POST.get('id')
            nuevo_estado = request.POST.get('estado')
            nuevo_valor = request.POST.get('valor', '0')
            
            nuevo_valor_limpio = ''.join(filter(str.isdigit, str(nuevo_valor))) or '0'

            infraccion = InfraccionesVehiculo.objects.get(pk=infraccion_id)

            if infraccion.estadoPagoInfraccion in ['Pagada', 'Anulada']:
                return JsonResponse({
                    'success': False, 
                    'error': 'No es posible editar una infracción que ya está Pagada o Anulada.'
                }, status=403)
                
            infraccion.estadoPagoInfraccion = nuevo_estado
            infraccion.valorInfraccion = int(nuevo_valor_limpio)
            infraccion.save()
            
            return JsonResponse({'success': True})
        except InfraccionesVehiculo.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Infracción no encontrada'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    return JsonResponse({'error': 'Método no permitido'}, status=405)