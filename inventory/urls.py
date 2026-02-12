from django.http import HttpResponseForbidden
from django.shortcuts import render, redirect
from django.urls import path, include
from django.contrib.auth.decorators import user_passes_test
from functools import wraps
from .views import (#manage_inventario_ajuste, manage_inventario_egreso, manage_inventario_ingreso,
                    manage_inventario_crear_item,new_inventario_crear_item, 
                    cargar_secciones_por_item,save_new_inventario_crear_item,status_item,
                    manage_inventario_crear_secciones,new_inventario_crear_secciones,save_new_inventario_crear_seccion,
                    status_inventario_seccion,
                    save_new_inventario_ingreso,save_new_inventario_egreso,
                    manage_inventario_crear_categorias, new_inventario_crear_categorias, save_new_inventario_crear_categoria,
                    manage_inventario_crear_duraciones, new_inventario_crear_duraciones, save_new_inventario_crear_duracion,
                    manage_inventario_stock,new_inventario_ajuste,new_inventario_ingreso,new_inventario_egreso  ,
                    save_new_inventario_ingreso,save_new_inventario_egreso,save_new_inventario_ajuste,
                    mostrar_registro_item,
                    )
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    #ITEMS

    #path('manage_inventario_ingreso', manage_inventario_ingreso, name="manage_inventario_ingreso"),
    #path('manage_inventario_egreso', manage_inventario_egreso, name="manage_inventario_egreso"),
    #path('manage_inventario_ajuste', manage_inventario_ajuste, name="manage_inventario_ajuste"),
    path('manage_inventario_crear_item', manage_inventario_crear_item, name="manage_inventario_crear_item"),
    path('new_inventario_crear_item', new_inventario_crear_item, name="new_inventario_crear_item"),
    path('cargar_secciones_por_item', cargar_secciones_por_item, name="cargar_secciones_por_item"),
    path('save_new_inventario_crear_item', save_new_inventario_crear_item, name="save_new_inventario_crear_item"),
    path('status_item', status_item, name="status_item"),
    path('mostrar_registro_item/<int:id>', mostrar_registro_item, name="mostrar_registro_item"),
    # SECCIONES
    path('manage_inventario_crear_secciones', manage_inventario_crear_secciones, name="manage_inventario_crear_secciones"),
    path('new_inventario_crear_secciones', new_inventario_crear_secciones, name="new_inventario_crear_secciones"),
    path('save_new_inventario_crear_seccion', save_new_inventario_crear_seccion, name="save_new_inventario_crear_seccion"),
    path('status_inventario_seccion', status_inventario_seccion, name="status_inventario_seccion"),
    
    # CATEGORIAS
    path('manage_inventario_crear_categorias', manage_inventario_crear_categorias, name="manage_inventario_crear_categorias"),
    path('new_inventario_crear_categorias', new_inventario_crear_categorias, name="new_inventario_crear_categorias"),
    path('save_new_inventario_crear_categoria', save_new_inventario_crear_categoria, name="save_new_inventario_crear_categoria"),
    # DURACION
    path('manage_inventario_crear_duraciones', manage_inventario_crear_duraciones, name="manage_inventario_crear_duraciones"),
    path('new_inventario_crear_duraciones', new_inventario_crear_duraciones, name="new_inventario_crear_duraciones"),
    path('save_new_inventario_crear_duracion', save_new_inventario_crear_duracion, name="save_new_inventario_crear_duracion"),
    # STOCK 
    path('manage_inventario_stock', manage_inventario_stock, name="manage_inventario_stock"),
    path('new_inventario_ajuste', new_inventario_ajuste, name="new_inventario_ajuste"),
    path('new_inventario_ingreso', new_inventario_ingreso, name="new_inventario_ingreso"),
    path('new_inventario_egreso', new_inventario_egreso, name="new_inventario_egreso"),
    path('save_new_inventario_ingreso', save_new_inventario_ingreso, name="save_new_inventario_ingreso"),
    path('save_new_inventario_egreso', save_new_inventario_egreso, name="save_new_inventario_egreso"),
    path('save_new_inventario_ajuste', save_new_inventario_ajuste, name="save_new_inventario_ajuste"),

]