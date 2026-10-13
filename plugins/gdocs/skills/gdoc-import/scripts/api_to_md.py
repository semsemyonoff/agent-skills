#!/usr/bin/env python3
"""Convert Google Docs/Sheets API JSON (Docs and Sheets MCP responses) to markdown.

  api_to_md.py doc   <read_doc.json> <out.md> [--images DIR --image-prefix NAME]
  api_to_md.py sheet <get_spreadsheet.json | get_values.json...> <out.md>

Input is either the raw API object or a saved MCP tool result wrapping it
(e.g. {"content": {...}}). Text is emitted verbatim, without markdown escaping:
clean_gdoc.py --source docs-api runs on the result afterwards.
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ORDERED = {'DECIMAL', 'ZERO_DECIMAL', 'ALPHA', 'UPPER_ALPHA', 'ROMAN', 'UPPER_ROMAN'}
MONO_FONTS = re.compile(r'mono|courier|consolas|menlo|code|inconsolata', re.I)
TOC_TITLE = re.compile(r'^(содержание|оглавление|contents|table of contents)$', re.I)
HEADINGS = {'TITLE': 1, 'SUBTITLE': 2, **{f'HEADING_{n}': n for n in range(1, 7)}}


def load(path, key):
    found = find(json.loads(Path(path).read_text()), key)
    if found is None:
        sys.exit(f'{path}: no "{key}" object found — not a Docs/Sheets API response?')
    return found


def find(data, key):
    """First dict holding `key` (breadth-first), unwrapping MCP result envelopes."""
    stack = [data]
    while stack:
        node = stack.pop(0)
        if isinstance(node, dict):
            if key in node:
                return node
            stack.extend(node.values())
        elif isinstance(node, str) and node.lstrip().startswith('{'):
            try:
                stack.append(json.loads(node))
            except json.JSONDecodeError:
                pass
    return None


# --- Docs -------------------------------------------------------------------

class Images:
    """Numbers images across tabs; downloads them when a directory is given."""
    EXT = {'image/png': 'png', 'image/jpeg': 'jpg', 'image/gif': 'gif', 'image/webp': 'webp'}

    def __init__(self, directory, prefix):
        self.dir, self.prefix = directory, prefix
        self.count = self.saved = 0

    def add(self, emb):
        self.count += 1
        label = emb.get('title') or emb.get('description') or f'image {self.count}'
        uri = emb.get('imageProperties', {}).get('contentUri')
        if not self.dir or not uri:
            return f'[{label}]'
        try:
            # contentUri is a short-lived signed URL: download right after read_doc
            with urllib.request.urlopen(uri, timeout=30) as resp:
                ext = self.EXT.get(resp.headers.get_content_type(), 'img')
                data = resp.read()
        except (urllib.error.URLError, TimeoutError) as e:
            print(f'  ! image {self.count} not downloaded: {e}', file=sys.stderr)
            return f'[{label}]'
        self.dir.mkdir(parents=True, exist_ok=True)
        name = f'{self.prefix}-{self.count}.{ext}'
        (self.dir / name).write_bytes(data)
        self.saved += 1
        return f'![{label}]({self.dir.name}/{name})'


class Doc:
    def __init__(self, tab, shift, images):
        self.lists = tab.get('lists', {})
        self.inline_objects = tab.get('inlineObjects', {})
        self.footnotes = tab.get('footnotes', {})
        self.footnote_refs = []
        self.shift = shift
        self.images = images

    def is_mono(self, style):
        family = (style.get('weightedFontFamily') or {}).get('fontFamily', '')
        return bool(MONO_FONTS.search(family))

    def run_text(self, el, plain):
        """Return (text, style) for one paragraph element; style None = no formatting."""
        if 'textRun' in el:
            run = el['textRun']
            if run.get('suggestedInsertionIds'):
                return '', None  # snapshot keeps the accepted text only
            return run.get('content', ''), run.get('textStyle', {})
        if 'inlineObjectElement' in el:
            obj = self.inline_objects.get(el['inlineObjectElement'].get('inlineObjectId'), {})
            return self.images.add(obj.get('inlineObjectProperties', {}).get('embeddedObject', {})), None
        if 'footnoteReference' in el:
            ref = el['footnoteReference']
            self.footnote_refs.append(ref)
            return f'[^{ref.get("footnoteNumber", len(self.footnote_refs))}]', None
        if 'person' in el:
            p = el['person'].get('personProperties', {})
            return p.get('name') or p.get('email', ''), None
        if 'richLink' in el:
            p = el['richLink'].get('richLinkProperties', {})
            title, uri = p.get('title', ''), p.get('uri', '')
            return (title if plain or not uri else f'[{title or uri}]({uri})'), None
        if 'dateElement' in el:
            p = el['dateElement'].get('dateElementProperties', {})
            return p.get('displayText') or p.get('timestamp', ''), None
        if 'horizontalRule' in el:
            return '\n---\n', None
        if 'equation' in el:
            return '[equation]', None
        return '', None  # pageBreak, columnBreak, autoText (page numbers)

    def inline(self, elements, plain=False):
        """Paragraph elements -> markdown text. plain=True drops formatting (headings)."""
        spans = []  # [text, key, url]
        for el in elements:
            text, style = self.run_text(el, plain)
            if not text:
                continue
            key, url = (), None
            if style is not None and not plain:
                url = (style.get('link') or {}).get('url')
                key = tuple(k for k, on in (('code', self.is_mono(style)),
                                            ('b', style.get('bold')),
                                            ('i', style.get('italic')),
                                            ('s', style.get('strikethrough'))) if on)
            if spans and spans[-1][1] == key and spans[-1][2] == url:
                spans[-1][0] += text
            else:
                spans.append([text, key, url])
        out = []
        for text, key, url in spans:
            out.append(wrap(text, key, url))
        return ''.join(out).replace('\x0b', '\n').rstrip('\n')

    def paragraph_is_code(self, p):
        runs = [e['textRun'] for e in p.get('elements', []) if 'textRun' in e]
        text = ''.join(r.get('content', '') for r in runs)
        return bool(text.strip()) and all(
            self.is_mono(r.get('textStyle', {})) for r in runs if r.get('content', '').strip())

    def code_text(self, p):
        return ''.join(e['textRun'].get('content', '') for e in p.get('elements', [])
                       if 'textRun' in e and not e['textRun'].get('suggestedInsertionIds')
                       ).replace('\x0b', '\n').rstrip('\n')

    def list_marker(self, bullet):
        level = bullet.get('nestingLevel', 0)
        levels = (self.lists.get(bullet.get('listId'), {})
                  .get('listProperties', {}).get('nestingLevels', []))
        glyph = levels[level].get('glyphType') if level < len(levels) else None
        return '   ' * level + ('1. ' if glyph in ORDERED else '- ')

    def blocks(self, content):
        """Structural elements -> list of (kind, text). kind: para|list|code|raw."""
        out = []
        for el in content:
            if 'paragraph' in el:
                p = el['paragraph']
                style = p.get('paragraphStyle', {}).get('namedStyleType', 'NORMAL_TEXT')
                if style in HEADINGS:
                    elements = p.get('elements', [])
                    images = [e for e in elements if 'inlineObjectElement' in e]
                    if images:  # a logo in a title line is not part of the heading
                        out.append(('para', self.inline(images)))
                    text = self.inline([e for e in elements if e not in images], plain=True).strip()
                    if text:
                        level = min(HEADINGS[style] + self.shift, 6)
                        out.append(('para', '#' * level + ' ' + text.replace('\n', ' ')))
                elif 'bullet' in p:
                    text = self.inline(p.get('elements', [])).strip()
                    if text:
                        out.append(('list', self.list_marker(p['bullet']) + text))
                elif self.paragraph_is_code(p):
                    out.append(('code', self.code_text(p)))
                else:
                    text = self.inline(p.get('elements', []))
                    if text.strip():
                        out.append(('para', '\n'.join(l.rstrip() for l in text.split('\n'))))
            elif 'table' in el:
                out.extend(self.table(el['table']))
            elif 'tableOfContents' in el:
                # drop the TOC's own title paragraph; clean_gdoc.py writes a fresh TOC here
                if out and out[-1][0] == 'para' and TOC_TITLE.match(
                        out[-1][1].lstrip('#').strip().strip('*')):
                    out.pop()
                out.append(('raw', '<!-- TOC -->'))
        return out

    def table(self, table):
        rows = table.get('tableRows', [])
        if len(rows) == 1 and len(rows[0].get('tableCells', [])) == 1:
            # one-cell table is a layout box (callout, code block): unwrap it
            return self.blocks(rows[0]['tableCells'][0].get('content', []))
        grid = [[self.cell(c) for c in r.get('tableCells', [])] for r in rows]
        width = max((len(r) for r in grid), default=0)
        if not width:
            return []
        grid = [r + [''] * (width - len(r)) for r in grid]
        # header cells are bold already; a bold run spanning the whole cell is just noise
        grid[0] = [re.sub(r'^\*\*([^*]+)\*\*$', r'\1', c) for c in grid[0]]
        lines = [md_row(grid[0]), '|' + ' --- |' * width] + [md_row(r) for r in grid[1:]]
        return [('raw', '\n'.join(lines))]

    def cell(self, cell):
        parts = []
        for kind, text in self.blocks(cell.get('content', [])):
            parts.append(f'`{text}`' if kind == 'code' and '\n' not in text else text)
        return '<br>'.join(p.replace('\n', '<br>') for p in parts)

    def footnote_lines(self):
        lines = []
        for ref in self.footnote_refs:
            note = self.footnotes.get(ref.get('footnoteId'), {})
            text = ' '.join(t for _, t in self.blocks(note.get('content', [])))
            lines.append(f'[^{ref.get("footnoteNumber", "?")}]: {text}')
        return lines


def wrap(text, key, url):
    """Apply markers around the non-blank core so spaces stay outside them."""
    m = re.match(r'^(\s*)(.*?)(\s*)$', text, re.S)
    lead, core, trail = m.groups()
    if not core:
        return text
    if 'code' in key:
        tick = '``' if '`' in core else '`'
        core = f'{tick}{core}{tick}'
    for k, mark in (('i', '*'), ('b', '**'), ('s', '~~')):
        if k in key:
            core = f'{mark}{core}{mark}'
    return lead + link(core, url) + trail


def link(text, url):
    """Markdown link, except autolinks whose text already is the address (divan.ru, https://…)."""
    if not url or not text.strip():
        return text
    bare = re.sub(r'^(https?://|mailto:)', '', url).rstrip('/')
    if bare == re.sub(r'^(https?://|mailto:)', '', text.strip()).rstrip('/'):
        return text
    return f'[{text}]({url})'


def md_row(cells):
    return '| ' + ' | '.join(c.replace('|', '\\|').strip() for c in cells) + ' |'


def render(blocks):
    """Paragraphs are separated by blank lines; consecutive list items and code lines group."""
    groups = []
    for kind, text in blocks:
        if groups and kind == groups[-1][0] and kind in ('code', 'list'):
            groups[-1][1] += '\n' + text
        else:
            groups.append([kind, text])
    out = []
    for kind, text in groups:
        if kind == 'code':
            fence = '```json' if is_json(text) else '```'
            text = f'{fence}\n{text}\n```'
        out.append(text)
    return '\n\n'.join(out)


def is_json(text):
    if not text.lstrip().startswith(('{', '[')):
        return False
    try:
        json.loads(text)
        return True
    except json.JSONDecodeError:
        return False


def walk_tabs(tabs, depth=0):
    for tab in tabs:
        yield tab, depth
        yield from walk_tabs(tab.get('childTabs', []), depth + 1)


def convert_doc(src, dst, images_dir=None, image_prefix='image'):
    doc = load(src, 'tabs')
    tabs = list(walk_tabs(doc['tabs']))
    multi = len(tabs) > 1
    parts = []
    images = Images(Path(images_dir) if images_dir else None, image_prefix)
    for tab, depth in tabs:
        body = tab.get('documentTab', {})
        d = Doc(body, shift=depth + 1 if multi else 0, images=images)
        blocks = d.blocks(body.get('body', {}).get('content', []))
        if multi:
            title = tab.get('tabProperties', {}).get('title', '')
            blocks.insert(0, ('para', '#' * min(depth + 1, 6) + ' ' + title))
        text = render(blocks)
        if d.footnote_refs:
            text += '\n\n' + '\n'.join(d.footnote_lines())
        parts.append(text)
    Path(dst).write_text('\n\n'.join(parts).strip() + '\n')
    saved = f', {images.saved} saved to {images.dir}' if images.dir else ''
    print(f'{src}: "{doc.get("title", "")}", {len(tabs)} tab(s), {images.count} image(s){saved} -> {dst}')


# --- Sheets -----------------------------------------------------------------

def sheet_title(rng):
    name = rng.rsplit('!', 1)[0] if '!' in rng else rng
    return name.strip("'").replace("''", "'")


def cell_md(cell):
    """Grid cell -> text with links from hyperlink, smart chips and link runs."""
    text = cell.get('formattedValue', '')
    if not text:
        return ''
    if cell.get('hyperlink'):
        return link(text, cell['hyperlink'])
    runs = {}  # start index -> url or None; a later run ends the previous one
    for r in cell.get('textFormatRuns', []):
        runs[r.get('startIndex', 0)] = r.get('format', {}).get('link', {}).get('uri')
    for r in cell.get('chipRuns', []):
        chip = r.get('chip', {})
        runs[r.get('startIndex', 0)] = (chip.get('richLinkProperties', {}).get('uri')
                                        or runs.get(r.get('startIndex', 0)))
    if not any(runs.values()):
        return text
    starts = sorted(runs)
    out = text[:starts[0]]
    for i, start in enumerate(starts):
        end = starts[i + 1] if i + 1 < len(starts) else len(text)
        out += link(text[start:end], runs[start])
    return out


def grid_rows(sheet):
    rows = []
    for block in sheet.get('data', []):
        r0, c0 = block.get('startRow', 0), block.get('startColumn', 0)
        for i, row in enumerate(block.get('rowData', [])):
            while len(rows) <= r0 + i:
                rows.append([])
            cells = rows[r0 + i]
            for j, cell in enumerate(row.get('values', [])):
                while len(cells) <= c0 + j:
                    cells.append('')
                cells[c0 + j] = cell_md(cell)
    return rows


def table_md(title, rows):
    rows = [[c.strip() for c in r] for r in rows]
    while rows and not any(rows[-1]):
        rows.pop()
    width = max((len(r) for r in rows), default=0)
    while width and not any(len(r) >= width and r[width - 1] for r in rows):
        width -= 1
    if not width:
        return f'## {title}\n\n(empty)', 0, 0
    rows = [(r + [''] * width)[:width] for r in rows]
    keep = [j for j in range(width) if any(r[j] for r in rows)]  # drop spacer columns
    rows = [[r[j] for j in keep] for r in rows]
    width = len(keep)
    if width == 1:  # a notes sheet, not a table
        return f'## {title}\n\n' + '\n\n'.join(r[0] for r in rows if r[0]), len(rows), 1
    cells = [[c.replace('\n', '<br>') for c in r] for r in rows]
    table = [md_row(cells[0]), '|' + ' --- |' * width] + [md_row(r) for r in cells[1:]]
    return f'## {title}\n\n' + '\n'.join(table), len(rows), width


def convert_sheets(srcs, dst):
    sheets = []  # (title, rows)
    for src in srcs:
        data = json.loads(Path(src).read_text())
        spreadsheet = find(data, 'sheets')
        if spreadsheet is None:
            vr = find(data, 'values')
            if vr is None:
                sys.exit(f'{src}: neither a spreadsheet nor a values range')
            sheets.append((sheet_title(vr.get('range', src)),
                           [[str(v) for v in r] for r in vr.get('values', [])]))
            continue
        for sheet in spreadsheet['sheets']:
            if 'data' not in sheet:
                sys.exit(f'{src}: no grid data — call get_spreadsheet with includeGridData=true')
            sheets.append((sheet.get('properties', {}).get('title', ''), grid_rows(sheet)))
    parts = []
    for title, rows in sheets:
        text, n, width = table_md(title, rows)
        parts.append(text)
        print(f'sheet "{title}": {n} rows x {width} cols')
    Path(dst).write_text('\n\n'.join(parts) + '\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)
    d = sub.add_parser('doc', help='Docs read_doc response -> markdown')
    d.add_argument('src')
    d.add_argument('dst')
    d.add_argument('--images', help='download images here (link uses the directory name)')
    d.add_argument('--image-prefix', default='image', help='image file name prefix')
    s = sub.add_parser('sheet', help='Sheets get_spreadsheet (grid data) or get_values responses -> markdown')
    s.add_argument('srcs', nargs='+')
    s.add_argument('dst')
    a = p.parse_args()
    if a.cmd == 'doc':
        convert_doc(a.src, a.dst, a.images, a.image_prefix)
    else:
        convert_sheets(a.srcs, a.dst)
