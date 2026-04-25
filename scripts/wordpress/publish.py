#!/usr/bin/env python3
"""
WordPress Publish Script

Unified script that creates new WordPress draft posts or syncs updates
to existing posts. Matches posts by slug via the WP REST API: if a post
with the same slug exists, it is updated; otherwise a new draft is
created.

Usage:
    uv run scripts/wordpress/publish.py posts/<slug>/index.md
"""

import os
import sys
from typing import Optional, Dict

import requests

from wordpress_utils import (
    setup_common_args,
    extract_post_data,
    get_auth_headers,
    get_user_id,
    lookup_post_id_by_slug,
    resolve_categories_and_tags,
    convert_markdown_to_html,
    verify_authentication,
    prepare_seo_meta_fields,
    upload_and_replace_article_images,
)

REQUEST_TIMEOUT = 30
SUCCESS_STATUSES = (200, 201)
# Every post gets these WP categories, in addition to anything listed in
# the frontmatter. Case-insensitive match against existing WP categories.
REQUIRED_CATEGORIES = ("Engineering", "Blogs")


def _ensure_required_categories(categories):
    """Return a category list that includes every entry in REQUIRED_CATEGORIES."""
    seen = {c.lower() for c in categories if c}
    merged = list(categories)
    for required in REQUIRED_CATEGORIES:
        if required.lower() not in seen:
            merged.append(required)
            seen.add(required.lower())
    return merged


