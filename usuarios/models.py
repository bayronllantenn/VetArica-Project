from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models


# recordatorio: validar rut y telefono tengo hueva ahora

# el manager es lo que usa django cuando creas un usuario, por ejemplo con
# createsuperuser. el que trae django por defecto pide username, y como
# nosotros no tenemos ese campo hay que escribir uno propio bien simple
# que cree el usuario usando el email 

class PersonaManager(BaseUserManager):

    def create_user(self, email, password, rut='', telefono=''):
        email = self.normalize_email(email)
        user = self.model(email=email, rut=rut, telefono=telefono)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, rut='', telefono=''):
        user = self.create_user(email, password, rut, telefono)
        user.is_staff = True
        user.is_superuser = True
        user.save()
        return user


class Persona(AbstractUser):
    ROLES = [
        ('cliente', 'Cliente'),
        ('secretaria', 'Secretaria'),
        ('veterinaria', 'Veterinaria'),
        ('tecnico', 'Técnico'),
    ]

    username = None  # django trae este campo por defecto lo sacamos porque no lo usamos se loguea con email
    email = models.EmailField(unique=True)
    rut = models.CharField('RUT', max_length=12, unique=True)
    telefono = models.CharField('Teléfono', max_length=20)
    rol = models.CharField(max_length=20, choices=ROLES, default='cliente')

    USERNAME_FIELD = 'email'  # esto es porque vamos a logear al usuario con correo
    REQUIRED_FIELDS = []  # si lo saco se rompe el codigo porque abstractuser ya trae email aca por defecto y no puede repetirse con el username field

    objects = PersonaManager()  # type: ignore  # esta linea le dice a Persona que use el manager de arriba en vez del de django

    def __str__(self):
        return self.email


