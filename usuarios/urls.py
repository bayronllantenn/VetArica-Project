from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('registro/', views.registro_view, name='registro'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('sin-acceso/', views.sin_acceso_view, name='sin_acceso'),
    path('dashboard/', views.dashboard_usuario, name='dashboard'),
    path('historial-citas/', views.historial_citas, name='historial_citas'),
    path('mascota/<int:mascota_id>/', views.ficha_mascota, name='ficha_mascota'),
    path('configuracion/', views.configuracion, name='configuracion'),
    path('restablecer/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='usuarios/cliente/nueva_password.html'), name='password_reset_confirm'),
]
