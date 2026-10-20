"""Testes da fundacao de auditoria e exclusao logica (apps/core_domain/auditoria).

Os mixins ainda nao estao aplicados em nenhum model real, entao os testes
usam um model concreto proprio, cuja tabela e criada e removida aqui
mesmo (sem migracao). O model so fica registrado no app "core" enquanto
MixinsAuditoriaTests roda: as FKs PROTECT dele pra UsuarioSistema fariam
qualquer outro teste que apaga um usuario procurar a tabela inexistente.
"""

from datetime import timedelta

from asgiref.sync import iscoroutinefunction
from django.apps import apps
from django.db import connection, models
from django.db.models import ProtectedError
from django.forms import modelform_factory
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.utils import timezone

from apps.core_domain.auditoria import get_ator_atual_id, usando_ator
from apps.core_domain.auditoria.middleware import AtorAtualMiddleware
from apps.core_domain.auditoria.mixins import AuditoriaMixin, ExclusaoLogicaMixin
from core.models import UsuarioSistema


def _registrar_modelo_de_teste():
    class RegistroAuditado(AuditoriaMixin, ExclusaoLogicaMixin, models.Model):
        nome = models.CharField(max_length=50)
        observacao = models.CharField(max_length=50, blank=True)

        class Meta:
            app_label = "core"

    return RegistroAuditado


def _desregistrar_modelo_de_teste(modelo):
    del apps.all_models["core"][modelo._meta.model_name]
    # Limpa os caches de _meta (inclusive as relacoes reversas de
    # UsuarioSistema) pra esquecer o model.
    apps.clear_cache()


def _criar_usuario(sufixo):
    return UsuarioSistema.objects.create(
        nome_completo=f"Staff {sufixo}",
        email_institucional=f"staff.{sufixo}@uncisal.com.br",
        cpf=f"{sufixo:0>11}",
        nivel_acesso=UsuarioSistema.NivelAcesso.RECEPCIONISTA,
    )


class ContextoAtorTests(SimpleTestCase):
    def test_sem_ator_por_padrao(self):
        self.assertIsNone(get_ator_atual_id())

    def test_usando_ator_aceita_id_e_restaura_o_anterior(self):
        with usando_ator(1):
            with usando_ator(2):
                self.assertEqual(get_ator_atual_id(), 2)
            self.assertEqual(get_ator_atual_id(), 1)
        self.assertIsNone(get_ator_atual_id())

    def test_usando_ator_aceita_instancia(self):
        with usando_ator(UsuarioSistema(pk=5)):
            self.assertEqual(get_ator_atual_id(), 5)

    def test_usando_ator_restaura_mesmo_com_erro(self):
        with self.assertRaises(RuntimeError), usando_ator(3):
            raise RuntimeError
        self.assertIsNone(get_ator_atual_id())


class _SessaoFalsa(dict):
    async def aget(self, chave, padrao=None):
        return self.get(chave, padrao)


class AtorAtualMiddlewareTests(SimpleTestCase):
    def _request(self, **sessao):
        request = RequestFactory().get("/")
        request.session = _SessaoFalsa(sessao)
        return request

    def _rodar_sync(self, request):
        visto = {}

        def view(req):
            visto["ator"] = get_ator_atual_id()
            return HttpResponse()

        AtorAtualMiddleware(view)(request)
        return visto["ator"]

    def test_define_ator_a_partir_do_staff_na_sessao(self):
        self.assertEqual(self._rodar_sync(self._request(staff_usuario_id=7)), 7)
        self.assertIsNone(get_ator_atual_id())

    def test_paciente_logado_nao_vira_ator(self):
        self.assertIsNone(self._rodar_sync(self._request(paciente_id=9)))

    def test_valor_invalido_na_sessao_fica_sem_ator(self):
        self.assertIsNone(self._rodar_sync(self._request(staff_usuario_id="abc")))

    def test_restaura_o_ator_mesmo_quando_a_view_falha(self):
        def view(req):
            raise ValueError

        with self.assertRaises(ValueError):
            AtorAtualMiddleware(view)(self._request(staff_usuario_id=7))
        self.assertIsNone(get_ator_atual_id())

    async def test_caminho_async(self):
        visto = {}

        async def view(req):
            visto["ator"] = get_ator_atual_id()
            return HttpResponse()

        middleware = AtorAtualMiddleware(view)
        self.assertTrue(iscoroutinefunction(middleware))
        await middleware(self._request(staff_usuario_id=4))
        self.assertEqual(visto["ator"], 4)
        self.assertIsNone(get_ator_atual_id())


