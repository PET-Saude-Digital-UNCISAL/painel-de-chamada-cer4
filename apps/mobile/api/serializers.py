from django.contrib.auth.hashers import check_password
from rest_framework import serializers

from apps.core_domain.models import Paciente, EncaixePaciente, TipoAtendimentoEncaixe
from apps.core_domain.business_rules import cpf_e_valido
from core.services import registrar_encaixe


class EncaixeSerializer(serializers.Serializer):
    nome_completo = serializers.CharField(max_length=150)
    cpf = serializers.CharField(max_length=14, required=False, allow_blank=True)
    data_nascimento = serializers.DateField(required=False, allow_null=True)
    nome_mae = serializers.CharField(max_length=150, required=False, allow_blank=True)
    tipos_atendimento = serializers.ListField(
        child=serializers.ChoiceField(choices=[t[0] for t in TipoAtendimentoEncaixe.TIPOS]),
        required=False,
        default=list,
    )
    justificativa = serializers.CharField(required=False, allow_blank=True)
    anexo = serializers.FileField(required=False, allow_null=True)

    senha = serializers.CharField(read_only=True)
    posicao_fila = serializers.IntegerField(read_only=True)

    def create(self, validated_data):
        anexo = validated_data.pop("anexo", None)
        encaixe = registrar_encaixe(validated_data, arquivo=anexo)
        return encaixe

    def to_representation(self, instance):
        return {
            "ok": True,
            "senha": instance.senha,
            "posicao": instance.posicao_fila,
        }


class FilaSerializer(serializers.ModelSerializer):
    class Meta:
        model = EncaixePaciente
        fields = (
            "senha", "nome_completo", "posicao_fila",
            "status", "sala", "chamado_em",
            "data_atendimento", "criado_em",
        )


class PacienteLoginSerializer(serializers.Serializer):
    cpf = serializers.CharField(max_length=14)
    senha = serializers.CharField(write_only=True)

    paciente = serializers.SerializerMethodField(read_only=True)

    def validate_cpf(self, value):
        if not cpf_e_valido(value):
            raise serializers.ValidationError("CPF inválido.")
        return value

    def validate(self, data):
        paciente = Paciente.objects.filter(
            cpf=data["cpf"], paciente_ativo=True
        ).first()
        if not paciente or not paciente.checar_senha(data["senha"]):
            raise serializers.ValidationError("CPF ou senha inválidos.")
        data["paciente"] = paciente
        return data

    def get_paciente(self, obj):
        return {"id": obj.pk, "nome_completo": obj.nome_completo, "cpf": obj.cpf}


class PacienteCadastroSerializer(serializers.ModelSerializer):
    senha = serializers.CharField(min_length=8, write_only=True)
    confirmar_senha = serializers.CharField(write_only=True)

    class Meta:
        model = Paciente
        fields = ("nome_completo", "cpf", "data_nascimento", "email", "senha", "confirmar_senha")

    def validate_cpf(self, value):
        digits = value
        if not cpf_e_valido(digits):
            raise serializers.ValidationError("CPF inválido.")
        if Paciente.objects.filter(cpf=digits).exists():
            raise serializers.ValidationError("Já existe uma conta com este CPF.")
        return digits

    def validate_email(self, value):
        if value and Paciente.objects.filter(email=value).exists():
            raise serializers.ValidationError("Este e-mail já está cadastrado.")
        return value

    def validate(self, data):
        if data.get("senha") != data.pop("confirmar_senha", None):
            raise serializers.ValidationError({"confirmar_senha": "As senhas não coincidem."})
        return data

    def create(self, validated_data):
        senha = validated_data.pop("senha")
        paciente = Paciente(**validated_data)
        paciente.set_senha(senha)
        paciente.save()
        return paciente


class PesquisaSatisfacaoSerializer(serializers.Serializer):
    cpf = serializers.CharField(max_length=14)
    nota_atendimento = serializers.IntegerField(min_value=1, max_value=5)
    nota_espera = serializers.IntegerField(min_value=1, max_value=5)
    nota_instalacao = serializers.IntegerField(min_value=1, max_value=5)
    nota_profissional = serializers.IntegerField(min_value=1, max_value=5)
    nota_clareza = serializers.IntegerField(min_value=1, max_value=5)
    comentario = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_cpf(self, value):
        from apps.core_domain.business_rules import cpf_e_valido
        if not cpf_e_valido(value):
            raise serializers.ValidationError("CPF inválido.")
        return value

    def validate(self, attrs):
        from datetime import date
        from apps.core_domain.models import PesquisaSatisfacao

        cpf = attrs["cpf"]
        encaixe = EncaixePaciente.objects.filter(
            cpf=cpf,
            data_atendimento=date.today(),
            status=EncaixePaciente.Status.CONCLUIDO,
        ).order_by("-criado_em").first()

        if not encaixe:
            raise serializers.ValidationError(
                {"erro": "Nenhum atendimento concluído hoje foi encontrado para este CPF."}
            )

        if PesquisaSatisfacao.objects.filter(encaixe=encaixe).exists():
            raise serializers.ValidationError(
                {"erro": "Este atendimento já recebeu uma avaliação."}
            )

        attrs["encaixe"] = encaixe
        return attrs

    def create(self, validated_data):
        from apps.core_domain.models import PesquisaSatisfacao
        encaixe = validated_data["encaixe"]
        categorias = (
            validated_data["nota_atendimento"],
            validated_data["nota_espera"],
            validated_data["nota_instalacao"],
            validated_data["nota_profissional"],
            validated_data["nota_clareza"],
        )
        nota_geral = round(sum(categorias) / len(categorias))
        return PesquisaSatisfacao.objects.create(
            encaixe=encaixe,
            paciente_nome=encaixe.nome_completo,
            paciente_cpf=validated_data["cpf"],
            nota=nota_geral,
            nota_atendimento=validated_data["nota_atendimento"],
            nota_espera=validated_data["nota_espera"],
            nota_instalacao=validated_data["nota_instalacao"],
            nota_profissional=validated_data["nota_profissional"],
            nota_clareza=validated_data["nota_clareza"],
            comentario=validated_data.get("comentario", ""),
        )

    def to_representation(self, instance):
        return {"ok": True, "id": instance.pk}
