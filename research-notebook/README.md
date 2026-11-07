# Research Notebook Skill

Skill para manter um registro persistente de hipóteses, tentativas e resultados (`HYPOTHESES.md`) entre diferentes sessões e agentes.

- **Version**: `1.0.0`
- **Specification**: Agent Skills compatible

See [`SKILL.md`](./SKILL.md) for full instructions, specification, and agent workflow.

## Arquivos incluídos

```text
research-notebook/
├── README.md
├── SKILL.md
└── assets/
    ├── AGENTS.snippet.md
    └── HYPOTHESES.template.md
```

## Instalação e Uso

1. Instale a skill no diretório de skills do agente (por exemplo, `~/.agents/skills/research-notebook/` ou `.agents/skills/research-notebook/` no projeto).
2. Ao investigar um problema no repositório, o agente usará `<repository-root>/HYPOTHESES.md` como fonte única de verdade (criando-o a partir de [`assets/HYPOTHESES.template.md`](./assets/HYPOTHESES.template.md) caso ainda não exista, sem sobrescrever histórico existente).
3. Opcionalmente, adicione o conteúdo de [`assets/AGENTS.snippet.md`](./assets/AGENTS.snippet.md) ao `AGENTS.md` do repositório para reforçar o uso automático em futuras sessões.
