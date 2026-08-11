# Guia de Investigação — Como investigar cada fluxo sozinha

> Mapa "fluxo → arquivo → função" para você abrir os arquivos certos e entender
> onde cada etapa acontece. Não é um guia de correção: é um mapa de leitura.
>
> **Como usar:** para cada fluxo, abra os arquivos na ordem listada e siga a
> cadeia `HTTP/Formulário → View → Service → Model → WebSocket → JS do template`.

---

## Fluxo 1 — Check-in & Validação (Mobile)

**O que deveria acontecer:** paciente informa CPF + Data de Nascimento + Nome da
Mãe → o back-end valida agendamento de hoje → gera senha, insere na fila e
redireciona para a Tela de Acompanhamento.

### Caminho de leitura (na ordem)

| # | Arquivo | O que olhar |
|---|---------|-------------|
| 1 | `apps/mobile/templates/mobile/fluxo_paciente.html` (buscar `step=identificacao` / `identificacao` no JS) | A tela que coleta CPF/Nascimento/Mãe e o JS que faz o POST |
| 2 | `core/forms.py` → `IdentificacaoForm` | Campos do formulário e `clean_cpf` (limpa máscara) |
| 3 | `core/views.py` → `fluxo_paciente_view` (procure o bloco `if step == "identificacao"`) | Tratamento do POST: onde busca o `Paciente`, compara nascimento e chama `registrar_checkin` |
| 4 | `core/services.py` → `registrar_checkin` | **Aqui está a validação do agendamento** (`Agendamento.objects.filter(paciente, data_agendamento=hoje, status=AGENDADO)`), geração da senha (`E{posição:03d}`) e criação do `EncaixePaciente` |
| 5 | `apps/core_domain/models/agendamento.py` e `apps/core_domain/models/encaixe_paciente.py` | Estrutura dos dados: status, senha, posicao_fila, data_atendimento |

### Perguntas para você responder investigando

- O `Paciente` é encontrado pelo CPF? (`core/views.py`)
- A Data de Nascimento informada é comparada com o banco? Em qual linha?
- O **Nome da Mãe é validado em algum lugar**? (spoiler: procure por `nome_mae` em `registrar_checkin`)
- Existe `Agendamento` para hoje? Quem cria esses registros? → `core/integrador.py` + `core/management/commands/seed_pacientes.py`

---

## Fluxo 2 — Acompanhamento em Tempo Real (Mobile)

**O que deveria acontecer:** exibir senha do paciente, senha chamada agora e
pessoas à frente, **sem refresh**.

### Caminho de leitura

| # | Arquivo | O que olhar |
|---|---------|-------------|
| 1 | `apps/mobile/templates/mobile/acompanhamento_atendimento.html` | **Duas seções de JS**: o WebSocket `ws/paciente/{cpf}` (bloco "WebSocket de notificação do paciente") e o **polling de 5s** (bloco "Polling da fila em tempo real") |
| 2 | `apps/mobile/api/views.py` → `FilaViewSet.fila_atual` (endpoint `GET /api/v1/fila/atual/`) | De onde vêm `chamando_agora`, `fila_espera` e `meu_encaixe.pacientes_a_frente` |
| 3 | `core/websocket_utils.py` → `notificar_fila_atualizada` | Para qual grupo o evento `fila_atualizada` é enviado (painel ou também pacientes?) |
| 4 | `apps/display/consumers/paciente_notificacao.py` | Quais eventos o consumer do paciente sabe tratar (procure handler `fila_atualizada`) |

### Perguntas para você responder

- O mobile recebe `fila_atualizada` **pelo WebSocket** ou só pelo `setInterval` de 5s?
- O WebSocket conecta com qual CPF? (`{{ cpf }}` no template) — esse CPF bate com o usado em `notificar_paciente`?
- `chamando_agora` é atualizado no banco por quem? (resposta: quem chama o paciente — ver Fluxo 3)

---

## Fluxo 3 — Gatilho de Chamada (Sistema Interno → Mobile + Painel)

**O que deveria acontecer:** clicar "Chamar Próximo" → atualiza o Painel (senha +
som) e transita o Mobile do paciente para ", **ao mesmo tempo**.

### Caminho de leitura

| # | Arquivo | O que olhar |
|---|---------|-------------|
| 1 | `apps/system/views.py` → `chamar_paciente_view` | **O coração do gatilho**: valida status, muda para `CHAMADO`, grava `chamado_em`, e dispara `notificar_painel_chamada` + `notificar_fila_atualizada` + `notificar_paciente` |
| 2 | `core/websocket_utils.py` → `notificar_painel_chamada`, `notificar_fila_atualizada`, `notificar_paciente` | Para quais grupos cada evento vai (`painel_chamada` e `paciente_{cpf}`) |
| 3 | `apps/display/routing.py` + `config/asgi.py` | As rotas dos WebSockets (`ws/painel-chamada/`, `ws/paciente/{cpf}/`) e o roteador ASGI |
| 4 | `apps/display/consumers/painel_consumer.py` | O consumer do painel e os handlers `paciente_chamado` / `fila_atualizada` |
| 5 | `config/settings.py` (bloco `CHANNEL_LAYERS`, ~linha 83) | **A configuração de tempo real**: Redis (`RedisChannelLayer`) ou memória (`InMemoryChannelLayer`) |
| 6 | `apps/display/templates/display/painel_chamada.html` (bloco JS do WebSocket) | Como o painel reage a `paciente_chamado` (destaque + `audio.play()`) |
| 7 | `apps/mobile/templates/mobile/acompanhamento_atendimento.html` e `paciente_chamado.html` (JS do WebSocket) | Como o mobile reage a `paciente_chamado` → `window.location.assign` para a tela "É a sua vez!" |

