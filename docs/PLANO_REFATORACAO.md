# Plano de Refatoração — Painel de Chamada CER4

> Documento de auditoria, refatoração e correção dividido por fases.
> O objetivo é **preservar o código existente** e corrigir as falhas de back-end
> e de tempo real sem reescrever as telas do front-end já desenvolvidas.

---

## 1. Especificação do Fluxo Ideal

O sistema possui 3 frentes integradas: **Mobile (Paciente)**, **Sistema Interno
(Administrativo)** e **Painel de Chamada (Display/TV)**.

### 1.1 Check-in & Validação (Mobile)

1. O paciente informa **CPF**, **Data de Nascimento** e **Nome da Mãe**.
2. O back-end valida se há **agendamento cadastrado para o dia atual**.
3. Se confirmado: gera a senha, insere o paciente na fila e o direciona para a
   **Tela de Acompanhamento**.

### 1.2 Acompanhamento em Tempo Real (Mobile)

A tela exibe em tempo real:
- a senha do paciente;
- a senha atualmente sendo chamada;
- quantas pessoas estão à sua frente.

Nenhuma atualização pode exigir refresh (F5) manual.

### 1.3 Gatilho de Chamada (Sistema Interno → Mobile + Painel)

Ao clicar em "Chamar Próximo" no Sistema Interno, dispara simultaneamente:
- atualização instantânea no **Painel de Chamada** (senha em destaque + aviso sonoro);
- transição instantânea na tela do **Mobile do paciente** para "É a sua vez!".

### 1.4 Encerramento & Pesquisa de Satisfação (Sistema Interno → Mobile)

Ao encerrar o atendimento:
- o estado do atendimento é atualizado no banco de dados;
- o **Mobile do paciente** renderiza automaticamente a **Pesquisa de Satisfação**;
- ao responder, os dados são salvos no **PostgreSQL** e alimentam os relatórios
  do **Sistema Interno**.

---

## 2. Método de Trabalho

Para cada fase:

1. **Auditoria do código existente** — mapear bugs, etapas puladas e problemas de estado.
2. **Plano de refatoração** — resumo do que está incorreto, causa raiz e como corrigir.
3. **Execução incremental** — código refatorado e corrigido após a aprovação do plano.
4. **Instruções de teste** — passo a passo de validação no ambiente ao vivo.

> Regra: **não fazer alterações em massa**. Cada fase é validada antes da próxima.

---

## 3. Estrutura Atual do Projeto (relevante ao plano)

```
apps/
├── core_domain/                # NOVA estrutura (models, business_rules, clock)
│   ├── models/                 # agendamento, encaixe_paciente, paciente, pesquisa_satisfacao, ...
│   ├── business_rules.py       # validação de CPF, força de senha, regras de horário
│   └── clock.py                # SystemClock
├── display/                    # Painel de Chamada (TV)
│   ├── consumers/              # painel_consumer.py, paciente_notificacao.py
│   ├── routing.py              # rotas WebSocket (/ws/painel-chamada/, /ws/paciente/{cpf}/)
│   └── templates/display/painel_chamada.html
├── mobile/                     # Fluxo do Paciente
│   ├── api/                    # views.py, serializers.py, urls.py (REST)
│   └── templates/mobile/       # acompanhamento_atendimento.html, paciente_chamado.html, fluxo_paciente.html, ...
└── system/                     # Sistema Interno
    ├── views.py                # chamar_paciente_view, marcar_ausente_view
    ├── urls.py
    └── templates/system/

core/                           # ESTRUTURA LEGADA
├── models.py                   # reexporta apps.core_domain.models
├── services.py                 # registrar_encaixe, registrar_checkin, contextos de tela
├── views.py                    # ~4700 linhas (fluxo_paciente, validar/iniciar/concluir, dashboard, ...)
├── urls.py
├── websocket_utils.py          # notificar_painel_chamada, notificar_fila_atualizada, notificar_paciente
├── state_machine.py            # (NOVO) serviço central de transições de status
├── forms.py
├── business_rules.py           # duplicado de apps/core_domain/business_rules.py
├── clock.py
├── integrador.py               # sincronização com sistema externo de agendamentos
└── management/commands/
    ├── seed_pacientes.py
    ├── seed_usuarios.py
    └── sincronizar_agendamentos.py

config/
├── settings.py                 # DATABASES, CHANNEL_LAYERS, INTEGRADOR_*
├── asgi.py                     # ProtocolTypeRouter (HTTP + WebSocket)
└── urls.py

.env.example / .env
render.yaml / start.sh          # produção (daphne + Redis)
```

