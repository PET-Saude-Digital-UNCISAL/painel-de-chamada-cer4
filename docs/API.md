# API — Painel de Chamada CER4

## Endpoints REST

### Mobile (`/api/v1/`)

#### `POST /api/v1/encaixes/`
Cria um novo encaixe (entrada manual na fila).

**Body:**
```json
{
  "nome_completo": "João da Silva",
  "cpf": "390.533.447-05",
  "data_nascimento": "1990-05-10",
  "nome_mae": "Maria da Silva",
  "tipos_atendimento": ["consulta"],
  "justificativa": "",
  "anexo": null
}
```

**Response `201`:**
```json
{ "ok": true, "senha": "E001", "posicao": 1 }
```

---

#### `GET /api/v1/fila/`
Lista todos os encaixes (opcionalmente filtrados por CPF).

**Query params:** `?cpf=39053344705`

**Response `200`:**
```json
[
  {
    "senha": "E001",
    "nome_completo": "João da Silva",
    "posicao_fila": 1,
    "status": "aguardando",
    "sala": "",
    "chamado_em": null,
    "data_atendimento": "2026-07-27",
    "criado_em": "2026-07-27T10:00:00-03:00"
  }
]
```

---

#### `GET /api/v1/fila/atual/`
Estado atual da fila: quem está sendo chamado, fila de espera e posição do paciente.

**Query params:** `?cpf=39053344705` (opcional)

**Response `200`:**
```json
{
  "chamando_agora": {
    "senha": "E003",
    "nome": "MARIA SANTOS",
    "sala": "Sala 03"
  },
  "fila_espera": [
    { "senha": "E004", "nome_completo": "Pedro Alves", ... }
  ],
  "meu_encaixe": {
    "senha": "E004",
    "status": "aguardando",
    "posicao_fila": 4,
    "pacientes_a_frente": 3
  }
}
```

---

#### `POST /api/v1/pacientes/login/`
Autenticação do paciente.

**Body:**
```json
{ "cpf": "390.533.447-05", "senha": "SenhaForte123!" }
```

**Response `200`:**
```json
{ "ok": true, "paciente": { "id": 1, "nome_completo": "João da Silva", "cpf": "39053344705" } }
```

---

#### `POST /api/v1/pacientes/cadastro/`
Registro de novo paciente.

**Body:**
```json
{
  "nome_completo": "João da Silva",
  "cpf": "390.533.447-05",
  "data_nascimento": "1990-05-10",
  "email": "joao@email.com",
  "senha": "MinhaSenha123!",
  "confirmar_senha": "MinhaSenha123!"
}
```

**Response `201`:**
```json
{ "ok": true, "paciente": { "id": 1, "nome_completo": "João da Silva", "cpf": "39053344705" } }
```

---

#### `POST /api/v1/pesquisa-satisfacao/`
Submete pesquisa de satisfação, com nota (1 a 5) por categoria.

**Body:**
```json
{
  "cpf": "390.533.447-05",
  "nota_atendimento": 5,
  "nota_espera": 4,
  "nota_instalacao": 5,
  "nota_profissional": 5,
  "nota_clareza": 4,
  "comentario": "Ótimo atendimento"
}
```

A nota geral (`nota`) é calculada automaticamente como a média arredondada das 5 categorias.

**Response `201`:**
```json
{ "ok": true, "id": 1 }
```

---

### Sistema Interno (`/sistema/`)

#### `POST /sistema/chamar/`
Chama um paciente (Staff autenticado via sessão).

**Body:** `senha=E001&sala=Sala+1&guiche=`

**Response `200`:**
```json
{ "ok": true, "senha": "E001" }
```

**Response `401`:** Sem autenticação staff

---

### Views HTML (`/`)

Endpoint | Método | Descrição
---|---|---
`/identificacao-paciente/` | GET/POST | Check-in do paciente
`/checkin-concluido/` | GET | Confirmação de check-in
`/acompanhamento-atendimento/` | GET | Acompanhamento da fila
`/paciente-chamado/` | GET | Paciente foi chamado
`/painel-chamada/` | GET | Painel de chamada (TV)
`/encaixe/{id}/validar/` | POST | VALIDAÇÃO → AGUARDANDO
`/encaixe/{id}/iniciar-atendimento/` | POST | CHAMADO → ATENDIMENTO
`/encaixe/{id}/concluir-atendimento/` | POST | ATENDIMENTO → CONCLUIDO
`/api/integrador/sincronizar/` | POST | Sincroniza agendamentos externos

### Status do Encaixe

```
VALIDACAO → AGUARDANDO → CHAMADO → ATENDIMENTO → CONCLUIDO
     ↑          ↑           ↑           ↑
 valida      chamar     iniciar     concluir
```

---

## WebSocket

### `ws://host/ws/painel-chamada/`
Painel de chamada (TV). Recebe eventos em tempo real.

**Evento `paciente_chamado`:**
```json
{
  "tipo": "paciente_chamado",
  "senha": "E001",
  "nome": "MARIA SANTOS",
  "sala": "Sala 03",
  "guiche": "Guiche 1",
  "timestamp": "2026-07-27T10:30:00"
}
```

**Evento `fila_atualizada`:**
```json
{
  "tipo": "fila_atualizada",
  "fila": [
    { "senha": "E002", "nome_completo": "João", "posicao_fila": 2, "status": "aguardando", "sala": "" }
  ],
  "recent_calls": [
    { "ticket": "E001", "room": "SALA 03", "patient_name": "MARIA SANTOS", "time": "10:30" }
  ],
  "timestamp": "2026-07-27T10:31:00"
}
```

### `ws://host/ws/paciente/{cpf}/`
Notificações individuais do paciente.

**Evento `paciente_chamado`:**
```json
{
  "tipo": "paciente_chamado",
  "senha": "E001",
  "nome": "MARIA SANTOS",
  "sala": "Sala 03",
  "guiche": "",
  "timestamp": "2026-07-27T10:30:00"
}
```

---

## Integração externa

### Contrato esperado do sistema externo

`GET /api/agendamentos?data=YYYY-MM-DD`
```json
[
  {
    "id": "ext-001",
    "nome_completo": "João Silva",
    "cpf": "39053344705",
    "data_nascimento": "1990-05-10",
    "nome_mae": "Maria Silva",
    "tipo_atendimento": "consulta",
    "data_agendamento": "2026-07-27",
    "hora_agendamento": "14:30",
    "observacoes": ""
  }
]
```

`POST /api/agendamentos/{id}/conclusao`
```json
{
  "senha": "E001",
  "cpf": "39053344705",
  "status": "concluido",
  "sala": "Sala 03",
  "concluido_em": "2026-07-27T11:00:00-03:00"
}
```