class MixinsAuditoriaTests(TestCase):
    @classmethod
    def setUpClass(cls):
        # Fora da transacao do TestCase: o SQLite nao aceita DDL dentro de
        # atomic com checagem de FK ligada.
        cls.Modelo = _registrar_modelo_de_teste()
        with connection.schema_editor() as editor:
            editor.create_model(cls.Modelo)
        super().setUpClass()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        with connection.schema_editor() as editor:
            editor.delete_model(cls.Modelo)
        _desregistrar_modelo_de_teste(cls.Modelo)

    @classmethod
    def setUpTestData(cls):
        cls.ana = _criar_usuario("1")
        cls.bruno = _criar_usuario("2")

    def _envelhecer(self, registro):
        """Joga atualizado_em pro passado, pra comparar sem depender da
        resolucao do relogio."""
        passado = timezone.now() - timedelta(days=1)
        self.Modelo.all_objects.filter(pk=registro.pk).update(atualizado_em=passado)
        return passado

    # --- criacao e alteracao ---

    def test_criacao_registra_o_ator(self):
        with usando_ator(self.ana):
            registro = self.Modelo.objects.create(nome="x")
        registro.refresh_from_db()
        self.assertEqual(registro.criado_por, self.ana)
        self.assertEqual(registro.atualizado_por, self.ana)
        self.assertIsNotNone(registro.criado_em)

    def test_criacao_sem_ator_deixa_campos_por_vazios(self):
        registro = self.Modelo.objects.create(nome="x")
        registro.refresh_from_db()
        self.assertIsNone(registro.criado_por)
        self.assertIsNone(registro.atualizado_por)

    def test_alteracao_preserva_criado_por(self):
        with usando_ator(self.ana):
            registro = self.Modelo.objects.create(nome="x")
        with usando_ator(self.bruno):
            registro.nome = "y"
            registro.save()
        registro.refresh_from_db()
        self.assertEqual(registro.criado_por, self.ana)
        self.assertEqual(registro.atualizado_por, self.bruno)

    def test_alteracao_sem_ator_limpa_atualizado_por(self):
        with usando_ator(self.ana):
            registro = self.Modelo.objects.create(nome="x")
        registro.save()
        registro.refresh_from_db()
        self.assertIsNone(registro.atualizado_por)

    def test_save_com_update_fields_atualiza_campos_de_alteracao(self):
        registro = self.Modelo.objects.create(nome="x")
        passado = self._envelhecer(registro)
        registro.refresh_from_db()

        with usando_ator(self.bruno):
            registro.nome = "y"
            registro.save(update_fields=["nome"])

        registro.refresh_from_db()
        self.assertEqual(registro.nome, "y")
        self.assertEqual(registro.atualizado_por, self.bruno)
        self.assertGreater(registro.atualizado_em, passado)

    def test_save_com_update_fields_em_tupla_e_campo_repetido(self):
        registro = self.Modelo.objects.create(nome="x")
        registro.nome = "y"
        registro.save(update_fields=("nome", "atualizado_em"))
        registro.refresh_from_db()
        self.assertEqual(registro.nome, "y")

    def test_update_fields_so_grava_os_campos_pedidos(self):
        registro = self.Modelo.objects.create(nome="x")
        registro.nome = "y"
        registro.observacao = "nao deve gravar"
        registro.save(update_fields=["nome"])
        registro.refresh_from_db()
        self.assertEqual(registro.observacao, "")

    def test_campos_de_auditoria_ficam_fora_do_modelform(self):
        form_class = modelform_factory(self.Modelo, fields="__all__")
        self.assertEqual(set(form_class.base_fields), {"nome", "observacao"})

    # --- exclusao logica ---

    def test_delete_de_instancia_e_logico(self):
        registro = self.Modelo.objects.create(nome="x")
        with usando_ator(self.ana):
            resultado = registro.delete()

        self.assertEqual(resultado, (1, {"core.RegistroAuditado": 1}))
        self.assertFalse(self.Modelo.objects.filter(pk=registro.pk).exists())
        excluido = self.Modelo.all_objects.get(pk=registro.pk)
        self.assertTrue(excluido.excluido)
        self.assertEqual(excluido.excluido_por, self.ana)
        self.assertEqual(excluido.atualizado_por, self.ana)

    def test_delete_de_instancia_ja_excluida_nao_muda_nada(self):
        registro = self.Modelo.objects.create(nome="x")
        with usando_ator(self.ana):
            registro.delete()
        excluido_em = registro.excluido_em
        with usando_ator(self.bruno):
            self.assertEqual(registro.delete(), (0, {}))
        registro.refresh_from_db()
        self.assertEqual(registro.excluido_em, excluido_em)
        self.assertEqual(registro.excluido_por, self.ana)

    def test_delete_em_massa_e_logico(self):
        a = self.Modelo.objects.create(nome="a")
        self.Modelo.objects.create(nome="b")
        self.Modelo.objects.create(nome="c")

        with usando_ator(self.bruno):
            resultado = self.Modelo.objects.exclude(pk=a.pk).delete()

        self.assertEqual(resultado, (2, {"core.RegistroAuditado": 2}))
        self.assertEqual(list(self.Modelo.objects.values_list("nome", flat=True)), ["a"])
        self.assertEqual(self.Modelo.all_objects.count(), 3)
        for excluido in self.Modelo.all_objects.excluidos():
            self.assertEqual(excluido.excluido_por, self.bruno)
            self.assertEqual(excluido.atualizado_por, self.bruno)

    def test_delete_em_massa_nao_reexclui(self):
        registro = self.Modelo.objects.create(nome="x")
        with usando_ator(self.ana):
            registro.delete()
        with usando_ator(self.bruno):
            total, _ = self.Modelo.all_objects.all().delete()
        self.assertEqual(total, 0)
        registro.refresh_from_db()
        self.assertEqual(registro.excluido_por, self.ana)

    def test_restaurar_instancia(self):
        registro = self.Modelo.objects.create(nome="x")
        registro.delete()
        with usando_ator(self.bruno):
            registro.restaurar()
        registro.refresh_from_db()
        self.assertFalse(registro.excluido)
        self.assertIsNone(registro.excluido_por)
        self.assertEqual(registro.atualizado_por, self.bruno)
        self.assertTrue(self.Modelo.objects.filter(pk=registro.pk).exists())

    def test_restaurar_em_massa(self):
        self.Modelo.objects.create(nome="a")
        self.Modelo.objects.create(nome="b")
        self.Modelo.objects.all().delete()
        self.assertEqual(self.Modelo.all_objects.all().restaurar(), 2)
        self.assertEqual(self.Modelo.objects.count(), 2)

    def test_excluir_definitivamente(self):
        a = self.Modelo.objects.create(nome="a")
        b = self.Modelo.objects.create(nome="b")
        a.excluir_definitivamente()
        b.delete()
        self.Modelo.all_objects.filter(pk=b.pk).excluir_definitivamente()
        self.assertFalse(self.Modelo.all_objects.exists())

    def test_apagar_usuario_com_registros_e_bloqueado(self):
        with usando_ator(self.ana):
            self.Modelo.objects.create(nome="x")
        with self.assertRaises(ProtectedError):
            self.ana.delete()
