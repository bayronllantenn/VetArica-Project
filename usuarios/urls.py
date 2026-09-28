from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # login, registro 
    path('registro/', views.registro_view, name='registro'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('sin-acceso/', views.sin_acceso_view, name='sin_acceso'),

    # recuperar contrasena
    path(
        'recuperar/',
        auth_views.PasswordResetView.as_view(
            template_name='usuarios/recuperar_password.html',
            email_template_name='usuarios/recuperar_email.txt',
            subject_template_name='usuarios/recuperar_asunto.txt',
        ),
        name='password_reset',
    ),
    path('recuperar/enviado/', auth_views.PasswordResetDoneView.as_view(template_name='usuarios/cliente/recuperar_enviado.html'), name='password_reset_done'),
    path('restablecer/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='usuarios/cliente/nueva_password.html'), name='password_reset_confirm'),
    path('restablecer/completado/', auth_views.PasswordResetCompleteView.as_view(template_name='usuarios/cliente/password_reset_completo.html'), name='password_reset_complete'),

    # vistas cliente
    path('dashboard/', views.dashboard_usuario, name='dashboard'),
    path('historial-citas/', views.historial_citas, name='historial_citas'),
    path('mascota/<int:mascota_id>/', views.ficha_mascota, name='ficha_mascota'),
    path('configuracion/', views.configuracion, name='configuracion'),

    # vistas doctora
    path('doctora/dashboard/', views.dashboard_doctora, name='dashboard_doctora'),
]
