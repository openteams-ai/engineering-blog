#!/usr/bin/env python3
"""
Sync authors from authors.yml to WordPress.

Creates contributor-role users for each author in the YAML file.
Existing users (matched by slug) are updated with current name/email/bio.

Usage:
    uv run scripts/wordpress/sync_authors.py
    uv run scripts/wordpress/sync_authors.py --dry-run
"""

import hashlib
import os
import secrets
import string
import sys
import yaml
import requests
from pathlib import Path
from typing import Dict, List, Optional

from wordpress_utils import get_auth_headers, DEFAULT_TIMEOUT

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AUTHORS_FILE = PROJECT_ROOT / "authors.yml"


def _generate_strong_password(length: int = 32) -> str:
    """Build a random password that satisfies common WP strength rules.

    Contains at least one uppercase, lowercase, digit, and symbol. Needed
    because some WP installs reject weak passwords (e.g. hex-only strings).
    """
    symbols = "!@#$%^&*"
    alphabet = string.ascii_letters + string.digits + symbols
    required = [
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.digits),
        secrets.choice(symbols),
    ]
    chars = required + [secrets.choice(alphabet) for _ in range(length - len(required))]
    secrets.SystemRandom().shuffle(chars)
    return "".join(chars)


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
        # Random password. Contributors are not expected to log in.
        "password": _generate_strong_password(),
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


IMAGE_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _reuse_wp_media(
    avatar_url: str, user_id: int, headers: Dict, wp_api_url: str
) -> Optional[int]:
    """If avatar_url points to this WordPress site, return the existing media ID
    (after transferring ownership to user_id) instead of uploading a duplicate.

    Returns None when avatar_url is external or the media isn't found.
    """
    wp_base = wp_api_url.rsplit("/wp-json", 1)[0]
    if not avatar_url.startswith(wp_base):
        return None

    filename = avatar_url.rsplit("/", 1)[-1]
    stem = filename.rsplit(".", 1)[0]
    resp = requests.get(
        f"{wp_api_url}/media",
        headers=headers,
        params={"search": stem, "per_page": 10},
        timeout=DEFAULT_TIMEOUT,
    )
    if resp.status_code != 200:
        return None
    for item in resp.json():
        if item.get("source_url") == avatar_url:
            media_id = item["id"]
            if item.get("author") != user_id:
                # Simple Local Avatars needs media.author == user being set.
                requests.post(
                    f"{wp_api_url}/media/{media_id}",
                    headers=headers,
                    json={"author": user_id},
                    timeout=DEFAULT_TIMEOUT,
                )
            return media_id
    return None


def _upload_external_avatar(
    avatar_url: str,
    marker: str,
    user_id: int,
    headers: Dict,
    wp_api_url: str,
) -> Optional[int]:
    """Download avatar_url and upload as a new media item owned by user_id."""
    img = requests.get(
        avatar_url,
        headers={"User-Agent": "OpenTeams-Engineering-Blog/1.0"},
        timeout=30,
    )
    if img.status_code != 200:
        print(f"  Failed to download avatar: {img.status_code}")
        return None

    content_type = img.headers.get("Content-Type", "image/png").split(";")[0].strip()
    extension = IMAGE_EXTENSIONS.get(content_type, ".png")
    filename = f"{marker}{extension}"

    upload_headers = {
        **headers,
        "Content-Type": content_type,
        "Content-Disposition": f'attachment; filename="{filename}"',
    }
    upload_resp = requests.post(
        f"{wp_api_url}/media",
        headers=upload_headers,
        data=img.content,
        timeout=DEFAULT_TIMEOUT,
    )
    if upload_resp.status_code not in (200, 201):
        print(f"  Failed to upload avatar: {upload_resp.status_code}")
        return None
    media_id = upload_resp.json()["id"]

    # Simple Local Avatars requires the media's author to match the target user.
    requests.post(
        f"{wp_api_url}/media/{media_id}",
        headers=headers,
        json={"author": user_id},
        timeout=DEFAULT_TIMEOUT,
    )
    return media_id


def sync_avatar(
    author: Dict,
    user_id: int,
    headers: Dict,
    wp_api_url: str,
    dry_run: bool,
) -> bool:
    """Upload or reuse avatar image and set it as the user's local avatar.

    If avatar_url already points at a media item on this WordPress site, that
    existing item is reused (ownership transferred to the target user) to
    avoid duplicating images in the media library. External URLs are
    downloaded and uploaded under a hashed filename.
    """
    avatar_url = author.get("avatar_url")
    if not avatar_url:
        return False

    url_hash = hashlib.sha256(avatar_url.encode("utf-8")).hexdigest()[:8]
    marker = f"avatar-{author['slug']}-{url_hash}"

    resp = requests.get(
        f"{wp_api_url}/users/{user_id}", headers=headers, timeout=DEFAULT_TIMEOUT
    )
    current = (resp.json() or {}).get("simple_local_avatar") or {}
    current_full = current.get("full", "")
    # Already in sync: either reusing the same WP media, or the sync-uploaded
    # copy whose filename encodes this URL's hash.
    if current_full == avatar_url or marker in current_full:
        print(f"  Avatar up to date: {author['name']}")
        return False
    previous_media_id = current.get("media_id")

    if dry_run:
        print(f"  [DRY RUN] Would set avatar for {author['name']} from {avatar_url}")
        return False

    media_id = _reuse_wp_media(avatar_url, user_id, headers, wp_api_url)
    if media_id is None:
        media_id = _upload_external_avatar(
            avatar_url, marker, user_id, headers, wp_api_url
        )
    if media_id is None:
        print(f"  Failed to resolve avatar for {author['name']}")
        return False

    avatar_resp = requests.post(
        f"{wp_api_url}/users/{user_id}",
        headers=headers,
        json={"simple_local_avatar": {"media_id": media_id}},
        timeout=DEFAULT_TIMEOUT,
    )
    if avatar_resp.status_code != 200:
        print(f"  Failed to set avatar for {author['name']}: "
              f"{avatar_resp.status_code} {avatar_resp.text}")
        return False

    # Delete the replaced avatar only if it was a sync-generated copy
    # (filename starts with `avatar-<slug>-`). User-uploaded originals and
    # reused WP media are left in place.
    if previous_media_id and previous_media_id != media_id:
        prev_filename = current_full.rsplit("/", 1)[-1]
        if prev_filename.startswith(f"avatar-{author['slug']}-"):
            requests.delete(
                f"{wp_api_url}/media/{previous_media_id}",
                headers=headers,
                params={"force": "true"},
                timeout=DEFAULT_TIMEOUT,
            )

    print(f"  Avatar set for {author['name']}")
    return True


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
    created, updated, avatars_set = 0, 0, 0

    for author in authors:
        slug = author["slug"]
        if slug in existing:
            user_id = existing[slug]["id"]
            if update_user(author, existing[slug], headers, wp_api_url, dry_run):
                updated += 1
        else:
            user_id = create_user(author, headers, wp_api_url, dry_run)
            if user_id:
                created += 1

        if user_id and sync_avatar(author, user_id, headers, wp_api_url, dry_run):
            avatars_set += 1

    print(f"\nDone: {created} created, {updated} updated, "
          f"{avatars_set} avatar(s) set, "
          f"{len(authors) - created - updated} unchanged")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sync authors.yml to WordPress")
    parser.add_argument(
        "--dry-run", action="store_true", help="Preview changes without writing"
    )
    args = parser.parse_args()
    sync_authors(dry_run=args.dry_run)
