# Mapeamento de Regras de Negócio — Painel de Chamada CER4

> **Propósito**: Documentar todas as validações, condições lógicas e regras de negócio
> implementadas no código atual (Views, Models, Forms, Services, Serializers, Business Rules).

---

## 1. Funcionalidade: Identificação do Paciente (Check-in Mobile)

### 1.1 Fluxo unificado (`fluxo_paciente_view` — step=identificacao)

**URL**: `/fluxo-paciente/?step=identificacao`  
**View**: `fluxo_paciente_view` (core/views.py:451)  
**Form**: `IdentificacaoForm` (core/forms.py:74)

#### Regras de negócio

| # | Regra | Localização |
|---|-------|-------------|
| RN01 | O paciente deve informar CPF + Data de Nascimento (opcional) + Nome da Mãe (opcional) | forms.py:77-118 |
| RN02 | O CPF é obrigatório (`required=True`). Data de Nascimento e Nome da Mãe são opcionais (`required=False`) | forms.py:77, 91, 106 |
| RN03 | O CPF é limpo da máscara (remove `\D` — pontos, traços, espaços). **Não há validação algorítmica do dígito verificador** | forms.py:120-123 |
| RN04 | A Data de Nascimento aceita dois formatos de entrada: `DD/MM/AAAA` e `AAAA-MM-DD` | forms.py:94 |
| RN05 | A máscara `data-mask="cpf"` no front-end formata o CPF como `XXX.XXX.XXX-XX` | forms.py:86 |
| RN06 | A máscara `data-mask="date"` no front-end formata a data como `DD/MM/AAAA` | forms.py:100 |

#### Validação no POST (fluxo_paciente_view)

| Condição | Ação | Código |
|----------|------|--------|
| `form.is_valid()` é `False` | Re-renderiza step=identificacao com erros do form | views.py:509-510 |
| `cpf == "00000000000"` | Redireciona para `?step=bloqueio` (bloqueio/direcionamento) | views.py:486-487 |
| `Paciente.objects.filter(cpf=cpf, paciente_ativo=True)` não encontrado | Redireciona para `?step=agendamento-nao-encontrado` | views.py:489-491 |
| Data de nascimento informada **e** não coincide com a do paciente | Redireciona para `?step=agendamento-nao-encontrado` | views.py:493-494 |
| Paciente encontrado + data coincide (ou não informada) | `registrar_encaixe()` cria encaixe com `tipos_atendimento=["consulta"]` e redireciona para `?step=checkin-concluido` | views.py:496-506 |
| `registrar_encaixe()` lança exceção | Redireciona para `?step=agendamento-nao-encontrado` | views.py:507-508 |

#### Campos obrigatórios para prosseguir

- **CPF**: obrigatório no formulário, obrigatório existir na tabela `Paciente`
- **Data de Nascimento**: opcional no formulário; se informada, **deve** bater com o banco
- **Nome da Mãe**: opcional no formulário; **não é validado contra o banco** (ignorado)

#### Observações

- O `nome_mae` do formulário é armazenado no `EncaixePaciente.nome_mae` mas nunca é validado contra o `Paciente` (que **não possui** campo `nome_mae` no modelo)
- O `Paciente` model **não** possui campo `nome_mae` — apenas `EncaixePaciente` armazena esse dado
- O CPF `00000000000` é tratado como caso especial de bloqueio (RN de direcionamento para recepção)
- O `paciente_ativo=True` é exigido na consulta do `Paciente`

---

### 1.2 Fluxo legado (`identificacao_paciente_view`)

**URL**: `/identificacao-paciente/`  
**View**: `identificacao_paciente_view` (core/views.py:355)  
**Form**: `IdentificacaoForm`

| Regra | Diferença do fluxo unificado |
|-------|------------------------------|
| Valida o CPF da mesma forma (sem algoritmo) | — |
| Cria encaixe SEMPRE com `nome_completo="Paciente"` (fixo) e CPF limpo | Não consulta a tabela `Paciente` |
| Não valida data de nascimento contra o banco | Ignora `data_nascimento` mesmo quando informada |
| `registrar_encaixe()` sempre com `tipos_atendimento=["consulta"]` | Fixo |
| Sucesso → `redirect("checkin-concluido")` | View separada |
| **Não há bloqueio para CPF 000.000.000-00** | — |

---

## 2. Funcionalidade: Check-in Concluído

### 2.1 Fluxo unificado (`fluxo_paciente_view` — step=checkin-concluido)

**URL**: `/fluxo-paciente/?step=checkin-concluido`  
**View**: `fluxo_paciente_view` (views.py:561-575)

