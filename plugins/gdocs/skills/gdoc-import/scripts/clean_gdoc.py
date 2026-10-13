#!/usr/bin/env python3
"""Cleanup of Google-Docs-exported markdown: tables, JSON blocks, auto-TOC."""
import json
import re
import sys
from pathlib import Path

UNESCAPE = re.compile(r'\\([\\_*#\-.\[\]<>|~`])')


def unescape(s, passes=1):
    """passes=2 для текста и таблиц: конвертер местами экранирует дважды (`\\\\\\*`).
    Для JSON строго один проход — там `\\\\\\\\` значит валидный JSON-escape `\\\\`."""
    for _ in range(passes):
        s = UNESCAPE.sub(r'\1', s)
    return s


SEP = re.compile(r'^\|(\s*:?-+:?\s*\|)+\s*$')
EMPTY_ROW = re.compile(r'^\|(\s+\|)+\s*$')


def fix_tables(lines):
    out = []
    i = 0
    while i < len(lines):
        if (EMPTY_ROW.match(lines[i]) and i + 2 < len(lines)
                and SEP.match(lines[i + 1]) and lines[i + 2].startswith('|')):
            out.append(unescape(lines[i + 2], 2))   # real header
            out.append(lines[i + 1])             # separator
            i += 3
            continue
        if lines[i].startswith('|'):
            out.append(unescape(lines[i], 2))
            i += 1
            continue
        out.append(lines[i])
        i += 1
    return out


FENCE = re.compile(r'^```(\w*)\s*$')


def find_json_blocks(lines, passes=1):
    """Yield (start, end_exclusive, parsed_obj, cleaned_lines)."""
    i = 0
    n = len(lines)
    while i < n:
        fence = FENCE.match(lines[i])
        if fence:
            j = next((k for k in range(i + 1, n) if lines[k].strip() == '```'), n)
            if fence.group(1) in ('', 'json'):
                try:
                    obj = json.loads('\n'.join(lines[i + 1:j]))
                    if isinstance(obj, (dict, list)):
                        yield (i, j + 1, obj, lines[i + 1:j])
                except json.JSONDecodeError:
                    if fence.group(1) == 'json':
                        print(f'  ! JSON parse failed at line {i+1}', file=sys.stderr)
            i = j + 1
            continue
        if lines[i].strip() in ('{', '['):
            depth = 0
            collected = []
            j = i
            ok = False
            while j < n:
                raw = lines[j]
                stripped = raw.strip()
                if stripped:
                    collected.append(unescape(raw.rstrip(), passes))
                    depth += stripped.count('{') + stripped.count('[')
                    depth -= stripped.count('}') + stripped.count(']')
                    if depth <= 0:
                        ok = True
                        break
                elif depth == 0:
                    break
                j += 1
            if ok:
                text = '\n'.join(collected)
                try:
                    obj = json.loads(text)
                except json.JSONDecodeError as e:
                    print(f'  ! JSON parse failed at line {i+1}: {e}', file=sys.stderr)
                    i = j + 1
                    continue
                yield (i, j + 1, obj, collected)
                i = j + 1
                continue
        i += 1


def latin_slug(s):
    words = re.findall(r'[A-Za-z][A-Za-z0-9]+', s)
    return '-'.join(w.lower() for w in words) or 'block'


def drop_auto_toc(lines):
    """Remove the Google-generated TOC (heading 'Содержание' + link-only lines)."""
    out = []
    i = 0
    done = False
    while i < len(lines):
        if not done and re.match(r'^#+\s*\*{0,2}Содержание\*{0,2}\s*$', lines[i]):
            done = True
            i += 1
            while i < len(lines) and (not lines[i].strip() or lines[i].lstrip().startswith('[')):
                i += 1
            out.append('<!-- TOC -->')
            continue
        out.append(lines[i])
        i += 1
    return out


def heading_text(line):
    return re.sub(r'\*+', '', line.lstrip('#').strip())


def insert_toc(lines):
    toc = ['## Содержание', '']
    for l in lines:
        m = re.match(r'^(#{1,3})\s+(.*\S)', l)
        if not m or heading_text(l).lower() == 'содержание':
            continue
        level = len(m.group(1))
        toc.append('  ' * (level - 1) + '- ' + heading_text(l))
    toc.append('')
    if '<!-- TOC -->' in lines:
        idx = lines.index('<!-- TOC -->')
        lines[idx:idx + 1] = toc
    return lines


def process(path, out_md, examples_dir, big=40, header='', source='drive'):
    lines = Path(path).read_text().split('\n')
    # api_to_md.py output is verbatim text with well-formed tables: nothing to unescape
    raw = source == 'docs-api'
    if not raw:
        lines = fix_tables(lines)

    blocks = list(find_json_blocks(lines, passes=0 if raw else 1))
    print(f'{path}: {len(blocks)} json blocks')

    # section name for each block = nearest preceding heading with latin words
    replacements = []
    used = {}
    for start, end, obj, collected in blocks:
        sect = ''
        for k in range(start, -1, -1):
            if re.match(r'^##\s', lines[k]):
                num = re.search(r'(\d+(?:\.\d+)*)', lines[k])
                prefix = num.group(1).replace('.', '-') if num else ''
                sect = '-'.join(p for p in (prefix, latin_slug(lines[k])) if p)
                break
        pretty = json.dumps(obj, ensure_ascii=False, indent=2)
        nlines = pretty.count('\n') + 1
        if nlines >= big and examples_dir:
            base = sect or 'example'
            used[base] = used.get(base, 0) + 1
            name = base if used[base] == 1 else f'{base}-{used[base]}'
            fp = examples_dir / f'{name}.json'
            fp.write_text(pretty + '\n')
            rel = f'{examples_dir.name}/{fp.name}'
            body = [f'Полный JSON вынесен в файл: [`{rel}`]({rel}) — {nlines} строк.']
            print(f'  -> {rel} ({nlines} lines)')
        else:
            body = ['```json'] + pretty.split('\n') + ['```']
        replacements.append((start, end, body))

    for start, end, body in reversed(replacements):
        lines[start:end] = body

    lines = ['' if not l.strip() else l for l in lines]
    lines = [l for l in lines if not re.match(r'^#+\s*$', l)]
    lines = drop_auto_toc(lines)
    lines = insert_toc(lines)

    # collapse 3+ blank lines
    text = '\n'.join(lines)
    text = re.sub(r'\n{3,}', '\n\n', text)
    Path(out_md).write_text(header + text.strip() + '\n')


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('src')
    p.add_argument('dst')
    p.add_argument('--examples', help='directory for extracted large JSON blocks')
    p.add_argument('--header', default='', help='text prepended to the result')
    p.add_argument('--source', choices=('drive', 'docs-api'), default='drive',
                   help='drive: Drive read_file_content markdown; docs-api: api_to_md.py output')
    a = p.parse_args()
    ex = Path(a.examples) if a.examples else None
    if ex:
        ex.mkdir(parents=True, exist_ok=True)
    process(a.src, a.dst, ex, header=(a.header + '\n\n' if a.header else ''), source=a.source)
