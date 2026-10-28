# Pugotistatus

Barra de status para o **Codex CLI**, inspirada no [claude-code-statusline](https://github.com/Jhonatan-de-Souza/claude-code-statusline). Usa os indicadores nativos do Codex: modelo, projeto, branch Git, contexto restante, limite de 5 horas e limite semanal. Os valores vêm do próprio Codex; nenhum token ou credencial é lido por este projeto.

## Instalação

Requer Python 3.11+ e Codex CLI com suporte a `/statusline`.

```bash
python3 install.py --bars
```

O instalador altera somente `tui.status_line` em `~/.codex/config.toml`, preserva as demais opções e cria um backup antes da alteração. Instala também o comando `~/.local/bin/pugotistatus`.

**Para ver as barrinhas**, abra uma nova sessão de terminal com:

```bash
pugotistatus
```

Ele abre o Codex CLI e reserva uma linha inferior com barras coloridas de uso restante nas janelas de 5 horas e 7 dias. Os percentuais vêm de `account/rateLimits/read` do próprio Codex e são atualizados a cada 90 segundos. O contexto continua na barra nativa do Codex, que o conhece com precisão por conversa. Um limite indisponível aparece como `—`.

No Fish, o instalador também configura o comando interativo `codex` sem argumentos para abrir com as barras. Subcomandos e usos não interativos continuam chamando o executável original. Em Bash ou Zsh, use `pugotistatus` diretamente.

Exemplo de configuração instalada:

```toml
[tui]
status_line = ["model-with-reasoning", "project-name", "git-branch", "context-remaining", "five-hour-limit", "weekly-limit"]
```

O Codex omite indicadores sem dados disponíveis. Em terminais estreitos, a faixa visual encurta as barras. O recurso é do **terminal Codex CLI** e não modifica a interface gráfica ou a extensão do editor.

Para escolher outro arquivo de configuração:

```bash
python3 install.py --config /caminho/config.toml
```

Para reverter, copie o backup informado pelo instalador sobre `config.toml`. Se você mudou outras opções depois da instalação, remova somente a linha `status_line = [...]` em `[tui]`.

## Testes

```bash
python3 -m unittest discover -s tests -v
```

Referências: [configuração oficial do Codex](https://learn.chatgpt.com/docs/config-file/config-reference), [IDs da barra no código do Codex](https://github.com/openai/codex/blob/main/codex-rs/tui/src/bottom_pane/status_line_setup.rs).

## Licença

MIT. Consulte [LICENSE](LICENSE).
