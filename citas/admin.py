from django.contrib import admin
from .models import TipoConsulta, SolicitudCita, FichaMedica, Mascota

admin.site.register(TipoConsulta)
admin.site.register(SolicitudCita)
admin.site.register(FichaMedica)
admin.site.register(Mascota)
