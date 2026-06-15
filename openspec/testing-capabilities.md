## Testing Capabilities

**Strict TDD Mode**: disabled
**Detected**: 2026-06-15

### Test Runner

- Command: none
- Framework: none (pure Markdown book project)

### Test Layers

| Layer       | Available | Tool        |
| ----------- | --------- | ----------- |
| Unit        | ❌        | —           |
| Integration | ❌        | —           |
| E2E         | ❌        | —           |

### Coverage

- Available: ❌
- Command: —

### Quality Tools

| Tool         | Available | Command        |
| ------------ | --------- | -------------- |
| Linter       | ❌        | —              |
| Type checker | ❌        | —              |
| Formatter    | ❌        | —              |

### Quality Gates (Project-Specific)

| Gate              | Command / Rule                          |
| ----------------- | --------------------------------------- |
| Min lines/chapter | 800 (hard gate)                         |
| Target lines      | 2800-3900                               |
| Prose language    | PT-BR                                   |
| Code language     | English                                 |
| CVE documentation | Required per chapter                    |
| Index file        | INDICE.md per book directory            |

### Notes

This is a book-writing project, not a code project. Quality is validated by:
- Line count per chapter (min 800, target 2800-3900)
- Prose review for PT-BR correctness
- Code compilation verification (manual, not automated)
- CVE accuracy and documentation completeness
