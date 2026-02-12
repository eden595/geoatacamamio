import os
from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from core.models import Ciudad, Nacionalidad, Genero, Faena
from datetime import datetime
from core.choices import opcion


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMINISTRADOR = "ADMINISTRADOR", "Administrador" #lo ve todo
        JEFE_MANTENCION = "JEFE MANTENCION", "Jefe Mantencion"
        SUPERVISOR = "SUPERVISOR", "Supervisor" #
        CONTROLADOR = "CONTROLADOR", "Controlador" #
        BASE_DATOS = "BASE DATOS", "Base de Datos"
        CONDUCTOR = "CONDUCTOR", "Conductor" #
        TRABAJADOR = "TRABAJADOR", "Trabajador" #
        SIN_ASIGNAR = "SIN ASIGNAR", "Sin Asignar" #no ve nada, solo su perfil

    base_role = "ADMIN"
    role = models.CharField(max_length=50, choices=Role.choices, verbose_name='Rol')
    phone = models.IntegerField(null=True, verbose_name='Telefono')


class UsuarioManager(BaseUserManager):
    def get_queryset(self, *args, **kwargs):
        results = super().get_queryset(*args, **kwargs)
        return results.filter(role=User.Role.SIN_ASIGNAR)

class Usuario(User):
    base_role = User.Role.SIN_ASIGNAR
    Usuario = UsuarioManager()
    class Meta:
        proxy = True

class UsuarioProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    faena = models.ForeignKey(Faena,on_delete=models.CASCADE,null=True, blank=True,verbose_name='Faena')
    ciudad = models.ForeignKey(Ciudad,on_delete=models.CASCADE,null=True, blank=True,verbose_name='Ciudad')
    nacionalidad = models.ForeignKey(Nacionalidad,on_delete=models.CASCADE,null=True, blank=True,verbose_name='Nacionalidad')
    genero = models.ForeignKey(Genero,on_delete=models.CASCADE,null=True, blank=True,verbose_name='Genero')
    fechaNacimiento = models.DateTimeField(auto_now=False,null=True, verbose_name='Fecha Nacimiento')
    fechaCedulaVencimiento = models.DateTimeField(auto_now=False,null=True, verbose_name='Cédula Identidad (Vencimiento)')
    seccionVehicular = models.CharField(max_length=10,choices=opcion,default='No',null=True, blank=True,verbose_name='Sección Vehicular')
    seccionSondaje = models.CharField(max_length=10,choices=opcion,default='No',null=True, blank=True,verbose_name='Sección Sondaje')
    seccionPrevencion = models.CharField(max_length=10,choices=opcion,default='No',null=True, blank=True,verbose_name='Sección Prevención de Riesgos')
    seccionInventario = models.CharField(max_length=10,choices=opcion,default='No',null=True, blank=True,verbose_name='Sección Inventario')
    def __str__(self) :
        return "{} {}".format(self.nacionalidad, self.ciudad)
    class Meta:
        verbose_name = 'Usuario Información Adicional'
        verbose_name_plural = 'Usuarios Información Adicional'
        
class LicenciasUsuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    fechaLicenciaVencimiento = models.DateTimeField(auto_now=False,null=True,verbose_name='Licencia Conducir (Vencimiento)')
    fechaLicenciaInternaVencimiento = models.DateTimeField(auto_now=False,null=True,verbose_name='Licencia Interna (Vencimiento)')
    licenciaClaseB = models.CharField(max_length=10,null=True,choices=opcion,verbose_name='Clase B')
    licenciaClaseC = models.CharField(max_length=10,null=True,choices=opcion,verbose_name='Clase C')
    licenciaClaseD = models.CharField(max_length=10,null=True,choices=opcion,verbose_name='Clase D')
    licenciaClaseE = models.CharField(max_length=10,null=True,choices=opcion,verbose_name='Clase E')
    licenciaClaseF = models.CharField(max_length=10,null=True,choices=opcion,verbose_name='Clase F')
    licenciaClaseA1 = models.CharField(max_length=10,null=True,choices=opcion,verbose_name='Clase A1')
    licenciaClaseA2 = models.CharField(max_length=10,null=True,choices=opcion,verbose_name='Clase A2')
    licenciaClaseA3 = models.CharField(max_length=10,null=True,choices=opcion,verbose_name='Clase A3')
    licenciaClaseA4 = models.CharField(max_length=10,null=True,choices=opcion,verbose_name='Clase A4')
    licenciaClaseA5 = models.CharField(max_length=10,null=True,choices=opcion,verbose_name='Clase A5')
    licenciaClaseA1Antigua = models.CharField(max_length=10,null=True,choices=opcion,verbose_name='Clase A1 Antigua')
    licenciaClaseA2Antigua = models.CharField(max_length=10,null=True,choices=opcion,verbose_name='Clase A2 Antigua')
    def __str__(self) :
        return "{}".format(self.id_usuario)
    class Meta:
        verbose_name = 'Licencia de Conducir'
        verbose_name_plural = 'Licencia de Conducir'
        db_table = 'user_licencia_conducir' 
    
class DocumentacionUsuario(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    def generaNombre(instance,filename):
        extension = os.path.splitext(filename)[1][1:]
        user_id = instance.user.username
        ruta = f'documentacion_usuario/{user_id}' 
        #ruta = 'documentacion_usuario'
        fecha =datetime.now().strftime("%Y%m%d_%H%M%S") 
        nombre = "{}.{}".format(fecha,extension)
        return os.path.join(ruta,nombre)            
    fotografiaUsuario = models.ImageField(upload_to=generaNombre,null=True,blank=True,default='documentacion_usuario/no-avatar.png')
    fotografiaCedula = models.ImageField(upload_to=generaNombre,null=True,blank=True,default='documentacion_usuario/no-imagen.png')
    fotografiaLicencia = models.ImageField(upload_to=generaNombre,null=True,blank=True,default='documentacion_usuario/no-imagen.png')
    fotografiaLicenciaInterna = models.ImageField(upload_to=generaNombre,null=True,blank=True,default='documentacion_usuario/no-imagen.png')
    def __str__(self) :
        return "{}".format(self.id_usuario)
    class Meta:
        verbose_name = 'Documentacion Usuario'
        verbose_name_plural = 'Documentacion Usuarios'
        db_table = 'user_documentacion' 

@receiver(post_save, sender=Usuario)
def create_usuario_profile(sender, instance, created, **kwargs):
    if created and instance.role.upper() == "SIN ASIGNAR":
        faena = Faena.objects.get(faena="SIN ASIGNAR")
        UsuarioProfile.objects.create(user=instance, faena=faena)

@receiver(post_save, sender=Usuario)
def create_licencias_usuario(sender, instance, created, **kwargs):
    LicenciasUsuario.objects.create(user=instance)
        
@receiver(post_save, sender=Usuario)
def create_documentacion_usuario(sender, instance, created, **kwargs):
    DocumentacionUsuario.objects.create(user=instance)



