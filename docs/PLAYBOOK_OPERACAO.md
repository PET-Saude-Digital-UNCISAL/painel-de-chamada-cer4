# Playbook de Operação — Painel de Chamada CER4

## 1. Inicialização

```bash
# Criar/ativar ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt

# Configurar variáveis de ambiente
cp .env.example .env
# Editar .env com dados do banco e integrações

# Migrar banco de dados
python manage.py migrate

# Criar usuário admin inicial
python manage.py seed_usuarios

# Iniciar servidor
python manage.py runserver
```

## 2. Comandos de Manutenção

### Sincronizar agendamentos do sistema externo
```bash
# Sincronizar agendamentos de hoje
python manage.py sincronizar_agendamentos

# Sincronizar data específica
python manage.py sincronizar_agendamentos --data 2026-07-27

# Sincronizar com URL/token explícitos
python manage.py sincronizar_agendamentos --base-url https://api.exemplo.com --token meu-token
```

### Importar agendamentos de arquivo
Acessar tela de Auditoria → clicar em "+ Importar Agendamentos"
Formatos aceitos: CSV, XLSX

### Gerar dados de desenvolvimento
```bash
python manage.py seed_pacientes --quantidade 50
python manage.py seed_usuarios
```

## 3. Monitoramento

### Dashboard
Acessar `/dashboard-monitoramento/` ou Sistema Interno → Dashboard

### WebSocket
Verificar conexão WebSocket em:
- Painel: `ws://host/ws/painel-chamada/`
- Paciente: `ws://host/ws/paciente/{cpf}/`

Logs de WebSocket aparecem no console do navegador.

### Logs de erro
```bash
# Verificar falhas de WebSocket
grep -r "Falha ao enviar WebSocket" logs/

# Verificar erros de integração
grep -r "Falha ao enviar WebSocket para grupo" logs/
```

## 4. Procedimentos de Recuperação

### WebSocket não está conectando
1. Verificar se Redis está rodando: `redis-cli ping`
2. Verificar variável `REDIS_URL` no `.env`
3. Se Redis não estiver disponível, o sistema usa `InMemoryChannelLayer` (fallback)
4. Reiniciar servidor: `python manage.py runserver`

### Sincronização com sistema externo falhou
1. Verificar `INTEGRADOR_BASE_URL` e `INTEGRADOR_TOKEN` no `.env`
2. Testar conectividade: `curl -I $INTEGRADOR_BASE_URL/api/agendamentos`
3. Executar sincronização manual: `python manage.py sincronizar_agendamentos`
4. Verificar logs de erro no console

### Banco de dados com problemas
```bash
# Verificar conexão
python manage.py dbshell

# Rodar migrações do zero (cuidado: apaga dados)
python manage.py migrate --run-syncdb
```

## 5. Deploy (Render)

O arquivo `render.yaml` contém a configuração de deploy. O `start.sh` executa:
1. Migrations: `python manage.py migrate`
2. Gunicorn + Uvicorn Workers (ASGI)

Variáveis de ambiente obrigatórias:
- `DATABASE_URL` — Internal Database URL do PostgreSQL do Render
- `REDIS_URL` — Injetado automaticamente pelo Render
- `SECRET_KEY` — Chave secreta do Django
- `INTEGRADOR_BASE_URL` — URL do sistema externo (opcional)
- `INTEGRADOR_TOKEN` — Token de autenticação (opcional)

## 6. Arquitetura de Diretórios

```
config/                  ← Configuração do projeto
  settings.py            ← Settings (DB, Redis, Integrador, DRF)
  asgi.py                ← ASGI (WebSocket + HTTP)
  urls.py                ← Root URL conf

core/                    ← App principal
  services.py            ← Lógica de negócio (Humble Object)
  websocket_utils.py     ← Utilitário de WebSocket
  integrator.py          ← Adapter de integração externa
  auth_decorators.py     ← Decorator @staff_required
  views.py               ← Views finas (Humble Object)
  urls.py                ← URL routing
  tests.py               ← Testes
  management/commands/   ← Comandos CLI
    sincronizar_agendamentos.py

apps/
  core_domain/models/    ← Modelos de domínio
  mobile/                ← App mobile (REST API + templates)
  system/                ← Sistema interno staff
  display/               ← Painel de chamada (WebSocket + template)
```

## 7. Verificações pós-deploy

- [ ] Servidor HTTP responde na porta 8000
- [ ] WebSocket `/ws/painel-chamada/` conecta sem erros
- [ ] WebSocket `/ws/paciente/{cpf}/` conecta sem erros
- [ ] Login staff funciona em `/sistema-interno/`
- [ ] Dashboard carrega com métricas
- [ ] Painel de chamada mostra dados corretos
- [ ] Fluxo mobile: check-in → fila → chamado → concluir
- [ ] Sincronização com sistema externo (se configurado)
