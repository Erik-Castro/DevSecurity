# Command: liquid-fix

> Fix Liquid syntax errors in Markdown files for GitHub Pages compatibility.

## Usage

Run from project root to scan and fix all `.md` files for Jekyll/Liquid compatibility.

## What It Does

1. Adds front matter (`layout: default`) to files missing it
2. Wraps `{{ }}` and `{% %}` inside code blocks with `{% raw %}{% endraw %}`
3. Verifies all raw/endraw tags are balanced and outside code blocks

## Execution

```bash
# Step 1: Add front matter to files missing it
for f in $(find docs/ -name "*.md" -not -path "*/logs_*"); do
  first=$(head -1 "$f")
  if [[ "$first" != "---" ]]; then
    basename=$(basename "$f" .md)
    tmpfile=$(mktemp)
    printf -- '---\nlayout: default\ntitle: "%s"\n---\n\n' "$basename" > "$tmpfile"
    cat "$f" >> "$tmpfile"
    mv "$tmpfile" "$f"
  fi
done

# Step 2: Fix Liquid syntax in code blocks
python3 scripts/fix_liquid_syntax.py

# Step 3: Verify
python3 -c "
import os
dirs = ['docs/book', 'docs/devsecops', 'docs/malware', 'docs/concurrency', 'docs/cryptography', 'docs/web']
for d in dirs:
    if not os.path.isdir(d): continue
    for f in sorted(os.listdir(d)):
        if not f.endswith('.md'): continue
        with open(os.path.join(d, f)) as fh:
            c = fh.read()
        r = c.count('{% raw %}')
        e = c.count('{% endraw %}')
        if r != e:
            print(f'UNBALANCED: {d}/{f} raw={r} endraw={e}')
print('Verification complete')
"
```

## When to Run

- After writing new book chapters containing `{{ }}` (C++ templates, GitHub Actions, Jinja2)
- After any mass-edit of markdown files
- Before first GitHub Pages build of a new book
