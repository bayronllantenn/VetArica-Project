from django.contrib import messages
from django.shortcuts import redirect, render
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
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
            return redirect('home')
        messages.error(request, 'Correo electrónico o contraseña incorrectos.')
    else:
        form = AuthenticationForm()
    return render(request, 'usuarios/login.html', {'form': form})