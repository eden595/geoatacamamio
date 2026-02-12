import os
from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from datetime import datetime
from core.models import Tipo, Ano, Marca, Modelo, Color, OcultarOpcionesVehiculo
from core.choices import tipotraccion, opcion, tenencia, estadopago
from django.core.validators import MinValueValidator
from mining.models import Faena

class SeccionItems(models.Model):
    seccion = models.CharField(max_length=50,unique=True,verbose_name='Sección')
    creador = models.CharField(max_length=50,verbose_name='Creador',null=True)
    status = models.BooleanField(null=True, verbose_name='Estado')
    fechacreacion = models.DateTimeField(null=False,default=timezone.now)
    def __str__(self):
        return "{}".format(self.seccion)
    class Meta:
        verbose_name = 'Sección'
        verbose_name_plural = 'Secciones'
        db_table = 'inventory_seccion_items'
        
class CategoriaItems(models.Model):
    seccion = models.ForeignKey(SeccionItems, on_delete=models.CASCADE, null=True,verbose_name='Sección')
    categoria = models.CharField(max_length=50,verbose_name='Categoría')
    creador = models.CharField(max_length=50,verbose_name='Creador',null=True)
    status = models.BooleanField(null=True, verbose_name='Estado')
    fechacreacion = models.DateTimeField(null=False,default=timezone.now)
    def __str__(self):
        return "{}".format(self.categoria)
    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        db_table = 'inventory_categoria_items'

class DuracionItems(models.Model):
    duracion = models.PositiveIntegerField(validators=[MinValueValidator(1)], verbose_name='Duración',null=True)
    creador = models.CharField(max_length=50, verbose_name='Creador', null=True)
    status = models.BooleanField(null=True, verbose_name='Estado')
    fechacreacion = models.DateTimeField(null=False, default=timezone.now)

    def __str__(self):
        return "{}".format(self.duracion) 

    class Meta:
        verbose_name = 'Duración'
        verbose_name_plural = 'Duraciones'
        db_table = 'inventory_duracion_items'
class Items(models.Model):
    def generaNombre(instance,filename):
        extension = os.path.splitext(filename)[1][1:]
        seccion_item = instance.items.seccion.upper()
        categoria_item = instance.items.categoria.upper()
        nombre_item = instance.items.item.upper()
        ruta = f'inventario_item/{seccion_item}/{categoria_item}/{nombre_item}' 
        fecha =datetime.now().strftime("%Y%m%d_%H%M%S") 
        nombre = "{}.{}".format(fecha,extension)
        return os.path.join(ruta,nombre)   
      
    faena = models.ForeignKey(Faena,on_delete=models.CASCADE,null=True,blank=True,verbose_name='Faena')
    seccion = models.ForeignKey(SeccionItems,on_delete=models.CASCADE,null=True,blank=True,verbose_name='Sección')
    categoria = models.ForeignKey(CategoriaItems,on_delete=models.CASCADE,null=True,blank=True,verbose_name='Categoría')
    item = models.CharField(max_length=250,verbose_name='Nombre')
    descripcion = models.CharField(max_length=250,verbose_name='Descripción')
    duracion = models.ForeignKey(DuracionItems,on_delete=models.CASCADE,null=True,blank=True,verbose_name='Duración')
    stock_minimo = models.CharField(max_length=250,verbose_name='Stock Minimo')
    stock_maximo = models.CharField(max_length=250,verbose_name='Stock Maximo')
    valor_neto = models.IntegerField(null=True,verbose_name='Valor Neto')
    marca = models.CharField(max_length=250, null=True,verbose_name='Marca')
    imagen_item = models.ImageField(upload_to=generaNombre, null=True, blank=True, default='inventario_item/no-imagen-item.png', verbose_name="Fotografía Item")
    status = models.BooleanField(null=True, verbose_name='Estado')
    fechacreacion = models.DateTimeField(null=False,default=timezone.now)
    def __str__(self):
        return "{} {} {}".format(self.seccion,self.categoria,self.item)
    class Meta:
        verbose_name = 'Item'
        verbose_name_plural = 'Items'
        db_table = 'inventory_item_items'
        unique_together = ('faena', 'seccion', 'categoria', 'item')


