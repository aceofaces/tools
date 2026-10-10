# Tools repo: conventions for building tools

This repo is a collection of small, single-page browser tools, in the style of
[simonw/tools](https://github.com/simonw/tools). It is published to GitHub Pages
by `.github/workflows/pages.yml`.

## Adding a tool

Every tool is two files in the repo root:

- `{slug}.html`: the tool itself
- `{slug}.docs.md`: YAML front matter plus an optional longer write-up

The slug is lowercase and hyphenated, for example `recipe-card`.

### `{slug}.html` rules

- **One self-contained file.** Inline `<style>` and `<script>`. No build step,
  no bundler, no React/JSX.
- **Dependencies come from a CDN with an exact pinned version**, e.g.
  `https://cdn.jsdelivr.net/npm/parse-ingredient@2.2.0/dist/...`. Prefer
  cdn.jsdelivr.net or cdnjs.cloudflare.com. Never use an unversioned URL.
- **Mobile first.** Viewport meta tag, `max-width` container, 16px inputs (so
  iOS doesn't zoom), no horizontal page scroll except inside wide tables.
- **Light and dark mode** via CSS custom properties and
  `prefers-color-scheme`.
- **Shareable state.** When a tool takes input that fits in a URL, read it from
  and write it to the query string or `#hash` so links reproduce the result.
- **`localStorage`** only for per-user conveniences (last-used settings), and
  always inside `try/catch`.
- **Fail visibly.** Show errors in the page, not only in the console.
- Include a `<title>` and a short `<h1>`. Don't add a site header or footer;
  `footer.js` is injected at build time.
- Don't hardcode secrets. If a tool needs an API key, ask the user for it and
  keep it in `localStorage`.

### `{slug}.docs.md` front matter

```markdown
---
title: Recipe Card
description: One sentence, starting with a verb, saying what the tool does.
tags: [cooking, parsing]
---

Optional longer markdown notes: how it works, limitations, credits.
```

`title` and `description` are required. `python build.py --check` fails when
either is missing, and CI runs it on every push.

## Building locally

```bash
python build.py          # writes the site to _site/
python -m http.server -d _site 8000
```

`build.py` uses only the Python standard library. It reads front matter and git
history (for created/updated dates and the colophon) and injects `footer.js`.

## Tests

Browser tests live in `tests/` and use pytest-playwright:

```bash
pip install -e '.[test]'
pytest
```

Not every tool needs tests. Add them when a tool has logic (parsing,
conversions) that's easy to break.

## Commits

Write commit messages that say what the tool does or what changed. They're
shown on the colophon page next to each tool.
