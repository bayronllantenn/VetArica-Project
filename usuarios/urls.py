from django.urls import path

from . import views

urlpatterns = [
    path('registro/', views.registro_view, name='registro'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('sin-acceso/', views.sin_acceso_view, name='sin_acceso'),
    path('dashboard/', views.dashboard_usuario, name='dashboard'),
]
