#!/usr/bin/env python3
"""
Trash the shadow preview drafts created for a pull request.

preview_draft.py previews an edit to an already-published post by copying it
to a throwaway draft under a `-preview-pr<N>` slug, so the live article is
never written to. Those copies are disposable, and this removes them once the
PR is closed or merged.

Only posts whose slug ends in the PR's own suffix are touched, and only when
they are still drafts, so a real article can never be caught by this.

Usage:
    uv run scripts/wordpress/cleanup_preview_drafts.py --pr 51
"""

import argparse
import os
import sys
from typing import Dict, List

import requests

from preview_draft import SHADOW_SLUG_SUFFIX
from wordpress_utils import DEFAULT_TIMEOUT, get_auth_headers

PER_PAGE = 100


def find_shadow_drafts(
    pr_number: int, wp_token: str, wp_api_url: str, username: str
) -> List[Dict]:
    """Return draft posts whose slug ends with this PR's shadow suffix."""
    suffix = f"{SHADOW_SLUG_SUFFIX}{pr_number}"
    headers = get_auth_headers(username, wp_token)
    matches: List[Dict] = []
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

        posts = response.json()
        if not posts:
            break

        matches.extend(p for p in posts if str(p.get("slug", "")).endswith(suffix))

        if len(posts) < PER_PAGE:
            break
        page += 1

    return matches


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
        description="Trash the shadow preview drafts belonging to a pull request."
    )
    parser.add_argument("--pr", type=int, required=True, help="Pull request number")
    args = parser.parse_args()

    username = os.environ.get("WP_USERNAME")
    wp_api_url = os.environ.get("WP_API_URL")
    wp_token = os.environ.get("WP_TOKEN")

    if not all([username, wp_api_url, wp_token]):
        print("❌ Missing environment variables: WP_TOKEN, WP_API_URL, WP_USERNAME")
        sys.exit(1)

    drafts = find_shadow_drafts(args.pr, wp_token, wp_api_url, username)
    if not drafts:
        print(f"No shadow preview drafts found for PR #{args.pr}.")
        return

    for draft in drafts:
        if trash_post(draft["id"], wp_token, wp_api_url, username):
            print(f"🗑️  Trashed {draft['slug']} (post {draft['id']})")
        else:
            print(f"⚠️  Could not trash {draft['slug']} (post {draft['id']})")


if __name__ == "__main__":
    main()