#### Regras

| Condição | Ação |
|----------|------|
| `request.session["encaixe_id"]` existe e o encaixe é encontrado | Renderiza tela com dados do encaixe real |
| `request.session["paciente_id"]` existe (fallback) | Busca último encaixe pelo CPF do paciente |
| Nenhum encaixe encontrado | Redireciona para `?step=identificacao` (views.py:636-637) |

#### Dados exibidos (quando encontrado)

- `encaixe.nome_completo` (nome do paciente)
- `encaixe.senha` (senha gerada, ex: "E001")
- Mensagem padrão: "Acompanhe sua posição na fila e aguarde sua chamada."
- Botão "Acompanhar fila" → `?step=acompanhamento`

### 2.2 View dedicada (`checkin_concluido_view`)

**URL**: `/checkin-concluido/`  
Regras idênticas à step=checkin-concluido, mas renderiza template separado `mobile/checkin_concluido.html`.

---

## 3. Funcionalidade: Acompanhamento de Atendimento (Fila)

### 3.1 Fluxo unificado (`fluxo_paciente_view` — step=acompanhamento)

**URL**: `/fluxo-paciente/?step=acompanhamento`  
**View**: `fluxo_paciente_view` (views.py:577-604)

#### Regras de cálculo

| # | Regra | Implementação |
|---|-------|---------------|
| RN07 | `pacientes_a_frente` = contagem de encaixes do mesmo dia com `posicao_fila` menor que a do paciente | `EncaixePaciente.objects.filter(data_atendimento=encaixe.data_atendimento, posicao_fila__lt=encaixe.posicao_fila).count()` |
| RN08 | `chamando_agora` = último paciente chamado (status=CHAMADO) no mesmo dia, ordenado por `chamado_em` decrescente | `filter(status=CHAMADO).order_by("-chamado_em").first()` |
| RN09 | Exige sessão com `encaixe_id` ou `paciente_id` | Fallback idêntico ao checkin-concluido |
| RN10 | Sem sessão → redireciona para `?step=identificacao` | views.py:636-637 |

---

## 4. Funcionalidade: Paciente Chamado

### 4.1 Fluxo unificado (`fluxo_paciente_view` — step=paciente-chamado)

**URL**: `/fluxo-paciente/?step=paciente-chamado`  
**View**: `fluxo_paciente_view` (views.py:606-623)

#### Regras

| # | Regra |
|---|-------|
| RN11 | Exibe dados do encaixe (senha, nome, sala, tipo de atendimento) |
| RN12 | Requer sessão com `encaixe_id` ou `paciente_id` |
| RN13 | Se `EncaixePaciente.sala` estiver vazio, exibe "10" como padrão |
| RN14 | Se não houver `tipos_atendimento`, exibe "Ambulatorial" como padrão |
| RN15 | Sem sessão → redireciona para `?step=identificacao` |

---

## 5. Funcionalidade: Perdeu a Chamada

**URLs**: `/fluxo-paciente/?step=perdeu-chamada` e `/perdeu-chamada/`  
**Views**: `fluxo_paciente_view` (views.py:625-634) e `perdeu_chamada_view` (views.py:642-671)

#### Regras

| # | Regra |
|---|-------|
| RN16 | Exibe `senha`, `setor` (fixo "Recepção Central") e `horario_chamada` (do campo `chamado_em`) |
| RN17 | Requer sessão com `encaixe_id` ou `paciente_id` |
| RN18 | Sem sessão → senha "---", setor fixo, horário "--:--" |
| RN19 | No fluxo unificado, sem sessão redireciona para `?step=identificacao` |

---

## 6. Funcionalidade: Check-in Assistido

**URLs**: `/fluxo-paciente/?step=checkin-assistido` e `/checkin-assistido/`  
**Views**: `fluxo_paciente_view` (views.py:514-524) e `checkin_assistido_view` (views.py:337-342)

#### Regras

| # | Regra |
|---|-------|
| RN20 | Tela informativa estática — **nenhuma validação ou formulário** |
| RN21 | Exibe mensagem "Nossa equipe no balcão principal ajudará com seu check-in" |
| RN22 | **Não exige sessão** (acessível sem autenticação) |

---

## 7. Funcionalidade: Bloqueio / Direcionamento para Recepção

**URLs**: `/fluxo-paciente/?step=bloqueio` e `/bloqueio-direcionamento/`  
**Views**: `fluxo_paciente_view` (views.py:526-545) e `bloqueio_direcionamento_view` (views.py:346-351)

#### Regras