### Perguntas para você responder

- `CHANNEL_LAYERS` usa Redis ou memória? (se `InMemoryChannelLayer`, **essa é a causa mais provável do tempo real não funcionar**)
- O evento `paciente_chamado` é enviado ao grupo `paciente_{cpf}` com o **mesmo CPF** que o mobile usa na URL do WebSocket?
- O painel e o mobile estão conectados ao **mesmo processo/Redis**? (com `runserver`, cada worker tem memória isolada)

---

## Fluxo 4 — Encerramento & Pesquisa de Satisfação (Sistema Interno → Mobile)

**O que deveria acontecer:** encerrar atendimento → atualizar banco → mobile abre
a Pesquisa automaticamente → resposta salva e alimenta relatórios.

### Caminho de leitura

| # | Arquivo | O que olhar |
|---|---------|-------------|
| 1 | `core/views.py` → `concluir_atendimento_view` | Transição `ATENDIMENTO → CONCLUIDO`, grava `concluido_em`, dispara `notificar_paciente("paciente_concluido")` e retorna a `redirect_url` da pesquisa |
| 2 | `apps/mobile/templates/mobile/paciente_chamado.html` e `acompanhamento_atendimento.html` (JS) | Reação ao evento `paciente_concluido` → redirect para `/pesquisa-satisfacao/?cpf=...` |
| 3 | `core/views.py` → `pesquisa_satisfacao_view` | Renderiza o formulário (procure se valida que o encaixe está `CONCLUIDO`) |
| 4 | `apps/mobile/api/serializers.py` → `PesquisaSatisfacaoSerializer` | O POST que salva a resposta; procure se exige encaixe `CONCLUIDO` e se impede duplicidade |
| 5 | `apps/core_domain/models/pesquisa_satisfacao.py` | Modelo onde as respostas são persistidas |
| 6 | `core/views.py` → `qualidade_metrics_api` + `apps/system/templates/system/gestao_qualidade.html` | Onde as respostas alimentam os relatórios do Sistema Interno |
| 7 | `core/integrador.py` → `IntegradorHttp.notificar_conclusao` | Notificação ao sistema externo (opcional) |

### Perguntas para você responder

- Ao encerrar, o mobile recebe `paciente_concluido` e abre a pesquisa? Se o WebSocket estiver fora, existe **fallback** (polling)?
- `pesquisa_satisfacao_view` exige que o encaixe esteja concluído?
- O serializer impede responder 2x o mesmo atendimento?
- A pesquisa salva aparece em `qualidade_metrics_api`?

---

## Arquivos de apoio (leitura transversal)

| Arquivo | Para que serve |
|---------|----------------|
| `config/settings.py` | Database (PostgreSQL), `CHANNEL_LAYERS` (Redis/memória), apps instalados |
| `config/asgi.py` | Ponto de entrada de WebSocket + HTTP |
| `apps/display/routing.py` | Rotas WebSocket |
| `core/models.py` | Apenas reexporta `apps/core_domain/models` — leia os models em `apps/core_domain/models/` |
| `core/business_rules.py` vs `apps/core_domain/business_rules.py` | Dois arquivos quase idênticos (legado vs novo) — fique atenta a qual está sendo importado |
| `apps/mobile/api/urls.py` | Rotas REST do mobile |
| `apps/system/urls.py` | Rotas POST do Sistema Interno (`/sistema/chamar/`, `/sistema/marcar-ausente/`) |
| `core/urls.py` | Rotas do fluxo web (check-in, acompanhamento, paciente-chamado, encaixe) |
| `.env` | `REDIS_URL` (tempo real), `DB_*` (banco), `INTEGRADOR_*` (agendamentos externos) |

---

## Roteiro de investigação recomendado (na dúvida, comece por aqui)

1. **Tempo real não atualiza?** → `config/settings.py` (CHANNEL_LAYERS) → `core/websocket_utils.py` → `apps/display/consumers/*.py` → JS do template.
2. **Pula etapas / check-in errado?** → `core/views.py` (`fluxo_paciente_view`) → `core/services.py` (`registrar_checkin`) → `apps/core_domain/models/encaixe_paciente.py`.
3. **Chamada não chega ao mobile/painel?** → `apps/system/views.py` (`chamar_paciente_view`) → `core/websocket_utils.py` → `config/settings.py` (Redis) → consumers.
4. **Pesquisa não aparece / não salva?** → `core/views.py` (`concluir_atendimento_view` → `pesquisa_satisfacao_view`) → `apps/mobile/api/serializers.py` → `apps/core_domain/models/pesquisa_satisfacao.py`.
5. **Sem dados para testar?** → `core/management/commands/seed_pacientes.py` e `core/integrador.py`.

> Dica: use `Select-String -Path <arquivo> -Pattern 'def '` ou pesquise por nomes
> de função (ex.: `registrar_checkin`, `notificar_paciente`) no editor para pular
> direto para o código relevante em arquivos grandes como `core/views.py`.
