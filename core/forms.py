import re

from django import forms

from core.models import UsuarioSistema


class UsuarioSistemaForm(forms.ModelForm):
    class Meta:
        model = UsuarioSistema
        fields = ("nome_completo", "email_institucional", "cpf", "nivel_acesso", "usuario_ativo")

    def clean_cpf(self):
        digits = re.sub(r"\D", "", self.cleaned_data["cpf"])
        if len(digits) != 11:
            raise forms.ValidationError("Informe um CPF com 11 dígitos.")
        return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"
