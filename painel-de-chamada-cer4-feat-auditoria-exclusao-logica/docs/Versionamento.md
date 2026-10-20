# Guia de Contribuição

Oieeeeeeee, fiz esse guia de como trabalhar com branchs e commit semânticos .Para manter o desenvolvimento organizado, padronizado e fácil de acompanhar, seguimos algumas passos simples.

---

## Branches (Ramos)

Iremos adotar um fluxo de trabalho baseado em duas branches principais para garantir a estabilidade do código.

*   **`main`**: Contém o código de produção. É a versão estável que está (ou estará) disponível para os usuários. `Ninguém deve fazer commits diretamente nela.`
*   **`develop`**: É a branch de desenvolvimento. Todo o novo desenvolvimento (novas features, correções) é centralizado aqui.

**Regra:** Todo o trabalho deve ser feito em uma branch de suporte (feature, fix, etc.) criada a partir da `develop`.

### Padrão de Nomenclatura

Use o seguinte padrão para nomear suas branches, usando um prefixo que descreve o tipo de trabalho:

*   **`feat/<nome-da-funcionalidade>`**: Para adicionar uma nova funcionalidade.
    *   *Exemplo:* `feat/login-de-usuario`
*   **`fix/<descricao-da-correcao>`**: Para corrigir um bug.
    *   *Exemplo:* `fix/ajuste-layout-responsivo`
*   **`docs/<descricao-da-documentacao>`**: Para adicionar ou melhorar a documentação.
    *   *Exemplo:* `docs/atualiza-readme-setup`
*   **`refactor/<descricao-da-refatoracao>`**: Para refatorar código sem alterar a funcionalidade.
    *   *Exemplo:* `refactor/simplifica-funcao-de-calculo`

### Fluxo de Trabalho com Branches

1.  **Sincronize sua branch `develop` local:**
    ```bash
    git checkout develop
    git pull origin develop
    ```

2.  **Crie sua nova branch a partir da `develop`:**
    ```bash
    git checkout -b feat/minha-nova-funcionalidade
    ```

3.  **Trabalhe e faça seus commits** (siga a seção de Commits Semânticos abaixo).

4.  **Envie sua branch para o repositório remoto:**
    ```bash
    git push origin feat/minha-nova-funcionalidade
    ```

5.  **Pull Request (PR)** no GitHub, `Não faça o PR`, avise o responsável pelo repositório para que o código seja revisado e integrado.

---

## Commits Semânticos

Iremos utilizar o padrão **Conventional Commits** para escrever mensagens de commit claras e significativas. Isso nos ajuda a entender rapidamente o histórico de alterações e a automatizar a geração de changelogs.

### Estrutura do Commit

```
<tipo>: <descrição>
```

### Tipos de Commit Mais Comuns

*   **`feat`**: Adição de uma nova funcionalidade (`feature`).
*   **`fix`**: Correção de um erro (`bug fix`).
*   **`docs`**: Alterações apenas na documentação.
*   **`style`**: Ajustes de formatação, espaços em branco, etc., que não afetam a lógica do código.
*   **`refactor`**: Refatoração de código que não corrige um bug nem adiciona uma funcionalidade.
*   **`test`**: Adição ou correção de testes.
*   **`chore`**: Atualizações de tarefas de build, gerenciadores de pacotes, etc. (ex: `chore: atualiza dependencias no requirements.txt`).

### Exemplos de Bons Commits

```bash
# Ruim
git commit -m "ajustes"

# Bom
git commit -m "feat: adiciona sistema de autenticação com email e senha"

# Ruim
git commit -m "corrigi o bug do form"

# Bom
git commit -m "fix: impede envio de formulário de contato com email inválido"
```

Qualquer dúvida é só mandar mensagem. Para quem não está familiarizado indico fazer esse curso : https://youtube.com/playlist?list=PLcoYAcR89n-qbO7YAVj5S0alABLis_QVU&si=Q1NvbVOdtxXNP8yV 

Para consultar o conteúdo, meu caderno de Git e Github [Daniely] : https://app.notion.com/p/Git-e-Github-220f6ee9ba2b80eda633fa35eaf87343?source=copy_link 
