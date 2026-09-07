from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


# recordatorio: validar rut y telefono tengo hueva ahora 

class Persona(AbstractUser):
    ROLES = [
        ('cliente', 'Cliente'),
        ('secretaria', 'Secretaria'),
        ('veterinaria', 'Veterinaria'),
        ('tecnico', 'Técnico'),
    ]

    username = None  # django trae este campo por defecto lo sacamos porque no lo usamos se loguea con email
    email = models.EmailField(unique=True)
    rut = models.CharField(max_length=12, unique=True)
    telefono = models.CharField(max_length=20)
    rol = models.CharField(max_length=20, choices=ROLES, default='cliente')

    USERNAME_FIELD = 'email'  # esto es porque vamos a logear al usuario con correo
    REQUIRED_FIELDS = []  # si lo saco truena porque abstractuser ya trae email aca por defecto y no puede repetirse con el username field

    def __str__(self):
        return self.email
