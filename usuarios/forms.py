from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django import forms

from .models import Persona

VOCALES = 'aeiouáéíóúü'

PATRONES_TECLADO = [
    'qwe', 'asd', 'sdf', 'dfg', 'fgh', 'ghj', 'hjk', 'jkl',
    'zxc', 'xcv', 'cvb', 'vbn', 'bnm',
]

DOMINIOS_CONOCIDOS = {
    'gmail': ['gmail.com'],
    'hotmail': ['hotmail.com', 'hotmail.cl', 'hotmail.es'],
    'outlook': ['outlook.com', 'outlook.cl', 'outlook.es'],
    'yahoo': ['yahoo.com', 'yahoo.cl', 'yahoo.es'],
    'live': ['live.com', 'live.cl'],
    'icloud': ['icloud.com'],
}

EXTENSIONES_VALIDAS = ['com', 'cl', 'net', 'org', 'es', 'edu', 'gob', 'info', 'io']

def parece_texto_al_azar(texto, revisar_vocales=True):
    """Devuelve True si alguna palabra parece escrita al azar."""
    for palabra in texto.lower().split():
    
        if revisar_vocales and not any(letra in VOCALES for letra in palabra):
            return True

        consonantes_seguidas = 0
        for letra in palabra:
            if letra.isalpha() and letra not in VOCALES:
                consonantes_seguidas += 1
                if consonantes_seguidas >= 5:
                    return True
            else:
                consonantes_seguidas = 0

        for i in range(len(palabra) - 2):
            if palabra[i] == palabra[i + 1] == palabra[i + 2]:
                return True

        for i in range(len(palabra) - 5):
            if palabra[i:i + 3] == palabra[i + 3:i + 6]:
                return True

        for patron in PATRONES_TECLADO:
            if patron in palabra:
                return True

    return False

class RegisterForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Persona
        fields = ('email', 'first_name', 'last_name', 'rut', 'telefono')

    def clean_telefono(self): #validacion para el telefono
        
        value = self.cleaned_data['telefono']

        telefono = value.replace(' ', '') # Limpia el telefono quitando los espacios
    
        if telefono.startswith('+56'): # si el numero empieza en +56 toma el telefono desde la posicion 3
            telefono = telefono[3:]
    
        elif telefono.startswith('56'): # si el numero empieza en 56 toma el telefono desde la posicion 2
            telefono = telefono[2:]
    
        if len(telefono) != 9: # valida si el telefono tiene 9 digitos
            raise ValidationError ('El telefono debe tener 9 dígitos (ej: 998555962).')
    
        if telefono[0] != '9': # valida si el numero empieza en 9
            raise ValidationError ('El telefono debe empezar con 9.')
    
        if not telefono.isdigit(): # valida si el telefono contiene solo numeros 
            raise ValidationError('El telefono solo puede números')
        
        return telefono

    def clean_rut(self):

        value = self.cleaned_data['rut']

        rut = value.replace('.', '') # limpia el rut quitando los "."
        rut = rut.replace('-', '') # limpia el rut quitando "-"
        rut = rut.upper() # si el dv esta en minuscula lo pasa a mayusculas

        cuerpo = rut[:-1]  # toma todo el rut menos el ultimo digito el dv (digito identificador)
        dv_rut = rut[-1] # toma el ultimo digito del rut

        if not cuerpo.isdigit():   # revisa si el cuerpo del rut son solo numeros
            raise ValidationError('El rut ingresado es invalido.')

        if len(cuerpo) < 7 or len(cuerpo) > 8: # revisa si el cuerpo del rut tiene el largo correcto de 7 a 8 digitos
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
        value = self.cleaned_data['first_name']

        nombre = value.lower()  # pasa todo a minusculas

        if len(nombre) < 3:      # si el nombre tiene menos de 3 caracteres = error
            raise ValidationError('El nombre ingresado no es valido.')

        if len(nombre) > 15:      # si el nombre tiene mas de 15 caracteres = error
            raise ValidationError('El nombre ingresado no es valido.')

        if not nombre.isalpha():  
            raise ValidationError('El nombre ingresado no es valido.')

        return nombre

    def clean_last_name(self):

        value = self.cleaned_data['last_name']

        apellido = value.lower()

        if len(apellido) < 3: # si el apellido tiene menos de 3 caracteres = error
            raise ValidationError('El apellido ingresado no es valido.')
        
        if len(apellido) > 15: # si el apellido tiene mas de 15 caracteres = error
            raise ValidationError('El apellido ingresado no es valido.')
        
        if not apellido.isalpha():
            raise ValidationError('El apellido ingresado no es valido.')
        
        return apellido

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()

        if not email:
            raise forms.ValidationError('El correo es obligatorio.')
        if ' ' in email:
            raise forms.ValidationError('El correo no puede contener espacios.')
        if email.count('@') != 1:
            raise forms.ValidationError('El correo debe contener un solo @.')
        if len(email) > 100:
            raise forms.ValidationError('El correo es demasiado largo.')

        usuario, dominio = email.split('@')

        # Parte antes del @ ---
        if len(usuario) < 3:
            raise forms.ValidationError('La parte antes del @ es muy corta.')
        for letra in usuario:
            if not (letra.isalnum() or letra in '._-+'):
                raise forms.ValidationError('El correo contiene caracteres no permitidos.')
        if usuario.startswith('.') or usuario.endswith('.') or '..' in usuario:
            raise forms.ValidationError('El correo no puede empezar o terminar con punto, ni tener dos puntos seguidos.')

        # Revisamos solo las letras (ej. "juan.perez91" -> "juan perez")
        solo_letras = ''.join(letra if letra.isalpha() else ' ' for letra in usuario)
        if parece_texto_al_azar(solo_letras, revisar_vocales=False):
            raise forms.ValidationError('El correo no parece válido. Revisa que esté bien escrito.')

        # Parte después del @ ---
        if '.' not in dominio:
            raise forms.ValidationError('Ingresa un correo válido, por ejemplo nombre@gmail.com.')

        extension = dominio.split('.')[-1]
        if extension not in EXTENSIONES_VALIDAS:
            raise forms.ValidationError(f'La terminación ".{extension}" no es válida. Revisa tu correo.')

        # si se usa gmail, hotmail, outlook, yahoo etc debe estar bien escrito
        nombre_dominio = dominio.split('.')[0]
        if nombre_dominio in DOMINIOS_CONOCIDOS and dominio not in DOMINIOS_CONOCIDOS[nombre_dominio]:
            sugerencia = DOMINIOS_CONOCIDOS[nombre_dominio][0]
            raise forms.ValidationError(f'El dominio no es correcto. ¿Quisiste decir @{sugerencia}?')

        return email




