from django.conf import settings
from django.db import models


class TipoConsulta(models.Model):
    nombre = models.CharField(max_length=100)
    precio_base = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.nombre} - ${self.precio_base}"


class SolicitudCita(models.Model):

    ESTADOS = [
        ('Pendiente', 'Pendiente'),
        ('Confirmada', 'Confirmada'),
        ('Cancelada', 'Cancelada'),
        ('Finalizado', 'Finalizado'),
    ]
    ESTADOS_PAGO = [
        ('Pendiente', 'Pendiente'),
        ('Pagado', 'Pagado'),
        ('Rechazado', 'Rechazado'),
        ('Anulado', 'Anulado'),
    ]

    # si el que agenda tiene cuenta y esta logueado, lo guardamos aca
    # si no tiene cuenta, cliente queda en null y se usan los campos de contacto de abajo
    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='citas_solicitadas',
    )

    estado_pago = models.CharField(max_length=20, choices=ESTADOS_PAGO, default='Pendiente')
    webpay_token = models.CharField(max_length=255, blank=True, null=True)
    webpay_orden = models.CharField(max_length=100, blank=True, null=True)

    monto_pagado = models.PositiveIntegerField(null=True, blank=True)
    fecha_pago = models.DateTimeField(null=True, blank=True)
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)

    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=9)

    nombre_mascota = models.CharField(max_length=100)

    tipo_consulta = models.ForeignKey(TipoConsulta, on_delete=models.CASCADE, related_name='solicitudes')
    veterinario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='citas_asignadas',
    )

    # fecha para la cita
    fecha_hora = models.DateTimeField()

    observaciones = models.TextField(blank=True)

    estado = models.CharField(max_length=20, choices=ESTADOS, default='Pendiente')

    # fecha en la que se creo la solicitud
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido} - {self.nombre_mascota}"


class FichaMedica(models.Model):
    solicitud = models.OneToOneField(SolicitudCita, on_delete=models.CASCADE, related_name='ficha_medica')
    especie = models.CharField(max_length=50, default='No especifica')
    raza = models.CharField(max_length=100, blank=True)
    sexo = models.CharField(max_length=20, blank=True)
    edad_mascota = models.PositiveIntegerField(null=True, blank=True)
    peso = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    motivo_consulta = models.TextField()
    diagnostico = models.TextField()
    tratamiento = models.TextField()
    observaciones = models.TextField(blank=True)
    fecha_atencion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Ficha de {self.solicitud.nombre_mascota}"

