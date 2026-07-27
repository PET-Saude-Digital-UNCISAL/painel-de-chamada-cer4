# Guia prático - Desenvolvimento isolado por tela

Este guia permite que 6 devs trabalhem em telas diferentes sem depender do fluxo completo da aplicação.

## 1) Rotas diretas por tela

Cada tela possui URL dedicada em `core/urls.py`.

Exemplos:
- `/telas/dev1/`
- `/telas/dev2/`
- `/telas/dev3/`
- `/telas/dev4/`
- `/telas/dev5/`
- `/telas/dev6/`

Uso prático:
1. Suba o servidor com `python manage.py runserver`.
2. Acesse a URL da sua tela diretamente.
3. Trabalhe no template/view da sua rota sem bloquear os outros devs.

## 2) Mocks e Test Data Builders

Estrutura criada em `core/dev_builders.py`:
- `ScreenDataBuilder`: builder puro em Python.
- `build_fake_screen_list()`: gera cards fake para listagem.
- `build_mocked_screen_payload()`: gera payload fake para uma tela.

Vantagem:
- Não precisa popular banco inteiro para começar a implementar layout e comportamento visual.

### factory_boy (opcional)

O projeto está preparado para usar `factory_boy` se você instalar:

```bash
pip install factory_boy
```

No endpoint de mock individual, você pode testar com factory via querystring:
- `/__dev__/mocks/telas/dev1/?factory=1`

## 3) Rotas ocultas somente em desenvolvimento

As rotas de dev só são registradas quando `DEBUG=True`.

Configuração em `config/urls.py`:
- Prefixo oculto: `/__dev__/`
- URLs:
  - `/__dev__/mocks/`
  - `/__dev__/mocks/telas/<slug>/`

Com `DEBUG=False`, essas rotas ficam inacessíveis (404).

## 4) Padrão Humble Object nas views

Princípio aplicado:
- Views só renderizam.
- Lógica de composição de dados vai para serviços/builders.

Onde está a lógica:
- `core/services.py`: contexto das telas de negócio.
- `core/dev_builders.py`: geração de mock data.

Onde a view fica "burra":
- `core/views.py` chama serviço/builder e faz `render()`.

## 5) Fluxo recomendado para o time

1. Cada dev trabalha na sua branch e na sua rota dedicada (`/telas/devX/`).
2. Para front-end sem dados reais, usar `/__dev__/mocks/`.
3. Validar testes antes de subir PR:

```bash
python manage.py test
python manage.py check
```

4. Quando integrar, mover regras consolidadas para serviços/modelos.

## 6) Arquivos principais criados/ajustados

- `config/urls.py`
- `core/urls.py`
- `core/dev_urls.py`
- `core/views.py`
- `core/services.py`
- `core/dev_builders.py`
- `core/tests.py`
- `core/templates/core/home.html`
- `core/templates/core/screen.html`
- `core/templates/core/dev_preview.html`
