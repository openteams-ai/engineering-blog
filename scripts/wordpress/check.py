#!/usr/bin/env python3
"""
Pre-flight post checker.

Validates a blog post against everything ``publish.py`` requires *before* you
open a PR, so broken frontmatter, missing authors, or dead image links are
caught locally instead of after the post merges to ``main`` and the publish
workflow runs.

No WordPress credentials are needed.

Usage:
    uv run scripts/wordpress/check.py posts/your-article.md
    uv run scripts/wordpress/check.py posts/*.md        # check several
    uv run scripts/wordpress/check.py --all             # check every post

Exit code is 0 when all checked posts pass (warnings allowed), 1 when any
post has an error. Pass --strict to also fail on warnings (used in CI).
"""

import argparse
import glob
import os
import re
import sys
from pathlib import Path

import yaml

from wordpress_utils import is_valid_slug

# Required frontmatter fields, per CLAUDE.md and the PostMetadata model.
REQUIRED_FIELDS = (
    "title",
    "slug",
    "authors",
    "categories",
    "meta_description",
    "focus_keyword",
)

# WordPress auto-adds "Engineering"; meta_description SEO sweet spot.
META_MIN, META_MAX = 120, 160

REPO_ROOT = Path(__file__).resolve().parents[2]
AUTHORS_FILE = REPO_ROOT / "authors.yml"

# Matches markdown images: ![alt](src)
IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")


def load_author_slugs():
    """Return the set of author slugs declared in authors.yml."""
    if not AUTHORS_FILE.exists():
        return None
    data = yaml.safe_load(AUTHORS_FILE.read_text(encoding="utf-8")) or {}
    return {a.get("slug") for a in data.get("authors", []) if a.get("slug")}


def split_frontmatter(text):
    """Return (meta_dict, body, error). error is set if frontmatter is broken."""
    if not text.startswith("---"):
        return None, text, "no YAML frontmatter (file must start with '---')"
    parts = text.split("---", 2)
    if len(parts) < 3:
        return None, text, "frontmatter is not closed with a second '---'"
    try:
        meta = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError as exc:
        return None, parts[2], f"frontmatter is not valid YAML: {exc}"
    if not isinstance(meta, dict):
        return None, parts[2], "frontmatter did not parse to a mapping"
    return meta, parts[2], None


class Report:
    """Collects errors and warnings for a single post."""

    def __init__(self, path):
        self.path = path
        self.errors = []
        self.warnings = []

    def error(self, msg):
        self.errors.append(msg)

    def warn(self, msg):
        self.warnings.append(msg)

    @property
    def ok(self):
        return not self.errors


