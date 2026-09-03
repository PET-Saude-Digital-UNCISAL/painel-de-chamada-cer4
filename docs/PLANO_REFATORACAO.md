# Plano de Refatoração e Correção por Fases — Painel de Chamada CER4

> Este documento existe porque o `docs/README.md` já referenciava um
> `PLANO_REFATORACAO.md` que não tinha sido criado ainda. Este arquivo
> preenche essa lacuna.

## Regra de ouro do plano

**Nenhuma fase pode alterar comportamento visível sem querer.** Isso significa,
em ordem de prioridade:

1. Nomes de função, assinatura e valores de contexto de template (as chaves
   dos dicts passados pro `render()`) **não mudam** nas fases de organização
   de código (1 a 3). Só movem de arquivo.
2. Toda fase termina com a suíte de testes passando (`python manage.py test`)
   e um teste manual do fluxo afetado.
3. Cada fase é um branch/PR isolado, pequeno o bastante pra revisar em uma
   sentada. Nunca misturar "mover código" com "mudar regra de negócio" no
   mesmo commit — são coisas diferentes e precisam de revisão diferente.
4. Se uma fase quebrar algo, o rollback é reverter aquele PR específico — por
   isso elas são independentes e em ordem de risco crescente.
5. As fases 1 a 3 são refactor puro (mesmo comportamento, código organizado
   diferente). A fase 4 em diante muda comportamento de verdade (segurança,
   regra de negócio) e por isso exige mais atenção e talvez decisão em
   equipe antes de seguir.

Estimativa de esforço é aproximada, pensando em quem já conhece o projeto.

---

## Fase 0 — Rede de segurança (antes de tocar em qualquer código)

**Objetivo:** garantir que dá pra saber se algo quebrou, antes de começar a mexer.

- [ ] Normalizar terminação de linha do repositório (`git add --renormalize .`
      ou configurar `.gitattributes` com `* text=auto eol=lf`) e commitar isso
      **sozinho**, num commit só de normalização, sem nenhuma mudança de
      código junto. Isso resolve aquele ruído de "115 arquivos modificados"
      que vimos na auditoria e evita que ele contamine os diffs das fases
      seguintes.
- [ ] Confirmar que `python manage.py test` roda limpo localmente antes de
      começar (baseline).
- [ ] Anotar manualmente (numa checklist simples, pode ser neste próprio
      arquivo) os fluxos críticos pra testar à mão depois de cada fase:
      login de paciente → check-in → ser chamado → pesquisa de satisfação;
      login de staff → chamar paciente → marcar ausente; painel de chamada
      atualizando em tempo real.
- [ ] Criar um branch dedicado para o refactor (ex.: `refactor/organizacao-core`),
      partindo de `develop` atualizado.

**Risco:** nenhum — não toca em lógica.

---

## Fase 1 — Faxina de baixo risco

**Objetivo:** arrumar a casa sem mexer em nenhuma linha de lógica de negócio.

- [ ] Remover `db.sqlite3` da raiz (ou adicionar ao `.gitignore` se alguém
      ainda usa localmente por algum motivo) e atualizar o `docs/README.md`
      pra não falar mais em "banco local sqlite" — deixar claro que é sempre
      Postgres, inclusive em dev.
- [ ] Adicionar `server.log` e `server_err.log` ao `.gitignore` e removê-los
      do controle de versão (`git rm --cached`).
- [ ] Mover os `test_*_tmp.py` da raiz para uma pasta `scripts/qa_manual/`
      (ou apagar os que já não servem mais) — separar claramente "suíte de
      teste automatizada" (`core/tests.py`) de "scripts de investigação
      pontual".
- [ ] Escolher uma estratégia única de versionamento em `requirements.txt`
      (todas as libs fixadas com `==`, geradas por `pip freeze` ou
      `pip-compile`) em vez de misturar `==` e `>=`.
- [ ] Adicionar um `pyproject.toml`/`ruff.toml` versionado com a configuração
      real do `ruff` usada no CI, em vez de rodar só com os padrões
      implícitos da ferramenta.

**Como validar:** `python manage.py check`, `python manage.py test`, CI verde.
Nenhum teste deveria mudar de resultado nessa fase — se mudar, algo saiu do
escopo.

**Risco:** muito baixo. Não mexe em nenhuma view, model ou service.

---

## Fase 2 — Eliminar a duplicação da resolução de sessão do paciente

