from django.shortcuts import render, redirect, get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.utils.datastructures import MultiValueDictKeyError
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from core.decorators import sondaje_admin_or_base_datos_or_supervisor_required, admin_required
from .models import ChecklistMaterialesSonda, ChecklistMaterialesCaseta, EstadoEtapasReporteDigital
from .forms import ChecklistMaterialesSondaEntradaForm, ChecklistMaterialesSondaSalidaForm, ChecklistMaterialesCasetaFormTop, ChecklistMaterialesCasetaFormBottom
from core.forms import FormMaterialesCaseta, FormMaterialesSonda
from core.models import MaterialesCaseta, MaterialesSonda, Sondajes, Sondas
from core.choices import jornada, turno
from django.db.models import Max
from django.http import Http404
from django.utils.dateparse import parse_datetime

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_checklist_materiales_sonda(request): 
    lista = ChecklistMaterialesSonda.objects.values('id_checklist', 'fecha_checklist', 'turno', 'jornada', 'creador').distinct().order_by('-fecha_checklist')
    context = {
        'documentos': lista,
        'sidebar': 'manage_checklist_materiales_sonda',
        'sidebarmain': 'system_checklist', 
    }
    return render(request,'pages/checklist/manage_materiales_sonda.html', context)

@login_required
def save_checklist_materiales_sonda_entrada(request):
    if request.method == 'POST':
        form = ChecklistMaterialesSondaEntradaForm(request.POST)
        if form.is_valid():
            try:
                jornada = '1' #forzamos "Inicio jornada" para no confiar en el POST
                turno = form.cleaned_data['turno_entrada']
                fecha_checklist = form.cleaned_data['fecha_checklist_entrada']
                sonda_entrada = form.cleaned_data['sonda_entrada']
                sonda_entrada = Sondas.objects.get(sonda=sonda_entrada)
                sondaje_entrada = form.cleaned_data['sondaje_entrada']
                sondaje_entrada = Sondajes.objects.get(sondaje=sondaje_entrada)
                serie_entrada = form.cleaned_data['serie_entrada']
                estado_entrada = form.cleaned_data['estado_entrada']
                etapa = "Entrada"
                progreso = "Por Revisar"
                # Obtener el próximo id_checklist correlativo
                ultimo_id_checklist = ChecklistMaterialesSonda.objects.aggregate(Max('id_checklist'))['id_checklist__max'] or 0
                nuevo_id_checklist = ultimo_id_checklist + 1
                # Guardar los materiales con las cantidades, jornada, turno y fecha_checklist
                for material in MaterialesSonda.objects.filter(status=True):
                    #cantidad = request.POST.get(f'cantidad_{material.id}', 0)
                    cantidad = int(request.POST.get(f'cantidad_{material.id}', '') or 0)
                    ChecklistMaterialesSonda.objects.update_or_create(
                        item=material,
                        id_checklist=nuevo_id_checklist,
                        etapa= etapa,
                        defaults={
                            'cantidad': cantidad,
                            'creador': request.user.first_name+" "+request.user.last_name,
                            'jornada': jornada,
                            'turno': turno,
                            'sonda': sonda_entrada,
                            'sondajeCodigo': sondaje_entrada,
                            'sondajeSerie': serie_entrada,
                            'sondajeEstado': estado_entrada,
                            'progreso': progreso,
                            'status': True,
                            'fecha_checklist': fecha_checklist
                        }
                    )
                
                EstadoEtapasReporteDigital.objects.update_or_create(
                    id_checklist=nuevo_id_checklist,
                    defaults={
                        'checklistEntrada':  True,
                        'reporteDigital': False,
                        'checklistSalida': False,
                    }
                )
                
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'message': 'Error al guardar el formulario.'})
        else:
            return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})

