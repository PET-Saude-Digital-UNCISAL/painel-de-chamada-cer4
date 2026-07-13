import re

from django import forms

from core.business_rules import cpf_e_valido
from core.models import Paciente, UsuarioSistema


class UsuarioSistemaForm(forms.ModelForm):
    class Meta:
        model = UsuarioSistema
        fields = ("nome_completo", "email_institucional", "cpf", "nivel_acesso", "usuario_ativo")

    def clean_cpf(self):
        digits = re.sub(r"\D", "", self.cleaned_data["cpf"])
        if len(digits) != 11:
            raise forms.ValidationError("Informe um CPF com 11 dígitos.")
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


class LoginPacienteForm(forms.Form):
    """Formulário da tela de Login (Acesso ao Portal)."""

    cpf = forms.CharField(
        label="CPF",
        max_length=14,
        widget=forms.TextInput(
            attrs={
                "class": "campo-input",
                "placeholder": "000.000.000-00",
                "id": "id_cpf",
                "inputmode": "numeric",
                "autocomplete": "username",
            }
        ),
    )
    senha = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(
            attrs={
                "class": "campo-input",
                "placeholder": "••••••••",
                "id": "id_senha",
                "autocomplete": "current-password",
            }
        ),
    )

    def clean_cpf(self):
        cpf = self.cleaned_data["cpf"]
        if not cpf_e_valido(cpf):
            raise forms.ValidationError("CPF inválido.")
        return re.sub(r"\D", "", cpf)


class CadastroPacienteForm(forms.ModelForm):
    """Formulário da tela de Criar Conta (Cadastro do paciente)."""

    senha = forms.CharField(
        label="Senha",
        min_length=8,
        widget=forms.PasswordInput(
            attrs={
                "class": "campo-input",
                "placeholder": "Mínimo 8 caracteres",
                "id": "id_senha",
                "autocomplete": "new-password",
            }
        ),
    )

    class Meta:
        model = Paciente
        fields = ("nome_completo", "cpf", "data_nascimento", "email")
        labels = {
            "nome_completo": "Nome completo",
            "cpf": "CPF",
            "data_nascimento": "Nascimento",
            "email": "E-mail",
        }
        widgets = {
            "nome_completo": forms.TextInput(
                attrs={"class": "campo-input", "placeholder": "Ex: Maria Oliveira Silva"}
            ),
            "cpf": forms.TextInput(
                attrs={
                    "class": "campo-input",
                    "placeholder": "999.999.999-99",
                    "id": "id_cpf",
                    "inputmode": "numeric",
                }
            ),
            "data_nascimento": forms.DateInput(
                attrs={"class": "campo-input", "type": "date"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "campo-input", "placeholder": "nome@exemplo.com"}
            ),
        }

    def clean_cpf(self):
        digits = re.sub(r"\D", "", self.cleaned_data["cpf"])
        if not cpf_e_valido(digits):
            raise forms.ValidationError("CPF inválido.")
        if Paciente.objects.filter(cpf=digits).exists():
            raise forms.ValidationError("Já existe uma conta cadastrada com este CPF.")
        return digits

    def save(self, commit=True):
        paciente = super().save(commit=False)
        paciente.set_senha(self.cleaned_data["senha"])
        if commit:
            paciente.save()
        return paciente
