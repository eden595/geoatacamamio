from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from core.decorators import admin_required
from django.contrib import messages
from django.http import JsonResponse
from .forms import FormNuevoItem, FormNuevaSeccion, FormNuevaDuracion, FormNuevaCategoria
from .forms import  FormSeccionSelect,FormCategorySelect
from .forms import  FormInventarioNuevoIngreso,FormInventarioNuevoEgreso,FormInventarioNuevoAjuste
from .models import Items, SeccionItems, CategoriaItems, DuracionItems, StockItems, StockEgresoItems,Faena,StockItemsHistorico

from messenger.views import notificacion_mantenedor_email, notificacion_admin_jefe_mantencion_email
from django.utils.datastructures import MultiValueDictKeyError
import hashlib

    

#### CREAR ITEM
@login_required
@admin_required
def manage_inventario_crear_item(request):
    storage = messages.get_messages(request)
    storage.used = True
    #inventario_crear_item = list(ReporteError.objects.all().order_by('fechacreacion')) 
    items = Items.objects.all().order_by('item')
    context = {
        'items': items,  # Pasar las items al contexto
        'sidebarmain': 'system_inventario_crear_item',  
        'sidebarmenu': 'manage_inventory',
        'sidebarsubmenu': 'manage_secciones',
    }
    return render(request,'pages/inventory/manage_inventario_crear_item.html', context)

@login_required  
@admin_required  
def new_inventario_crear_item(request):
    context = {
        'formularioseccion': FormSeccionSelect,
        'formnuevoitem': FormNuevoItem,   
        'sidebarmain': 'system_inventario_crear_item', 
        'sidebar': 'dashboard',
    }
    return render(request,'pages/inventory/new_inventario_crear_item.html', context)

def cargar_secciones_por_item(request):
    seccion_id = request.GET.get('seccion_id')
    if seccion_id:
        categorias = CategoriaItems.objects.filter(seccion_id=seccion_id,status=True)
        data = [{'id': categoria.id, 'nombre': categoria.categoria} for categoria in categorias]
        return JsonResponse(data, safe=False)
    else:
        return JsonResponse({}, status=400)

@login_required
@admin_required
def save_new_inventario_crear_item(request):

    if request.method == 'POST':
        item_name = request.POST.get('item')
        faena_id = request.POST.get('faena')
        seccion_id = request.POST.get('seccion')
        categoria_id = request.POST.get('categoria')
        duracion = request.POST.get('duracion')
        duracion_instance = DuracionItems.objects.get(id=duracion)

        # Verificar si ya existe un Item con los mismos valores
        existing_item = Items.objects.filter(
            item=item_name,
            faena_id=faena_id,
            seccion_id=seccion_id,
            categoria_id=categoria_id
        )

        if existing_item.exists():
            print("El item ya existe con esa combinación.")
            return JsonResponse({'success': False, 'errors': 'El Item ya existe con esa combinación.'}, status=400)
        else:
            # Si no existe, crea el nuevo item
            nuevo_item = Items(
                item=item_name,
                faena_id=faena_id,
                seccion_id=seccion_id,
                categoria_id=categoria_id,
                descripcion=request.POST.get('descripcion'),
                stock_minimo=request.POST.get('stock_minimo'),
                stock_maximo=request.POST.get('stock_maximo'),
                valor_neto=request.POST.get('valor_neto'),
                marca=request.POST.get('marca'),
                duracion=duracion_instance,
                status=True
            )
            nuevo_item.save()


            try:
                stock_item = StockItems(
                    faena_id=faena_id,  # Usar _id en claves foráneas
                    seccion_id=seccion_id,
                    categoria_id=categoria_id,
                    item_id=nuevo_item.id,  # Se usa `nuevo_item.id`
                    cantidad=0,
                    cantidad_actual=0,
                    descripcion=request.POST.get('descripcion'),
                    status=True,
                    creador=f"{request.user.first_name} {request.user.last_name}",
                )
                stock_item.save()
            except Exception as e:
                print(f"Error al guardar stock_item: {e}")
                return JsonResponse({'success': False, 'errors': 'Error al guardar stock item.'}, status=500)

            return JsonResponse({'success': True})     
            
    else:
        return redirect('new_inventario_crear_item')

