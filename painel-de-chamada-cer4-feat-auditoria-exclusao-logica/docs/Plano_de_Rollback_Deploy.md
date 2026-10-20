# Plano de rollback — deploy de auditoria e exclusão lógica (Render)

## O que o deploy muda no banco

- **0019** `auditoria_exclusao_logica_schema`: adiciona colunas `criado_por`, `atualizado_por`, `excluido_por`, `excluido_em` (e `criado_em`/`atualizado_em` onde faltavam) em `Paciente`, `Agendamento`, `EncaixePaciente`, e uma CheckConstraint por tabela.
- **0020** `backfill_auditoria_legado`: preenche `EncaixePaciente.atualizado_em` e passa a coluna para **NOT NULL**.

O `start.sh` roda `migrate --noinput` a cada start, só para frente.

## Ponto crítico

Depois da 0020, **voltar apenas o código não é seguro**: o código antigo não
conhece `EncaixePaciente.atualizado_em` (NOT NULL, sem default no banco) e
os `INSERT` de encaixe falhariam. Por isso o rollback de código exige
reverter a migration antes.

Registros excluídos logicamente voltam a aparecer como ativos no código
antigo, que ignora `excluido_em`.

## Antes do deploy

1. Backup do Postgres no Render (Dashboard → banco → Backups → *Create backup*, ou `pg_dump "$DATABASE_URL" -Fc -f pre-auditoria.dump`). Anotar horário e confirmar que o arquivo existe.
2. Anotar o commit em produção (para o rollback de código).
3. CI verde na branch (ruff bloqueante, `check`, `makemigrations --check`, `migrate`, testes).
4. Janela de baixo uso (fora do horário de atendimento).

## Deploy

1. Merge em `main` (fluxo do `Versionamento.md`); o Render faz o build e roda o `start.sh`.
2. Verificar nos logs: `Applying core.0019...` e `Applying core.0020...` sem erro.
3. Verificação rápida: `/health/`, abrir `/admin/` (Pacientes com filtro "Situação"), criar um encaixe de teste e checar a senha/posição.

## Rollback

### Caso A — migration falhou no start

Postgres roda cada migration em transação: uma falha deixa o banco como estava. Reverter o código para o commit anterior (Render → *Deploys* → *Rollback*) e investigar.

### Caso B — migrations aplicadas, problema na aplicação

Ordem importa: **banco primeiro, código depois.**

1. (Opcional, se há excluídos que não podem reaparecer) exportar/anotar os excluídos:
   ```sql
   SELECT id, excluido_em FROM core_paciente WHERE excluido_em IS NOT NULL;
   ```
   Se for preciso que continuem fora do ar, decidir com a equipe antes (ex.: apagá-los fisicamente), pois o código antigo os mostrará.
2. No *Shell* do serviço (ainda no deploy novo):
   ```bash
   python manage.py migrate core 0018
   ```
   Reverte 0020 e 0019 (remove as colunas e as constraints). **Perde-se** o histórico de autoria/exclusão registrado desde o deploy.
3. Render → *Deploys* → *Rollback* para o commit anotado.
4. Conferir `/health/`, criação de encaixe e login.

### Caso C — reversão falhou ou dados corrompidos

Restaurar o backup do passo "Antes do deploy" (Render → banco → *Restore*, ou `pg_restore --clean --no-owner -d "$DATABASE_URL" pre-auditoria.dump`). Perde os dados gravados após o backup; avisar a recepção.

## Pós-rollback

- Registrar o motivo e o horário.
- Reaplicar a feature só com a causa corrigida e o CI verde.