@login_required
def save_checklist_materiales_sonda_salida(request):
    if request.method == 'POST':
        form = ChecklistMaterialesSondaSalidaForm(request.POST)
        if form.is_valid():
            try:
                jornada = '2' #Forzamos "Final jornada" para no confiar en el POST
                turno = form.cleaned_data['turno_salida']
                fecha_checklist = form.cleaned_data['fecha_checklist_salida']
                sonda_salida = form.cleaned_data['sonda_salida']
                sonda_salida = Sondas.objects.get(sonda=sonda_salida)
                sondaje_salida = form.cleaned_data['sondaje_salida']
                sondaje_salida = Sondajes.objects.get(sondaje=sondaje_salida)
                serie_salida = form.cleaned_data['serie_salida']
                estado_salida = form.cleaned_data['estado_salida']
                id_check = request.POST['id']
                etapa = "Salida"
                progreso = "Por Revisar"
                # Obtener el próximo id_checklist 
                nuevo_id_checklist = id_check
                
                # Guardar los materiales con las cantidades, jornada, turno y fecha_checklist
                for material in MaterialesSonda.objects.filter(status=True):
                    cantidad = int(request.POST.get(f'cantidad_{material.id}', '') or 0)
                    ChecklistMaterialesSonda.objects.update_or_create(
                        item=material,
                        id_checklist=nuevo_id_checklist,
                        etapa= etapa,
                        defaults={
                            'cantidad': cantidad,
                            'creador': request.user.first_name+" "+request.user.last_name,
                            'jornada': jornada,
                            'turno': turno,
                            'sonda': sonda_salida,
                            'sondajeCodigo': sondaje_salida,
                            'sondajeSerie': serie_salida,
                            'sondajeEstado': estado_salida,
                            'progreso': progreso,
                            'status': True,
                            'fecha_checklist': fecha_checklist
                        }
                    )
                
                EstadoEtapasReporteDigital.objects.update_or_create(
                    id_checklist=nuevo_id_checklist,
                    defaults={
                        'checklistSalida': True,
                    }
                )
                
                return JsonResponse({'success': True})
            except Exception as e:
                return JsonResponse({'success': False, 'message': 'Error al guardar el formulario.'})
        else:
            return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def edit_checklist_materiales_sonda(request):
    try:
        request.session['edit_id'] = request.POST['id']            
    except MultiValueDictKeyError:
        request.session['edit_id'] = request.session['edit_id']
    checklist_id = request.session['edit_id']
    
    # Obtener los datos de ChecklistMaterialesSonda correspondientes al id_checklist
    checklists = ChecklistMaterialesSonda.objects.filter(id_checklist=checklist_id)

    # Obtener los primeros datos para los valores iniciales del formulario
    first_checklist = checklists.first()  # Usamos first() para obtener el primer resultado

    # Inicializar el formulario con los valores actuales del checklist
    form = ChecklistMaterialesSondaEntradaForm(initial={
        'fecha_checklist': first_checklist.fecha_checklist,
        'turno': first_checklist.turno,
        'jornada': first_checklist.jornada,
    })
    
    # Pasar los datos al contexto para el template
    context = {
        'documento_id': first_checklist.id_checklist,
        'form': form,
        'checklist': checklists,
        'sidebar': 'manage_checklist_materiales_sonda',
        'sidebarmain': 'system_checklist',
    }
    return render(request, 'pages/checklist/edit_materiales_sonda.html', context)

@login_required
def save_edit_checklist_materiales_sonda_entrada(request):
    # Si la solicitud es POST, se actualizan los datos
    if request.method == 'POST':
        # Obtener los valores de turno, jornada
        #turno = request.POST.get('turno')
        #jornada = request.POST.get('jornada')            

        for key, value in request.POST.items():
            if key.startswith('cantidad_'):
                material_id = int(key.split('_')[1])
                checklist = ChecklistMaterialesSonda.objects.get(id=material_id)
                checklist.cantidad = value  # Nueva cantidad
                #checklist.turno = turno  # Actualizar turno
                #checklist.jornada = jornada  # Actualizar jornada
                checklist.save()  # Guardar el registro actualizado
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    
@login_required
def save_edit_checklist_materiales_sonda_salida(request):
    # Si la solicitud es POST, se actualizan los datos
    if request.method == 'POST':
        # Obtener los valores de turno, jornada
        #turno = request.POST.get('turno')
        #jornada = request.POST.get('jornada')            

        for key, value in request.POST.items():
            if key.startswith('cantidad_'):
                material_id = int(key.split('_')[1])
                checklist = ChecklistMaterialesSonda.objects.get(id=material_id)
                checklist.cantidad = value  # Nueva cantidad
                #checklist.turno = turno  # Actualizar turno
                #checklist.jornada = jornada  # Actualizar jornada
                checklist.save()  # Guardar el registro actualizado
        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    
@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def manage_checklist_materiales_caseta(request): 
    lista = ChecklistMaterialesCaseta.objects.values('id_checklist', 'fecha_checklist', 'creador', 'creador_cargo', 'turno', 'supervisor').distinct().order_by('-fecha_checklist')
    context = {
        'documentos': lista,
        'sidebar': 'manage_checklist_materiales_caseta',
        'sidebarmain': 'system_checklist', 
    }
    return render(request,'pages/checklist/manage_materiales_caseta.html', context)