def _notify_slack_new_post(post_data: Dict, final_url: str) -> None:
    """Fire the design-team Slack workflow when a NEW post is created.

    Sync updates are intentionally excluded so post edits don't re-notify.
    No-op when SLACK_PUBLISH_WEBHOOK is unset (local runs).
    """
    webhook = os.environ.get("SLACK_PUBLISH_WEBHOOK")
    if not webhook:
        return
    try:
        resp = requests.post(
            webhook,
            json={
                "post_title": post_data.get("title") or "",
                "post_url": final_url,
                "author": post_data.get("_author_username") or "",
            },
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            print(f"  ⚠️  Slack notify failed: {resp.status_code}")
    except requests.exceptions.RequestException as exc:
        print(f"  ⚠️  Slack notify error: {exc}")


def _prepare_wp_context(post_data: Dict, wp_token: str, wp_api_url: str, username: str):
    """Authenticate and resolve all WordPress resources needed for a post."""
    current_user = verify_authentication(wp_token, wp_api_url, username)
    if not current_user:
        return None

    headers = get_auth_headers(username, wp_token)
    headers["Content-Type"] = "application/json"

    # The post appears under the frontmatter `author`, not the authenticated
    # user. Fall back to the authenticated user if no author is specified.
    target_author = post_data.get("_author_username") or username
    author_id = get_user_id(target_author, wp_token, wp_api_url, username)
    if not author_id:
        print(f"  ❌ Could not find WordPress user '{target_author}'")
        return None

    html_content = convert_markdown_to_html(post_data.get("content", ""), post_data)
    taxonomy_ids = resolve_categories_and_tags(
        post_data, wp_token, wp_api_url, username
    )
    seo_meta = prepare_seo_meta_fields(post_data)

    return {
        "headers": headers,
        "author_id": author_id,
        "html_content": html_content,
        "taxonomy_ids": taxonomy_ids,
        "seo_meta": seo_meta,
    }


def _build_wp_payload(post_data: Dict, context: Dict, *, include_create_fields: bool) -> Dict:
    """Build the WordPress API payload from post data and resolved context.

    Args:
        post_data: Extracted frontmatter and content from the markdown file.
        context: Resolved WordPress context from _prepare_wp_context.
        include_create_fields: True for new posts (adds slug, author, format).
    """
    payload = {
        "title": post_data["title"],
        "content": context["html_content"],
        "author": context["author_id"],
    }

    if include_create_fields:
        payload["slug"] = post_data["slug"]
        payload["format"] = "standard"
        payload["status"] = post_data.get("status") or post_data.get("_default_status", "draft")
    elif post_data.get("status"):
        payload["status"] = post_data["status"]

    if context["taxonomy_ids"]["category_ids"]:
        payload["categories"] = context["taxonomy_ids"]["category_ids"]
    if context["taxonomy_ids"]["tag_ids"]:
        payload["tags"] = context["taxonomy_ids"]["tag_ids"]
    if context["seo_meta"]:
        payload["meta"] = context["seo_meta"]

    return payload


def _build_published_url(wp_api_url: str, wp_post: Dict, post_data: Dict) -> str:
    """Construct the final published URL from the API base and post slug."""
    base_domain = wp_api_url.replace("/wp-json/wp/v2", "")
    slug = wp_post.get("slug") or post_data.get("slug") or ""
    return f"{base_domain}/{slug}/" if slug else base_domain


def _send_wp_request(method: str, url: str, headers: Dict, payload: Dict) -> Optional[requests.Response]:
    """Send a request to the WordPress API with consistent error handling."""
    try:
        response = requests.request(
            method, url, headers=headers, json=payload, timeout=REQUEST_TIMEOUT
        )
        if response.status_code in SUCCESS_STATUSES:
            return response
        print("❌ WordPress API error")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")
        return None
    except requests.exceptions.RequestException as e:
        print(f"❌ WordPress request failed: {e}")
        return None


def create_post(
    post_data: Dict,
    wp_token: str,
    wp_api_url: str,
    username: str,
) -> Optional[Dict]:
    """Create a new WordPress post as draft."""
    context = _prepare_wp_context(post_data, wp_token, wp_api_url, username)
    if not context:
        return None

    payload = _build_wp_payload(post_data, context, include_create_fields=True)
    response = _send_wp_request("POST", f"{wp_api_url}/posts", context["headers"], payload)
    return response.json() if response else None


def sync_post(
    post_data: Dict,
    wp_token: str,
    wp_api_url: str,
    username: str,
) -> bool:
    """Update an existing WordPress post."""
    post_id = post_data["wordpress_id"]

    context = _prepare_wp_context(post_data, wp_token, wp_api_url, username)
    if not context:
        print("❌ Authentication failed")
        return False

    payload = _build_wp_payload(post_data, context, include_create_fields=False)
    response = _send_wp_request("PUT", f"{wp_api_url}/posts/{post_id}", context["headers"], payload)

    if response:
        result = response.json()
        print(f"✅ Updated WordPress post {post_id}: {result.get('link', 'Unknown')}")
        return True
    return False


def _validate_and_prepare(
    file_path: str, username: str, wp_token: str, wp_api_url: str
) -> Optional[Dict]:
    """Extract post data, validate required fields, and upload images."""
    post_data = extract_post_data(file_path)
    if not post_data:
        print("  ❌ Could not extract data from file")
        return None

    if not (post_data.get("title") or "").strip():
        print("❌ Missing title")
        return None

    post_data["content"] = upload_and_replace_article_images(
        post_data["content"], file_path, wp_token, wp_api_url, username
    )
    post_data["_author_username"] = post_data.get("author") or username
    post_data["categories"] = _ensure_required_categories(
        post_data.get("categories", [])
    )

    print(f"Title: {post_data['title']}")
    print(f"Slug: {post_data['slug']}")
    print(f"Author: {post_data['_author_username']}")

    return post_data


def _sync_existing_post(
    post_data: Dict, wp_token: str, wp_api_url: str, username: str
) -> bool:
    """Sync updates to an existing WordPress post."""
    print(f"Mode: sync (wordpress_id: {post_data['wordpress_id']})")
    return sync_post(post_data, wp_token, wp_api_url, username)


def _create_new_post(
    post_data: Dict, wp_api_url: str, wp_token: str, username: str
) -> bool:
    """Create a new WordPress draft post."""
    print("Mode: create (new draft)")
    wp_post = create_post(post_data, wp_token, wp_api_url, username)
    if not wp_post:
        print("  ❌ Failed to create WordPress post")
        return False

    final_url = _build_published_url(wp_api_url, wp_post, post_data)
    print(f"Draft URL: {wp_post['link']}")
    print(f"Published URL: {final_url}")
    _notify_slack_new_post(post_data, final_url)
    return True


def process_file(
    file_path: str,
    username: str,
    wp_token: str,
    wp_api_url: str,
    default_status: str = "draft",
) -> bool:
    """Publish or sync a markdown file to WordPress.

    default_status is used for NEW posts only and only when frontmatter
    does not specify `status`. Sync mode preserves whatever status the
    post already has in WordPress.
    """
    post_data = _validate_and_prepare(file_path, username, wp_token, wp_api_url)
    if not post_data:
        return False
    post_data["_default_status"] = default_status

    existing_id = lookup_post_id_by_slug(
        post_data["slug"], wp_token, wp_api_url, username
    )
    if existing_id:
        post_data["wordpress_id"] = existing_id
        return _sync_existing_post(post_data, wp_token, wp_api_url, username)
    return _create_new_post(post_data, wp_api_url, wp_token, username)


def main():
    """Main entry point."""
    parser = setup_common_args(
        "Publish or sync a blog post to WordPress.\n"
        "Creates a new draft if no post with the same slug exists, "
        "or syncs updates to the existing post."
    )
    parser.add_argument(
        "--status",
        choices=("draft", "publish"),
        default="draft",
        help="Status to use for NEW posts when frontmatter doesn't specify one. "
        "Default: draft (safe for local testing). Use 'publish' in CI to make "
        "merged posts live.",
    )
    args = parser.parse_args()

    username = os.environ.get("WP_USERNAME")
    wp_api_url = os.environ.get("WP_API_URL")
    wp_token = os.environ.get("WP_TOKEN")

    if not all([username, wp_api_url, wp_token]):
        print("❌ Missing environment variables. Ensure .env has:")
        print("   WP_TOKEN, WP_API_URL, WP_USERNAME")
        sys.exit(1)

    success = process_file(
        args.file, username, wp_token, wp_api_url, default_status=args.status
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
