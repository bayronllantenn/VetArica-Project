from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render, get_object_or_404
from django.urls import reverse
from django.utils import timezone

from .forms import MascotaForm, SolicitudCitaForm, obtener_horas_disponibles
from .models import Mascota, SolicitudCita
from .utils import get_webpay_transaction


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
    mascotas = Mascota.objects.filter(dueno=request.user) if request.user.is_authenticated else []
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
    # completos, si falta alguno se muestran para que los complete ahi
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
            return redirect('confirmar_cita', solicitud.id)
    else:
        initial = {'fecha': fecha_seleccionada}
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
    return render(request, 'citas/confirmar_cita.html', {'solicitud': solicitud})


def cancelar_solicitud(request, id):
    solicitud = get_object_or_404(SolicitudCita, id=id)
    solicitud.delete()
    messages.info(request, 'Cancelaste la solicitud de cita.')
    return redirect('agendar')


# WEBPAY

def iniciar_pago_webpay(request, id):
    solicitud = get_object_or_404(SolicitudCita, id=id)

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


def retorno_webpay(request):
    # si el cliente anula el pago o se le acaba el tiempo en la pagina de
    # webpay, transbank no manda "token_ws" sino "TBK_TOKEN"
    tbk_token = request.GET.get('TBK_TOKEN') or request.POST.get('TBK_TOKEN')
    if tbk_token:
        solicitud = SolicitudCita.objects.filter(webpay_token=tbk_token).first()
        if solicitud:
            solicitud.estado = 'Cancelada'
            solicitud.estado_pago = 'Rechazado'
            solicitud.save()
        messages.error(request, 'Cancelaste el pago. La cita fue cancelada.')
        return redirect('reserva_fallida')

    # webpay devuelve un token llamado "token_ws" despues del pago
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
            # mandar correo de confirmacion (falta plantilla y config de email)
            messages.success(request, 'Tu cita fue reservada y pagada correctamente.')
            return redirect('reserva_exitosa', solicitud.pk)
        else:
            solicitud.estado = 'Cancelada'
            solicitud.estado_pago = 'Rechazado'
            solicitud.save()
            messages.error(request, 'El pago no fue aprobado. La cita fue cancelada.')
            return redirect('reserva_fallida_id', solicitud.pk)
    except Exception as e:
        solicitud.estado = 'Cancelada'
        solicitud.estado_pago = 'Rechazado'
        solicitud.save()
        messages.error(request, f'Error al confirmar el pago: {e}')
        return redirect('reserva_fallida_id', solicitud.pk)


def reserva_exitosa(request, id):
    solicitud = get_object_or_404(SolicitudCita, id=id)
    return render(request, 'citas/pago/reserva_exitosa.html', {'solicitud': solicitud})


def reserva_fallida(request, id=None):
    solicitud = None
    if id:
        solicitud = get_object_or_404(SolicitudCita, id=id)
    return render(request, 'citas/pago/reserva_fallida.html', {'solicitud': solicitud})