@login_required
def new_checklist_materiales_caseta(request):
    if request.method == 'POST':
        formTop = ChecklistMaterialesCasetaFormTop(request.POST)
        formBottom = ChecklistMaterialesCasetaFormBottom(request.POST, request.FILES)
        if formTop.is_valid():
            creador = formTop.cleaned_data['responsable']
            turno = formTop.cleaned_data['turno']
            fecha_checklist = formTop.cleaned_data['fecha_checklist']
            cargo = formTop.cleaned_data['cargo']
            
            # Obtener el próximo id_checklist correlativo
            ultimo_id_checklist = ChecklistMaterialesCaseta.objects.aggregate(Max('id_checklist'))['id_checklist__max'] or 0
            nuevo_id_checklist = ultimo_id_checklist + 1

            # Guardar los materiales junto con los campos adicionales e imagen
            for material in MaterialesCaseta.objects.filter(status=True):
                b = int(request.POST.get(f'b_{material.id}', '') or 0)
                m = int(request.POST.get(f'm_{material.id}', '') or 0)
                observacion = request.POST.get(f'observacion_{material.id}', "")
                fecha_str = request.POST.get(f'fecha_{material.id}', "")
                fotografia = request.FILES.get(f'fotografia_{material.id}', None)

                # Crear un nuevo registro en lugar de actualizar
                ChecklistMaterialesCaseta.objects.create(
                    item=material,
                    b=b,
                    m=m,
                    observacion=observacion,
                    fotografiaMaterial=fotografia,
                    creador=creador,
                    creador_cargo=cargo,
                    status=True,
                    turno=turno,
                    id_checklist=nuevo_id_checklist,
                    fecha_checklist=fecha_checklist,
                    fecha_control=parse_datetime(fecha_str) if fecha_str else None,
                    fecha_revision=None,
                    observaciones_revision=None,
                    supervisor=None,
                )
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})
    else:
        responsable = f"{request.user.first_name} {request.user.last_name}"
        role = request.user.role.capitalize()
        formTop = ChecklistMaterialesCasetaFormTop(initial={
            'responsable': responsable,
            'cargo': role,
        })
        formBottom = ChecklistMaterialesCasetaFormBottom()
        
    materiales = MaterialesCaseta.objects.filter(status=True)
    context = {
        'formTop': formTop,
        'formBottom': formBottom,
        'materiales': materiales,
        'sidebar': 'new_checklist_materiales_caseta',
        'sidebarmain': 'system_checklist', 
    }
    return render(request, 'pages/checklist/new_materiales_caseta.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def edit_checklist_materiales_caseta(request):
    try:
        request.session['edit_id'] = request.POST['id']            
    except MultiValueDictKeyError:
        request.session['edit_id'] = request.session['edit_id']
    checklist_id = request.session['edit_id']
    
    # Obtener los datos de ChecklistMaterialesCaseta correspondientes al id_checklist
    checklists = ChecklistMaterialesCaseta.objects.filter(id_checklist=checklist_id)

    # Obtener los primeros datos para los valores iniciales del formulario
    first_checklist = checklists.first()  # Usamos first() para obtener el primer resultado

    # Inicializar el formulario con los valores actuales del checklist
    formTop = ChecklistMaterialesCasetaFormTop(initial={
        'fecha_checklist': first_checklist.fecha_checklist,
        'turno': first_checklist.turno,
        'responsable': first_checklist.creador,
        'cargo': first_checklist.creador_cargo
    })
    supervisor = f"{request.user.first_name} {request.user.last_name}"
    formBottom = ChecklistMaterialesCasetaFormBottom(initial={
        'supervisor': supervisor,
        'observaciones': first_checklist.observaciones_revision
    })
    
    # Pasar los datos al contexto para el template
    context = {
        'documento_id': first_checklist.id_checklist,
        'formTop': formTop,
        'formBottom': formBottom,
        'checklist': checklists,
        'sidebar': 'manage_checklist_materiales_caseta',
        'sidebarmain': 'system_checklist',
    }
    return render(request, 'pages/checklist/edit_materiales_caseta.html', context)

@login_required
@sondaje_admin_or_base_datos_or_supervisor_required
def save_edit_checklist_materiales_caseta(request):
    # Si la solicitud es POST, se actualizan los datos
    if request.method == 'POST':
        turno = request.POST.get('turno')
        fecha_revision_str = request.POST.get('fecha_revision')
        fecha_revision = parse_datetime(fecha_revision_str) if fecha_revision_str else None
        observaciones_revision = request.POST.get('observaciones')
        supervisor = request.POST.get('supervisor')

        for key, value in request.POST.items():
            if key.startswith('observacion_'):
                material_id = int(key.split('_')[1])
                checklist = ChecklistMaterialesCaseta.objects.get(id=material_id)
                checklist.b = request.POST.get(f'b_{material_id}')
                checklist.m = request.POST.get(f'm_{material_id}')
                checklist.observacion = value
                fecha_str = request.POST.get(f'fecha_{material_id}', "")
                fecha_control = parse_datetime(fecha_str) if fecha_str else None
                checklist.fecha_control = fecha_control
                checklist.turno = turno
                checklist.fecha_revision = fecha_revision
                checklist.observaciones_revision = observaciones_revision
                checklist.supervisor = supervisor

                # Actualizar la imagen si se subió una nueva
                nueva_foto = request.FILES.get(f'fotografia_{material_id}', None)
                if nueva_foto:
                    checklist.fotografiaMaterial = nueva_foto

                checklist.save()  # Guardar el registro actualizado

        return JsonResponse({'success': True})
    else:
        return JsonResponse({'success': False, 'message': 'El formulario no es válido.'})