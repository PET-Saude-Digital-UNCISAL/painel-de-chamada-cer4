import re

from django import forms

from core.business_rules import cpf_e_valido
from core.models import Paciente, TipoAtendimentoEncaixe, UsuarioSistema


class EncaixeForm(forms.Form):
    """Formulário de encaixe manual de paciente na fila do dia."""

    TIPOS_ATENDIMENTO = TipoAtendimentoEncaixe.TIPOS
    EXTENSOES_PERMITIDAS = (".pdf", ".doc", ".docx")

    nome_completo = forms.CharField(max_length=150, label="Nome do paciente")
    cpf = forms.CharField(max_length=14, required=False, label="CPF")
    data_nascimento = forms.DateField(
        required=False,
        label="Data de Nascimento",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    nome_mae = forms.CharField(max_length=150, required=False, label="Nome da Mãe")
    tipos_atendimento = forms.MultipleChoiceField(
        choices=TIPOS_ATENDIMENTO,
        label="Tipo de Atendimento",
        widget=forms.CheckboxSelectMultiple,
    )
    justificativa = forms.CharField(
        required=False, label="Justificativa", widget=forms.Textarea(attrs={"rows": 3})
    )
    anexo = forms.FileField(required=False, label="Anexo")

    def clean_anexo(self):
        arquivo = self.cleaned_data.get("anexo")
        if arquivo:
            nome = arquivo.name.lower()
            if not any(nome.endswith(ext) for ext in self.EXTENSOES_PERMITIDAS):
                raise forms.ValidationError("Apenas arquivos PDF, DOC ou DOCX são permitidos.")
        return arquivo


class UsuarioSistemaForm(forms.ModelForm):
    cpf = forms.CharField(max_length=14)

    class Meta:
        model = UsuarioSistema
        fields = ("nome_completo", "email_institucional", "cpf", "nivel_acesso", "usuario_ativo")

    def clean_cpf(self):
        digits = re.sub(r"\D", "", self.cleaned_data["cpf"])
        if len(digits) != 11:
            raise forms.ValidationError("Informe um CPF com 11 dígitos.")
        return digits


class PacientePerfilForm(forms.ModelForm):
    """Formulário de edição do próprio perfil pelo paciente autenticado."""

    class Meta:
        model = Paciente
        fields = ("nome_completo", "email", "data_nascimento")
        widgets = {
            "nome_completo": forms.TextInput(attrs={"class": "campo-input"}),
            "email": forms.EmailInput(attrs={"class": "campo-input"}),
            "data_nascimento": forms.DateInput(attrs={"class": "campo-input", "type": "date"}),
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        qs = Paciente.objects.filter(email=email).exclude(pk=self.instance.pk)
        if email and qs.exists():
            raise forms.ValidationError("Este e-mail já está em uso por outro cadastro.")
        return email


class IdentificacaoForm(forms.Form):
    """Formulário da tela de Identificação do Paciente (check-in)."""

    cpf = forms.CharField(
        label="CPF",
        max_length=14,
        widget=forms.TextInput(
            attrs={
                "class": "field-input",
                "placeholder": "000.000.000-00",
                "inputmode": "numeric",
                "autocomplete": "username",
                "data-mask": "cpf",
                "maxlength": "14",
            }
        ),
    )
    data_nascimento = forms.DateField(
        label="Data de Nascimento",
        required=False,
        input_formats=["%d/%m/%Y", "%Y-%m-%d"],
        widget=forms.DateInput(
            attrs={
                "class": "field-input",
                "placeholder": "DD/MM/AAAA",
                "inputmode": "numeric",
                "autocomplete": "bday",
                "data-mask": "date",
                "maxlength": "10",
            }
        ),
    )
    nome_mae = forms.CharField(
        label="Nome da Mãe",
        required=False,
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "field-input",
                "placeholder": "Nome completo da mãe",
                "autocapitalize": "characters",
                "data-uppercase": "",
            }
        ),
    )

    def clean_cpf(self):
        import re
        cpf = self.cleaned_data["cpf"]
        return re.sub(r"\D", "", cpf)


class MeuPerfilForm(forms.ModelForm):
    """Formulário de edição do próprio perfil pelo usuário autenticado."""

    class Meta:
        model = UsuarioSistema
        fields = ("nome_completo", "email_institucional")

    def clean_email_institucional(self):
        email = self.cleaned_data["email_institucional"]
        qs = UsuarioSistema.objects.filter(email_institucional=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Este e-mail já está em uso por outro usuário.")
        return email


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

    def clean(self):
        cleaned = super().clean()
        cpf = cleaned.get("cpf")
        senha = cleaned.get("senha")

        if cpf and senha:
            usuario = UsuarioSistema.objects.filter(cpf=cpf, usuario_ativo=True).first()
            if usuario and usuario.checar_senha(senha):
                cleaned["usuario_autenticado"] = usuario
                return cleaned

            paciente = Paciente.objects.filter(cpf=cpf, paciente_ativo=True).first()
            if paciente and paciente.checar_senha(senha):
                cleaned["paciente_autenticado"] = paciente
                return cleaned

            raise forms.ValidationError("CPF ou senha inválidos.")
        return cleaned


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
    confirmar_senha = forms.CharField(
        label="Confirmar senha",
        widget=forms.PasswordInput(
            attrs={
                "class": "campo-input",
                "placeholder": "Repita a senha",
                "id": "id_confirmar_senha",
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
                attrs={"class": "campo-input", "placeholder": "Ex: Maria Oliveira Silva", "autocomplete": "name"}
            ),
            "cpf": forms.TextInput(
                attrs={
                    "class": "campo-input",
                    "placeholder": "999.999.999-99",
                    "id": "id_cpf",
                    "inputmode": "numeric",
                    "autocomplete": "off",
                }
            ),
            "data_nascimento": forms.DateInput(
                attrs={"class": "campo-input", "type": "date", "autocomplete": "bday"}
            ),
            "email": forms.EmailInput(
                attrs={"class": "campo-input", "placeholder": "nome@exemplo.com", "autocomplete": "email"}
            ),
        }

    def clean_nome_completo(self):
        nome = self.cleaned_data["nome_completo"].strip()
        if len(nome.split()) < 2:
            raise forms.ValidationError("Informe o nome completo (nome e sobrenome).")
        return nome.title()

    def clean_cpf(self):
        digits = re.sub(r"\D", "", self.cleaned_data["cpf"])
        if not cpf_e_valido(digits):
            raise forms.ValidationError("CPF inválido.")
        if Paciente.objects.filter(cpf=digits).exists():
            raise forms.ValidationError("Já existe uma conta cadastrada com este CPF.")
        return digits

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        if email and Paciente.objects.filter(email=email).exists():
            raise forms.ValidationError("Este e-mail já está cadastrado.")
        return email

    def clean(self):
        cleaned = super().clean()
        senha = cleaned.get("senha")
        confirmar = cleaned.get("confirmar_senha")
        if senha and confirmar and senha != confirmar:
            self.add_error("confirmar_senha", "As senhas não coincidem.")
        return cleaned

    def save(self, commit=True):
        paciente = super().save(commit=False)
        paciente.set_senha(self.cleaned_data["senha"])
        if commit:
            paciente.save()
        return paciente
