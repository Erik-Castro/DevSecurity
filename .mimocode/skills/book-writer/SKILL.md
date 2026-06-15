# Skill: book-writer

> Write a complete technical book for the DevSecurity series. Orchestrates chapter creation, actor delegation, quality gates, and publishing.

## When to Use

- User asks to "start writing Book N" or "write the next book"
- Creating a new book in the DevSecurity series (PT-BR technical books on software security)

## Workflow

### Phase 1: Setup

1. Create directory: `mkdir -p docs/<book-slug>/`
2. Decide chapter structure (18 chapters standard, `NN-slug-name.md` format)
3. Write `docs/<book-slug>/INDICE.md` with chapter list, dependency graph, reading paths, and CVE table

### Phase 2: Preface (inline)

Write `00-prefacio.md` inline via bash heredoc. Target 200-400 lines. Include:
- Why this book exists
- Target audience
- Prerequisites
- How to use the book
- Conventions (PT-BR prose, English code, no emojis)

### Phase 3: Chapters via Background Actors

Spawn background actors for ch01-ch17. Each actor prompt must include:
- Chapter number and title
- Target line count (MINIMUM 2800, ideally 3500+)
- Required CVEs (specific IDs)
- Required sections (Objetivos, Technical, Code, CVEs, Exercises, References)
- Language rules: ALL prose in PT-BR, code identifiers in English, no emojis
- Use `bash heredoc` for file writing (Write tool truncates at ~50KB)

**IMPORTANT: Do NOT pass `model` parameter to actors** — causes `ProviderModelGroupNotFoundError`.

### Phase 4: Monitor and Fix

1. Check actor status periodically: `actor({ operation: "status", actor_id: "..." })`
2. Actors stuck at `turnCount=0` for >5 minutes are dead — cancel them
3. Cancel dead actors: `actor({ operation: "cancel", actor_id: "..." })`
4. Write replacement chapters inline via bash heredoc
5. **NEVER rewrite a file that's above 800 lines** — actors may have produced more than expected

### Phase 5: Quality Gates

1. Verify all chapters exist: `ls docs/<book-slug>/*.md`
2. Check line counts: `wc -l docs/<book-slug>/*.md`
3. Any chapter below 800 lines → expand via `cat >> file << 'ENDOFFILE'` (append, don't overwrite)
4. Target: all chapters 2,800+ lines

### Phase 6: Jekyll Compatibility

1. Add front matter to all .md files (if not present):
   ```bash
   # For each .md without front matter:
   printf -- '---\nlayout: default\ntitle: "filename"\n---\n\n' | cat - file > tmp && mv tmp file
   ```
2. Run Liquid syntax fix: `python3 scripts/fix_liquid_syntax.py`
3. Verify: no unprotected `{{` outside code blocks

### Phase 7: Commit and Push

```bash
git add docs/<book-slug>/
git commit -m "feat(<slug>): add Book N - <Title>"
git remote set-url origin https://ghp_<TOKEN>@github.com/Erik-Castro/DevSecurity.git
git push origin master
git remote set-url origin https://github.com/Erik-Castro/DevSecurity.git
```

**ALWAYS clean token from remote URL after push.**

## Anti-Patterns (from 3 books of experience)

| Anti-Pattern | Why | Fix |
|-------------|-----|-----|
| Reading files before writing | Causes read-loop, negative progress | Write from scratch, never read first |
| Rewriting with Write tool | Truncates at ~50KB, produces shorter files | Use bash heredoc for large files |
| Passing `model` to actors | ProviderModelGroupNotFoundError | Never pass model param |
| Overwriting actor files above 800 lines | May truncate to less | Keep if above minimum |
| Not checking actor turnCount=0 | Stuck actors waste time | Cancel after 5min, rewrite inline |

## Actor Prompt Template

```
Write Chapter NN of Book N (<Title>) for DevSecurity project.

Write to docs/<book-slug>/NN-slug-name.md using bash heredoc:
```bash
cat > docs/<book-slug>/NN-slug-name.md << 'ENDOFFILE'
[content]
ENDOFFILE
```

ALL prose in PT-BR, code in English. Target MINIMUM 2800 lines. No emojis.

Title: <Chapter Title>

Sections:
1. Objetivos de Aprendizado
2-14. [Chapter-specific sections]
15. Exercises (5+)
16. References
```