---

## 4. Auditoria Geral — Causas-Raiz

| ID | Causa raiz | Evidência | Fase |
|----|-----------|-----------|------|
| R1 | Real-time quebrado: sem Redis local → `InMemoryChannelLayer`; `runserver` (reloader) usa 2 processos com memória isolada e perde eventos | `config/settings.py:83-98`; `.env` com `REDIS_URL=` vazio | 2 |
| R2 | Máquina de estados descentralizada; transições exigem status exato e falham se o staff pula etapa | `core/views.py:4171-4367`; `apps/system/views.py:14-55` | 1 |
| R3 | Check-in não valida Nome da Mãe (spec exige CPF+Nasc+Mãe) | `core/services.py:2168-2266` | 1 |
| R4 | Encaixe manual não normaliza CPF → buscas `?cpf=` e grupo WebSocket `paciente_{cpf}` divergem | `core/forms.py:9-39`; `apps/mobile/api/serializers.py:9-35`; `core/websocket_utils.py:73-79` | 1 |
| R5 | Mobile de Acompanhamento não recebe push de `fila_atualizada` (só polling de 5s) | `core/websocket_utils.py:32-70`; `apps/mobile/templates/mobile/acompanhamento_atendimento.html:1104-1155` | 2 |
| R6 | Corrida na geração de senha/posição (sem lock nem constraint única) | `core/services.py:2106-2162` | 1 |
| R7 | Fuso inconsistente: `date.today()` vs `timezone.localdate()` | `core/websocket_utils.py:34`; `apps/mobile/api/views.py:37` | 1 |
| R8 | Pesquisa sem validações (aceita encaixe não concluído; permite duplicidade; grava pesquisa órfã) | `core/views.py:4043-4095`; `apps/mobile/api/serializers.py:117-132` | 3 |
| R9 | Sem dados para teste ao vivo (agendamentos só via seed/integrador externo) | `core/management/commands/seed_pacientes.py`; `core/integrador.py:85-146` | 1/4 |

---

## 5. FASE 1 — Lógica de Negócio e Estados (Django / PostgreSQL)

### Objetivo
Mapear models, implementar a **máquina de estados da fila**
(`VALIDACAO → AGUARDANDO → CHAMADO → ATENDIMENTO → CONCLUIDO`), validar o
check-in (CPF / Nascimento / Mãe) e corrigir a geração/ordenação de senhas.

### Ações e arquivos afetados

| # | Ação | Arquivos afetados |
|---|------|-------------------|
| 1.1 | **Criar serviço central de transições de status** (`StatusTransitionService`) que valida a transição, resolve transições implícitas (ex.: concluir a partir de `CHAMADO` ou `ATENDIMENTO`) e centraliza as notificações WebSocket | `core/state_machine.py` (novo) |
| 1.2 | **Refatorar as views de transição** para usar o serviço (manter contratos HTTP atuais) | `apps/system/views.py`, `core/views.py` |
| 1.3 | **Validar Nome da Mãe no check-in** (comparação case-insensitive com `paciente.nome_mae`; divergência → "agendamento não encontrado") | `core/services.py` (`registrar_checkin`) |
| 1.4 | **Normalizar CPF** (apenas dígitos) no encaixe manual e na API; usar dígitos em todos os grupos WebSocket e buscas | `core/forms.py` (`EncaixeForm.clean_cpf`), `apps/mobile/api/serializers.py` (`EncaixeSerializer`), `core/services.py` (`registrar_encaixe`), `core/websocket_utils.py` |
| 1.5 | **Corrigir corrida de senha/posição**: `select_for_update()` no registro mais recente + `UniqueConstraint(data_atendimento, posicao_fila)` + retry em `IntegrityError` | `core/services.py`; `apps/core_domain/models/encaixe_paciente.py` + migração nova |
| 1.6 | **Padronizar fuso**: usar `timezone.localdate()` em vez de `date.today()` onde houver filtros por `data_atendimento` | `core/websocket_utils.py`, `apps/mobile/api/views.py`, `core/views.py`, `core/services.py` |
| 1.7 | **Bloquear check-in duplicado** de CPF com encaixe ativo no dia (comportamento já existe em `fluxo_paciente_view`) | `apps/mobile/api/views.py` (`EncaixeViewSet`) |
| 1.8 | **Completar seed para testes** (CPFs válidos + agendamento de hoje + mãe/nascimento consistentes) | `core/management/commands/seed_pacientes.py` |

