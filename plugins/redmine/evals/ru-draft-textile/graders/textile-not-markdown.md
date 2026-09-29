---
type: regex
pattern: '(\*\*\S|```(?!textile)|^#{2,} |\]\(http)'
flags: m
match: not_contains
target: {source: file, path: 4512-drafts.md}
---

The draft must be Textile: no markdown bold, no non-textile code fences, no "## " headings, no `[text](url)` links.
