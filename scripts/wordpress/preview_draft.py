#!/usr/bin/env python3
"""
Publish a post to WordPress as a draft and report its preview URL.

Used by the PR preview workflow so a contributor can see their post rendered
by the real theme (Elementor lightbox, brand fonts, content column width)
before it goes live. The local preview.py renders the same markdown pipeline
but in a bare HTML shell, so it cannot confirm anything the theme provides.

Safety: publish.py matches posts by slug, so previewing a slug that is
already live would overwrite the live article with unreviewed changes from
the PR branch. Such a post is instead previewed as a throwaway shadow copy
under a `-preview-pr<N>` slug, which the cleanup job trashes when the PR
closes.

Usage:
    uv run scripts/wordpress/preview_draft.py posts/<file> [--pr N] [--result-file out.jsonl]
"""

import argparse
import json
import os
import sys
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterator, NamedTuple, Optional, Tuple

import requests
import yaml

from publish import process_file
from wordpress_utils import (
    DEFAULT_TIMEOUT,
    extract_post_data,
    get_auth_headers,
)

SHADOW_SLUG_SUFFIX = "-preview-pr"

# Statuses that mean a post is already serving readers, so its slug must not
# be written to by a preview run.
LIVE_STATUSES = ("publish", "private")


class WordPressAuth(NamedTuple):
    """Credentials for one WordPress site."""

    username: str
    token: str
    api_url: str

    @property
    def headers(self) -> Dict:
        return get_auth_headers(self.username, self.token)

    @property
    def site_url(self) -> str:
        return self.api_url.replace("/wp-json/wp/v2", "")


def lookup_post_by_slug(slug: str, auth: WordPressAuth) -> Optional[Dict]:
    """Return {id, status} for an existing post with this slug, else None."""
    response = requests.get(
        f"{auth.api_url}/posts",
        headers=auth.headers,
        params={"slug": slug, "status": "any"},
        timeout=DEFAULT_TIMEOUT,
    )
    if response.status_code != 200:
        return None
    results = response.json()
    if not results:
        return None
    return {"id": results[0]["id"], "status": results[0].get("status", "")}


def is_live(post: Optional[Dict]) -> bool:
    """True when an existing post is already serving readers."""
    return bool(post) and post["status"] in LIVE_STATUSES


def build_wp_preview_url(post_id: int, auth: WordPressAuth) -> str:
    """Return WordPress's own draft preview URL for a post ID.

    Viewing it requires being logged in to WordPress as a user who can edit
    the post. Used only as a fallback when a public link is unavailable.
    """
    return f"{auth.site_url}/?p={post_id}&preview=true"


def guaranteed_until(expires_in_hours: int) -> str:
    """Return the UTC time a freshly minted preview link is valid until.

    Public Post Preview derives its nonce from a tick of `expiry / 2`, and
    accepts the current tick and the previous one. A link is therefore good
    for somewhere between half and all of the configured window, depending on
    where in the tick it was minted. Quote the half, which always holds.
    """
    deadline = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours / 2)
    return deadline.strftime("%Y-%m-%d %H:%M UTC")


def request_public_preview_url(post_id: int, auth: WordPressAuth) -> Optional[Dict]:
    """Return {url, expires} anyone can open without an account, or None.

    Needs two things on the WordPress side: the Public Post Preview plugin,
    and a snippet registering the openteams/v1/public-preview route. Both are
    configured on openteams.com, not in this repo, because the preview nonce
    is derived from the site's NONCE_SALT and can only be minted server side.

    Returning None lets the caller fall back to the login-required URL rather
    than failing the run, so previews still work if the route goes away.
    """
    endpoint = (
        f"{auth.api_url.replace('/wp/v2', '')}/openteams/v1/public-preview/{post_id}"
    )
    try:
        response = requests.post(
            endpoint,
            headers=auth.headers,
            # ModSecurity on this host rejects bodyless POSTs to wp-json with a
            # 406 before they ever reach WordPress. Sending an empty JSON object
            # is enough to get through; without it this silently returns None
            # and every preview quietly falls back to a login-required link.
            json={},
            timeout=DEFAULT_TIMEOUT,
        )
    except requests.RequestException:
        return None
    if response.status_code != 200:
        return None

    payload = response.json()
    url = payload.get("url")
    if not url:
        return None
    return {
        "url": url,
        "expires": guaranteed_until(int(payload.get("expires_in_hours") or 48)),
    }


def frontmatter_status(file_path: str) -> str:
    """Return the raw `status:` value from a post's YAML frontmatter.

    PostMetadata does not model `status`, so extract_post_data drops it and
    post_data never carries one. Reading the raw frontmatter is the only way
    to see what the author actually wrote.
    """
    text = Path(file_path).read_text(encoding="utf-8")
    if not text.startswith("---"):
        return ""
    parts = text.split("---", 2)
    if len(parts) < 3:
        return ""
    meta = yaml.safe_load(parts[1]) or {}
    return str(meta.get("status") or "").strip().lower()


def skip_reason(
    file_path: str, existing: Optional[Dict], pr_number: Optional[int]
) -> Optional[str]:
    """Return why this post cannot be previewed, or None when it can.

    A `status: publish` in frontmatter is silently discarded by the pipeline,
    so the author's stated intent and the actual behaviour disagree. Refuse
    rather than guess which one is right.

    A live slug is only refused without a PR number, since the shadow copy
    that keeps the live article safe is named after the PR.
    """
    if frontmatter_status(file_path) == "publish":
        return (
            "frontmatter sets `status: publish`, which the publish pipeline "
            "ignores. Remove the line to enable previews."
        )
    if is_live(existing) and pr_number is None:
        return (
            f"already published on WordPress (post {existing['id']}), and no "
            "PR number was given to build a shadow preview under."
        )
    return None


