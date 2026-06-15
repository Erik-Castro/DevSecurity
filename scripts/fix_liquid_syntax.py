#!/usr/bin/env python3
"""Wrap {{ }} inside markdown code blocks with {% raw %}{% endraw %} for Jekyll/Liquid compatibility."""
import os
import sys

def fix_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '{{' not in content and '{% ' not in content:
        return False
    
    # Step 1: Remove ALL existing raw/endraw tags
    for tag in ['{% raw %}\n', '{% endraw %}\n', '\n{% raw %}', '\n{% endraw %}', '{% raw %}', '{% endraw %}']:
        content = content.replace(tag, '')
    
    # Step 2: Find code blocks containing {{ or {% and wrap them
    lines = content.split('\n')
    result = []
    i = 0
    code_fence_count = 0
    
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        
        if stripped.startswith('```'):
            code_fence_count += 1
            is_opening = (code_fence_count % 2 == 1)
            
            if is_opening:
                code_block = [line]
                j = i + 1
                while j < len(lines):
                    if lines[j].strip().startswith('```'):
                        code_block.append(lines[j])
                        break
                    code_block.append(lines[j])
                    j += 1
                
                code_content = '\n'.join(code_block)
                if '{{' in code_content or '{% ' in code_content:
                    result.append('{% raw %}')
                    result.extend(code_block)
                    result.append('{% endraw %}')
                else:
                    result.extend(code_block)
                i = j + 1
            else:
                result.append(line)
                i += 1
        else:
            result.append(line)
            i += 1
    
    new_content = '\n'.join(result)
    
    # Ensure front matter
    if not new_content.startswith('---'):
        basename = os.path.basename(filepath).replace('.md', '')
        new_content = f'---\nlayout: default\ntitle: "{basename}"\n---\n\n' + new_content
    
    if new_content != content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

def main():
    root = '/home/Projetos/DevSecurity'
    dirs = ['docs/book', 'docs/devsecops', 'docs/malware', 'docs/concurrency', 'docs/cryptography', 'docs/web']
    fixed = 0
    
    for d in dirs:
        dirpath = os.path.join(root, d)
        if not os.path.isdir(dirpath):
            continue
        for fname in sorted(os.listdir(dirpath)):
            if not fname.endswith('.md'):
                continue
            fpath = os.path.join(dirpath, fname)
            if fix_file(fpath):
                print(f'Fixed: {d}/{fname}')
                fixed += 1
    
    # Verify balance
    issues = 0
    for d in dirs:
        dirpath = os.path.join(root, d)
        if not os.path.isdir(dirpath):
            continue
        for fname in sorted(os.listdir(dirpath)):
            if not fname.endswith('.md'):
                continue
            with open(os.path.join(dirpath, fname)) as fh:
                c = fh.read()
            r = c.count('{% raw %}')
            e = c.count('{% endraw %}')
            if r != e:
                print(f'UNBALANCED: {d}/{fname} raw={r} endraw={e}')
                issues += 1
    
    print(f'\nFixed {fixed} files, {issues} balance issues')

if __name__ == '__main__':
    main()
