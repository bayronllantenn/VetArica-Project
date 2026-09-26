from django.urls import path
from . import views

urlpatterns = [
    path('agendar/', views.agendar_view, name='agendar'),
    path('mascotas/agregar/', views.agregar_mascota, name='agregar_mascota'),
    path('confirmar/<int:id>/', views.confirmar_cita, name='confirmar_cita'),
    path('cancelar/<int:id>/', views.cancelar_solicitud, name='cancelar_solicitud'),

    # webpay
    path('pago/iniciar/<int:id>/', views.iniciar_pago_webpay, name='iniciar_pago_webpay'),
    path('pago/retorno/', views.retorno_webpay, name='retorno_webpay'),
    path('pago/exitosa/<int:id>/', views.reserva_exitosa, name='reserva_exitosa'),
    path('pago/fallida/', views.reserva_fallida, name='reserva_fallida'),
    path('pago/fallida/<int:id>/', views.reserva_fallida, name='reserva_fallida_id'),
]