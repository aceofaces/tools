#!/usr/bin/env python3
"""Build the static site into _site/.

Each tool is {slug}.html plus {slug}.docs.md with YAML front matter.
Standard library only.

    python build.py            # build _site/
    python build.py --check    # validate front matter, don't build
"""

import argparse
import html
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "_site"
SITE_TITLE = "Tools"
REPO_URL = "https://github.com/aceofaces/tools"
# Generated pages; never treated as tools
RESERVED = {"index", "colophon"}
# Files and directories copied into the site as-is (besides tool pages)
STATIC = ["footer.js"]
REQUIRED_FIELDS = ("title", "description")


# --- Front matter ---------------------------------------------------------

def parse_scalar(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    if value.startswith("[") and value.endswith("]"):
        return [parse_scalar(v) for v in value[1:-1].split(",") if v.strip()]
    if value.lower() in ("true", "false"):
        return value.lower() == "true"
    return value


def parse_front_matter(text):
    """Parse a small YAML subset: `key: value`, `key: [a, b]` and `- item` lists."""
    match = re.match(r"^---\s*\n(.*?)\n---\s*(?:\n|$)(.*)", text, re.S)
    if not match:
        return {}, text
    meta, current = {}, None
    for line in match.group(1).splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        item = re.match(r"^\s+-\s+(.*)$", line)
        if item and current:
            if not isinstance(meta.get(current), list):
                meta[current] = []
            meta[current].append(parse_scalar(item.group(1)))
            continue
        pair = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if pair:
            current = pair.group(1)
            meta[current] = parse_scalar(pair.group(2)) if pair.group(2) else []
    return meta, match.group(2)


# --- Git history ----------------------------------------------------------

def git_log(path):
    """Commits touching path, newest first: [{hash, date, message}]."""
    try:
        out = subprocess.run(
            ["git", "log", "--follow", "--format=%H%x1f%aI%x1f%B%x1e", "--", path],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    commits = []
    for record in out.split("\x1e"):
        parts = record.strip().split("\x1f")
        if len(parts) == 3:
            commits.append({"hash": parts[0], "date": parts[1], "message": parts[2].strip()})
    return commits


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --- Tools ----------------------------------------------------------------

def find_tools():
    tools, errors = [], []
    for page in sorted(ROOT.glob("*.html")):
        slug = page.stem
        if slug in RESERVED:
            continue
        docs = ROOT / f"{slug}.docs.md"
        meta, body = ({}, "")
        if docs.exists():
            meta, body = parse_front_matter(docs.read_text(encoding="utf-8"))
        else:
            errors.append(f"{slug}: missing {docs.name}")
        for field in REQUIRED_FIELDS:
            if docs.exists() and not meta.get(field):
                errors.append(f"{slug}: front matter is missing '{field}'")
        tags = meta.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",") if t.strip()]
        commits = git_log(page.name)
        tools.append({
            "slug": slug,
            "url": f"{slug}.html",
            "title": meta.get("title") or slug.replace("-", " ").title(),
            "description": meta.get("description") or "",
            "tags": tags,
            "notes": body.strip(),
            "created": commits[-1]["date"] if commits else now_iso(),
            "updated": commits[0]["date"] if commits else now_iso(),
            "commits": commits,
        })
    tools.sort(key=lambda t: t["updated"], reverse=True)
    return tools, errors


# --- Pages ----------------------------------------------------------------

STYLE = """
:root { --bg:#fff; --fg:#1d1d1f; --muted:#6b6b70; --card:#f6f6f7; --border:#e2e2e6; --accent:#0b62d6; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#151517; --fg:#ececef; --muted:#9a9aa2; --card:#1f1f23; --border:#33333a; --accent:#6ea8ff; }
}
* { box-sizing: border-box; }
body { margin:0; background:var(--bg); color:var(--fg);
  font:16px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; }
main { max-width: 760px; margin: 0 auto; padding: 24px 16px 48px; }
h1 { font-size: 1.8rem; margin: 0 0 4px; }
a { color: var(--accent); }
.lede { color: var(--muted); margin: 0 0 20px; }
input[type=search] { width:100%; font-size:16px; padding:10px 12px; border-radius:8px;
  border:1px solid var(--border); background:var(--card); color:var(--fg); margin-bottom:16px; }
ul.tools { list-style:none; padding:0; margin:0; display:grid; gap:10px; }
ul.tools li { background:var(--card); border:1px solid var(--border); border-radius:10px; padding:12px 14px; }
ul.tools a.name { font-weight:600; font-size:1.05rem; text-decoration:none; }
ul.tools p { margin:4px 0 0; }
.meta { color:var(--muted); font-size:.85rem; margin-top:6px; }
.tag { display:inline-block; border:1px solid var(--border); border-radius:99px; padding:0 8px; margin-right:4px; }
.commit { margin: 8px 0 0 0; padding-left: 12px; border-left: 3px solid var(--border); }
.commit pre { white-space: pre-wrap; font: inherit; margin: 2px 0 0; }
"""


