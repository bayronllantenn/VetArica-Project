from datetime import datetime, timedelta

from django import forms
from django.db.models import Q
from django.utils import timezone

from .models import SolicitudCita

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

# Horas disponibles: cada 30 minutos, de 9:00 a 19:00
# De 14:00 a 16:00 es almuerzo, por eso no aparecen 14:00, 14:30, 15:00 ni 15:30
HORAS_ATENCION = [
    ('', 'Selecciona una hora'),
    ('09:00', '09:00'), ('09:30', '09:30'),
    ('10:00', '10:00'), ('10:30', '10:30'),
    ('11:00', '11:00'), ('11:30', '11:30'),
    ('12:00', '12:00'), ('12:30', '12:30'),
    ('13:00', '13:00'), ('13:30', '13:30'),
    ('16:00', '16:00'), ('16:30', '16:30'),
    ('17:00', '17:00'), ('17:30', '17:30'),
    ('18:00', '18:00'), ('18:30', '18:30'),
]

MINUTOS_PARA_PAGAR = 15


def citas_que_bloquean():
    limite = timezone.now() - timedelta(minutes=MINUTOS_PARA_PAGAR)
    return SolicitudCita.objects.exclude(estado='Cancelada').filter(Q(estado_pago='Pagado') | Q(estado_pago='Pendiente', fecha_creacion__gte=limite)
    )


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


def validar_nombre(valor, etiqueta, minimo=2, maximo=40):
    """Validación común para nombre, apellido y nombre de mascota."""
    valor = ' '.join(valor.split())  

    if len(valor) < minimo:
        raise forms.ValidationError(f'{etiqueta} debe tener al menos {minimo} letras.')
    if len(valor) > maximo:
        raise forms.ValidationError(f'{etiqueta} no puede superar los {maximo} caracteres.')
    if not valor.replace(' ', '').isalpha():
        raise forms.ValidationError(f'{etiqueta} solo puede contener letras.')
    if parece_texto_al_azar(valor):
        raise forms.ValidationError(f'{etiqueta} no parece válido. Revisa que esté bien escrito.')

    return valor.title()


class SolicitudCitaForm(forms.ModelForm):
    # fecha y hora separadas para que el usuario elija a su gusto
    fecha = forms.DateField(
        label='Fecha',
        widget=forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        error_messages={'required': 'Elige una fecha.'},
    )
    hora = forms.ChoiceField(
        label='Hora',
        choices=HORAS_ATENCION,
        error_messages={'required': 'Elige una hora.'},
    )

    class Meta:
        model = SolicitudCita
        
        fields = [
            'nombre',
            'apellido',
            'email',
            'telefono',
            'nombre_mascota',
            'tipo_consulta',
            'observaciones',
        ]
        widgets = {
            'email': forms.EmailInput(attrs={'placeholder': 'nombre@gmail.com'}),
            'telefono': forms.TextInput(attrs={'placeholder': '912345678'}),
            'observaciones': forms.Textarea(attrs={'placeholder': 'Observaciones (opcional)', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # El calendario no deja elegir días anteriores a hoy
        self.fields['fecha'].widget.attrs['min'] = timezone.localdate().isoformat()

    def clean_nombre(self):
        return validar_nombre(self.cleaned_data['nombre'], 'El nombre')

    def clean_apellido(self):
        return validar_nombre(self.cleaned_data['apellido'], 'El apellido')

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

    def clean_telefono(self):
        telefono = self.cleaned_data['telefono'].replace(' ', '')

        if not telefono.isdigit():
            raise forms.ValidationError('El teléfono solo puede contener números.')
        if len(telefono) != 9:
            raise forms.ValidationError('El teléfono debe tener 9 dígitos.')
        if not telefono.startswith('9'):
            raise forms.ValidationError('El teléfono debe comenzar con 9.')

        # valida que no sea un numero repetido o un numero falso como 12345678 o 87654321
        resto = telefono[1:]
        if resto == resto[0] * 8 or resto in ('12345678', '87654321'):
            raise forms.ValidationError('Ingresa un número de teléfono real.')

        return telefono


    def clean_nombre_mascota(self):
        return validar_nombre(self.cleaned_data['nombre_mascota'], 'El nombre de la mascota')

    def clean_tipo_consulta(self):
        tipo = self.cleaned_data['tipo_consulta']
        if tipo.precio_base <= 0:
            raise forms.ValidationError('Este tipo de consulta no está disponible.')
        return tipo

    def clean_fecha(self):
        fecha = self.cleaned_data['fecha']
        hoy = timezone.localdate()

        # No puede ser una fecha en el pasado
        if fecha < hoy:
            raise forms.ValidationError('No puedes agendar en una fecha pasada.')

        # No se atiende los domingos
        if fecha.weekday() == 6:
            raise forms.ValidationError('No atendemos los domingos.')

        # Máximo 60 días hacia adelante
        if fecha > hoy + timedelta(days=60):
            raise forms.ValidationError('Solo puedes agendar hasta 60 días hacia adelante.')

        return fecha

    def clean_observaciones(self):
        observaciones = ' '.join(self.cleaned_data.get('observaciones', '').split())

        # Es opcional, pero si escriben algo debe tener sentido
        if observaciones:
            if len(observaciones) < 10:
                raise forms.ValidationError('Si agregas observaciones, escribe al menos 10 caracteres.')
            if len(observaciones) > 500:
                raise forms.ValidationError('Las observaciones no pueden superar los 500 caracteres.')

        return observaciones

    def clean(self):
        cleaned_data = super().clean()
        fecha = cleaned_data.get('fecha')
        hora = cleaned_data.get('hora')
        telefono = cleaned_data.get('telefono')

        if fecha and hora:
            # Juntamos fecha + hora en un solo datetime (con la zona horaria de Chile)
            hora_elegida = datetime.strptime(hora, '%H:%M').time()
            fecha_hora = timezone.make_aware(datetime.combine(fecha, hora_elegida))

            # Horario de almuerzo: de 14:00 a 16:00 no se atiende
            if 14 <= hora_elegida.hour < 16:
                self.add_error('hora', 'Entre 14:00 y 16:00 es horario de almuerzo, elige otra hora.')

            # Si es hoy, la hora no puede haber pasado
            elif fecha_hora < timezone.now():
                self.add_error('hora', 'Esa hora ya pasó, elige una más tarde.')

            # El horario no puede estar ocupado por una cita pagada o en proceso de pago
            elif citas_que_bloquean().filter(fecha_hora=fecha_hora).exists():
                self.add_error('hora', 'Ese horario ya está ocupado, elige otro.')

            else:
                # Se guarda en el campo fecha_hora del modelo
                self.instance.fecha_hora = fecha_hora

        # Una misma persona no puede tener dos citas el mismo día
        if telefono and fecha:
            existe = citas_que_bloquean().filter(
                telefono=telefono,
                fecha_hora__date=fecha,
            ).exists()

            if existe:
                raise forms.ValidationError('Ya tienes una cita agendada para ese día.')

        return cleaned_data