| # | Regra |
|---|-------|
| RN23 | Tela informativa — **nenhuma validação** |
| RN24 | Acionada quando CPF = `00000000000` no `fluxo_paciente_view` |
| RN25 | Exibe "Confirmação presencial necessária" + orientação para ir ao balcão |
| RN26 | **Não exige sessão** |

---

## 8. Funcionalidade: Agendamento Não Encontrado

**URLs**: `/fluxo-paciente/?step=agendamento-nao-encontrado` e `/agendamento-nao-encontrado/`  
**Views**: `fluxo_paciente_view` (views.py:547-548) e `agendamento_nao_encontrado_view` (views.py:885-886)

#### Gatilhos de redirecionamento

| Condição no fluxo unificado | Ação |
|-----------------------------|------|
| CPF não encontrado em `Paciente` | `redirect(?step=agendamento-nao-encontrado)` |
| Data de nascimento não coincide | `redirect(?step=agendamento-nao-encontrado)` |
| Exceção em `registrar_encaixe()` | `redirect(?step=agendamento-nao-encontrado)` |

#### Regras

| # | Regra |
|---|-------|
| RN27 | Tela informativa — **nenhuma validação ou formulário** |
| RN28 | **Não exige sessão** |

---

## 9. Funcionalidade: Chamar Paciente (Sistema Interno)

**URL**: `/sistema/chamar/` (POST)  
**View**: `chamar_paciente_view` (apps/system/views.py:12-39)

#### Regras

| # | Regra | Implementação |
|---|-------|---------------|
| RN29 | Apenas método POST | `@require_POST` |
| RN30 | Parâmetros obrigatórios: `senha` | `request.POST.get("senha", "")` |
| RN31 | Parâmetros opcionais: `sala` (padrão "Sala 1"), `guiche` | `request.POST.get("sala", "Sala 1")` |
| RN32 | Se `senha` não existir em `EncaixePaciente` → HTTP 404 | `get_object_or_404` |
| RN33 | Ao chamar, altera o status do encaixe para `CHAMADO` | `encaixe.status = EncaixePaciente.Status.CHAMADO` |
| RN34 | Registra timestamp da chamada | `encaixe.chamado_em = timezone.now()` |
| RN35 | Atualiza a sala no encaixe | `encaixe.sala = sala` |
| RN36 | Dispara evento WebSocket para o grupo `"painel_chamada"` | `async_to_sync(channel_layer.group_send)(...)` |
| RN37 | Payload do WebSocket: `senha`, `nome`, `sala`, `guiche`, `timestamp` | — |
| RN38 | Retorna JSON `{"ok": true, "senha": ...}` | — |

---

## 10. Funcionalidade: Login (Acesso ao Portal)

**URL**: `/login/`  
**View**: `login_view` (core/views.py:890-913)  
**Form**: `LoginPacienteForm` (core/forms.py:141-173)

#### Regras de validação do formulário

| # | Regra | Código |
|---|-------|--------|
| RN39 | CPF obrigatório (`required=True`) | forms.py:144 |
| RN40 | CPF é validado pelo algoritmo (`cpf_e_valido()`) | forms.py:170-172 |
| RN41 | CPF é limpo para apenas dígitos | forms.py:173 |
| RN42 | Senha obrigatória com widget `PasswordInput` | forms.py:157-167 |
| RN43 | **Senha não é validada no formulário** (validação ocorre na view) | — |

#### Regras de autenticação na view

| Condição | Ação |
|----------|------|
| `form.is_valid()` é `False` | Re-renderiza login com erros |
| `UsuarioSistema.objects.filter(cpf=<formatado>, usuario_ativo=True)` encontrado | Seta `session["staff_usuario_id"]` |
| `Paciente.objects.filter(cpf=<dígitos>, paciente_ativo=True)` encontrado | Seta `session["paciente_id"]` |
| Sempre seta `session["staff_logged_in"] = True` | — |
| Redireciona para `sistema-interno` | views.py:911 |
| Se já logado (`staff_logged_in`) e não está no modo interno | Redireciona para `sistema-interno` (views.py:892-894) |

#### Observações

- **A senha não é validada para staff**. O login apenas verifica existência do usuário ativo, sem checar senha.
- **A senha não é validada para paciente**. O login apenas verifica se `paciente_ativo=True`, sem checar a senha.
- O CPF do staff é armazenado formatado (`123.456.789-09`) e a busca usa o CPF formatado.
- O CPF do paciente é armazenado sem máscara (`12345678909`) e a busca usa dígitos limpos.

---

## 11. Funcionalidade: Cadastro (Criar Conta do Paciente)