### Máquina de estados alvo

```
VALIDACAO → AGUARDANDO → CHAMADO → ATENDIMENTO → CONCLUIDO
   (default)   validar    chamar     iniciar      concluir
                               └── AUSENTE (rechamada possível)
```

### Teste Fase 1

1. `python manage.py seed_pacientes`
2. Check-in com CPF correto + mãe correta → senha gerada (ex.: `E001`) e encaixe em `AGUARDANDO`.
3. Check-in com mãe incorreta → tela "Agendamento não encontrado".
4. `POST /api/v1/encaixes/` duas vezes com o mesmo CPF ativo → segunda rejeitada.
5. Encaixe manual com CPF mascarado (`390.533.447-05`) → armazenado como dígitos.
6. `python manage.py test core` (regressão).

---

## 6. FASE 2 — Camada Real-Time (Django Channels / WebSockets / Redis)

### Objetivo
Fazer o tempo real funcionar de ponta a ponta: **Redis** como channel layer,
broadcast para o **Painel** e mensagens direcionadas por CPF ao **Mobile**, com
reconexão automática.

### Ações e arquivos afetados

| # | Ação | Arquivos afetados |
|---|------|-------------------|
| 2.1 | **Subir Redis local** (`docker run -d --name cer4-redis -p 6379:6379 redis:7-alpine`) e configurar `REDIS_URL=redis://localhost:6379` | `.env`; validar `config/settings.py:83-98` |
| 2.2 | **Enviar `fila_atualizada` ao mobile** por CPF (payload: `chamando_agora`, `pacientes_a_frente`, `status`) | `core/websocket_utils.py` (novo `notificar_fila_paciente`), `apps/display/consumers/paciente_notificacao.py` (handler `fila_atualizada`), `core/services.py` (disparo no check-in), `apps/mobile/api/views.py` |
| 2.3 | **Disparo simultâneo da chamada** (painel + paciente na mesma ação) | `core/websocket_utils.py` (`notificar_chamada` unificado), `apps/system/views.py` (`chamar_paciente_view`) |
| 2.4 | **Extrair JS de WebSocket** para helper com reconexão com backoff e heartbeat; remover duplicação entre templates | `core/static/core/js/ws_reconnect.js` (novo), `apps/mobile/templates/mobile/acompanhamento_atendimento.html`, `apps/mobile/templates/mobile/paciente_chamado.html`, `apps/mobile/templates/mobile/fluxo_paciente.html`, `apps/display/templates/display/painel_chamada.html` |
| 2.5 | **Garantir daphne na produção** (já configurado no `start.sh`; manter e documentar) | `start.sh`, `render.yaml`, `README.md` |

### Teste Fase 2

1. `docker ps` → container `cer4-redis` ativo; `redis-cli ping` → `PONG`.
2. Abrir **2 abas**: `/painel-chamada/` (TV) e `/fluxo-paciente/?step=acompanhamento` (mobile, com CPF com encaixe).
3. Clicar "Chamar Próximo" no Sistema Interno:
   - Painel atualiza a senha com destaque + áudio;
   - Mobile transita para "É a sua vez!" **sem F5**.
4. Chamar outro paciente → o mobile do primeiro mostra "pacientes à frente" atualizado em tempo real (sem polling).
5. Matar a conexão WebSocket (DevTools → Network → Offline) e religar → reconexão automática e re-sincronização de estado.

---

## 7. FASE 3 — Encerramento e Pesquisa de Satisfação

### Objetivo
Fechar o ciclo do atendimento: atualizar o banco, renderizar a pesquisa
automaticamente no mobile e persistir as respostas alimentando o módulo de
relatórios do Sistema Interno.

### Ações e arquivos afetados