def _as_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def check_post(path, author_slugs):
    """Run all checks against one post file and return a Report."""
    rep = Report(path)
    text = Path(path).read_text(encoding="utf-8")

    meta, body, fm_error = split_frontmatter(text)
    if fm_error:
        rep.error(fm_error)
        return rep

    # Required fields present and non-empty.
    for field in REQUIRED_FIELDS:
        value = meta.get(field)
        if value is None or (isinstance(value, (str, list)) and len(value) == 0):
            rep.error(f"missing required field: {field}")

    slug = meta.get("slug")
    if isinstance(slug, str) and slug:
        if not is_valid_slug(slug):
            rep.error(
                f"invalid slug '{slug}': must be lowercase, hyphenated, "
                "3-50 chars, no spaces or underscores"
            )
        # Publish matches posts to WordPress by slug, so a slug that drifts
        # from the filename is a known footgun (CLAUDE.md).
        stem = Path(path).stem
        if slug != stem:
            rep.warn(
                f"slug '{slug}' does not match filename '{stem}' "
                "(harmless once published, but confusing)"
            )

    # Authors must exist in authors.yml, or publish can't find the WP user.
    authors = _as_list(meta.get("authors"))
    if author_slugs is None:
        rep.warn("authors.yml not found; skipped author validation")
    else:
        for a in authors:
            if a not in author_slugs:
                rep.error(
                    f"author '{a}' is not in authors.yml "
                    "(add yourself there before publishing)"
                )

    # meta_description length: SEO guidance, not fatal to publish.
    desc = meta.get("meta_description")
    if isinstance(desc, str) and desc:
        n = len(desc)
        if n > META_MAX:
            rep.warn(f"meta_description is {n} chars; keep it under {META_MAX}")
        elif n < META_MIN:
            rep.warn(
                f"meta_description is {n} chars; aim for {META_MIN}-{META_MAX} "
                "for a fuller search snippet"
            )

    # Focus keyword should appear in title and slug (SEO skill requirement).
    kw = meta.get("focus_keyword")
    title = meta.get("title")
    if isinstance(kw, str) and kw:
        # Compare on words (Yoast-style) so reordered or hyphenated keywords
        # still count as present.
        kw_words = re.findall(r"[a-z0-9]+", kw.lower())
        if isinstance(title, str):
            title_words = set(re.findall(r"[a-z0-9]+", title.lower()))
            missing = [w for w in kw_words if w not in title_words]
            if missing:
                rep.warn(
                    f"focus_keyword '{kw}' not in title "
                    f"(missing: {', '.join(missing)})"
                )
        if isinstance(slug, str):
            slug_words = set(re.findall(r"[a-z0-9]+", slug.lower()))
            missing = [w for w in kw_words if w not in slug_words]
            if missing:
                rep.warn(
                    f"focus_keyword '{kw}' not in slug "
                    f"(missing: {', '.join(missing)})"
                )

    # Referenced relative images must exist; publish silently leaves a dead
    # link otherwise.
    file_dir = Path(path).parent
    expected_img_dir = f"images/{slug}/" if isinstance(slug, str) else None
    for alt, src in IMAGE_RE.findall(body):
        if src.startswith(("http://", "https://", "data:", "//")):
            continue
        if not (file_dir / src).exists():
            rep.error(f"image not found: {src}")
            continue
        if expected_img_dir and not src.startswith(expected_img_dir):
            rep.warn(
                f"image '{src}' is outside the conventional '{expected_img_dir}' "
                "directory"
            )
        if not alt.strip():
            rep.warn(f"image '{src}' has empty alt text (hurts SEO/accessibility)")

    # .md files can't run executable code blocks; {python} only works in .qmd.
    if path.endswith(".md") and re.search(r"^```\{[a-zA-Z]", body, re.MULTILINE):
        rep.warn(
            "executable code block ({...}) found in a .md file; "
            "rename to .qmd or it will publish verbatim"
        )

    return rep


def print_report(rep):
    """Print a single post's report. Returns True if the post is clean."""
    if rep.ok and not rep.warnings:
        print(f"\033[32m✓\033[0m {rep.path}")
        return True

    icon = "\033[32m✓\033[0m" if rep.ok else "\033[31m✗\033[0m"
    print(f"{icon} {rep.path}")
    for msg in rep.errors:
        print(f"    \033[31merror\033[0m   {msg}")
    for msg in rep.warnings:
        print(f"    \033[33mwarning\033[0m {msg}")
    return rep.ok


def main():
    parser = argparse.ArgumentParser(
        description="Pre-flight check a blog post before opening a PR.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("files", nargs="*", help="Post files (.md/.qmd) to check")
    parser.add_argument(
        "--all", action="store_true", help="Check every post under posts/"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as failures (exit 1)",
    )
    args = parser.parse_args()

    files = list(args.files)
    if args.all:
        files += sorted(
            glob.glob(str(REPO_ROOT / "posts" / "*.md"))
            + glob.glob(str(REPO_ROOT / "posts" / "*.qmd"))
        )
    if not files:
        parser.error("no files given; pass post paths or --all")

    # De-dup while preserving order, and drop non-post paths.
    seen = set()
    targets = []
    for f in files:
        if f in seen:
            continue
        seen.add(f)
        if not (f.endswith(".md") or f.endswith(".qmd")):
            print(f"\033[33mskip\033[0m {f} (not a .md/.qmd file)")
            continue
        if not os.path.exists(f):
            print(f"\033[31m✗\033[0m {f}\n    \033[31merror\033[0m   file not found")
            targets.append(("__missing__", f))
            continue
        targets.append(("file", f))

    author_slugs = load_author_slugs()

    n_errors = 0
    n_warnings = 0
    n_clean = 0
    for kind, f in targets:
        if kind == "__missing__":
            n_errors += 1
            continue
        rep = check_post(f, author_slugs)
        print_report(rep)
        n_errors += len(rep.errors)
        n_warnings += len(rep.warnings)
        if rep.ok and not rep.warnings:
            n_clean += 1

    total = len(targets)
    print(
        f"\n{total} post(s) checked: {n_clean} clean, "
        f"{n_errors} error(s), {n_warnings} warning(s)."
    )

    if n_errors or (args.strict and n_warnings):
        sys.exit(1)


if __name__ == "__main__":
    main()