**URL**: `/cadastro/`  
**View**: `cadastro_view` (core/views.py:917-931)  
**Form**: `CadastroPacienteForm` (core/forms.py:176-266)

#### Regras de validação do formulário

| # | Regra | Código |
|---|-------|--------|
| RN44 | Nome completo obrigatório, **mínimo 2 palavras** (nome + sobrenome) | forms.py:233-237 |
| RN45 | Nome completo é convertido para `title()` | forms.py:237 |
| RN46 | CPF obrigatório, validado pelo algoritmo (`cpf_e_valido`) | forms.py:240-242 |
| RN47 | CPF **não pode existir** em `Paciente` (unicidade) | forms.py:243-245 |
| RN48 | CPF armazenado como apenas dígitos (limpo da máscara) | forms.py:245 |
| RN49 | Data de nascimento obrigatória no model (`DateField` com `type="date"`) | forms.py:225-226, model fields |
| RN50 | E-mail opcional (pode ser vazio); se informado, **não pode existir** em outro cadastro | forms.py:247-251 |
| RN51 | Senha obrigatória, **mínimo 8 caracteres** | forms.py:179-181 |
| RN52 | Confirmar senha obrigatório | forms.py:191-201 |
| RN53 | Senha e confirmar senha **devem coincidir** | forms.py:253-259 |
| RN54 | Senha é hashada com `set_senha()` (PBKDF2 via Django) antes de persistir | forms.py:261-265 |
| RN55 | IntegrityError (CPF ou e-mail duplicado) tratado como erro de formulário | views.py:926-927 |

#### Salvamento

| Condição | Ação |
|----------|------|
| Form válido → `form.save()` | Cria paciente com senha hashada |
| Seta `session["paciente_id"]` | — |
| Redireciona para `login` | views.py:925 |

---

## 12. Funcionalidade: Encaixe Manual (API REST)

**URL**: `/api/v1/encaixe/` (POST)  
**View**: `EncaixeViewSet` (CreateModelMixin)  
**Serializer**: `EncaixeSerializer` (apps/mobile/api/serializers.py:9-35)

#### Regras

| # | Regra |
|---|-------|
| RN56 | `nome_completo` obrigatório (max 150) |
| RN57 | `cpf` opcional (`required=False, allow_blank=True`) |
| RN58 | `data_nascimento` opcional (`required=False, allow_null=True`) |
| RN59 | `nome_mae` opcional |
| RN60 | `tipos_atendimento` opcional (lista de choices: `consulta`, `terapia`, `exame_auditivo`); padrão lista vazia |
| RN61 | `justificativa` opcional |
| RN62 | `anexo` opcional (FileField) |
| RN63 | Chama `registrar_encaixe()` do service |
| RN64 | Retorno: `{"ok": true, "senha": "...", "posicao": N}` |
| RN65 | **Sem autenticação** (`AllowAny`) |
| RN66 | **Sem validação de CPF** (apenas o que o serializer faz) |
| RN67 | **Sem consulta a Paciente** (cria encaixe para qualquer CPF) |

---

## 13. Funcionalidade: Login via API (REST)

**URL**: `/api/v1/auth/login/` (POST)  
**View**: `PacienteAuthViewSet.login`  
**Serializer**: `PacienteLoginSerializer` (apps/mobile/api/serializers.py:44-65)

#### Regras

| # | Regra |
|---|-------|
| RN68 | `cpf` obrigatório, validado pelo algoritmo (`cpf_e_valido`) |
| RN69 | `senha` obrigatória (`write_only=True`) |
| RN70 | `Paciente` deve existir com `cpf` informado **e** `paciente_ativo=True` |
| RN71 | Senha é verificada com `paciente.checar_senha()` (Django `check_password`) |
| RN72 | Se CPF não encontrado ou senha incorreta → erro "CPF ou senha inválidos." |
| RN73 | Sucesso → `{"ok": true, "paciente": {id, nome_completo, cpf}}` |
| RN74 | **Sem autenticação** (`AllowAny`) |

---

## 14. Funcionalidade: Cadastro via API (REST)

**URL**: `/api/v1/auth/cadastro/` (POST)  
**View**: `PacienteAuthViewSet.cadastro`  
**Serializer**: `PacienteCadastroSerializer` (apps/mobile/api/serializers.py:68-99)

#### Regras (idênticas ao formulário web)