class StockItems(models.Model):
    faena = models.ForeignKey(Faena,on_delete=models.CASCADE,null=True,blank=True,verbose_name='Faena')
    seccion = models.ForeignKey(SeccionItems,on_delete=models.CASCADE,null=True,blank=True,verbose_name='Sección')
    categoria = models.ForeignKey(CategoriaItems,on_delete=models.CASCADE,null=True,blank=True,verbose_name='Categoría')
    item = models.ForeignKey(Items,on_delete=models.CASCADE,null=True,blank=True,verbose_name='Item')
    cantidad = models.IntegerField(verbose_name='Cantidad',default=0)
    cantidad_actual = models.IntegerField(verbose_name='Cantidad Actual',default=0)
    creador = models.CharField(max_length=50,verbose_name='Creador',null=True)
    fechacreacion = models.DateTimeField(null=False,default=timezone.now)
    descripcion = models.CharField(max_length=500,null=True,verbose_name='Observación')
    status = models.BooleanField(null=True, verbose_name='Estado')
    
    def __str__(self):
        return "{}".format(self.item)

    class Meta:
        verbose_name = 'StockItem'
        verbose_name_plural = 'StockItems'
        db_table = 'inventory_stockitem_stockitems'
        unique_together = ('faena', 'seccion', 'categoria', 'item')

class StockItemsHistorico(models.Model):
    faena = models.ForeignKey(Faena,on_delete=models.CASCADE,null=True,blank=True,verbose_name='Faena')
    seccion = models.ForeignKey(SeccionItems,on_delete=models.CASCADE,null=True,blank=True,verbose_name='Sección')
    categoria = models.ForeignKey(CategoriaItems,on_delete=models.CASCADE,null=True,blank=True,verbose_name='Categoría')
    item = models.ForeignKey(Items,on_delete=models.CASCADE,null=True,blank=True,verbose_name='Item')
    movimiento = models.CharField(max_length=250,verbose_name='Movimiento')
    cantidad = models.IntegerField(verbose_name='Cantidad',default=0)
    descripcion = models.CharField(max_length=250,null=True,verbose_name='Observación')
    rut_receptor = models.CharField(max_length=250, null=True, blank=True, verbose_name='Rut Receptor')
    cargo_receptor = models.CharField(max_length=250, null=True, blank=True, verbose_name='Cargo Receptor')
    nombre_receptor = models.CharField(max_length=250, null=True, blank=True, verbose_name='Nombre Receptor')
    creador = models.CharField(max_length=50,verbose_name='Creador',null=True)
    fechacreacion = models.DateTimeField(null=False,default=timezone.now)


    def __str__(self):
        return "{}".format(self.item)

    class Meta:
        verbose_name = 'StockItemHistorico'
        verbose_name_plural = 'StockItemsHstoricos'
        db_table = 'inventory_stockitemhistorico_stockitemshistoricos'

class StockEgresoItems(models.Model):
    faena = models.ForeignKey(Faena,on_delete=models.CASCADE,null=True,blank=True,verbose_name='Faena')
    seccion = models.ForeignKey(SeccionItems,on_delete=models.CASCADE,null=True,blank=True,verbose_name='Sección')
    categoria = models.ForeignKey(CategoriaItems,on_delete=models.CASCADE,null=True,blank=True,verbose_name='Categoría')
    item = models.CharField(max_length=250,unique=True,verbose_name='Item')
    movimiento = models.CharField(max_length=250,verbose_name='Movimiento')
    cantidad = models.IntegerField(verbose_name='Cantidad Stock',default=0)
    cantidad_actual = models.IntegerField(verbose_name='Cantidad Entregada')
    rut_receptor = models.CharField(max_length=250,null=True,verbose_name='Rut Receptor')
    cargo_receptor = models.CharField(max_length=250,null=True,verbose_name='Cargo Receptor')
    nombre_receptor = models.CharField(max_length=250,null=True,verbose_name='Nombre Receptor')
    descripcion = models.CharField(max_length=250,null=True,verbose_name='Observación')
    creador = models.CharField(max_length=50,verbose_name='Creador',null=True)
    fechacreacion = models.DateTimeField(null=False,default=timezone.now)

    def __str__(self):
        return "{}".format(self.item)

    class Meta:
        verbose_name = 'StockEgresoItem'
        verbose_name_plural = 'StockEgresoItems'
        db_table = 'inventory_stockegresoitem_stockEgresoitems'


        