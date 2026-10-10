# tools

Small single-page browser tools, mostly built with the help of LLMs, in the
spirit of [simonw/tools](https://github.com/simonw/tools).

Published at **https://aceofaces.github.io/tools/**. The
[colophon](https://aceofaces.github.io/tools/colophon.html) lists each tool's
commit history.

## Tools

| Tool | What it does |
|---|---|
| [Recipe Card](https://aceofaces.github.io/tools/recipe-card.html) | Recipe URL in, Cooking for Engineers-style card out, with scaling and unit conversion |

## How it works

- Each tool is a self-contained `{slug}.html` plus a `{slug}.docs.md` with YAML
  front matter (`title`, `description`, `tags`).
- `build.py` (standard library only) builds `_site/`: the index, the
  colophon, `tools.json`, and a footer injected into every tool.
- `.github/workflows/pages.yml` deploys to GitHub Pages on every push to
  `main`. `.github/workflows/test.yml` validates front matter and runs the
  Playwright tests.

See [CLAUDE.md](CLAUDE.md) for the conventions to follow when adding a tool.

```bash
python build.py && python -m http.server -d _site 8000
pip install -e '.[test]' && pytest
```
