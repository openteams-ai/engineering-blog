#!/usr/bin/env python3
"""
Local preview for blog posts.

Renders a .md or .qmd file to self-contained HTML and opens it in the default
browser. Uses the same convert_markdown_to_html pipeline as publish.py, so
Prism.js directives, Mermaid blocks, and Quarto syntax render the same way as
they will on WordPress.

Watches the file and reloads the browser on every save by default. Pass
--no-watch for a one-shot render, which is what scripts and agents want since
watching blocks until interrupted.

Usage:
    uv run scripts/wordpress/preview.py posts/<file>
    uv run scripts/wordpress/preview.py --no-watch posts/<file>
    uv run scripts/wordpress/preview.py --no-watch --no-open posts/<file>
"""

import argparse
import functools
import re
import sys
import threading
import time
import webbrowser
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from wordpress_utils import extract_post_data, convert_markdown_to_html


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / ".preview"
WATCH_POLL_SECONDS = 0.5

LIVE_RELOAD_SCRIPT = """
<script>
(function () {
    var seen = null;
    setInterval(function () {
        fetch(location.href, { method: "HEAD", cache: "no-store" })
            .then(function (res) {
                var stamp = res.headers.get("Last-Modified");
                if (!stamp) return;
                if (seen && stamp !== seen) location.reload();
                seen = stamp;
            })
            .catch(function () { /* server stopped; keep polling */ });
    }, 500);
})();
</script>
"""

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


def local_asset_url(local: Path, served: bool) -> str:
    """Return the URL a rendered page should use for a local file.

    Pages opened straight off disk reference file:// URLs. Pages served by
    --watch reference paths rooted at the project, since a browser blocks
    file:// subresources on an http:// page.
    """
    if not served:
        return local.as_uri()
    try:
        return "/" + local.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return local.as_uri()


def rewrite_image_srcs(html: str, base_dir: Path, served: bool = False) -> str:
    """Point relative <img src> and <a href> paths at their local files.

    Rewriting <a href> as well as <img src> keeps click-to-zoom working in the
    local preview, since images wrapped in an anchor link to the image itself.
    """
    def replace(match):
        prefix, src, suffix = match.group(1), match.group(2), match.group(3)
        if src.startswith(("http://", "https://", "data:", "//", "file:")):
            return match.group(0)
        local = (base_dir / src).resolve()
        if not local.exists():
            return match.group(0)
        return f"{prefix}{local_asset_url(local, served)}{suffix}"

    html = re.sub(r'(<img[^>]+src=["\'])([^"\']+)(["\'])', replace, html)
    return re.sub(r'(<a[^>]+href=["\'])([^"\']+)(["\'])', replace, html)


def render_hero(featured: str, base_dir: Path, served: bool = False) -> str:
    """Return a hero <img> for the featured image, or an empty string."""
    if not featured:
        return ""
    if featured.startswith(("http://", "https://")):
        src = featured
    else:
        local = (base_dir / featured).resolve()
        if not local.exists():
            return ""
        src = local_asset_url(local, served)
    return f'<img class="preview-hero" src="{src}" alt="Featured image">'


def build_preview_html(file_path: Path, served: bool = False) -> str:
    post = extract_post_data(str(file_path))
    if not post:
        raise SystemExit(f"Could not extract post data from {file_path}")
    body = convert_markdown_to_html(post.get("content", ""), post)
    base_dir = file_path.parent
    body = rewrite_image_srcs(body, base_dir, served)
    hero = render_hero(post.get("featured_image") or "", base_dir, served)
    title = post.get("title") or file_path.stem
    html = HTML_TEMPLATE.format(title=title, hero=hero, content=body)
    if served:
        html = html.replace("</body>", f"{LIVE_RELOAD_SCRIPT}</body>")
    return html


def default_output_path(file_path: Path) -> Path:
    DEFAULT_OUTPUT_DIR.mkdir(exist_ok=True)
    return DEFAULT_OUTPUT_DIR / f"{file_path.stem}.html"


def render_to_disk(file_path: Path, served: bool = False) -> Path:
    """Render one post and write it to its preview path."""
    out_path = default_output_path(file_path)
    out_path.write_text(build_preview_html(file_path, served), encoding="utf-8")
    return out_path


class PreviewRequestHandler(SimpleHTTPRequestHandler):
    """Static handler that never caches and does not log every request."""

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, format, *args):
        pass


def start_preview_server() -> ThreadingHTTPServer:
    """Serve the project root on a free port, in a background thread."""
    handler = functools.partial(PreviewRequestHandler, directory=str(PROJECT_ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def watch(file_paths: list[Path], open_browser: bool) -> None:
    """Rebuild previews whenever their source changes, reloading open tabs."""
    server = start_preview_server()
    port = server.server_address[1]

    for file_path in file_paths:
        out_path = render_to_disk(file_path, served=True)
        url = f"http://127.0.0.1:{port}/{out_path.relative_to(PROJECT_ROOT).as_posix()}"
        print(f"Preview: {url}")
        if open_browser:
            webbrowser.open(url)

    print("Watching for changes. Press Ctrl+C to stop.")
    seen = {p: p.stat().st_mtime for p in file_paths}
    try:
        while True:
            time.sleep(WATCH_POLL_SECONDS)
            for file_path in file_paths:
                if not file_path.exists():
                    continue
                mtime = file_path.stat().st_mtime
                if mtime == seen[file_path]:
                    continue
                seen[file_path] = mtime
                try:
                    render_to_disk(file_path, served=True)
                    print(f"Rebuilt {file_path} at {time.strftime('%H:%M:%S')}")
                except Exception as err:
                    print(f"Error rendering {file_path}: {err}", file=sys.stderr)
    except KeyboardInterrupt:
        print("\nStopped watching.")
    finally:
        server.shutdown()


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
    parser.add_argument(
        "--watch",
        dest="watch",
        action="store_true",
        default=True,
        help="Rebuild on every save and reload the open browser tab (default)",
    )
    parser.add_argument(
        "--no-watch",
        dest="watch",
        action="store_false",
        help="Render once and exit, instead of watching for changes",
    )
    args = parser.parse_args()

    file_paths = []
    for file_arg in args.files:
        file_path = Path(file_arg)
        if not file_path.exists():
            print(f"Error: {file_path} does not exist", file=sys.stderr)
            sys.exit(1)
        file_paths.append(file_path)

    if args.watch:
        watch(file_paths, open_browser=not args.no_open)
        return

    for file_path in file_paths:
        out_path = render_to_disk(file_path)
        print(f"Preview: {out_path}")

        if not args.no_open:
            webbrowser.open(out_path.as_uri())


if __name__ == "__main__":
    main()
