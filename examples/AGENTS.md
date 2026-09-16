# Terminal context

When you begin a meaningful task in an interactive terminal, run:

```sh
context-tabs set --task "Short human task name" --state working --tool Codex
```

Use `--state waiting` only when input or an external event is genuinely needed,
and `--state done` when the named task is complete. Do not put secrets, customer
names, ticket contents, or private paths in a visible task label.
