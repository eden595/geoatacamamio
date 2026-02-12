from django.urls import path, include
from .views import (save_checklist_materiales_sonda_entrada, save_checklist_materiales_sonda_salida, 
                    edit_checklist_materiales_sonda, manage_checklist_materiales_sonda, 
                    save_edit_checklist_materiales_sonda_entrada,save_edit_checklist_materiales_sonda_salida, 
                    new_checklist_materiales_caseta, edit_checklist_materiales_caseta, manage_checklist_materiales_caseta, 
                    save_edit_checklist_materiales_caseta)

urlpatterns = [
    path('save_checklist_materiales_sonda_entrada', save_checklist_materiales_sonda_entrada, name="save_checklist_materiales_sonda_entrada"),
    path('save_checklist_materiales_sonda_salida', save_checklist_materiales_sonda_salida, name="save_checklist_materiales_sonda_salida"),
    path('edit_checklist_materiales_sonda', edit_checklist_materiales_sonda, name='edit_checklist_materiales_sonda'),
    path('manage_checklist_materiales_sonda', manage_checklist_materiales_sonda, name="manage_checklist_materiales_sonda"),
    path('save_edit_checklist_materiales_sonda_entrada', save_edit_checklist_materiales_sonda_entrada, name="save_edit_checklist_materiales_sonda_entrada"),
    path('save_edit_checklist_materiales_sonda_salida', save_edit_checklist_materiales_sonda_salida, name="save_edit_checklist_materiales_sonda_salida"),

    path('new_checklist_materiales_caseta', new_checklist_materiales_caseta, name="new_checklist_materiales_caseta"),
    path('edit_checklist_materiales_caseta', edit_checklist_materiales_caseta, name='edit_checklist_materiales_caseta'),
    path('manage_checklist_materiales_caseta', manage_checklist_materiales_caseta, name="manage_checklist_materiales_caseta"),
    path('save_edit_checklist_materiales_caseta', save_edit_checklist_materiales_caseta, name="save_edit_checklist_materiales_caseta"),
]