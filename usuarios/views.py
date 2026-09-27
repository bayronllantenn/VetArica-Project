from django.contrib import messages
from django.shortcuts import redirect, render, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils import timezone
from django.views.decorators.cache import never_cache
from citas.models import Mascota
from .forms import LoginForm, RegisterForm, ConfiguracionForm

@never_cache
def registro_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cuenta creada correctamente. Ya puedes iniciar sesión.')
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'usuarios/registro_form.html', {'form': form})


@never_cache
def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            usuario = form.get_user()
            login(request, usuario)
            messages.success(request, f'Bienvenido, {usuario.first_name} {usuario.last_name}.')
            return redirect('dashboard')
        messages.error(request, 'Correo electrónico o contraseña incorrectos.')
    else:
        form = LoginForm()
    return render(request, 'usuarios/login_form.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, 'Sesión cerrada correctamente.')
    return redirect('home')


def sin_acceso_view(request):
    return render(request, 'usuarios/autorizacion/error.html')


@never_cache
@login_required(login_url='sin_acceso')
def dashboard_usuario(request):
    ahora = timezone.now()
    citas = request.user.citas_solicitadas.all().order_by('-fecha_hora')
    mascotas = request.user.mascotas.all()
    nombres = [m.nombre for m in mascotas]
    if len(nombres) > 1:
        nombres_mascotas = ", ".join(nombres[:-1]) + " y " + nombres[-1]
    else:
        nombres_mascotas = "".join(nombres)

    proxima_cita = (
        request.user.citas_solicitadas
        .filter(fecha_hora__gte=ahora)
        .exclude(estado__iexact='cancelada')
        .order_by('fecha_hora')
        .first()
    )

    citas_anio = (
        request.user.citas_solicitadas
        .filter(fecha_hora__year=ahora.year, fecha_hora__lt=ahora)
        .exclude(estado__iexact='cancelada')
        .count()
    )

    context = {
        'citas': citas,
        'mascotas': mascotas,
        'nombres_mascotas': nombres_mascotas,
        'proxima_cita': proxima_cita,
        'citas_anio': citas_anio,
    }
    return render(request, 'usuarios/cliente/dashboard.html', context)


@never_cache
@login_required(login_url='sin_acceso')
def historial_citas(request):
    anio_actual = timezone.now().year
    citas = (
        request.user.citas_solicitadas
        .select_related('mascota')
        .order_by('-fecha_hora')
    )


    periodo = request.GET.get('periodo', 'este_ano')
    mascota_sel = request.GET.get('mascota', '')
    estado_sel = request.GET.get('estado', '')

    if periodo == 'este_ano':
        citas = citas.filter(fecha_hora__year=anio_actual)
    elif periodo == 'ano_pasado':
        citas = citas.filter(fecha_hora__year=anio_actual - 1)

    if mascota_sel:
        citas = citas.filter(mascota_id=mascota_sel)
    if estado_sel:
        citas = citas.filter(estado__iexact=estado_sel)

    campo_estado = request.user.citas_solicitadas.model._meta.get_field('estado')
    estados = campo_estado.choices or [
        (e, e.capitalize())
        for e in request.user.citas_solicitadas.values_list('estado', flat=True).distinct()
    ]


    page_obj = Paginator(citas, 8).get_page(request.GET.get('page'))
    params = request.GET.copy()
    params.pop('page', None)

    context = {
        'page_obj': page_obj,
        'mascotas': request.user.mascotas.all(),
        'estados': estados,
        'periodo': periodo,
        'mascota_sel': mascota_sel,
        'estado_sel': estado_sel,
        'querystring': params.urlencode(),
    }
    return render(request, 'usuarios/cliente/historial_citas_list.html', context)

@login_required(login_url='sin_acceso')
def ficha_mascota(request, mascota_id):
    mascota = get_object_or_404(Mascota, id=mascota_id, dueno=request.user)
    return render(request, 'usuarios/cliente/ficha_mascota.html', {'mascota': mascota})


@login_required
def configuracion(request):
    if request.method == "POST":
        form = ConfiguracionForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Tus cambios se guardaron correctamente.")
            return redirect("dashboard")
        messages.error(request, "Revisa los campos marcados en rojo.")
    else:
        form = ConfiguracionForm(instance=request.user)

    return render(request, "usuarios/cliente/configuracion.html", {"form": form})