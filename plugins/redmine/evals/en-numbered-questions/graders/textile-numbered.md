---
type: regex
pattern: '^# \S'
flags: m
match: contains
target: {source: file, path: 650-drafts.md}
---

The question to the client must be a Textile numbered list ("# ..."), not markdown "1." items.