def write_shadow_post(file_path: str, slug: str, pr_number: int) -> Path:
    """Write a throwaway copy of the post under a preview-only slug.

    The copy sits in the same directory as the original so relative image
    paths still resolve, and drops wordpress_id/url so it can never resolve
    back to the live post. The caller must delete it.
    """
    original = Path(file_path)
    parts = original.read_text(encoding="utf-8").split("---", 2)
    meta = yaml.safe_load(parts[1]) or {}
    body = parts[2]

    meta["slug"] = f"{slug}{SHADOW_SLUG_SUFFIX}{pr_number}"
    meta["title"] = f"[PR #{pr_number} preview] {meta.get('title') or slug}"
    meta.pop("wordpress_id", None)
    meta.pop("wordpress_url", None)

    shadow = original.with_name(f".preview-pr{pr_number}-{original.name}")
    shadow.write_text(
        "---\n"
        + yaml.safe_dump(meta, sort_keys=False, allow_unicode=True)
        + "---"
        + body,
        encoding="utf-8",
    )
    return shadow


@contextmanager
def publish_target(
    file_path: str, slug: str, pr_number: Optional[int], shadow: bool
) -> Iterator[Tuple[str, str]]:
    """Yield the (path, slug) to publish, removing a shadow copy afterwards."""
    if not shadow:
        yield file_path, slug
        return

    copy = write_shadow_post(file_path, slug, pr_number)
    try:
        yield str(copy), f"{slug}{SHADOW_SLUG_SUFFIX}{pr_number}"
    finally:
        copy.unlink(missing_ok=True)


def create_draft(file_path: str, slug: str, auth: WordPressAuth) -> Optional[Dict]:
    """Publish a file as a draft and return the resulting post, or None.

    process_file reports only success or failure, so the post is re-resolved
    by slug to recover the ID that the preview URL needs.
    """
    if not process_file(
        file_path, auth.username, auth.token, auth.api_url, default_status="draft"
    ):
        return None
    return lookup_post_by_slug(slug, auth)


def describe_preview(post_id: int, auth: WordPressAuth) -> Dict:
    """Return the url/public/expires fields for a created draft."""
    public = request_public_preview_url(post_id, auth)
    if public:
        return {"public": True, "url": public["url"], "expires": public["expires"]}
    return {"public": False, "url": build_wp_preview_url(post_id, auth), "expires": ""}


def preview_file(
    file_path: str, auth: WordPressAuth, pr_number: Optional[int] = None
) -> Dict:
    """Preview one post as a WordPress draft and return a result record."""
    result = {
        "file": file_path,
        "state": "failed",
        "url": "",
        "public": False,
        "shadow": False,
        "expires": "",
        "reason": "",
    }

    post_data = extract_post_data(file_path)
    if not post_data or not post_data.get("slug"):
        return {**result, "reason": "could not read slug from frontmatter"}

    slug = post_data["slug"]
    existing = lookup_post_by_slug(slug, auth)

    reason = skip_reason(file_path, existing, pr_number)
    if reason:
        return {**result, "state": "skipped", "reason": reason}

    shadow = is_live(existing)
    with publish_target(file_path, slug, pr_number, shadow) as (target, target_slug):
        created = create_draft(target, target_slug, auth)

    if not created:
        return {**result, "reason": "could not create the draft; see the log above"}

    return {
        **result,
        **describe_preview(created["id"], auth),
        "state": "ok",
        "shadow": shadow,
    }


def report(result: Dict) -> None:
    """Print a one-line summary of what happened to this post."""
    if result["state"] == "ok":
        kind = "public" if result["public"] else "login required"
        shadow = ", shadow copy" if result["shadow"] else ""
        print(f"✅ Draft preview ({kind}{shadow}): {result['url']}")
    elif result["state"] == "skipped":
        print(f"⏭️  Skipped {result['file']}: {result['reason']}")
    else:
        print(f"❌ Failed {result['file']}: {result['reason']}")


def main():
    parser = argparse.ArgumentParser(
        description="Publish a post as a WordPress draft and report its preview URL."
    )
    parser.add_argument("file", help="Path to a .md or .qmd file to preview")
    parser.add_argument(
        "--result-file",
        help="Append the result to this file as one JSON object per line.",
    )
    parser.add_argument(
        "--pr",
        type=int,
        help="Pull request number. Required to preview a post whose slug is "
        "already live, which is done through a shadow copy named after the PR.",
    )
    args = parser.parse_args()

    username = os.environ.get("WP_USERNAME")
    wp_api_url = os.environ.get("WP_API_URL")
    wp_token = os.environ.get("WP_TOKEN")

    if not all([username, wp_api_url, wp_token]):
        print("❌ Missing environment variables: WP_TOKEN, WP_API_URL, WP_USERNAME")
        sys.exit(1)

    auth = WordPressAuth(username=username, token=wp_token, api_url=wp_api_url)
    result = preview_file(args.file, auth, args.pr)
    report(result)

    if args.result_file:
        with Path(args.result_file).open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(result) + "\n")

    # A skip is a deliberate safety outcome, not a build failure.
    sys.exit(0 if result["state"] in ("ok", "skipped") else 1)


if __name__ == "__main__":
    main()