@login_required
@admin_required
def status_item(request):
    print(request.POST)
    if request.method == 'POST': 
        item = Items.objects.get(id=request.POST['item'])

        if (item.status):
            Items.objects.filter(id=request.POST['item']).update(status=False)
            messages.success(request, 'Vehículo Deshabilitado Correctamente')
         
        else:            
            Items.objects.filter(id=request.POST['item']).update(status=True)

            messages.success(request, 'Vehículo Habilitado Correctamente')
        return redirect('manage_inventario_crear_item') 
    else:
        return redirect('manage_inventario_crear_item') 
#### CREAR SECCION
@login_required
@admin_required
def manage_inventario_crear_secciones(request):
    storage = messages.get_messages(request)
    storage.used = True
    # Obtener todas las secciones desde el modelo
    secciones = SeccionItems.objects.all().order_by('seccion')  # Ordenar por el campo 'seccion'
    context = {
        'secciones': secciones,  # Pasar las secciones al contexto
        'sidebarmain': 'manage_system',
        'sidebarmenu': 'manage_inventory',
        'sidebarsubmenu': 'manage_secciones',
    }
    return render(request,'pages/inventory/manteiner/manage_inventario_crear_secciones.html', context)

@login_required 
@admin_required  
def new_inventario_crear_secciones(request):
    context = {
        'formnuevaseccion': FormNuevaSeccion,
        'sidebarmain': 'manage_system',
        'sidebarmenu': 'manage_inventory',
        'sidebarsubmenu': 'manage_secciones',
    }
    return render(request,'pages/inventory/manteiner/new_inventario_crear_secciones.html', context)

@login_required
@admin_required
def save_new_inventario_crear_seccion(request):
    if request.method == 'POST':
        
        form = FormNuevaSeccion(request.POST)
        if form.is_valid():
            nueva_seccion = form.save(commit=False)
            nueva_seccion.creador = f"{request.user.first_name} {request.user.last_name}"  # Asigna el creador
            nueva_seccion.status = True  
            nueva_seccion.save()
    
            return JsonResponse({'success': True})

        else:
            # Enviar errores si el formulario no es válido
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        return redirect('new_inventario_crear_seccion')

@login_required 
@admin_required
def status_inventario_seccion(request):
    if request.method == 'POST': 
        seccion = SeccionItems.objects.get(id=request.POST['id'])
        if (seccion.status): 
            SeccionItems.objects.filter(id=request.POST['id']).update(status=False)
            notificacion_mantenedor_email(request,seccion,'secciones','deshabilitada')  
            messages.success(request, 'seccion Deshabilitado Correctamente')  
        else:
            SeccionItems.objects.filter(id=request.POST['id']).update(status=True)
            notificacion_mantenedor_email(request,seccion,'secciones','habilitada')  
            messages.success(request, 'seccion Habilitado Correctamente') 
        return redirect('manage_inventario_crear_secciones') 
#### CREAR CATEGORIAS
@login_required
@admin_required
def manage_inventario_crear_categorias(request):
    storage = messages.get_messages(request)
    storage.used = True
    #inventario_crear_seccion = list(ReporteError.objects.all().order_by('fechacreacion')) 

    # Obtener todas las categorias desde el modelo
    categorias = CategoriaItems.objects.all().order_by('categoria')  # Ordenar por el campo 'categoria'

    context = {
        'categorias' : categorias,
        'sidebarmain': 'manage_system',
        'sidebarmenu': 'manage_inventory',
        'sidebarsubmenu': 'manage_categorias',
    }
    return render(request,'pages/inventory/manteiner/manage_inventario_crear_categorias.html', context)

@login_required  
@admin_required 
def new_inventario_crear_categorias(request):
    context = {
        'formnuevacategoria': FormNuevaCategoria, 
        'sidebarmain': 'manage_system',
        'sidebarmenu': 'manage_inventory',
        'sidebarsubmenu': 'manage_categorias',
    }
    return render(request,'pages/inventory/manteiner/new_inventario_crear_categorias.html', context)