def page(title, body):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>{STYLE}</style>
</head>
<body>
<main>
{body}
</main>
</body>
</html>
"""


def fmt_date(iso):
    return iso[:10]


def build_index(tools):
    items = []
    for t in tools:
        tags = "".join(f'<span class="tag">{html.escape(tag)}</span>' for tag in t["tags"])
        search = " ".join([t["title"], t["description"], " ".join(t["tags"]), t["slug"]]).lower()
        items.append(
            f'<li data-search="{html.escape(search)}">'
            f'<a class="name" href="{t["url"]}">{html.escape(t["title"])}</a>'
            f'<p>{html.escape(t["description"])}</p>'
            f'<div class="meta">{tags}updated {fmt_date(t["updated"])}</div></li>'
        )
    body = f"""<h1>{SITE_TITLE}</h1>
<p class="lede">Small single-page browser tools, mostly built with the help of LLMs.
See the <a href="colophon.html">colophon</a> for how each one was made, or the
<a href="{REPO_URL}">source on GitHub</a>.</p>
<input type="search" id="q" placeholder="Search {len(tools)} tools" aria-label="Search tools">
<ul class="tools" id="list">
{chr(10).join(items)}
</ul>
<script>
const q = document.getElementById('q');
const items = [...document.querySelectorAll('#list li')];
function filter() {{
  const terms = q.value.toLowerCase().split(/\\s+/).filter(Boolean);
  for (const li of items) li.hidden = !terms.every(t => li.dataset.search.includes(t));
  history.replaceState(null, '', q.value ? '#' + encodeURIComponent(q.value) : location.pathname);
}}
q.addEventListener('input', filter);
if (location.hash) {{ q.value = decodeURIComponent(location.hash.slice(1)); filter(); }}
</script>"""
    return page(SITE_TITLE, body)


def build_colophon(tools):
    sections = []
    for t in tools:
        commits = "".join(
            f'<div class="commit"><a href="{REPO_URL}/commit/{c["hash"]}">{c["hash"][:7]}</a> '
            f'<span class="meta">{fmt_date(c["date"])}</span><pre>{linkify(c["message"])}</pre></div>'
            for c in t["commits"]
        )
        sections.append(
            f'<section id="{t["slug"]}"><h2><a href="{t["url"]}">{html.escape(t["title"])}</a></h2>'
            f'<p>{html.escape(t["description"])}</p>'
            f'<p class="meta"><a href="{REPO_URL}/blob/main/{t["url"]}">source</a> · '
            f'created {fmt_date(t["created"])} · updated {fmt_date(t["updated"])}</p>'
            f"{commits}</section>"
        )
    body = f"""<h1>Colophon</h1>
<p class="lede">Every tool, with the commit history that built it. <a href="index.html">All tools</a>.</p>
{chr(10).join(sections)}"""
    return page(f"Colophon · {SITE_TITLE}", body)


def linkify(text):
    escaped = html.escape(text)
    return re.sub(r"(https?://[^\s<]+)", r'<a href="\1">\1</a>', escaped)


def inject_footer(source):
    tag = '<script type="module" src="footer.js"></script>'
    if 'src="footer.js"' in source:
        return source
    idx = source.lower().rfind("</body>")
    if idx == -1:
        return source + "\n" + tag + "\n"
    return source[:idx] + tag + "\n" + source[idx:]


def build(tools):
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    for t in tools:
        source = (ROOT / t["url"]).read_text(encoding="utf-8")
        (OUT / t["url"]).write_text(inject_footer(source), encoding="utf-8")
    for name in STATIC:
        src = ROOT / name
        if src.is_dir():
            shutil.copytree(src, OUT / name)
        elif src.exists():
            shutil.copy2(src, OUT / name)
    (OUT / "index.html").write_text(build_index(tools), encoding="utf-8")
    (OUT / "colophon.html").write_text(build_colophon(tools), encoding="utf-8")
    public = [{k: t[k] for k in ("slug", "url", "title", "description", "tags", "created", "updated")} for t in tools]
    (OUT / "tools.json").write_text(json.dumps(public, indent=2), encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="validate front matter only")
    args = parser.parse_args()
    tools, errors = find_tools()
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if errors:
        sys.exit(1)
    if args.check:
        print(f"ok: {len(tools)} tools")
        return
    build(tools)
    print(f"built {len(tools)} tools into {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
