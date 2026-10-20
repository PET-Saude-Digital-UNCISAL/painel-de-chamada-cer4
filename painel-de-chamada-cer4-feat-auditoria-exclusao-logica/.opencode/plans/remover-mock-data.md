# Plano: Remover dados mockados do seed e limpar módulo Atendimentos do Dia

## Problema
O `seed_pacientes.py` cria `EncaixePaciente` (fichas de atendimento) automaticamente, 
burlanodo o fluxo real onde o profissional da recepção adiciona manualmente 
pacientes sem consulta agendada.

## Passos

### 1. `core/management/commands/seed_pacientes.py`
- Remover import: `from core.models import EncaixePaciente, Paciente` → `from core.models import Paciente`
- Remover import: `from core.services import registrar_encaixe`
- Remover variáveis `encaixes_criados` e `encaixes_ignorados`
- Remover linhas 112-131 (bloco que verifica e cria `EncaixePaciente`)

### 2. `core/services.py` — `_resolve_auditoria_date_range()`
- Quando `filtros_dict` vazio (sem `data`, `data_inicio`, `data_fim`), retornar `(hoje, hoje)` em vez de `(None, None)`

### 3. Limpar registros existentes
- Executar no Django shell: `EncaixePaciente.objects.filter(cpf__in=[...]).delete()`
- Ou: `python manage.py shell -c "from core.models import EncaixePaciente; print(EncaixePaciente.objects.count(), 'removidos'); EncaixePaciente.objects.all().delete()"`

## Resultado esperado
1. `python manage.py seed_pacientes` cria apenas contas `Paciente` (sem fichas)
2. Abrir "Atendimentos do Dia" → lista vazia
3. Fazer check-in manual → paciente aparece na lista
4. Seed data não polui a tela de Atendimentos do Dia
