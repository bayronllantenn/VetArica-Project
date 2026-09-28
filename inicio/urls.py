from django.urls import path

from . import views
from usuarios import views as usuarios_views
urlpatterns = [
    path('', views.index_view, name='home'),
    path('login/', usuarios_views.login_view, name='login'),
]
