#!/usr/bin/env python3
"""
Backfill wordpress_id and wordpress_url frontmatter fields.

One-shot maintenance script for posts that were published before the
publish workflow started recording WP identifiers in frontmatter. For
each post under posts/ that is missing wordpress_id or wordpress_url,
look up the live WP post by slug and write the values back.

Usage:
    uv run scripts/wordpress/backfill_wordpress_ids.py --dry-run
    uv run scripts/wordpress/backfill_wordpress_ids.py
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

from wordpress_utils import (
    build_published_url,
    extract_post_data,
    lookup_post_id_by_slug,
    update_qmd_metadata,
)

POSTS_DIR = Path(__file__).resolve().parents[2] / "posts"


def _iter_post_files() -> List[Path]:
    return sorted([*POSTS_DIR.glob("*.md"), *POSTS_DIR.glob("*.qmd")])


def _resolve_updates(
    post_data: Dict, wp_id: int, wp_url: str
) -> Dict[str, object]:
    """Return only the fields that need writing (missing or different)."""
    updates: Dict[str, object] = {}
    if post_data.get("wordpress_id") != wp_id:
        updates["wordpress_id"] = wp_id
    if post_data.get("wordpress_url") != wp_url:
        updates["wordpress_url"] = wp_url
    return updates


def _process_file(
    path: Path, wp_token: str, wp_api_url: str, username: str, dry_run: bool
) -> str:
    """Process one post file. Returns a status tag for the summary."""
    post_data = extract_post_data(str(path))
    if not post_data or not post_data.get("slug"):
        print(f"⚠️  {path.name}: no slug in frontmatter; skipping")
        return "skipped"

    slug = post_data["slug"]
    wp_id = lookup_post_id_by_slug(slug, wp_token, wp_api_url, username)
    if not wp_id:
        print(f"⚠️  {path.name}: no WP post matches slug '{slug}'")
        return "missing"

    wp_url = build_published_url(wp_api_url, slug)
    updates = _resolve_updates(post_data, wp_id, wp_url)

    if not updates:
        print(f"✓  {path.name}: already populated (id={wp_id})")
        return "ok"

    print(f"📝 {path.name}: {'would update' if dry_run else 'updating'} {updates}")
    if not dry_run:
        update_qmd_metadata(str(path), updates)
    return "updated"


def _summarize(counts: Dict[str, int], dry_run: bool) -> None:
    label = "Would update" if dry_run else "Updated"
    print()
    print(f"{label}: {counts['updated']}")
    print(f"Already populated: {counts['ok']}")
    print(f"No matching WP post: {counts['missing']}")
    print(f"Skipped (no slug): {counts['skipped']}")


def _load_credentials() -> Tuple[str, str, str]:
    username = os.environ.get("WP_USERNAME")
    wp_api_url = os.environ.get("WP_API_URL")
    wp_token = os.environ.get("WP_TOKEN")
    if not all([username, wp_api_url, wp_token]):
        print("❌ Missing environment variables. Ensure .env has:")
        print("   WP_TOKEN, WP_API_URL, WP_USERNAME")
        sys.exit(1)
    return username, wp_api_url, wp_token


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would change without writing files.",
    )
    args = parser.parse_args()

    username, wp_api_url, wp_token = _load_credentials()

    counts = {"updated": 0, "ok": 0, "missing": 0, "skipped": 0}
    for path in _iter_post_files():
        status = _process_file(path, wp_token, wp_api_url, username, args.dry_run)
        counts[status] += 1

    _summarize(counts, args.dry_run)


if __name__ == "__main__":
    main()
