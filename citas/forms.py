from datetime import datetime, timedelta

from django import forms
from django.utils import timezone

from .models import (
    ESPECIES_MASCOTA,
    SEXOS_MASCOTA,
    UNIDADES_EDAD_MASCOTA,
    Mascota,
    SolicitudCita,
    TipoConsulta,
)

DOMINIOS_CONOCIDOS = {
    'gmail': ['gmail.com'],
    'hotmail': ['hotmail.com', 'hotmail.cl', 'hotmail.es'],
    'outlook': ['outlook.com', 'outlook.cl', 'outlook.es'],
    'yahoo': ['yahoo.com', 'yahoo.cl', 'yahoo.es'],
}

# entre las 14:00 y las 16:00 no atendemos, es hora de almuerzo
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
MINUTOS_ANTICIPACION_MINIMA = 60


def cancelar_citas_vencidas():
    # si ya paso el tiempo para pagar y el cliente nunca pago la cita se cancela sola
    limite = timezone.now() - timedelta(minutes=MINUTOS_PARA_PAGAR)
    SolicitudCita.objects.filter(estado_pago='Pendiente', fecha_creacion__lt=limite).update(
        estado='Cancelada', estado_pago='Rechazado'
    )


def citas_que_bloquean():
    cancelar_citas_vencidas()

    # las citas pendientes que todavia estan a tiempo de pagarse tambien
    # cuentan como ocupadas, para que nadie mas agende esa misma hora
    citas = SolicitudCita.objects.filter(estado_pago__in=['Pagado', 'Pendiente'])

    # si alguien cancela una cita a mano desde el admin, esa hora se libera
    # de nuevo, aunque el pago haya quedado marcado como pagado
    return citas.exclude(estado='Cancelada')


def obtener_horas_disponibles(fecha=None):
    if not fecha:
        fecha = timezone.localdate()

    citas = citas_que_bloquean().filter(fecha_hora__date=fecha)
    horas_ocupadas = [timezone.localtime(c.fecha_hora).strftime('%H:%M') for c in citas]

    minimo = timezone.now() + timedelta(minutes=MINUTOS_ANTICIPACION_MINIMA)

    horas_libres = [('', 'Selecciona una hora')]
    for hora, etiqueta in HORAS_ATENCION:
        if not hora or hora in horas_ocupadas:
            continue

        # junto la fecha con la hora para saber si ya paso o esta muy cerca
        # asi funciona bien tanto para hoy como para cualquier otro dia
        hora_elegida = datetime.strptime(hora, '%H:%M').time()
        fecha_hora = timezone.make_aware(datetime.combine(fecha, hora_elegida))
        if fecha_hora < minimo:
            continue

        horas_libres.append((hora, etiqueta))

    return horas_libres


def validar_edad(valor, unidad):
    if valor <= 0:
        return 'La edad debe ser mayor a 0.'

    limite = 40 if unidad == 'años' else 480
    if valor > limite:
        return f'Esa edad no parece real estando en {unidad}.'

    return None


def validar_nombre(valor, etiqueta, minimo=2, maximo=40):
    valor = ' '.join(valor.split())

    if len(valor) < minimo:
        raise forms.ValidationError(f'{etiqueta} debe tener al menos {minimo} letras.')
    if len(valor) > maximo:
        raise forms.ValidationError(f'{etiqueta} no puede superar los {maximo} caracteres.')
    if not valor.replace(' ', '').isalpha():
        raise forms.ValidationError(f'{etiqueta} solo puede contener letras.')

    return valor.title()


