from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db.models import Sum
from django.http import Http404
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache

from usuarios.views import es_personal_clinica
from .forms import FichaMedicaForm, MascotaForm, SolicitudCitaForm, obtener_horas_disponibles, rango_del_dia
from .models import FichaMedica, Mascota, SolicitudCita
from .utils import get_webpay_transaction


def puede_ver_solicitud(request, solicitud):
    if solicitud.cliente_id:
        return request.user.is_authenticated and request.user.id == solicitud.cliente_id

    return solicitud.id in request.session.get('mis_solicitudes', [])


def enviar_correo_confirmacion(solicitud):
    if not solicitud.email:
        return

    fecha = timezone.localtime(solicitud.fecha_hora).strftime('%d/%m/%Y %H:%M')
    asunto = 'Recordatorio de tu cita - Vet Arica'
    mensaje = (
        f'Hola {solicitud.nombre}, te recordamos tu cita para {solicitud.nombre_mascota} '
        f'el {fecha}. Te esperamos en Vet Arica.'
    )
    try:
        send_mail(asunto, mensaje, None, [solicitud.email])
    except Exception:
        pass


@login_required(login_url='sin_acceso')
def agregar_mascota(request):
    if request.method == 'POST':
        form = MascotaForm(request.POST, request.FILES)
        if form.is_valid():
            mascota = form.save(commit=False)
            mascota.dueno = request.user
            mascota.save()
            messages.success(request, 'Mascota agregada correctamente.')
            return redirect('dashboard')
    else:
        form = MascotaForm()
    return render(request, 'citas/agregar_mascota_form.html', {'form': form})


def agendar_view(request):
    if request.user.is_authenticated:
        mascotas = Mascota.objects.filter(dueno=request.user)
    else:
        mascotas = []
    fecha_param = request.GET.get('fecha') or request.POST.get('fecha')
    mascota_id = request.GET.get('mascota_id') or request.POST.get('mascota_id')

    try:
        fecha_seleccionada = datetime.strptime(str(fecha_param), '%Y-%m-%d').date()
    except (ValueError, TypeError):
        fecha_seleccionada = timezone.localdate()

    mascota_elegida = None
    if mascota_id and request.user.is_authenticated:
        mascota_elegida = Mascota.objects.filter(id=mascota_id, dueno=request.user).first()

    # solo escondemos los datos de contacto si la cuenta ya los tiene
    # completos si falta alguno se muestran para que los complete ahi
    cuenta_completa = bool(
        request.user.is_authenticated
        and request.user.first_name
        and request.user.last_name
        and request.user.telefono
    )

    if request.method == 'POST':
        datos = request.POST.copy()
        if cuenta_completa:
            datos.update({
                'nombre': request.user.first_name,
                'apellido': request.user.last_name,
                'email': request.user.email,
                'telefono': request.user.telefono,
            })
        form = SolicitudCitaForm(datos)
        form.fields['hora'].choices = obtener_horas_disponibles(fecha_seleccionada)
        if form.is_valid():
            solicitud = form.save(commit=False)
            if request.user.is_authenticated:
                solicitud.cliente = request.user
                solicitud.mascota = mascota_elegida
            solicitud.estado = 'Pendiente'
            solicitud.estado_pago = 'Pendiente'
            solicitud.save()

            ids_sesion = request.session.get('mis_solicitudes', [])
            ids_sesion.append(solicitud.id)
            request.session['mis_solicitudes'] = ids_sesion

            return redirect('confirmar_cita', solicitud.id)
    else:
        # si viene de recargar la pagina (por ejemplo al cambiar la fecha)
        # esto rescata lo que la persona ya habia escrito en el formulario
        campos_del_form = [
            'fecha', 'hora', 'nombre', 'apellido', 'email', 'telefono',
            'nombre_mascota', 'especie_mascota', 'raza_mascota', 'sexo_mascota',
            'edad_valor_mascota', 'edad_unidad_mascota', 'tipo_consulta', 'observaciones',
        ]
        initial = {}
        for campo in campos_del_form:
            valor = request.GET.get(campo)
            if valor:
                initial[campo] = valor
        initial['fecha'] = fecha_seleccionada
        if cuenta_completa:
            initial.update({
                'nombre': request.user.first_name,
                'apellido': request.user.last_name,
                'email': request.user.email,
                'telefono': request.user.telefono,
            })
        if mascota_elegida:
            initial.update({
                'nombre_mascota': mascota_elegida.nombre,
                'especie_mascota': mascota_elegida.especie,
                'raza_mascota': mascota_elegida.raza,
                'sexo_mascota': mascota_elegida.sexo,
                'edad_valor_mascota': mascota_elegida.edad_valor,
                'edad_unidad_mascota': mascota_elegida.edad_unidad,
            })
        form = SolicitudCitaForm(initial=initial)
        form.fields['hora'].choices = obtener_horas_disponibles(fecha_seleccionada)

    form.fields['fecha'].widget.attrs['min'] = timezone.localdate().isoformat()

    return render(request, 'citas/agendar_form.html', {
        'form': form,
        'mascotas': mascotas,
        'fecha_seleccionada': fecha_seleccionada,
        'mascota_elegida': mascota_elegida,
        'cuenta_completa': cuenta_completa,
    })


