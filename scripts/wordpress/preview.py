#!/usr/bin/env python3
"""
Local preview for blog posts.

Renders a .md or .qmd file to self-contained HTML and opens it in the default
browser. Uses the same convert_markdown_to_html pipeline as publish.py, so
Prism.js directives, Mermaid blocks, and Quarto syntax render the same way as
they will on WordPress.

Usage:
    uv run scripts/wordpress/preview.py posts/<file>
    uv run scripts/wordpress/preview.py --no-open posts/<file>
"""

import argparse
import re
import sys
import webbrowser
from pathlib import Path

from wordpress_utils import extract_post_data, convert_markdown_to_html


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / ".preview"

HTML_TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
:root {{ color-scheme: light; }}
body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
    line-height: 1.6;
    color: #2F2D2E;
    background: #ffffff;
    margin: 0;
    padding: 2rem 1rem 4rem;
}}
.preview-shell {{ max-width: 720px; margin: 0 auto; }}
.preview-banner {{
    background: #fff4da;
    border: 1px solid #f1dca0;
    color: #614b00;
    padding: 0.5rem 1rem;
    border-radius: 4px;
    font-size: 0.875rem;
    margin-bottom: 2rem;
}}
h1 {{ font-size: 2.25rem; line-height: 1.2; margin: 1rem 0 1.5rem; }}
h2 {{ font-size: 1.6rem; margin-top: 2.5rem; margin-bottom: 0.75rem; }}
h3 {{ font-size: 1.25rem; margin-top: 2rem; margin-bottom: 0.5rem; }}
p {{ margin: 0 0 1rem; }}
img {{ max-width: 100%; height: auto; }}
.preview-hero {{ margin: 1rem 0 2rem; border-radius: 6px; }}
code {{
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: 0.9em;
    background: #f5f2f0;
    padding: 0.1em 0.3em;
    border-radius: 3px;
}}
pre code {{ background: transparent; padding: 0; }}
blockquote {{
    border-left: 3px solid #72BEFA;
    padding: 0.25rem 0 0.25rem 1rem;
    color: #555;
    margin: 1rem 0;
}}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #e4e4e4; padding: 0.5rem; text-align: left; }}
</style>
</head>
<body>
<div class="preview-shell">
<div class="preview-banner">Preview only. Does not reflect OpenTeams theme styling.</div>
{hero}
<h1>{title}</h1>
{content}
</div>
</body>
</html>
"""


def rewrite_image_srcs(html: str, base_dir: Path) -> str:
    """Point relative <img src> paths at local files via file:// URLs."""
    def replace(match):
        prefix, src, suffix = match.group(1), match.group(2), match.group(3)
        if src.startswith(("http://", "https://", "data:", "//", "file:")):
            return match.group(0)
        local = (base_dir / src).resolve()
        if not local.exists():
            return match.group(0)
        return f"{prefix}{local.as_uri()}{suffix}"

    return re.sub(r'(<img[^>]+src=["\'])([^"\']+)(["\'])', replace, html)


def render_hero(featured: str, base_dir: Path) -> str:
    """Return a hero <img> for the featured image, or an empty string."""
    if not featured:
        return ""
    if featured.startswith(("http://", "https://")):
        src = featured
    else:
        local = (base_dir / featured).resolve()
        if not local.exists():
            return ""
        src = local.as_uri()
    return f'<img class="preview-hero" src="{src}" alt="Featured image">'


def build_preview_html(file_path: Path) -> str:
    post = extract_post_data(str(file_path))
    if not post:
        raise SystemExit(f"Could not extract post data from {file_path}")
    body = convert_markdown_to_html(post.get("content", ""), post)
    base_dir = file_path.parent
    body = rewrite_image_srcs(body, base_dir)
    hero = render_hero(post.get("featured_image") or "", base_dir)
    title = post.get("title") or file_path.stem
    return HTML_TEMPLATE.format(title=title, hero=hero, content=body)


def default_output_path(file_path: Path) -> Path:
    DEFAULT_OUTPUT_DIR.mkdir(exist_ok=True)
    return DEFAULT_OUTPUT_DIR / f"{file_path.stem}.html"


def main():
    parser = argparse.ArgumentParser(
        description="Render a blog post to local HTML and open it in a browser."
    )
    parser.add_argument("files", nargs="+", help="Post file paths (.md or .qmd)")
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the rendered HTML in the browser",
    )
    args = parser.parse_args()

    for file_arg in args.files:
        file_path = Path(file_arg)
        if not file_path.exists():
            print(f"Error: {file_path} does not exist", file=sys.stderr)
            sys.exit(1)

        html = build_preview_html(file_path)
        out_path = default_output_path(file_path)
        out_path.write_text(html, encoding="utf-8")
        print(f"Preview: {out_path}")

        if not args.no_open:
            webbrowser.open(out_path.as_uri())


if __name__ == "__main__":
    main()