| # | Regra |
|---|-------|
| RN75 | Nome completo obrigatório |
| RN76 | CPF obrigatório, validado pelo algoritmo, **não pode existir** |
| RN77 | Data de nascimento obrigatória |
| RN78 | E-mail opcional; se informado, **não pode existir** |
| RN79 | Senha obrigatória, **mínimo 8 caracteres** |
| RN80 | Confirmar senha obrigatório, **deve coincidir** com senha |
| RN81 | Senha hashada com `set_senha()` |
| RN82 | Sucesso → HTTP 201 + `{"ok": true, "paciente": {id, nome_completo, cpf}}` |
| RN83 | **Sem autenticação** (`AllowAny`) |

---

## 15. Funcionalidade: Filas via API (REST)

**URL**: `/api/v1/fila/` (GET)  
**View**: `FilaViewSet` (ListModelMixin)  
**Serializer**: `FilaSerializer`

#### Regras

| # | Regra |
|---|-------|
| RN84 | Lista todos os `EncaixePaciente` ordenados por `-criado_em` |
| RN85 | Parâmetro opcional `?cpf=...` — filtra por CPF |
| RN86 | Campos retornados: `senha`, `nome_completo`, `posicao_fila`, `data_atendimento`, `criado_em` |
| RN87 | **Sem autenticação** (`AllowAny`) |

---

## 16. Funcionalidade: Painel de Chamada (Display TV)

**URL**: `/painel-chamada/`  
**View**: `painel_chamada_view` (core/views.py:176-224)

#### Regras de dados

| # | Regra |
|---|-------|
| RN88 | `current_call` = primeiro encaixe do dia ordenado por `-criado_em` |
| RN89 | Se não houver encaixe → exibe placeholders "---" |
| RN90 | `recent_calls` = últimos 5 encaixes do dia |
| RN91 | `sala` extraída de `EncaixePaciente.sala`; se vazio, "SALA 01" |
| RN92 | `service_type` extraído do primeiro `TipoAtendimentoEncaixe`; se vazio, "AMBULATORIAL" |
| RN93 | **Sem autenticação** |

---

## 17. Funcionalidade: Dashboard de Monitoramento

**URL**: `/dashboard-monitoramento/`  
**View**: `dashboard_monitoramento_view` (core/views.py:39-172)

#### Regras de KPI

| # | Regra | Cálculo |
|---|-------|---------|
| RN94 | "Check-ins recebidos" = total de encaixes hoje | `EncaixePaciente.objects.filter(data_atendimento=hoje).count()` |
| RN95 | "Em fluxo" = slice dos primeiros 12 encaixes de hoje | — |
| RN96 | "Pendências" = total de encaixes hoje | Mesmo que RN94 |
| RN97 | Se pendentes ≥ 20 → badge "ALERTA" (vermelho) | — |
| RN98 | Gráfico = últimos 7 dias com contagem por dia | Loop `hoje - timedelta(days=i)` |
| RN99 | Kanban: 4 colunas (Validação, Aguardando, Chamado, Finalizados) | Filtro por `status` |
| RN100 | Kanban: máximo 5 pacientes por coluna com contagem "+N pacientes" | `qs[:5]` |
| RN101 | Kanban: paciente em `CHAMADO` mostra profissional (fixo "Profissional") e sala | — |
| RN102 | Kanban: paciente em `CONCLUIDO` mostra flag `completed` e horário | — |

#### Autenticação

| Condição | Ação |
|----------|------|
| Sessão `staff_logged_in` opcional | views.py:111-115 |
| Se logado, exibe nome e nível do usuário | — |

---

## 18. Funcionalidade: Configurações (Gestão de Usuários)

**URL**: `/configuracoes/`  
**View**: `configuracoes_view` (core/views.py:375-440)  
**Form**: `UsuarioSistemaForm` (core/forms.py:42-51)

#### Regras de acesso

| # | Regra |
|---|-------|
| RN103 | Ações de criação/edição/exclusão/bloqueio exigem `SUPER_ADMIN` OU tabela vazia |
| RN104 | Usuários sem `SUPER_ADMIN` e com tabela não vazia são redirecionados → `sistema-interno` |
| RN105 | `tabela_vazia = not UsuarioSistema.objects.exists()` |
| RN106 | `pode_criar = is_admin or tabela_vazia` |

#### Ações disponíveis

| Ação | Parâmetro | Regra |
|------|-----------|-------|
| Criar | `action=create` | Cria novo usuário se form válido |
| Atualizar | `action=update` + `usuario_id` | Atualiza dados do usuário |
| Ativar/Desativar | `action=toggle` + `usuario_id` | Inverte `usuario_ativo` |
| Excluir | `action=delete` + `usuario_id` | Remove registro |

#### Validação do formulário `UsuarioSistemaForm`

