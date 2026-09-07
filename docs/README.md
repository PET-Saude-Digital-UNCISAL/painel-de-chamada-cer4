# Painel de Chamada CER4

> **Guia de investigação dos fluxos (qual arquivo analisar):** veja [GUIA_INVESTIGACAO.md](./GUIA_INVESTIGACAO.md)
>
> **Plano de refatoração e correção por fases:** veja [PLANO_REFATORACAO.md](./PLANO_REFATORACAO.md)
> para a auditoria, causas-raiz, arquivos afetados e testes de cada fase
> (Lógica/Estados, Real-Time, Encerramento/Pesquisa e Validação E2E).

## Estrutura do projeto

- `manage.py` — ponto de entrada do Django
- `config/` — configuração principal do projeto
- `core/` — app principal da aplicação
- `requirements.txt` — dependências do projeto

> **Banco de dados:** o projeto usa **PostgreSQL** em todos os ambientes, inclusive em desenvolvimento local (veja `.env.example`). Não há suporte a SQLite — o arquivo `db.sqlite3` que pode aparecer na raiz é apenas um artefato vazio e não é utilizado pela aplicação.

## Requisitos

- Python 3.10+
- pip
- virtualenv / venv
- PostgreSQL instalado e em execução
- Git (para clonar o repositório)
- pgAdmin 4 (opcional, para gerenciar o banco)


## Como rodar localmente

1. Clone o repositório
2. Entre na pasta do projeto
3. Crie e ative o ambiente virtual

```bash
python -m venv .venv
source .venv/Scripts/activate
```

4. Instale as dependências

```bash
pip install -r requirements.txt
```

5. Configure as variáveis de ambiente

Copie o arquivo `.env.example` para `.env` e preencha os valores conforme o seu ambiente.

```bash
copy .env.example .env
```

6. Execute as migrações

```bash
python manage.py migrate
```

7. Inicie o servidor

```bash
python manage.py runserver
```

A aplicação estará disponível em:

```text
http://127.0.0.1:8000/
```

## Observações

Este projeto ainda está em fase inicial de estruturação e configuração.

## Deploy no Render

O processo web deve aplicar as migrations antes de iniciar o Gunicorn. O
`render.yaml` já configura esse fluxo. Em um serviço criado manualmente no
Render, use o seguinte Start Command:

```bash
bash start.sh
```

No painel do serviço web, configure `DATABASE_URL` com a **Internal Database
URL** do PostgreSQL do Render. Não use `localhost` em `DB_HOST` no ambiente de
produção.
