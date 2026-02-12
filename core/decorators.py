from functools import wraps
from django.shortcuts import redirect

def is_admin(user):
    if not user.is_authenticated:
        return False
    return user.role == 'ADMINISTRADOR'

def is_jefe_mantencion(user):
    if not user.is_authenticated:
        return False
    return user.role == 'JEFE MANTENCION'

def is_supervisor(user):
    if not user.is_authenticated:
        return False
    return user.role == 'SUPERVISOR'

def is_conductor(user):
    if not user.is_authenticated:
        return False
    return user.role == 'CONDUCTOR'

def is_trabajador(user):
    if not user.is_authenticated:
        return False
    return user.role == 'TRABAJADOR'

def is_controlador(user):
    if not user.is_authenticated:
        return False
    return user.role == 'CONTROLADOR'

def is_base_datos(user):
    if not user.is_authenticated:
        return False
    return user.role == 'BASE DATOS'

def is_admin_or_jefe_mantencion(user):
    if not user.is_authenticated:
        return False
    return user.role in ['ADMINISTRADOR', 'JEFE MANTENCION']

def is_admin_or_controlador_or_base_datos_or_supervisor(user):
    if not user.is_authenticated:
        return False
    return user.role in ['ADMINISTRADOR', 'CONTROLADOR', 'BASE DATOS', 'SUPERVISOR']

def is_admin_or_base_datos_or_supervisor(user):
    if not user.is_authenticated:
        return False
    return user.role in ['ADMINISTRADOR', 'BASE DATOS', 'SUPERVISOR']

def controlador_or_base_datos(user):
    if not user.is_authenticated:
        return False
    return user.role in ['CONTROLADOR', 'BASE DATOS']

def is_admin_or_jefe_mantencion_or_supervisor(user):
    if not user.is_authenticated:
        return False
    return user.role in ['ADMINISTRADOR', 'JEFE MANTENCION', 'SUPERVISOR']

def vehicle_admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not is_admin(request.user):
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_or_jefe_mantencion_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not is_admin_or_jefe_mantencion(request.user):
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_or_jefe_mantencion_or_supervisor_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not is_admin_or_jefe_mantencion_or_supervisor(request.user):
            return redirect('dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def sondaje_admin_or_controlador_or_base_datos_or_supervisor_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not is_admin_or_controlador_or_base_datos_or_supervisor(request.user):
            return redirect('dashboardSondaje')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def sondaje_admin_or_base_datos_or_supervisor_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not is_admin_or_base_datos_or_supervisor(request.user):
            return redirect('dashboardSondaje')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not is_admin(request.user):
            if request.session['seccion'] == 'vehicular':
                return redirect('dashboard')
            if request.session['seccion'] == 'sondaje':
                return redirect('dashboardSondaje')
            if request.session['seccion'] == 'prevencion':
                return redirect('dashboardPrevencion')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
