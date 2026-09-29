# Textile cheat sheet (Redmine)

Redmine here uses Textile. Markdown renders as literal characters, so check every draft against this list.

| Need | Textile | Markdown (wrong here) |
|---|---|---|
| Heading | `h2. Title` (h1-h6, blank line after) | `## Title` |
| Bold | `*bold*` | `**bold**` |
| Italic | `_italic_` | `*italic*` |
| Inline code | `@code@` | `` `code` `` |
| Code block | `<pre>...</pre>` (or `<pre><code class="sql">...</code></pre>`) | ```` ``` ```` fence |
| Link | `"text":https://example.com` | `[text](url)` |
| Issue link | `#123` | - |
| Bullet list | `* item`, nested `** item` | `- item` |
| Numbered list | `# item`, nested `## item` | `1. item` |
| Table | `\|_. Head\|_. Head\|` then `\|a\|b\|` | `\| a \| b \|` with `---` row |
| Quote | `bq. text` | `> text` |
| Strike | `-text-` | `~~text~~` |

## Pitfalls

- Blank line before and after headings, lists, tables and `<pre>`; a list glued to the preceding paragraph
  is rendered as text.
- `*` and `#` list markers need a space after them. `**` at line start followed by a space is a nested
  bullet, not bold.
- Bold with `*...*` must hug the text: `*bold*`, not `* bold *`. It breaks when a word starts or ends with
  punctuation next to the asterisk; add a space or use `<strong>`.
- Inside `<pre>` and `@...@` nothing is interpreted. Text with `*`, `_`, `<`, `-` in identifiers
  (snake_case, `a-b`) should be in `@...@`, otherwise underscores turn into italics.
- A line starting with `#` followed by a space is a numbered item, even if you meant a number sign.
- Single newlines inside a paragraph become line breaks; separate paragraphs with a blank line.
- Table cells cannot contain newlines; keep them short or use a list instead.
- Escape literal markup by wrapping in `==...==` (no Textile) or `@...@`.
- Unicode dashes and «ёлочки» are fine. Straight quotes in link text can break `"text":url`; keep the link
  text free of double quotes.