| # | Regra |
|---|-------|
| RN107 | CPF deve ter 11 dígitos após limpeza → erro "Informe um CPF com 11 dígitos." |
| RN108 | CPF é formatado como `XXX.XXX.XXX-XX` antes de salvar |
| RN109 | **Não valida dígito verificador** do CPF (apenas quantidade de dígitos) |
| RN110 | **Não valida unicidade do CPF** (model já tem `unique=True` no banco) |

---

## 19. Funcionalidade: Meu Perfil

**URL**: `/meu-perfil/`  
**View**: `meu_perfil_view` (core/views.py:977-1033)  
**Forms**: `PacientePerfilForm` (para pacientes) / `MeuPerfilForm` (para staff)

#### Regras

| # | Regra |
|---|-------|
| RN111 | Exige `session["staff_logged_in"] = True` |
| RN112 | Se não logado → exibe erro "Sessão expirada" |
| RN113 | Escolhe formulário conforme tipo: `PacientePerfilForm` se `session["paciente_id"]`, senão `MeuPerfilForm` |
| RN114 | `PacientePerfilForm` edita: `nome_completo`, `email`, `data_nascimento` (campos do model) |
| RN115 | `MeuPerfilForm` edita: `nome_completo`, `email_institucional` |
| RN116 | E-mail é validado como único (excluindo o próprio usuário) |
| RN117 | `IntegrityError` tratado como erro de formulário |

---

## 20. Funcionalidade: Encaixe Manual (Formulário Web / POST JSON)

**URL**: `/encaixe/` (POST)  
**View**: `encaixe_view` (core/views.py:962-973)  
**Form**: `EncaixeForm` (core/forms.py:9-39)

#### Regras

| # | Regra |
|---|-------|
| RN118 | Apenas POST | `@require_POST` |
| RN119 | `nome_completo` obrigatório (max 150) | forms.py:15 |
| RN120 | `cpf` opcional (`required=False`) | forms.py:16 |
| RN121 | `data_nascimento` opcional | forms.py:17-21 |
| RN122 | `nome_mae` opcional | forms.py:22 |
| RN123 | `tipos_atendimento` obrigatório (MultipleChoice) | forms.py:23-27 |
| RN124 | `justificativa` opcional | forms.py:28-30 |
| RN125 | `anexo` opcional; extensões permitidas: `.pdf`, `.doc`, `.docx` | forms.py:31, 33-39 |
| RN126 | Sucesso → JSON `{"ok": true, "senha": ..., "posicao": N}` | — |
| RN127 | Erro de negócio → JSON `{"ok": false, "erros": {...}}` status 400/500 | — |
| RN128 | **Sem validação de CPF** (apenas max_length e required) | — |

---

## 21. Funcionalidade: Auditoria de Percurso e Segurança

**URL**: `/telas/auditoria-percurso-seguranca/`  
**View**: `auditoria_percurso_seguranca_view` (core/views.py:783-842)  
**Service**: `filtrar_auditoria()` (core/services.py, ~linha 227)

#### Regras de filtro

| Filtro | Parâmetro | Comportamento |
|--------|-----------|---------------|
| Busca textual | `q` | Busca por nome (case-insensitive), ficha (senha) ou CPF (parcial) |
| Data única | `data` | Filtra por data exata |
| Intervalo | `data_inicio` + `data_fim` | Intervalo inclusivo; se `inicio > fim`, inverte |
| Setor | `setor` | Exato; "Todos" desabilita o filtro |
| Status | `status` | Exato (maiúsculo); "TODOS" desabilita |
| Apenas alertas | `apenas_alertas` | Filtra só `status_class == "alert"` |

#### Regras de dados

| # | Regra |
|---|-------|
| RN129 | Dados combinam mock fixo (`AUDITORIA_MOCK_DATA`) + encaixes reais do banco |
| RN130 | Encaixes reais são convertidos para o mesmo formato do mock |
| RN131 | Export CSV disponível via `?export=csv` |
| RN132 | Paginação: `?pagina=` (8 páginas totais no mock) |
| RN133 | Colunas do CSV: Ordem, Ficha, Paciente, CPF, Check-in, Entrada Fila, Chamada, Encerramento, Status, Setor, Data Referência, Badges, Log |

---

## 22. Business Rules Globais (core/business_rules.py)