**Objetivo:** consertar, numa tacada só e num lugar só, o padrão frágil que
gerou o bug corrigido em `paciente_chamado_view` — hoje ele está copiado (com
pequenas variações) em pelo menos mais 5 views.

- [ ] Criar uma função única em `core/services.py` (ou um novo módulo
      `core/patient_session.py`, se preferir manter `services.py` mais magro
      desde já), por exemplo:

      ```python
      def resolver_encaixe_da_sessao(request, *, permitir_fallback_por_senha=False):
          """Resolve o EncaixePaciente do paciente da sessão atual.

          Nunca retorna o encaixe de outro paciente quando a sessão tem uma
          identidade conhecida (paciente_id). Só usa `?senha=` como último
          recurso quando não existe NENHUMA identidade de sessão.
          """
          ...  # mesma lógica já corrigida em paciente_chamado_view
      ```

- [ ] Trocar, **uma view por vez, em commits separados**, cada um dos 6
      lugares que hoje reimplementam essa lógica
      (`acompanhamento_atendimento_view`, `checkin_concluido_view`,
      `checagem_documentos_paciente_view`, `perdeu_chamada_view`,
      `fluxo_paciente_view`, e conferir se `paciente_chamado_view` já está
      usando a versão centralizada) para chamar a função única.
- [ ] Prestar atenção especial em `checagem_documentos_paciente_view`: ela
      hoje aceita `?cpf=` da URL com prioridade **maior** que a sessão — ao
      migrar para a função centralizada, esse comportamento também fica
      corrigido (a sessão passa a mandar), então essa view merece um teste
      manual extra depois da troca.
- [ ] Rodar teste manual do fluxo completo do paciente depois de cada view
      trocada, não só no final.

**Como validar:** os testes existentes que tocam nessas views continuam
passando; teste manual do fluxo do paciente do início ao fim; teste manual
específico do cenário que motivou a correção original (paciente com mais de
um encaixe no mesmo dia).

**Risco:** baixo-médio. É a fase mais parecida com a correção que já foi
feita e validada — mesma técnica, aplicada mais 5 vezes.

---

## Fase 3 — Quebrar os arquivos monolíticos (`views.py` e `services.py`)

**Objetivo:** só reorganizar arquivo, sem mudar nenhuma lógica. Isso é
puramente "corta e cola com cuidado".

- [ ] Definir a divisão por domínio de tela, por exemplo:
      - `core/views/paciente.py` — identificação, check-in, acompanhamento,
        paciente chamado, perdeu chamada, bloqueio.
      - `core/views/sistema.py` — dashboard, configurações, auditoria,
        gestão de qualidade.
      - `core/views/autenticacao.py` — login, cadastro, logout.
      - `core/views/encaixe.py` — encaixe, validar, iniciar/concluir
        atendimento.
      - Mesma divisão espelhada em `core/services/`.
      - Um `core/views/__init__.py` que reexporta tudo (`from .paciente import *`
        etc.), pra que `core.urls` **não precise mudar uma linha sequer** —
        os imports em `core/urls.py` (`from core import views`,
        `views.login_view` etc.) continuam funcionando exatamente como hoje.
- [ ] Fazer a divisão em PRs pequenos, um domínio por vez (ex.: primeiro só
      "autenticacao", valida, merge; depois "paciente", valida, merge...).
- [ ] Não renomear nenhuma função nesse processo — só mudar de arquivo. Se
      quiser renomear algo, isso vira uma fase separada, depois.
- [ ] Aproveitar a divisão do `services.py` pra também resolver os imports
      locais (dentro de função) que existem hoje pra evitar import circular
      — com os arquivos menores, geralmente o ciclo desaparece sozinho e os
      imports podem voltar pro topo do arquivo.

**Como validar:** `python manage.py check` (garante que todas as rotas ainda
resolvem), suíte de testes completa, `grep` conferindo que nenhum lugar do
projeto ainda importa do caminho antigo de um jeito que quebrou.

**Risco:** médio — é mecânico, mas mexe em muitos arquivos de uma vez. Vale
fazer com o editor mostrando "find usages" de cada função antes de mover, e
rodar os testes a cada domínio movido, não só no final.

---

## Fase 4 — Endurecer segurança (decisão de equipe antes de começar)

**Objetivo:** essa fase muda comportamento de verdade, então precisa de
combinado prévio sobre o que é aceitável mudar.

- [ ] Trocar `DEFAULT_PERMISSION_CLASSES` do DRF de `AllowAny` para algo mais
      restritivo por padrão (ex.: `IsAuthenticated`), e então revisar
      endpoint por endpoint quais realmente precisam ser públicos (ex.:
      login/cadastro do paciente obviamente precisam).