@login_required
@admin_required
def save_new_inventario_crear_categoria(request):
    if request.method == 'POST':
        seccion = SeccionItems.objects.get(id=request.POST['seccion'])
        formulario = FormNuevaCategoria(data=request.POST)
        if formulario.is_valid():
            try:
                CategoriaItems.objects.get(seccion=seccion,categoria=request.POST['categoria'])
                return JsonResponse({'success': False, 'errors': 'La Categoria ya existe en la Seccion seleccionada.'}, status=400)

            except:  
                categoria = CategoriaItems(
                    seccion = seccion,
                    categoria = request.POST['categoria'],
                    status = True,
                    creador = request.user.first_name+" "+request.user.last_name,
                )
                categoria.save()
                notificacion_mantenedor_email(request,categoria,'categoria Items','creada')
                return JsonResponse({'success': True})
        else:
            # Enviar errores si el formulario no es válido
            return JsonResponse({'success': False, 'errors': formulario.errors}, status=400)
    
    else:
        return redirect('new_inventario_crear_categoria')

#### CREAR DURACIONES
@login_required
@admin_required
def manage_inventario_crear_duraciones(request):
    storage = messages.get_messages(request)
    storage.used = True
    #inventario_crear_seccion = list(ReporteError.objects.all().order_by('fechacreacion')) 

    # Obtener todas las secciones desde el modelo
    duracion = DuracionItems.objects.all().order_by('fechacreacion')  # Ordenar por el campo 'seccion'
    context = {
        'duraciones': duracion,
        'sidebarmain': 'manage_system',
        'sidebarmenu': 'manage_inventory',
        'sidebarsubmenu': 'manage_duraciones',
    }
    return render(request,'pages/inventory/manteiner/manage_inventario_crear_duraciones.html', context)

@login_required   
@admin_required
def new_inventario_crear_duraciones(request):
    context = {
        'formnuevaduracion': FormNuevaDuracion,   
        'sidebarmain': 'manage_system',
        'sidebarmenu': 'manage_inventory',
        'sidebarsubmenu': 'manage_duraciones',
    }
    return render(request,'pages/inventory/manteiner/new_inventario_crear_duraciones.html', context)

@login_required
@admin_required
def save_new_inventario_crear_duracion(request):

    if request.method == 'POST':
        form = FormNuevaDuracion(request.POST)
        if form.is_valid():
            nueva_duracion = form.save(commit=False)
            nueva_duracion.creador = f"{request.user.first_name} {request.user.last_name}"  # Asigna el creador
            nueva_duracion.status = True  
            nueva_duracion.save()    
            return JsonResponse({'success': True})
        else:
            # Enviar errores si el formulario no es válido
            return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        return redirect('new_inventario_crear_duracion')

#### STOCK

def manage_inventario_stock(request):

    storage = messages.get_messages(request)
    storage.used = True
    # Obtener todas las categorias desde el modelo
    items = list(StockItems.objects.filter(status=True)) 

    
    context = {
        'items' : items,
        'sidebarmain': 'system_inventario_stock',
    }
    return render(request,'pages/inventory/manage_inventario_stock.html', context)


#### INGRESO
@login_required
@admin_required
def manage_inventario_ingreso(request):
    storage = messages.get_messages(request)
    storage.used = True

    context = {
        'sidebarmain': 'system_inventario_stock', 
    }
    return render(request,'pages/inventory/manage_inventario_ingreso.html', context)

