# Painel de Chamada CER4

## Estrutura do projeto

- `manage.py` — ponto de entrada do Django
- `config/` — configuração principal do projeto
- `core/` — app principal da aplicação
- `db.sqlite3` — banco de dados local de desenvolvimento
- `requirements.txt` — dependências do projeto

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