| Função | Regra |
|--------|-------|
| `is_deadline_expired(deadline_at)` | Retorna `True` se `clock.now() > deadline_at` |
| `can_run_reception_workflow()` | Retorna `True` se dia da semana < 5 (segunda a sexta) |
| `apenas_digitos(valor)` | Remove todos os caracteres não-dígitos |
| `formatar_cpf(cpf_digitos)` | Formata 11 dígitos como `XXX.XXX.XXX-XX` |
| `cpf_e_valido(cpf)` | Valida dígitos verificadores do CPF (algoritmo oficial) + rejeita sequências iguais (111.111.111-11) |
| `nivel_forca_senha(senha)` | Retorna 0-3 com base em: ≥8 chars (+1), maiúscula + minúscula (+1), dígito + especial (+1), ≥12 chars (+1) |

#### Observações sobre `cpf_e_valido`

- **Usado em**: `LoginPacienteForm`, `PacienteCadastroForm`, `PacienteLoginSerializer`, `PacienteCadastroSerializer`
- **NÃO usado em**: `IdentificacaoForm` (removido), `EncaixeForm`, `UsuarioSistemaForm`, `FluxoPacienteView`
- **Regra**: rejeita CPFs com menos de 11 dígitos, mais de 11, todos dígitos iguais, ou dígitos verificadores incorretos

---

## 23. Business Rules do Service `registrar_encaixe()`

**Localização**: core/services.py (~linha 411)

| # | Regra | Implementação |
|---|-------|---------------|
| RN134 | Senha gerada automaticamente no formato `E` + número de 3 dígitos | `f"E{proxima_posicao:03d}"` |
| RN135 | `posicao_fila` = último `posicao_fila` do dia + 1 (ou 1 se primeiro) | `EncaixePaciente.objects.filter(data_atendimento=hoje).order_by("-posicao_fila").first()` |
| RN136 | `data_atendimento` = data atual (SystemClock) | `SystemClock.now().date()` |
| RN137 | `status` inicial = `VALIDACAO` (default do model) | — |
| RN138 | Operação atômica (transaction) | `@transaction.atomic` |
| RN139 | `TipoAtendimentoEncaixe` criados em bulk | `bulk_create()` |

---

## 24. Modelos — Regras de Domínio

### Paciente

| Campo | Regra |
|-------|-------|
| `cpf` | `unique=True`, `max_length=14` — armazenado sem máscara |
| `senha_hash` | `max_length=128` — hash Django (PBKDF2) |
| `paciente_ativo` | `default=True` — controle de bloqueio de conta |
| `data_nascimento` | `null=True, blank=True` — pode ser nulo |

### EncaixePaciente

| Campo | Regra |
|-------|-------|
| `status` | Ciclo: `VALIDACAO → AGUARDANDO → CHAMADO → ATENDIMENTO → CONCLUIDO` |
| `senha` | `max_length=10` — gerado como `E001` |
| `posicao_fila` | `PositiveIntegerField` — sequencial por dia |
| `data_atendimento` | `default=timezone.localdate` |
| `sala` | `blank=True, default=""` |
| `chamado_em` | Preenchido quando status muda para `CHAMADO` |
| `cpf` | **Não é FK** — `CharField` simples (desnormalizado) |
| `nome_mae` | Apenas informacional, sem validação |

### UsuarioSistema

| Campo | Regra |
|-------|-------|
| `nivel_acesso` | Choices: `recepcionista`, `coordenacao`, `super_admin` |
| `usuario_ativo` | `default=True` |
| `cpf` | `unique=True` — armazenado **formatado** (`123.456.789-09`) |
| `cargo` | `default=""` (livre) |
| `departamento` | `default=""` (livre) |

---

## 25. Tabela Resumo: Onde o CPF é validado pelo algoritmo?

| Fluxo | Arquivo | Valida `cpf_e_valido`? |
|-------|---------|------------------------|
| Identificação (Check-in) | `IdentificacaoForm` / `fluxo_paciente_view` | **NÃO** |
| Login Web | `LoginPacienteForm` | **SIM** |
| Cadastro Web | `CadastroPacienteForm` | **SIM** |
| Login API | `PacienteLoginSerializer` | **SIM** |
| Cadastro API | `PacienteCadastroSerializer` | **SIM** |
| Encaixe Manual (Web) | `EncaixeForm` | **NÃO** |
| Encaixe Manual (API) | `EncaixeSerializer` | **NÃO** |
| Configurações (Staff) | `UsuarioSistemaForm` | **NÃO** (só 11 dígitos) |

---

## 26. Tabela Resumo: Sessão vs. Acesso