def confirmar_cita(request, id):
    solicitud = get_object_or_404(SolicitudCita, id=id)
    if not puede_ver_solicitud(request, solicitud):
        raise Http404
    return render(request, 'citas/confirmar_cita.html', {'solicitud': solicitud})


def cancelar_solicitud(request, id):
    solicitud = get_object_or_404(SolicitudCita, id=id)
    if not puede_ver_solicitud(request, solicitud):
        raise Http404
    solicitud.delete()
    messages.info(request, 'Cancelaste la solicitud de cita.')
    return redirect('agendar')


# WEBPAY

def iniciar_pago_webpay(request, id):
    solicitud = get_object_or_404(SolicitudCita, id=id)
    if not puede_ver_solicitud(request, solicitud):
        raise Http404

    if solicitud.estado_pago == 'Pagado':
        messages.info(request, 'Esta cita ya se encuentra pagada.')
        return redirect('reserva_exitosa', solicitud.pk)

    monto = solicitud.tipo_consulta.precio_base

    buy_order = f'cita-{solicitud.pk}-{int(timezone.now().timestamp())}'
    session_id = f'sesion-{solicitud.pk}'

    return_url = request.build_absolute_uri(reverse('retorno_webpay'))

    try:
        tx = get_webpay_transaction()
        response = tx.create(buy_order=buy_order, session_id=session_id, amount=monto, return_url=return_url)
        solicitud.webpay_orden = buy_order
        solicitud.webpay_token = response['token']
        solicitud.save()

        return render(request, 'citas/pago/redirigir_webpay.html', {'url': response['url'], 'token': response['token']})

    except Exception as e:
        messages.error(request, f'Error al iniciar el pago: {e}')
        return redirect('reserva_fallida')


def marcar_pago_rechazado(solicitud):
    solicitud.estado = 'Cancelada'
    solicitud.estado_pago = 'Rechazado'
    solicitud.save()


def retorno_webpay(request):

    tbk_token = request.GET.get('TBK_TOKEN') or request.POST.get('TBK_TOKEN')
    if tbk_token:
        solicitud = SolicitudCita.objects.filter(webpay_token=tbk_token).first()
        if solicitud:
            marcar_pago_rechazado(solicitud)
        messages.error(request, 'Cancelaste el pago. La cita fue cancelada.')
        return redirect('reserva_fallida')

    token = request.GET.get('token_ws') or request.POST.get('token_ws')

    if not token:
        messages.error(request, 'No se recibió respuesta de Webpay.')
        return redirect('reserva_fallida')

    # a que cita corresponde el pago
    solicitud = SolicitudCita.objects.filter(webpay_token=token).first()
    if not solicitud:
        messages.error(request, 'No se encontró la solicitud asociada al pago.')
        return redirect('reserva_fallida')

    try:
        tx = get_webpay_transaction()
        # aqui se confirma el pago con webpay, commit(token) le pregunta a
        # webpay si el pago fue aprobado o rechazado
        response = tx.commit(token)
        if response.get('status') == 'AUTHORIZED':
            solicitud.estado = 'Confirmada'
            solicitud.estado_pago = 'Pagado'
            solicitud.monto_pagado = solicitud.tipo_consulta.precio_base
            solicitud.fecha_pago = timezone.now()
            solicitud.save()
            enviar_correo_confirmacion(solicitud)
            messages.success(request, 'Tu cita fue reservada y pagada correctamente.')
            return redirect('reserva_exitosa', solicitud.pk)
        else:
            marcar_pago_rechazado(solicitud)
            messages.error(request, 'El pago no fue aprobado. La cita fue cancelada.')
            return redirect('reserva_fallida_id', solicitud.pk)
    except Exception as e:
        marcar_pago_rechazado(solicitud)
        messages.error(request, f'Error al confirmar el pago: {e}')
        return redirect('reserva_fallida_id', solicitud.pk)