| # | Ação | Arquivos afetados |
|---|------|-------------------|
| 3.1 | **Validar pesquisa**: exigir encaixe `CONCLUIDO` de hoje; rejeitar duplicidade (1 resposta por encaixe) | `core/views.py` (`pesquisa_satisfacao_view`), `apps/mobile/api/serializers.py` (`PesquisaSatisfacaoSerializer`), `apps/core_domain/models/pesquisa_satisfacao.py` + migração |
| 3.2 | **Normalizar CPF e exigir encaixe** no registro da pesquisa (sem pesquisa órfã) | `apps/mobile/api/serializers.py` |
| 3.3 | **Garantir o fluxo de conclusão**: `paciente_concluido` com URL de pesquisa + fallback via polling | `core/views.py` (`concluir_atendimento_view`), `core/websocket_utils.py`, templates mobile (já tratam `paciente_concluido`) |
| 3.4 | **Atualização em tempo real do módulo de qualidade** (evento `pesquisa_registrada` no WS interno, para o dashboard atualizar sem refresh) | `apps/system/views.py` ou `apps/system/consumers/` (novo), `core/websocket_utils.py`, `apps/system/templates/system/gestao_qualidade.html` |

### Teste Fase 3

1. Encerrar atendimento no Sistema Interno → mobile abre a Pesquisa de Satisfação automaticamente.
2. Responder (nota 1–5 + comentário) → registro no PostgreSQL (`PesquisaSatisfacao`).
3. Verificar no "Gestão de Qualidade" que o feedback aparece sem refresh.
4. Tentar responder novamente o mesmo encaixe → rejeitado.
5. Submeter pesquisa de CPF sem encaixe concluído hoje → rejeitado.

---

## 8. FASE 4 — Validação Integrada de Ponta a Ponta

### Objetivo
Simular a jornada completa e tratar cenários de exceção (perda de conexão
WebSocket, reconexão, CPF inválido, múltiplos terminais, fim do dia).

### Ações e arquivos afetados

| # | Ação | Arquivos afetados |
|---|------|-------------------|
| 4.1 | **Script de simulação E2E** (jornada: cadastro → check-in → fila → chamada → ausente/rechamada → atendimento → conclusão → pesquisa) | `core/management/commands/simular_fluxo.py` (novo) |
| 4.2 | **Testes automatizados de fluxo e exceção** (Django `TestCase` + `WebsocketCommunicator` do Channels) | `core/tests.py` (ou `apps/`/tests), `core/test_clock_wrapper.py` |
| 4.3 | **Tratamento de desconexão**: re-sincronização de estado após reconexão (fallback via polling/API) | `core/views.py` (`paciente_status_api_view`), `apps/mobile/templates/mobile/*.html` (helper WS) |
| 4.4 | **Regressão completa** após cada fase | suite de testes + checklist manual abaixo |

### Checklist E2E

1. Cadastro de paciente novo (CPF válido, senha ≥ 8) → ok.
2. Check-in com os 3 dados (CPF + Nascimento + Mãe) → senha na fila.
3. Acompanhamento sem F5: senha atual chamada + pessoas à frente em tempo real.
4. Chamar no Sistema Interno → Painel + Mobile simultâneos (som + destaque).
5. Marcar ausente → mobile "Perdeu a Chamada"; rechamar → volta para "É a sua vez!".
6. Iniciar atendimento → mobile mostra "EM ATENDIMENTO".
7. Concluir → pesquisa renderiza automaticamente; resposta salva e visível no relatório.
8. Exceções: derrubar a rede no meio de cada etapa → reconexão automática e estado consistente.

---

## 9. Dependências de Infraestrutura

| Recurso | Local | Como configurar |
|---------|-------|-----------------|
| PostgreSQL 18 | já instalado e rodando | banco `painel_chamada_cer4`, usuário `cer4` |
| Redis 7 | via Docker | `docker run -d --name cer4-redis -p 6379:6379 redis:7-alpine` + `REDIS_URL` no `.env` |
| Integrador externo (agendamentos) | opcional | `INTEGRADOR_BASE_URL` e `INTEGRADOR_TOKEN` no `.env` (vazio desabilita) |

---

## 10. Como rodar (preservado)

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env            # preencher DB_* e REDIS_URL
python manage.py migrate
python manage.py seed_pacientes   # dados de teste para o dia
python manage.py runserver
```

Aplicação: http://127.0.0.1:8000/

| Tela | URL |
|------|-----|
| Identificação (Check-in) | `/fluxo-paciente/?step=identificacao` |
| Acompanhamento | `/fluxo-paciente/?step=acompanhamento` |
| Painel de Chamada (TV) | `/painel-chamada/` |
| Sistema Interno | `/sistema-interno/` |
| Pesquisa de Satisfação | `/pesquisa-satisfacao/?cpf=...` |