@login_required  
@admin_required  
def new_inventario_ingreso(request):
    #print(request.POST)
    try:
        request.session['item_id'] = request.POST['item_id']          
        request.session['cantidad']=request.POST.get('cantidad',0)
        request.session['cantidad_actual']=request.POST.get('cantidad_actual',0)
        request.session['faena'] = request.POST['faena']
        request.session['seccion_item'] = request.POST['seccion']
        request.session['categoria'] = request.POST['categoria']
    except MultiValueDictKeyError:
        request.session['item_id'] = request.session['item_id']          
        request.session['cantidad'] = request.session['cantidad']
        request.session['cantidad_actual'] = request.session['cantidad_actual']
        request.session['faena'] = request.session['faena']
        request.session['seccion_item'] = request.session['seccion_item']
        request.session['categoria'] = request.session['categoria']

    item = Items.objects.get(id=request.session['item_id'])
    stock_items = StockItems.objects.get(item=item)
    stock_items_historico = StockItemsHistorico.objects.filter(
        movimiento="Ingreso",
        item=item
    ).order_by('-fechacreacion') 
    context = {
            'forminventarionuevoingreso': FormInventarioNuevoIngreso(initial={
                'item':item.item,
                'item_id':item.id,
                'faena':item.faena.faena,
                'seccion':item.seccion.seccion,
                'categoria':item.categoria.categoria,
                'cantidad_actual':stock_items.cantidad_actual,
                }),  
            'sidebarmain': 'dashboardInventario',
            "item_id":item.id,
            "historicos": stock_items_historico,
            'sidebarmain': 'system_inventario_stock', 
    }
    return render(request,'pages/inventory/new_inventario_ingreso.html', context)

@login_required
@admin_required
def save_new_inventario_ingreso(request):
    print(request.POST)

    if request.method == 'POST':
        item = Items.objects.get(id=request.POST['item_id'])
        stock_items = StockItems.objects.get(item=item)
        stock_items.cantidad = int(request.POST.get('cantidad'))
        stock_items.cantidad_actual += int(request.POST.get('cantidad'))
        stock_items.save()

        try:
            stock_items_historico = StockItemsHistorico(
                faena=item.faena,
                seccion=item.seccion,
                categoria=item.categoria,
                item=item, 
                movimiento="Ingreso",
                cantidad=int(request.POST.get('cantidad')),
                descripcion=request.POST.get("descripcion"),
                creador=request.user.first_name + " " + request.user.last_name,
            )
        except Exception as e:
            print(f"Error al crear StockItemsHistorico: {e}")  # Muestra el error en la terminal
            return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})
        print("PASO")
        print(stock_items_historico)
        stock_items_historico.save()          
        return JsonResponse({'success': True})

    else:
        return redirect('manage_inventario_stock')
    
#### EGRESO

@login_required  
@admin_required  
def new_inventario_egreso(request):
    try:
        request.session['item_id'] = request.POST['item_id']          
        request.session['cantidad']=request.POST.get('cantidad',0)
        request.session['cantidad_actual']=request.POST.get('cantidad_actual',0)
        request.session['faena'] = request.POST['faena']
        request.session['seccion_item'] = request.POST['seccion']
        request.session['categoria'] = request.POST['categoria']
    except MultiValueDictKeyError:
        request.session['item_id'] = request.session['item_id']          
        request.session['cantidad'] = request.session['cantidad']
        request.session['cantidad_actual'] = request.session['cantidad_actual']
        request.session['faena'] = request.session['faena']
        request.session['seccion_item'] = request.session['seccion_item']
        request.session['categoria'] = request.session['categoria']

    item = Items.objects.get(id=request.session['item_id'])
    stock_items = StockItems.objects.get(item=item)

    stock_items_historico = StockItemsHistorico.objects.filter(
        movimiento="Egreso",
        item=item
    ).order_by('-fechacreacion') 

    context = {
        'forminventarionuevoegreso': FormInventarioNuevoEgreso(initial={
            'item':item.item,
            'item_id':item.id,
            'faena':item.faena.faena,
            'seccion':item.seccion.seccion,
            'categoria':item.categoria.categoria,
            'cantidad':stock_items.cantidad_actual,
            }),  
        'sidebarmain': 'system_inventario_stock', 
        "item_id":item.id,
        "historicos": stock_items_historico
    }
    
    return render(request,'pages/inventory/new_inventario_egreso.html', context)
        
