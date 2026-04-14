#!/usr/bin/env python3
"""
Sync authors from authors.yml to WordPress.

Creates contributor-role users for each author in the YAML file.
Existing users (matched by slug) are updated with current name/email/bio.

Usage:
    uv run scripts/wordpress/sync_authors.py
    uv run scripts/wordpress/sync_authors.py --dry-run
"""

import os
import sys
import yaml
import requests
from pathlib import Path
from typing import Dict, List, Optional

from wordpress_utils import get_auth_headers, DEFAULT_TIMEOUT

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AUTHORS_FILE = PROJECT_ROOT / "authors.yml"


def load_authors() -> List[Dict]:
    """Load author definitions from authors.yml."""
    with open(AUTHORS_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    authors = data.get("authors", [])
    for author in authors:
        missing = [f for f in ("name", "slug", "email") if not author.get(f)]
        if missing:
            print(f"  Skipping entry missing {', '.join(missing)}: {author}")
    return [a for a in authors if all(a.get(f) for f in ("name", "slug", "email"))]


def get_existing_users(headers: str, wp_api_url: str) -> Dict[str, Dict]:
    """Fetch all WordPress users and index by slug."""
    users = {}
    page = 1
    while True:
        resp = requests.get(
            f"{wp_api_url}/users",
            headers=headers,
            params={"per_page": 100, "page": page},
            timeout=DEFAULT_TIMEOUT,
        )
        if resp.status_code != 200:
            break
        batch = resp.json()
        if not batch:
            break
        for user in batch:
            users[user["slug"]] = user
        page += 1
    return users


def create_user(
    author: Dict, headers: Dict, wp_api_url: str, dry_run: bool
) -> Optional[int]:
    """Create a new WordPress contributor user."""
    payload = {
        "username": author["slug"],
        "name": author["name"],
        "slug": author["slug"],
        "email": author["email"],
        "description": author.get("bio", ""),
        "roles": ["contributor"],
        # Random password — contributors can't log in meaningfully
        "password": os.urandom(32).hex(),
    }

    if dry_run:
        print(f"  [DRY RUN] Would create user: {author['name']} ({author['slug']})")
        return None

    resp = requests.post(
        f"{wp_api_url}/users",
        headers=headers,
        json=payload,
        timeout=DEFAULT_TIMEOUT,
    )

    if resp.status_code == 201:
        user_id = resp.json()["id"]
        print(f"  Created: {author['name']} (id={user_id})")
        return user_id

    print(f"  Failed to create {author['name']}: {resp.status_code} {resp.text}")
    return None


def update_user(
    author: Dict, wp_user: Dict, headers: Dict, wp_api_url: str, dry_run: bool
) -> bool:
    """Update an existing WordPress user if fields have changed."""
    updates = {}
    if wp_user.get("name") != author["name"]:
        updates["name"] = author["name"]
    if wp_user.get("description", "") != author.get("bio", ""):
        updates["description"] = author.get("bio", "")

    if not updates:
        print(f"  Up to date: {author['name']}")
        return False

    if dry_run:
        print(f"  [DRY RUN] Would update {author['name']}: {list(updates.keys())}")
        return False

    resp = requests.post(
        f"{wp_api_url}/users/{wp_user['id']}",
        headers=headers,
        json=updates,
        timeout=DEFAULT_TIMEOUT,
    )

    if resp.status_code == 200:
        print(f"  Updated: {author['name']} ({list(updates.keys())})")
        return True

    print(f"  Failed to update {author['name']}: {resp.status_code} {resp.text}")
    return False


def sync_authors(dry_run: bool = False) -> None:
    """Sync all authors from YAML to WordPress."""
    wp_token = os.environ.get("WP_TOKEN")
    wp_api_url = os.environ.get("WP_API_URL")
    username = os.environ.get("WP_USERNAME")

    if not all([wp_token, wp_api_url, username]):
        print("Error: WP_TOKEN, WP_API_URL, and WP_USERNAME must be set")
        sys.exit(1)

    headers = get_auth_headers(username, wp_token)
    authors = load_authors()

    if not authors:
        print("No valid authors found in authors.yml")
        return

    print(f"Syncing {len(authors)} author(s)...")
    if dry_run:
        print("(dry run — no changes will be made)\n")

    existing = get_existing_users(headers, wp_api_url)
    created, updated = 0, 0

    for author in authors:
        slug = author["slug"]
        if slug in existing:
            if update_user(author, existing[slug], headers, wp_api_url, dry_run):
                updated += 1
        else:
            if create_user(author, headers, wp_api_url, dry_run):
                created += 1

    print(f"\nDone: {created} created, {updated} updated, "
          f"{len(authors) - created - updated} unchanged")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sync authors.yml to WordPress")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without writing"
    )
    args = parser.parse_args()
    sync_authors(dry_run=args.dry_run)
