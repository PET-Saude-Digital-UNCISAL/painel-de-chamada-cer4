"""Views do dominio de autenticacao: login, cadastro e logout do paciente
e do staff (o staff tambem entra por aqui antes de cair no sistema interno).
"""

from django.db import IntegrityError
from django.shortcuts import redirect, render
from django.views.decorators.clickjacking import xframe_options_sameorigin

from core.forms import CadastroPacienteForm, LoginPacienteForm
from core.services import get_cadastro_context, get_login_context


@xframe_options_sameorigin

def login_view(request):

    """Tela de Login — autentica paciente ou staff pelo CPF + senha."""

    if request.method != "POST" and request.session.get("staff_logged_in"):

        if request.GET.get("interno") != "1":

            return redirect("sistema-interno")

    if request.method == "POST":

        form = LoginPacienteForm(request.POST)

        if form.is_valid():

            usuario = form.cleaned_data.get("usuario_autenticado")

            paciente = form.cleaned_data.get("paciente_autenticado")



            if usuario:

                request.session.flush()

                request.session["staff_logged_in"] = True

                request.session["staff_usuario_id"] = usuario.pk

                return redirect("sistema-interno")

            request.session.flush()

            request.session["paciente_id"] = paciente.pk

            return redirect("area-paciente")

        context = {**get_login_context(), "form": form}

        return render(request, "mobile/login.html", context)

    context = {**get_login_context(), "form": LoginPacienteForm()}

    return render(request, "mobile/login.html", context)





@xframe_options_sameorigin

def cadastro_view(request):

    """Tela de Cadastro — persiste o paciente no banco com tratamento de erros."""

    if request.method == "POST":

        form = CadastroPacienteForm(request.POST)

        if form.is_valid():

            try:

                paciente = form.save()

                request.session["paciente_id"] = paciente.pk

                return redirect("login")

            except IntegrityError:

                form.add_error(None, "Erro ao salvar: CPF ou e-mail já cadastrado.")

        context = {**get_cadastro_context(), "form": form}

        return render(request, "mobile/cadastro.html", context)

    context = {**get_cadastro_context(), "form": CadastroPacienteForm()}

    return render(request, "mobile/cadastro.html", context)





def logout_view(request):

    request.session.flush()

    return redirect("login")