- [ ] Avaliar — sem necessariamente fazer agora — se migrar a autenticação
      caseira (`Paciente.senha_hash`, `UsuarioSistema.senha_hash`) para usar
      `django.contrib.auth` vale o esforço. Isso é uma mudança grande (afeta
      login, sessão, admin, todos os decorators de auth) — recomendo tratar
      como um projeto à parte, não como item de checklist rápido.
- [ ] Se decidirem não migrar a autenticação agora, ao menos documentar por
      que a decisão foi essa (evita que a próxima pessoa pergunte de novo).

**Como validar:** teste manual completo de todos os níveis de acesso
(recepcionista, coordenação, super_admin) e do app do paciente, checando que
ninguém perdeu acesso que devia ter nem ganhou acesso que não devia.

**Risco:** alto — é a única fase que muda comportamento de segurança. Fazer
em ambiente de homologação antes de produção, com o time revisando junto.

---

## Fase 5 — Higiene de migrations e dependências

**Objetivo:** deixar o histórico de banco mais previsível daqui pra frente.

- [ ] Revisar as migrations com nome "corretivo" (`0006`, `0007`, `0013`) e
      documentar, num comentário na própria migration ou aqui no plano, o
      que aconteceu — serve de referência se precisar recriar o banco do
      zero um dia.
- [ ] Antes de cada nova migration, revisar o SQL gerado
      (`python manage.py sqlmigrate core <numero>`) antes de aplicar em
      produção.

**Risco:** baixo — é processo, não código.

---

## Fase 6 — Validação E2E final

**Objetivo:** confirmar que, depois de tudo, o sistema se comporta
exatamente como antes de começar (fases 1–3) e como decidido (fase 4).

- [ ] Rodar a suíte automatizada completa.
- [ ] Rodar a checklist manual definida na Fase 0, ponta a ponta.
- [ ] Testar especificamente: paciente com dois encaixes no mesmo dia,
      dispositivo compartilhado com dois pacientes em sequência (a hipótese
      original do bug corrigido), e reconexão de WebSocket após queda de
      rede.
- [ ] Só depois disso, fazer merge do branch de refactor pra `develop`.

---

## Resumo — ordem sugerida

| Fase | O que muda | Risco | Muda comportamento? |
|---|---|---|---|
| 0 | Nada de código, só preparação | nenhum | não |
| 1 | Arquivos soltos, `.gitignore`, README | muito baixo | não |
| 2 | Duplicação da resolução de sessão | baixo-médio | não (é a mesma correção já validada, replicada) |
| 3 | Divisão de `views.py`/`services.py` | médio | não (só organização) |
| 4 | Permissões da API e autenticação | alto | **sim** — requer decisão de equipe |
| 5 | Migrations e dependências | baixo | não |
| 6 | Validação final | — | — |

As fases 0 a 3 e 5 podem ser feitas em sequência por uma pessoa só, aos
poucos, sem parar o desenvolvimento normal do projeto. A fase 4 é a única que
merece uma conversa de equipe antes de começar, porque é a única que
deliberadamente muda uma regra de acesso.

---

## Checklist de testes manuais (Fase 0 — linha de base)

Rodar esse roteiro **antes** de começar qualquer fase, anotando o resultado
(✅/❌ e data), e repetir depois de cada fase concluída, marcando aqui embaixo
qual fase foi validada.

- [ ] **Fluxo do paciente completo:** login/identificação → check-in →
      acompanhamento (posição na fila atualizando) → ser chamado (tela
      "PACIENTE CHAMADO" com os dados certos) → pesquisa de satisfação.
- [ ] **Fluxo da equipe:** login de staff → chamar paciente da fila →
      marcar paciente como ausente → recarregar o painel de chamada e
      confirmar que refletiu a mudança.
- [ ] **Tempo real:** com o painel de chamada (telão) aberto em uma aba e o
      acompanhamento do paciente em outra, chamar o paciente pela tela da
      equipe e confirmar que as duas telas atualizam sozinhas, sem precisar
      dar F5.
- [ ] **Caso específico do bug corrigido:** um paciente com dois encaixes no
      mesmo dia (ex.: consulta + exame) — confirmar que, ao ser chamado, a
      tela mostra o encaixe correto (o que está de fato em chamada), não o
      outro.

| Data | Fase validada | Resultado | Observações |
|---|---|---|---|
|  | baseline (antes da Fase 1) |  |  |
