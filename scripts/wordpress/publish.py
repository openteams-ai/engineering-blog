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
    get_ppma_author_term_ids,
    lookup_post_id_by_slug,
    resolve_categories_and_tags,
    convert_markdown_to_html,
    verify_authentication,
    prepare_seo_meta_fields,
    upload_and_replace_article_images,
    update_qmd_metadata,
    build_published_url,
    ImageUploadError,
)

REQUEST_TIMEOUT = 30
SUCCESS_STATUSES = (200, 201)
# Every post gets these WP categories, in addition to anything listed in
# the frontmatter. Case-insensitive match against existing WP categories.
REQUIRED_CATEGORIES = ("Engineering",)


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

    # Resolve all authors against PublishPress Authors. Returns None when
    # the plugin is not installed; in that case the post falls back to
    # the standard single-author WP behavior via author_id.
    authors = post_data.get("authors") or []
    ppma_author_ids = get_ppma_author_term_ids(
        authors, wp_token, wp_api_url, username
    )

    # PublishPress renders the byline, and an update that omits ppma_author
    # leaves whatever the post already had. Silently keeping a previous
    # author's name is worse than refusing to publish.
    if authors and ppma_author_ids == []:
        print(f"  ❌ No PublishPress author term for: {', '.join(authors)}")
        print("     Run sync_authors.py so the byline resolves.")
        return None

    return {
        "headers": headers,
        "author_id": author_id,
        "ppma_author_ids": ppma_author_ids,
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
        "comment_status": "closed",
        "ping_status": "closed",
    }

    if include_create_fields:
        payload["slug"] = post_data["slug"]
        payload["format"] = "standard"
        payload["status"] = post_data.get("status") or post_data.get("_default_status", "draft")
    elif post_data.get("status"):
        payload["status"] = post_data["status"]
    elif post_data.get("_default_status") == "publish":
        # An explicit `--status publish` run means "make this live", including
        # when the post already exists as a draft because the PR preview
        # created it. Without this, a previewed post syncs its content on
        # merge but silently stays a draft.
        payload["status"] = "publish"

    if context["taxonomy_ids"]["category_ids"]:
        payload["categories"] = context["taxonomy_ids"]["category_ids"]
    if context["taxonomy_ids"]["tag_ids"]:
        payload["tags"] = context["taxonomy_ids"]["tag_ids"]
    if context["seo_meta"]:
        payload["meta"] = context["seo_meta"]
    if context.get("ppma_author_ids"):
        payload["ppma_author"] = context["ppma_author_ids"]

    return payload


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
) -> Optional[Dict]:
    """Update an existing WordPress post and return the API response."""
    post_id = post_data["wordpress_id"]

    context = _prepare_wp_context(post_data, wp_token, wp_api_url, username)
    if not context:
        print("❌ Authentication failed")
        return None

    payload = _build_wp_payload(post_data, context, include_create_fields=False)
    response = _send_wp_request("PUT", f"{wp_api_url}/posts/{post_id}", context["headers"], payload)

    if response:
        result = response.json()
        print(f"✅ Updated WordPress post {post_id}: {result.get('link', 'Unknown')}")
        return result
    return None


def _record_wp_identifiers(file_path: str, post_data: Dict, wp_id: int, wp_url: str) -> None:
    """Write wordpress_id/url back to frontmatter when missing or out-of-date."""
    if post_data.get("wordpress_id") == wp_id and post_data.get("wordpress_url") == wp_url:
        return
    if update_qmd_metadata(file_path, {"wordpress_id": wp_id, "wordpress_url": wp_url}):
        print(f"📝 Updated frontmatter in {file_path}")


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

    # Without this the post would publish under whoever owns the CI
    # credentials, which is nobody's intent and gives no error.
    if not (post_data.get("authors") or []):
        print("❌ Missing authors")
        print("   Add an `authors:` list to the frontmatter naming who wrote this.")
        return None

    try:
        post_data["content"] = upload_and_replace_article_images(
            post_data["content"], file_path, wp_token, wp_api_url, username
        )
    except ImageUploadError as error:
        print(f"  ❌ {error}")
        print("     Publishing anyway would leave a broken image on the live site.")
        return None
    authors = post_data.get("authors") or []
    post_data["_author_username"] = authors[0] if authors else username
    post_data["categories"] = _ensure_required_categories(
        post_data.get("categories", [])
    )

    print(f"Title: {post_data['title']}")
    print(f"Slug: {post_data['slug']}")
    authors_display = ", ".join(authors) if authors else post_data["_author_username"]
    print(f"Authors: {authors_display}")

    return post_data


def _sync_existing_post(
    file_path: str, post_data: Dict, wp_token: str, wp_api_url: str, username: str
) -> bool:
    """Sync updates to an existing WordPress post."""
    print(f"Mode: sync (wordpress_id: {post_data['wordpress_id']})")
    wp_post = sync_post(post_data, wp_token, wp_api_url, username)
    if not wp_post:
        return False

    slug = wp_post.get("slug") or post_data.get("slug") or ""
    final_url = build_published_url(wp_api_url, slug)
    _record_wp_identifiers(file_path, post_data, wp_post["id"], final_url)
    return True


def _create_new_post(
    file_path: str, post_data: Dict, wp_api_url: str, wp_token: str, username: str
) -> bool:
    """Create a new WordPress draft post."""
    print("Mode: create (new draft)")
    wp_post = create_post(post_data, wp_token, wp_api_url, username)
    if not wp_post:
        print("  ❌ Failed to create WordPress post")
        return False

    slug = wp_post.get("slug") or post_data.get("slug") or ""
    final_url = build_published_url(wp_api_url, slug)
    print(f"Draft URL: {wp_post['link']}")
    print(f"Published URL: {final_url}")
    _record_wp_identifiers(file_path, post_data, wp_post["id"], final_url)
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
        return _sync_existing_post(file_path, post_data, wp_token, wp_api_url, username)
    return _create_new_post(file_path, post_data, wp_api_url, wp_token, username)


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