def reserva_exitosa(request, id):
    solicitud = get_object_or_404(SolicitudCita, id=id)
    if not puede_ver_solicitud(request, solicitud):
        raise Http404
    return render(request, 'citas/pago/reserva_exitosa.html', {'solicitud': solicitud})


def reserva_fallida(request, id=None):
    solicitud = None
    if id:
        solicitud = get_object_or_404(SolicitudCita, id=id)
        if not puede_ver_solicitud(request, solicitud):
            raise Http404
    return render(request, 'citas/pago/reserva_fallida.html', {'solicitud': solicitud})


@never_cache
@login_required(login_url='sin_acceso')
def ingresos_doctora(request):
    if request.user.rol != 'veterinaria':
        return redirect('sin_acceso')

    hoy = timezone.localdate()
    inicio_mes_dt = rango_del_dia(hoy.replace(day=1))[0]

    citas_pagadas = SolicitudCita.objects.select_related('tipo_consulta').filter(estado_pago='Pagado')
    citas_pagadas = citas_pagadas.order_by('-fecha_pago')

    citas_del_mes = citas_pagadas.filter(fecha_pago__gte=inicio_mes_dt)
    citas_del_anio = citas_pagadas.filter(fecha_pago__year=hoy.year)

    suma_mes = citas_del_mes.aggregate(total=Sum('monto_pagado'))['total']
    if suma_mes is None:
        ingresos_mes = 0
    else:
        ingresos_mes = suma_mes

    suma_anio = citas_del_anio.aggregate(total=Sum('monto_pagado'))['total']
    if suma_anio is None:
        ingresos_anio = 0
    else:
        ingresos_anio = suma_anio

    suma_total = citas_pagadas.aggregate(total=Sum('monto_pagado'))['total']
    if suma_total is None:
        ingresos_totales = 0
    else:
        ingresos_totales = suma_total

    context = {
        'citas_pagadas': citas_pagadas[:50],
        'ingresos_mes': ingresos_mes,
        'ingresos_anio': ingresos_anio,
        'ingresos_totales': ingresos_totales,
    }
    return render(request, 'citas/ingresos.html', context)


@never_cache
@login_required(login_url='sin_acceso')
def ficha_medica_detalle(request, cita_id):
    if not es_personal_clinica(request.user):
        return redirect('sin_acceso')

    solicitud = get_object_or_404(SolicitudCita, id=cita_id)

    try:
        ficha = solicitud.ficha_medica
    except FichaMedica.DoesNotExist:
        ficha = None

    if request.method == 'POST':
        form = FichaMedicaForm(request.POST, instance=ficha)
        if form.is_valid():
            ficha_nueva = form.save(commit=False)
            ficha_nueva.solicitud = solicitud
            ficha_nueva.especie = solicitud.especie_mascota
            ficha_nueva.raza = solicitud.raza_mascota
            ficha_nueva.sexo = solicitud.sexo_mascota
            ficha_nueva.edad_mascota = solicitud.edad_valor_mascota
            ficha_nueva.save()
            messages.success(request, 'Ficha clínica guardada correctamente.')
            return redirect('agenda_doctora')
        messages.error(request, 'Revisa los campos marcados en rojo.')
    else:
        form = FichaMedicaForm(instance=ficha)

    context = {
        'solicitud': solicitud,
        'ficha': ficha,
        'form': form,
    }
    return render(request, 'citas/ficha_medica_form.html', context)