class SolicitudCitaForm(forms.ModelForm):
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
    tipo_consulta = forms.ModelChoiceField(
        queryset=TipoConsulta.objects.all(),
        empty_label=None,
        error_messages={'required': 'Elige un tipo de consulta.'},
    )
    especie_mascota = forms.ChoiceField(
        label='Especie',
        choices=[('', 'Especie de tu mascota')] + ESPECIES_MASCOTA,
        error_messages={'required': 'Elige la especie de tu mascota.'},
    )
    sexo_mascota = forms.ChoiceField(
        label='Sexo',
        choices=[('', 'Sexo de tu mascota')] + SEXOS_MASCOTA,
        error_messages={'required': 'Elige el sexo de tu mascota.'},
    )
    edad_unidad_mascota = forms.ChoiceField(
        label='Unidad',
        choices=UNIDADES_EDAD_MASCOTA,
        required=False,
        initial='años',
    )

    class Meta:
        model = SolicitudCita
        fields = [
            'nombre',
            'apellido',
            'email',
            'telefono',
            'nombre_mascota',
            'especie_mascota',
            'raza_mascota',
            'sexo_mascota',
            'edad_valor_mascota',
            'edad_unidad_mascota',
            'tipo_consulta',
            'observaciones',
        ]
        widgets = {
            'email': forms.EmailInput(attrs={'placeholder': 'nombre@gmail.com'}),
            'telefono': forms.TextInput(attrs={'placeholder': '912345678'}),
            'raza_mascota': forms.TextInput(attrs={'placeholder': 'Raza (opcional)'}),
            'edad_valor_mascota': forms.NumberInput(attrs={'placeholder': 'Edad', 'min': 1}),
            'observaciones': forms.Textarea(attrs={'placeholder': 'Observaciones (opcional)', 'rows': 3}),
        }

    def clean_nombre(self):
        return validar_nombre(self.cleaned_data['nombre'], 'El nombre')

    def clean_apellido(self):
        return validar_nombre(self.cleaned_data['apellido'], 'El apellido')

    def clean_nombre_mascota(self):
        return validar_nombre(self.cleaned_data['nombre_mascota'], 'El nombre de la mascota')

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        dominio = email.split('@')[1]
        nombre_dominio = dominio.split('.')[0]

        if nombre_dominio in DOMINIOS_CONOCIDOS and dominio not in DOMINIOS_CONOCIDOS[nombre_dominio]:
            sugerencia = DOMINIOS_CONOCIDOS[nombre_dominio][0]
            raise forms.ValidationError(f'Revisa el correo, ¿es @{sugerencia}?')

        return email

    def clean_telefono(self):
        telefono = self.cleaned_data['telefono'].replace(' ', '')

        if not telefono.isdigit():
            raise forms.ValidationError('El teléfono solo puede contener números.')
        if len(telefono) != 9 or not telefono.startswith('9'):
            raise forms.ValidationError('El teléfono debe tener 9 dígitos y empezar con 9.')

        resto = telefono[1:]
        if resto == resto[0] * 8 or resto in ('12345678', '87654321'):
            raise forms.ValidationError('Ingresa un número de teléfono real.')

        return telefono

    def clean_tipo_consulta(self):
        tipo = self.cleaned_data['tipo_consulta']
        if tipo.precio_base <= 0:
            raise forms.ValidationError('Este tipo de consulta no está disponible.')
        return tipo

    def clean_fecha(self):
        fecha = self.cleaned_data['fecha']
        hoy = timezone.localdate()

        if fecha < hoy:
            raise forms.ValidationError('No puedes agendar en una fecha pasada.')
        if fecha.weekday() == 6:
            raise forms.ValidationError('No atendemos los domingos.')
        if fecha > hoy + timedelta(days=60):
            raise forms.ValidationError('Solo puedes agendar hasta 60 días hacia adelante.')

        return fecha

    def clean_observaciones(self):
        observaciones = ' '.join((self.cleaned_data.get('observaciones') or '').split())

        if len(observaciones) > 500:
            raise forms.ValidationError('Las observaciones no pueden superar los 500 caracteres.')

        return observaciones

    def clean(self):
        cleaned_data = super().clean()
        fecha = cleaned_data.get('fecha')
        hora = cleaned_data.get('hora')
        telefono = cleaned_data.get('telefono')
        edad_valor = cleaned_data.get('edad_valor_mascota')
        edad_unidad = cleaned_data.get('edad_unidad_mascota')

        if edad_valor is not None:
            error = validar_edad(edad_valor, edad_unidad)
            if error:
                self.add_error('edad_valor_mascota', error)

        if fecha and hora:
            hora_elegida = datetime.strptime(hora, '%H:%M').time()
            fecha_hora = timezone.make_aware(datetime.combine(fecha, hora_elegida))

            if fecha_hora < timezone.now() + timedelta(minutes=MINUTOS_ANTICIPACION_MINIMA):
                self.add_error('hora', 'Elige un horario con al menos 1 hora de anticipación.')
            elif citas_que_bloquean().filter(fecha_hora=fecha_hora).exists():
                self.add_error('hora', 'Ese horario ya está ocupado, elige otro.')
            else:
                self.instance.fecha_hora = fecha_hora

        # una persona no puede tener dos citas el mismo dia
        if telefono and fecha:
            if citas_que_bloquean().filter(telefono=telefono, fecha_hora__date=fecha).exists():
                raise forms.ValidationError('Ya tienes una cita agendada para ese día.')

        return cleaned_data


class MascotaForm(forms.ModelForm):
    class Meta:
        model = Mascota
        fields = ['nombre', 'especie', 'raza', 'sexo', 'edad_valor', 'edad_unidad', 'imagen']

    def clean_nombre(self):
        return validar_nombre(self.cleaned_data['nombre'], 'El nombre de la mascota')

    def clean_imagen(self):
        imagen = self.cleaned_data.get('imagen')
        if imagen and imagen.size > 2 * 1024 * 1024:
            raise forms.ValidationError('La imagen no puede pesar más de 2 MB.')
        return imagen

    def clean(self):
        cleaned_data = super().clean()
        valor = cleaned_data.get('edad_valor')
        unidad = cleaned_data.get('edad_unidad')

        if valor is not None:
            error = validar_edad(valor, unidad)
            if error:
                self.add_error('edad_valor', error)

        return cleaned_data
