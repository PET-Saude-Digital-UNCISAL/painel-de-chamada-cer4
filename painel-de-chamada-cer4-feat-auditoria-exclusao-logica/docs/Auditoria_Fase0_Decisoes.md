# Auditoria e exclusão lógica — Fase 0: decisões, linha de base e contrato

> Status: **decisões propostas, a validar com a equipe.** Cada item abaixo
> descreve o que o código já implementa (Tarefas 1–4). A coluna
> "Validação" deve ser preenchida na reunião; se a equipe discordar,
> o item vira tarefa de ajuste.

## 1. Decisões

| # | Pergunta | Decisão adotada | Validação |
|---|----------|-----------------|-----------|
| 1 | Ator sem usuário (paciente, rotina automática, admin)? | Campos `*_por` ficam **nulos**. Paciente nunca é ator (`sem_ator`). Integrador/importer/comandos usam `usando_ator(...)`. Edição pelo Django Admin grava `atualizado_por` vazio (admin não tem ator). | ☐ |
| 2 | Registros legados? | `criado_por`/`atualizado_por` ficam **nulos**; `atualizado_em` do encaixe recebe `criado_em` (migration 0020). Sem usuário "legado". | ☐ |
| 3 | `paciente_ativo` x exclusão lógica? | **Independentes.** `paciente_ativo=False` = sem acesso ao fluxo mobile, continua visível ao staff. `excluido_em` preenchido = removido de todas as consultas (`objects`). | ☐ |
| 4 | Cascata Paciente → Agendamento/Encaixe? | Excluir paciente exclui seus agendamentos e encaixes com o **mesmo carimbo e ator**; restaurar devolve só o que tem esse carimbo. Exige ator. | ☐ |
| 5 | Exclusão física de `UsuarioSistema`? | **Bloqueada** (FK `PROTECT`; admin sem delete). Caminho: desativar (`usuario_ativo=False`). Usuário sem registros vinculados ainda pode ser excluído pelo serviço. | ☐ |
| 6 | Quem pode excluir/restaurar? | Exclusão: staff pelas telas do sistema (exige ator). Restauração: superusuário do Django Admin (ação "Restaurar"). Sem tela de restauração para a recepção nesta entrega. | ☐ |
| 7 | LGPD / eliminação definitiva? | `excluir_definitivamente()` existe, **sem UI**: uso manual, por pedido formal do titular, via shell, com registro do pedido fora do sistema. Dados de excluídos continuam no banco até lá. | ☐ |
| 8 | CPF de paciente excluído? | Continua ocupando o `unique`. Importador restaura o paciente; autocadastro devolve erro de validação. | ☐ |
| 9 | Senha da fila com encaixe excluído? | Senha/posição consultam `all_objects`: senha excluída **não é reaproveitada**. | ☐ |

## 2. Branch e commits

```bash
git checkout develop && git pull origin develop
git checkout -b feat/auditoria-registros   # se ainda não existir
```

Commits em Conventional Commits (ver `Versionamento.md`), por exemplo:

```
feat(admin): campos de auditoria somente leitura, filtro de excluídos e ação restaurar
test(core): testes de integração de auditoria e exclusão lógica
ci: relatório geral do ruff, checagem de migrações pendentes
docs: SAD, decisões da Fase 0 e plano de rollback
```

## 3. Linha de base (preencher antes de iniciar o trabalho)

Não foi possível medir no ambiente de preparação (sem acesso à rede para
instalar dependências). Rodar na branch **antes** das mudanças desta tarefa:

```bash
python manage.py test 2>&1 | tail -5      # total / falhas
ruff check . --statistics | tail -15
```

| Medida | Valor |
|--------|-------|
| Testes (total / falhas) | ____ / ____ |
| `ruff check .` | 258 erros pré-existentes (conforme `pyproject.toml`); conferir o número atual: ____ |

O CI passa a rodar o relatório geral do ruff **sem bloquear** e bloquear
apenas `core/admin.py` e `apps/core_domain/auditoria`.

## 4. Contrato de nomes

- Campos: `criado_por`, `criado_em`, `atualizado_por`, `atualizado_em`, `excluido_por`, `excluido_em`.
- Managers: `objects` (só ativos, padrão) e `all_objects` (todos).
- Ator atual: `apps.core_domain.auditoria.get_ator_atual_id()`; definir com `usando_ator(ator)`; ignorar com `@sem_ator`.
- API do model: `delete()` (lógico), `restaurar()`, `excluir_definitivamente()`; no queryset: `ativos()`, `excluidos()`, `delete()`, `restaurar()`, `excluir_definitivamente()`.

## 5. Limitações conhecidas (ficam para a fase de melhorias)

- No admin, criar paciente com CPF de um paciente excluído resulta em erro de banco (a validação de unicidade do admin só enxerga ativos).
- No admin, editar um agendamento/encaixe cujo paciente está excluído pode falhar na validação do campo `paciente`.
- A ação "Restaurar" só enxerga o que o filtro atual mostra: usar o filtro "Excluídos" ou "Todos".
