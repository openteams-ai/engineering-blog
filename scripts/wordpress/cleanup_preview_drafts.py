#!/usr/bin/env python3
"""
Trash the WordPress drafts a pull request left behind.

Two kinds of draft accumulate while a PR is open:

  Shadow copies, named `<slug>-preview-pr<N>`, created when previewing an edit
  to an already-published post. Always disposable, whatever the PR's fate.

  The post's own draft, created when previewing a brand new article. On a
  merged PR this becomes the published article and must be left alone. On an
  abandoned PR nothing will ever publish it, so it is litter.

Pass --merged to keep the second kind. Only posts still in `draft` status are
ever touched, so a live article cannot be caught by this even by mistake.

Usage:
    uv run scripts/wordpress/cleanup_preview_drafts.py --pr 51 [--merged] [posts/a.md ...]
"""

import argparse
import os
import sys
from typing import Dict, List, Set

import requests

from preview_draft import SHADOW_SLUG_SUFFIX
from wordpress_utils import DEFAULT_TIMEOUT, extract_post_data, get_auth_headers

PER_PAGE = 100


def slugs_from_posts(paths: List[str]) -> Set[str]:
    """Return the frontmatter slug of each post file that can be read."""
    slugs = set()
    for path in paths:
        if not os.path.exists(path):
            continue
        post_data = extract_post_data(path)
        if post_data and post_data.get("slug"):
            slugs.add(post_data["slug"])
    return slugs


def list_drafts(wp_token: str, wp_api_url: str, username: str) -> List[Dict]:
    """Return every draft post as {id, slug}, following pagination."""
    headers = get_auth_headers(username, wp_token)
    drafts: List[Dict] = []
    page = 1

    while True:
        response = requests.get(
            f"{wp_api_url}/posts",
            headers=headers,
            params={
                "status": "draft",
                "per_page": PER_PAGE,
                "page": page,
                "_fields": "id,slug",
            },
            timeout=DEFAULT_TIMEOUT,
        )
        if response.status_code != 200:
            break

        batch = response.json()
        if not batch:
            break

        drafts.extend(batch)
        if len(batch) < PER_PAGE:
            break
        page += 1

    return drafts


def drafts_to_trash(
    drafts: List[Dict], pr_number: int, abandoned_slugs: Set[str]
) -> List[Dict]:
    """Pick the drafts belonging to this PR.

    Shadow copies are matched by the PR-scoped suffix. Abandoned slugs are
    matched exactly, and the caller passes none of them for a merged PR.
    """
    suffix = f"{SHADOW_SLUG_SUFFIX}{pr_number}"
    return [
        draft
        for draft in drafts
        if str(draft.get("slug", "")).endswith(suffix)
        or draft.get("slug") in abandoned_slugs
    ]


def trash_post(post_id: int, wp_token: str, wp_api_url: str, username: str) -> bool:
    """Move a post to trash. Not a permanent delete, so it stays recoverable."""
    response = requests.delete(
        f"{wp_api_url}/posts/{post_id}",
        headers=get_auth_headers(username, wp_token),
        timeout=DEFAULT_TIMEOUT,
    )
    return response.status_code == 200


def main():
    parser = argparse.ArgumentParser(
        description="Trash the WordPress drafts a pull request left behind."
    )
    parser.add_argument("--pr", type=int, required=True, help="Pull request number")
    parser.add_argument(
        "--merged",
        action="store_true",
        help="The PR was merged, so keep each post's own draft. It is about to "
        "become the published article.",
    )
    parser.add_argument(
        "posts",
        nargs="*",
        help="Post files the PR touched. Their drafts are trashed unless --merged.",
    )
    args = parser.parse_args()

    username = os.environ.get("WP_USERNAME")
    wp_api_url = os.environ.get("WP_API_URL")
    wp_token = os.environ.get("WP_TOKEN")

    if not all([username, wp_api_url, wp_token]):
        print("❌ Missing environment variables: WP_TOKEN, WP_API_URL, WP_USERNAME")
        sys.exit(1)

    abandoned = set() if args.merged else slugs_from_posts(args.posts)
    if args.merged:
        print("PR was merged; keeping each post's own draft.")

    drafts = list_drafts(wp_token, wp_api_url, username)
    targets = drafts_to_trash(drafts, args.pr, abandoned)

    if not targets:
        print(f"No preview drafts to clean up for PR #{args.pr}.")
        return

    for draft in targets:
        if trash_post(draft["id"], wp_token, wp_api_url, username):
            print(f"🗑️  Trashed {draft['slug']} (post {draft['id']})")
        else:
            print(f"⚠️  Could not trash {draft['slug']} (post {draft['id']})")


if __name__ == "__main__":
    main()
