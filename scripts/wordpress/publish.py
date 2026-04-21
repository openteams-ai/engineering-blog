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

import hashlib
import os
import sys
import tempfile
from pathlib import Path
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
    upload_image_to_wordpress,
)

REQUEST_TIMEOUT = 30
SUCCESS_STATUSES = (200, 201)
FEATURED_IMAGE_EXTENSIONS = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


def _resolve_featured_media_id(
    post_data: Dict,
    file_path: str,
    wp_token: str,
    wp_api_url: str,
    username: str,
) -> Optional[int]:
    """Resolve `featured_image` frontmatter to a WordPress media ID.

    Accepts either a local path (resolved relative to the post file) or an
    absolute http(s) URL. Returns None when no featured image is configured
    or when upload fails.
    """
    featured = (post_data.get("featured_image") or "").strip()
    if not featured:
        return None

    if featured.startswith(("http://", "https://")):
        return _upload_featured_image_from_url(
            featured, wp_token, wp_api_url, username
        )

    local_path = Path(file_path).parent / featured
    if not local_path.exists():
        print(f"  ⚠️  Featured image not found: {local_path}")
        return None

    media = upload_image_to_wordpress(local_path, wp_token, wp_api_url, username)
    if not media:
        return None
    print(f"  Featured image: {local_path.name} (id={media['id']})")
    return media["id"]


def _upload_featured_image_from_url(
    image_url: str, wp_token: str, wp_api_url: str, username: str
) -> Optional[int]:
    """Download a featured image from a URL and upload to WordPress.

    Uses a hash of the source URL in the uploaded filename so that changing
    the URL in frontmatter triggers a fresh upload instead of reusing the
    old media item.
    """
    resp = requests.get(
        image_url,
        headers={"User-Agent": "OpenTeams-Engineering-Blog/1.0"},
        timeout=REQUEST_TIMEOUT,
    )
    if resp.status_code != 200:
        print(f"  ⚠️  Failed to download featured image: {resp.status_code}")
        return None

    content_type = resp.headers.get("Content-Type", "image/png").split(";")[0].strip()
    extension = FEATURED_IMAGE_EXTENSIONS.get(content_type, ".png")
    url_hash = hashlib.sha256(image_url.encode("utf-8")).hexdigest()[:8]
    filename = f"featured-{url_hash}{extension}"

    with tempfile.NamedTemporaryFile(suffix=extension, delete=False) as tmp:
        tmp.write(resp.content)
        tmp_path = Path(tmp.name)

    try:
        renamed = tmp_path.with_name(filename)
        tmp_path.rename(renamed)
        media = upload_image_to_wordpress(renamed, wp_token, wp_api_url, username)
    finally:
        for p in (tmp_path, tmp_path.with_name(filename)):
            if p.exists():
                p.unlink()

    if not media:
        return None
    print(f"  Featured image: {filename} (id={media['id']})")
    return media["id"]


def _prepare_wp_context(post_data: Dict, wp_token: str, wp_api_url: str, username: str):
    """Authenticate and resolve all WordPress resources needed for a post."""
    current_user = verify_authentication(wp_token, wp_api_url, username)
    if not current_user:
        return None

    headers = get_auth_headers(username, wp_token)
    headers["Content-Type"] = "application/json"

    html_content = convert_markdown_to_html(post_data.get("content", ""), post_data)
    taxonomy_ids = resolve_categories_and_tags(
        post_data, wp_token, wp_api_url, username
    )
    seo_meta = prepare_seo_meta_fields(post_data)

    return {
        "headers": headers,
        "author_id": current_user["id"],
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
    }

    if include_create_fields:
        payload["slug"] = post_data["slug"]
        payload["author"] = context["author_id"]
        payload["format"] = "standard"
        payload["status"] = post_data.get("status", "draft")
    elif post_data.get("status"):
        payload["status"] = post_data["status"]

    if context["taxonomy_ids"]["category_ids"]:
        payload["categories"] = context["taxonomy_ids"]["category_ids"]
    if context["taxonomy_ids"]["tag_ids"]:
        payload["tags"] = context["taxonomy_ids"]["tag_ids"]
    if context["seo_meta"]:
        payload["meta"] = context["seo_meta"]
    if post_data.get("_featured_media_id"):
        payload["featured_media"] = post_data["_featured_media_id"]

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
    author_id: int,
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
    post_data["_featured_media_id"] = _resolve_featured_media_id(
        post_data, file_path, wp_token, wp_api_url, username
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
    author_username = post_data["_author_username"]
    author_id = get_user_id(author_username, wp_token, wp_api_url, username)
    if not author_id:
        print(f"  ❌ Could not find WordPress user '{author_username}'")
        return False

    wp_post = create_post(post_data, author_id, wp_token, wp_api_url, username)
    if not wp_post:
        print("  ❌ Failed to create WordPress post")
        return False

    final_url = _build_published_url(wp_api_url, wp_post, post_data)
    print(f"Draft URL: {wp_post['link']}")
    print(f"Published URL: {final_url}")
    return True


def process_file(
    file_path: str, username: str, wp_token: str, wp_api_url: str
) -> bool:
    """Publish or sync a markdown file to WordPress."""
    post_data = _validate_and_prepare(file_path, username, wp_token, wp_api_url)
    if not post_data:
        return False

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
    args = parser.parse_args()

    username = os.environ.get("WP_USERNAME")
    wp_api_url = os.environ.get("WP_API_URL")
    wp_token = os.environ.get("WP_TOKEN")

    if not all([username, wp_api_url, wp_token]):
        print("❌ Missing environment variables. Ensure .env has:")
        print("   WP_TOKEN, WP_API_URL, WP_USERNAME")
        sys.exit(1)

    success = process_file(args.file, username, wp_token, wp_api_url)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