| Tela | Exige `staff_logged_in`? | Exige `encaixe_id`? | Exige `paciente_id`? |
|------|-------------------------|---------------------|----------------------|
| Identificação | Não | Não | Não |
| Check-in Concluído | Não | Sim (fallback paciente_id) | — |
| Acompanhamento | Não | Sim (fallback paciente_id) | — |
| Paciente Chamado | Não | Sim (fallback paciente_id) | — |
| Perdeu Chamada | Não | Sim (fallback paciente_id) | — |
| Check-in Assistido | Não | Não | Não |
| Bloqueio | Não | Não | Não |
| Agendamento Não Encontrado | Não | Não | Não |
| Dashboard | Não | Não | Não |
| Configurações | Não (mas exige admin para ações) | — | — |
| Login | Não | — | — |
| Cadastro | Não | — | — |
| Meu Perfil | **Sim** | — | Opcional |
| Sistema Interno | **Sim** | — | — |

---

## 27. Tabela Resumo: Ciclo de Vida do EncaixePaciente

```
                  chamar_paciente_view (POST /sistema/chamar/)
                            |
[identificacao] → VALIDACAO → AGUARDANDO → CHAMADO → ATENDIMENTO → CONCLUIDO
  (criação)           ↑           ↑
                  (default)   (status inicial      
                              do fluxo não    
                              é alterado no   
                              código atual)   
```

**Nota**: No código atual, o encaixe é criado com `status=VALIDACAO` (default do model). A única transição explícita implementada é `VALIDACAO → CHAMADO` (feita por `chamar_paciente_view`). As demais transições (`AGUARDANDO`, `ATENDIMENTO`, `CONCLUIDO`) não possuem views/endpoints implementados — os status existem apenas como choices no model.

---

## 28. Diagrama de Fluxo do Paciente (Mobile)

```
                    ┌──────────────────┐
                    │   Identificação  │  ← fluxo_paciente_view (step=identificacao)
                    │   (CPF + Data)   │
                    └────────┬─────────┘
                             │
               ┌─────────────┼─────────────┐
               ▼             ▼             ▼
        ┌──────────┐  ┌────────────┐  ┌──────────────┐
        │Check-in  │  │Bloqueio    │  │Agendamento   │
        │Concluído │  │(CPF=0...0)│  │Não Encontrado│
        └────┬─────┘  └────────────┘  └──────────────┘
             │
             ▼
      ┌──────────────┐
      │Acompanhamento│  ← consulta fila (posicao_fila)
      │(Fila)       │
      └──────────────┘
             │
             ▼
      ┌──────────────┐
      │Paciente      │  ← chamado (status=CHAMADO)
      │Chamado       │
      └──────────────┘
             │
             ▼
      ┌──────────────┐
      │Perdeu        │
      │Chamada       │
      └──────────────┘
```

---

## 29. Inconsistências e Pontos de Atenção Identificados

| ID | Descrição | Localização |
|----|-----------|-------------|
| I01 | `identificacao_paciente_view` (legado) cria encaixe com nome fixo "Paciente" em vez de consultar o nome real do `Paciente` | views.py:359-365 |
| I02 | `nome_mae` não existe no model `Paciente`, mas é solicitado no formulário de check-in e armazenado apenas em `EncaixePaciente` | forms.py:106-118 |
| I03 | `novo_usuario_logado` no dashboard usa o primeiro encaixe do dia (RN94), mas o mock mistura dados reais com placeholders | views.py:50-51 |
| I04 | Login (`login_view`) não valida senha — qualquer CPF ativo + submit loga o usuário | views.py:895-911 |
| I05 | CPF do `UsuarioSistema` é armazenado **formatado** (`123.456.789-09`), enquanto CPF do `Paciente` é armazenado **sem máscara** (`12345678909`) — isso força a view de login a fazer duas buscas distintas | views.py:899-904 |
| I06 | `cpf_e_valido` não é usado no check-in (`IdentificacaoForm`), mas é usado no login (`LoginPacienteForm`) e cadastro (`CadastroPacienteForm`) — assimetria proposital |
| I07 | `registrar_encaixe()` no fluxo unificado fixa `tipos_atendimento=["consulta"]` — ignore o tipo vindo do formulário | views.py:502 |
| I08 | O ciclo de status `VALIDACAO → AGUARDANDO → ATENDIMENTO → CONCLUIDO` não tem endpoints implementados — apenas `CHAMADO` é atingível via `chamar_paciente_view` | — |
| I09 | Export CSV da auditoria conta com total de 8 páginas fixas no mock, sem paginação real | services.py (~dashboard) |
| I10 | `EncaixeForm` e `EncaixeSerializer` aceitam CPF opcional — é possível criar um encaixe sem CPF | forms.py:16, serializer:11 |