@login_required
@admin_required
def save_new_inventario_egreso(request):
    print(request.POST)
    if request.method == 'POST':
        try:
            item = Items.objects.get(id=request.POST['item_id'])
            stock_items = StockItems.objects.get(item=item)

            if int(stock_items.cantidad_actual) < int(request.POST.get('cantidad_actual')):
                return JsonResponse({'success': False, 'message': 'No hay suficiente stock'})
            
            else:
                stock_items.cantidad = int(request.POST.get('cantidad_actual'))
                stock_items.cantidad_actual += (int(request.POST.get('cantidad_actual')))*-1
                stock_items.save()
                print(1)

                stock_items_historico = StockItemsHistorico(
                    faena=item.faena,
                    seccion=item.seccion,
                    categoria=item.categoria,
                    item=item, 
                    movimiento="Egreso",   
                    cantidad=int(request.POST.get('cantidad')),
                    descripcion=request.POST.get("descripcion"),
                    rut_receptor=request.POST.get("rut_receptor"),
                    cargo_receptor=request.POST.get("cargo_receptor"),
                    nombre_receptor=request.POST.get("nombre_receptor"),
                    creador=request.user.first_name + " " + request.user.last_name,
                )
                print(2)
                stock_items_historico.save()  
                return JsonResponse({'success': True})

        except Exception as e:
            print(f"Error al crear StockItemsHistorico: {e}")  # Muestra el error en la terminal
            return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})
    else:
        return redirect('manage_inventario_stock')

    
#### AJUSTE

@login_required  
@admin_required  
def new_inventario_ajuste(request):
    print(request.POST)
    try:
        request.session['item_id'] = request.POST['item_id']          
        request.session['cantidad']=request.POST.get('cantidad',0)
        request.session['cantidad_actual']=request.POST.get('cantidad_actual',0)
        request.session['faena'] = request.POST['faena']
        request.session['seccion_item'] = request.POST['seccion']
        request.session['categoria'] = request.POST['categoria']
    except MultiValueDictKeyError:
        request.session['item_id'] = request.session['item_id']          
        request.session['cantidad'] = request.session['cantidad']
        request.session['cantidad_actual'] = request.session['cantidad_actual']
        request.session['faena'] = request.session['faena']
        request.session['seccion_item'] = request.session['seccion_item']
        request.session['categoria'] = request.session['categoria']

    item = Items.objects.get(id=request.session['item_id'])
    stock_items = StockItems.objects.get(item=item)
    stock_items_historico = StockItemsHistorico.objects.filter(
        movimiento="Ajuste",
        item=item
    ).order_by('-fechacreacion') 
    context = {
        'forminventarionuevoajuste': FormInventarioNuevoAjuste(initial={
            'item':item.item,
            'item_id':item.id,
            'faena':item.faena.faena,
            'seccion':item.seccion.seccion,
            'categoria':item.categoria.categoria,
            'cantidad_actual':stock_items.cantidad_actual,
            }),  
        'sidebarmain': 'system_inventario_stock', 
        "item_id":item.id,
        "historicos": stock_items_historico
    }
    return render(request,'pages/inventory/new_inventario_ajuste.html', context)

@login_required
@admin_required
def save_new_inventario_ajuste(request):
    print(request.POST)

    if request.method == 'POST':
        item = Items.objects.get(id=request.POST['item_id'])
        stock_items = StockItems.objects.get(item=item)
        stock_items.cantidad = int(request.POST.get('cantidad'))
        stock_items.cantidad_actual += int(request.POST.get('cantidad'))
        stock_items.save()

        try:
            stock_items_historico = StockItemsHistorico(
                faena=item.faena,
                seccion=item.seccion,
                categoria=item.categoria,
                item=item, 
                movimiento="Ajuste",
                cantidad=int(request.POST.get('cantidad')),
                descripcion=request.POST.get("descripcion"),
                creador=request.user.first_name + " " + request.user.last_name,
            )
        except Exception as e:
            print(f"Error al crear StockItemsHistorico: {e}")  # Muestra el error en la terminal
            return JsonResponse({'success': False, 'message': f'Error: {str(e)}'})
        print("PASO")
        print(stock_items_historico)
        stock_items_historico.save()          
        return JsonResponse({'success': True})

    else:
        return redirect('manage_inventario_stock')
    

def mostrar_registro_item(request, id):
    item_ver = Items.objects.get(id=id)
    context = {
        'item_ver': item_ver,
        'sidebarmain': 'system_report_error',
    }
    return render(request,'pages/inventory/mostrarregistroitem.html', context)