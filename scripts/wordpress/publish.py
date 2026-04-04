#!/usr/bin/env python3
"""
WordPress Publish Script

Unified script that creates new WordPress draft posts or syncs updates
to existing posts. Determines behavior based on whether the file already
has a wordpress_id in its YAML frontmatter.

Usage:
    uv run scripts/wordpress/publish.py posts/<slug>/index.md
"""

import os
import sys
import time
import requests
from typing import Optional, Dict

from wordpress_utils import (
    setup_common_args,
    has_wordpress_id,
    extract_post_data,
    get_auth_headers,
    get_user_id,
    resolve_categories_and_tags,
    convert_markdown_to_html,
    verify_authentication,
    update_qmd_metadata,
    prepare_yoast_meta_fields,
    upload_and_replace_article_images,
)

REQUEST_TIMEOUT = 30
SUCCESS_STATUSES = (200, 201)


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
    yoast_meta = prepare_yoast_meta_fields(post_data)

    return {
        "headers": headers,
        "author_id": current_user["id"],
        "html_content": html_content,
        "taxonomy_ids": taxonomy_ids,
        "yoast_meta": yoast_meta,
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
    if context["yoast_meta"]:
        payload["meta"] = context["yoast_meta"]

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


def process_file(
    file_path: str, username: str, wp_token: str, wp_api_url: str
) -> bool:
    """Process a file: create new post or sync existing one."""
    post_data = extract_post_data(file_path)
    if not post_data:
        print("  ❌ Could not extract data from file")
        return False

    if not (post_data.get("title") or "").strip():
        print("❌ Missing title")
        return False

    # Upload local images to WordPress and replace paths
    post_data["content"] = upload_and_replace_article_images(
        post_data["content"], file_path, wp_token, wp_api_url, username
    )

    # Resolve author: use frontmatter 'author' field if set, otherwise fall back to env USERNAME
    author_username = post_data.get("author") or username

    print(f"Title: {post_data['title']}")
    print(f"Slug: {post_data['slug']}")
    print(f"Author: {author_username}")

    if has_wordpress_id(file_path):
        # Sync existing post
        print(f"Mode: sync (wordpress_id: {post_data['wordpress_id']})")
        if sync_post(post_data, wp_token, wp_api_url, username):
            metadata_updates = {"last_synced": time.strftime("%Y-%m-%dT%H:%M:%SZ")}
            update_qmd_metadata(file_path, metadata_updates, mode="update")
            return True
        return False
    else:
        # Create new post
        print("Mode: create (new draft)")
        author_id = get_user_id(author_username, wp_token, wp_api_url, username)
        if not author_id:
            print(f"  ❌ Could not find WordPress user '{author_username}'")
            print(f"     Ensure this user exists on WordPress")
            return False

        wp_post = create_post(
            post_data, author_id, wp_token, wp_api_url, username
        )
        if not wp_post:
            print("  ❌ Failed to create WordPress post")
            return False

        post_id = wp_post["id"]
        final_url = _build_published_url(wp_api_url, wp_post, post_data)

        print(f"Draft URL: {wp_post['link']}")
        print(f"Published URL: {final_url}")

        metadata_updates = {
            "wordpress_url": final_url,
            "wordpress_id": post_id,
            "last_synced": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        if update_qmd_metadata(file_path, metadata_updates, mode="create"):
            return True
        else:
            print(f"  ❌ Failed to update {file_path}")
            return False


def main():
    """Main entry point."""
    parser = setup_common_args(
        "Publish or sync a blog post to WordPress.\n"
        "Creates a new draft if no wordpress_id exists, "
        "or syncs updates if wordpress_id is present."
    )
    args = parser.parse_args()

    username = os.environ.get("USERNAME")
    wp_api_url = os.environ.get("WP_API_URL")
    wp_token = os.environ.get("WP_TOKEN")

    if not all([username, wp_api_url, wp_token]):
        print("❌ Missing environment variables. Ensure .env has:")
        print("   WP_TOKEN, WP_API_URL, USERNAME")
        sys.exit(1)

    success = process_file(args.file, username, wp_token, wp_api_url)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
