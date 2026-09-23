from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.views.decorators.cache import never_cache
from .forms import RegisterForm


def registro_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Cuenta creada correctamente. Ya puedes iniciar sesión.')
            return redirect('registro')
    else:
        form = RegisterForm()
    return render(request, 'usuarios/registro.html', {'form': form})



def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            login(request, form.get_user())
            return redirect('dashboard')
        messages.error(request, 'Correo electrónico o contraseña incorrectos.')
    else:
        form = AuthenticationForm()
    return render(request, 'usuarios/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('home')


def sin_acceso_view(request):
    return render(request, 'usuarios/autorizacion/error.html')


@never_cache
@login_required(login_url='sin_acceso')
def dashboard_usuario(request):
    citas = request.user.citas_solicitadas.all().order_by('-fecha_hora')
    return render(request, 'usuarios/dashboard.html', {'citas': citas})