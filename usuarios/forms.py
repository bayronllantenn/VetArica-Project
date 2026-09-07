from django.contrib.auth.forms import UserCreationForm

from .models import Persona


class RegisterForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Persona
        fields = ('email', 'first_name', 'last_name', 'rut', 'telefono')
