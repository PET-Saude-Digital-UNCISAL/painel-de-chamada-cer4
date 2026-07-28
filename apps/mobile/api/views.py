from datetime import date

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.core_domain.models import EncaixePaciente
from apps.mobile.api.serializers import (
    EncaixeSerializer,
    FilaSerializer,
    PacienteCadastroSerializer,
    PacienteLoginSerializer,
    PesquisaSatisfacaoSerializer,
)


class EncaixeViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = EncaixePaciente.objects.none()
    serializer_class = EncaixeSerializer
    permission_classes = (AllowAny,)


class FilaViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    serializer_class = FilaSerializer
    permission_classes = (AllowAny,)

    def get_queryset(self):
        cpf = self.request.query_params.get("cpf", "").strip()
        qs = EncaixePaciente.objects.all().order_by("-criado_em")
        if cpf:
            qs = qs.filter(cpf=cpf)
        return qs

    @action(detail=False, methods=["get"], url_path="atual")
    def fila_atual(self, request):
        hoje = date.today()

        cpf = request.query_params.get("cpf", "").strip()
        meu_encaixe = None
        if cpf:
            meu_encaixe = EncaixePaciente.objects.filter(
                cpf=cpf, data_atendimento=hoje
            ).order_by("-criado_em").first()

        chamando = EncaixePaciente.objects.filter(
            data_atendimento=hoje,
            status__in=[EncaixePaciente.Status.CHAMADO, EncaixePaciente.Status.ATENDIMENTO],
        ).order_by("-chamado_em").first()

        fila_espera = EncaixePaciente.objects.filter(
            data_atendimento=hoje,
            status=EncaixePaciente.Status.AGUARDANDO,
        ).order_by("posicao_fila")[:10]

        data = {
            "chamando_agora": {
                "senha": chamando.senha,
                "nome": chamando.nome_completo,
                "sala": chamando.sala,
            } if chamando else None,
            "fila_espera": FilaSerializer(fila_espera, many=True).data,
        }

        if meu_encaixe:
            pacientes_a_frente = EncaixePaciente.objects.filter(
                data_atendimento=hoje,
                status__in=[EncaixePaciente.Status.AGUARDANDO, EncaixePaciente.Status.VALIDACAO],
                posicao_fila__lt=meu_encaixe.posicao_fila,
            ).count()

            data["meu_encaixe"] = {
                "senha": meu_encaixe.senha,
                "status": meu_encaixe.status,
                "posicao_fila": meu_encaixe.posicao_fila,
                "pacientes_a_frente": pacientes_a_frente,
            }

        return Response(data)


class PacienteAuthViewSet(viewsets.GenericViewSet):
    permission_classes = (AllowAny,)

    @action(detail=False, methods=["post"], url_path="login")
    def login(self, request):
        serializer = PacienteLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        paciente = serializer.validated_data["paciente"]
        return Response({
            "ok": True,
            "paciente": {
                "id": paciente.pk,
                "nome_completo": paciente.nome_completo,
                "cpf": paciente.cpf,
            },
        })

    @action(detail=False, methods=["post"], url_path="cadastro")
    def cadastro(self, request):
        serializer = PacienteCadastroSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        paciente = serializer.save()
        return Response({
            "ok": True,
            "paciente": {
                "id": paciente.pk,
                "nome_completo": paciente.nome_completo,
                "cpf": paciente.cpf,
            },
        }, status=status.HTTP_201_CREATED)


class PesquisaSatisfacaoViewSet(mixins.CreateModelMixin, viewsets.GenericViewSet):
    queryset = EncaixePaciente.objects.none()
    serializer_class = PesquisaSatisfacaoSerializer
    permission_classes = (AllowAny,)
