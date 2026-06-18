"""One-shot: migrate posts/*.md (WordPress frontmatter) into Hugo content/blog
leaf bundles for the darby theme.

Mapping:
  title          -> title
  (git add date) -> date
  authors[0]     -> author (display name) + authorAvatar (from authors.yml)
  meta_description -> summary + description
  categories     -> tags
  slug           -> slug (kept)

Images move from posts/images/<slug>/ into content/blog/<slug>/images/<slug>/
so existing relative `images/<slug>/x.png` refs keep resolving inside the bundle.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "posts"
CONTENT = ROOT / "content" / "blog"


def git_add_date(path: Path) -> str:
    out = subprocess.check_output(
        ["git", "log", "--diff-filter=A", "--follow", "--format=%aI", "-1", "--", str(path)],
        cwd=ROOT,
        text=True,
    ).strip()
    return out or "2026-01-01T00:00:00Z"


def load_authors() -> dict[str, dict]:
    data = yaml.safe_load((ROOT / "authors.yml").read_text())
    return {a["slug"]: a for a in data["authors"]}


def split_frontmatter(text: str) -> tuple[dict, str]:
    assert text.startswith("---\n"), "expected YAML frontmatter"
    _, fm, body = text.split("---\n", 2)
    return yaml.safe_load(fm), body


def main() -> None:
    authors = load_authors()
    CONTENT.mkdir(parents=True, exist_ok=True)

    for post in sorted(POSTS.glob("*.md")):
        fm, body = split_frontmatter(post.read_text())
        slug = fm["slug"]
        author_slugs = fm.get("authors") or []
        primary = authors.get(author_slugs[0]) if author_slugs else None

        new_fm: dict = {
            "title": fm["title"],
            "date": git_add_date(post),
            "slug": slug,
        }
        if primary:
            new_fm["author"] = primary["name"]
            if primary.get("github"):
                new_fm["authorGithub"] = primary["github"]
            if primary.get("avatar_url"):
                new_fm["authorAvatar"] = primary["avatar_url"]
        if fm.get("meta_description"):
            new_fm["summary"] = fm["meta_description"]
            new_fm["description"] = fm["meta_description"]
        if fm.get("categories"):
            new_fm["tags"] = fm["categories"]

        bundle = CONTENT / slug
        bundle.mkdir(parents=True, exist_ok=True)
        out = "---\n" + yaml.safe_dump(new_fm, sort_keys=False, allow_unicode=True) + "---\n" + body
        (bundle / "index.md").write_text(out)

        src_imgs = POSTS / "images" / slug
        if src_imgs.is_dir():
            dst = bundle / "images" / slug
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(src_imgs, dst, dirs_exist_ok=True)

        print(f"migrated {post.name} -> content/blog/{slug}/index.md")


if __name__ == "__main__":
    main()
