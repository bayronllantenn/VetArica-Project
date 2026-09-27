from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.core.exceptions import ValidationError
from django import forms
from django.core.validators import FileExtensionValidator

from .models import Persona

DOMINIOS_CONOCIDOS = {
    'gmail': ['gmail.com'],
    'hotmail': ['hotmail.com', 'hotmail.cl', 'hotmail.es'],
    'outlook': ['outlook.com', 'outlook.cl', 'outlook.es'],
    'yahoo': ['yahoo.com', 'yahoo.cl', 'yahoo.es'],
    'live': ['live.com', 'live.cl'],
    'icloud': ['icloud.com'],
}




def validar_nombre(valor, etiqueta):
    valor = valor.lower()

    if len(valor) < 3 or len(valor) > 15:
        raise ValidationError(f'{etiqueta} ingresado no es valido.')
    if not valor.isalpha():
        raise ValidationError(f'{etiqueta} ingresado no es valido.')

    return valor

class RegisterForm(UserCreationForm):
    class Meta:
        model = Persona
        fields = ('email', 'first_name', 'last_name', 'rut', 'telefono')
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'Nombre'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Apellido'}),
            'rut': forms.TextInput(attrs={'placeholder': 'RUT (ej: 12345678-9)'}),
            'telefono': forms.TextInput(attrs={
                'placeholder': '912345678',
                'inputmode': 'numeric',
                'pattern': '[0-9]{9}',
                'maxlength': '9',
                'title': 'Ingresa 9 números, ej: 912345678',
            }),
            'email': forms.EmailInput(attrs={'placeholder': 'Correo electrónico'}),
        }

    def __init__(self, data=None):
        super().__init__(data)
        self.fields['password1'].widget.attrs['placeholder'] = 'Contraseña'
        self.fields['password2'].widget.attrs['placeholder'] = 'Confirmar contraseña'

    def clean_telefono(self):
        telefono = self.cleaned_data['telefono'].replace(' ', '')

        if telefono.startswith('+56'):
            telefono = telefono[3:]
        elif telefono.startswith('56'):
            telefono = telefono[2:]

        if not telefono.isdigit():
            raise ValidationError('El telefono solo puede tener numeros.')
        if len(telefono) != 9:
            raise ValidationError('El telefono debe tener 9 digitos (ej: 998555962).')
        if telefono[0] != '9':
            raise ValidationError('El telefono debe empezar con 9.')

        return telefono

    def clean_rut(self):
        rut = self.cleaned_data['rut'].replace('.', '').replace('-', '').upper()

        cuerpo = rut[:-1]  # tambien puede sin el digito verificador, pero se necesita para validar
        dv_rut = rut[-1]  # necesita que tenga el digito verificardor al final 

        if not cuerpo.isdigit() or len(cuerpo) < 7 or len(cuerpo) > 8:
            raise ValidationError('El rut ingresado es invalido.')

        suma = 0
        multiplo = 2
        for digito in reversed(cuerpo):
            suma += int(digito) * multiplo
            multiplo += 1
            if multiplo > 7:
                multiplo = 2

        resto = 11 - (suma % 11)
        if resto == 11:
            dv_esperado = '0'
        elif resto == 10:
            dv_esperado = 'K'
        else:
            dv_esperado = str(resto)

        if dv_rut != dv_esperado:
            raise ValidationError('El rut ingresado es invalido.')

        return rut

    def clean_first_name(self):
        return validar_nombre(self.cleaned_data['first_name'], 'El nombre')

    def clean_last_name(self):
        return validar_nombre(self.cleaned_data['last_name'], 'El apellido')

    def clean_email(self):
        # el formato ya lo valida el EmailField
        email = self.cleaned_data['email'].strip().lower()
        dominio = email.split('@')[1]
        nombre_dominio = dominio.split('.')[0]

        if nombre_dominio in DOMINIOS_CONOCIDOS and dominio not in DOMINIOS_CONOCIDOS[nombre_dominio]:
            sugerencia = DOMINIOS_CONOCIDOS[nombre_dominio][0]
            raise forms.ValidationError(f'Revisa el correo, ¿es @{sugerencia}?')

        return email


class LoginForm(AuthenticationForm):
    def __init__(self, request=None, data=None):
        super().__init__(request, data=data)
        self.fields['username'].widget = forms.EmailInput(attrs={
            'placeholder': 'Correo electrónico',
            'autofocus': True,
        })
        self.fields['password'].widget.attrs['placeholder'] = 'Contraseña'


class ConfiguracionForm(forms.ModelForm):
    class Meta:
        model = Persona
        fields = ('first_name', 'last_name', 'telefono', 'email', 'foto')  
        labels = {
            'first_name': 'Nombre',
            'last_name': 'Apellidos',
            'telefono': 'Teléfono',
            'email': 'Email',
            'foto': 'Foto de perfil',
        }
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'Nombre'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Apellido'}),
            'telefono': forms.TextInput(attrs={
                'placeholder': '912345678',
                'inputmode': 'numeric',
                'pattern': '[0-9]{9}',
                'maxlength': '9',
                'title': 'Ingresa 9 números, ej: 912345678',
            }),
            'email': forms.EmailInput(attrs={'placeholder': 'Correo electrónico'}),
            'foto': forms.FileInput(attrs={'accept': 'image/*'}),
        }

    clean_first_name = RegisterForm.clean_first_name
    clean_last_name = RegisterForm.clean_last_name