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


def create_post(
    post_data: Dict,
    author_id: int,
    wp_token: str,
    wp_api_url: str,
    username: str,
) -> Optional[Dict]:
    """Create a new WordPress post as draft."""
    headers = get_auth_headers(username, wp_token)
    headers["Content-Type"] = "application/json"

    current_user = verify_authentication(wp_token, wp_api_url, username)
    if current_user:
        author_id = current_user["id"]

    taxonomy_ids = resolve_categories_and_tags(
        post_data, wp_token, wp_api_url, username
    )

    html_content = convert_markdown_to_html(post_data.get("content", ""), post_data)
    yoast_meta = prepare_yoast_meta_fields(post_data)

    wp_post_data = {
        "title": post_data["title"],
        "content": html_content,
        "slug": post_data["slug"],
        "status": post_data.get("status", "draft"),
        "author": author_id,
        "format": "standard",
    }

    if yoast_meta:
        wp_post_data["meta"] = yoast_meta
    if taxonomy_ids["category_ids"]:
        wp_post_data["categories"] = taxonomy_ids["category_ids"]
    if taxonomy_ids["tag_ids"]:
        wp_post_data["tags"] = taxonomy_ids["tag_ids"]

    try:
        response = requests.post(
            f"{wp_api_url}/posts", headers=headers, json=wp_post_data, timeout=30
        )
        if response.status_code in [200, 201]:
            return response.json()
        else:
            print(f"❌ Failed to create WordPress post")
            print(f"   Status: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return None
    except requests.exceptions.RequestException as e:
        print(f"❌ Error creating WordPress post: {e}")
        return None


def sync_post(
    post_data: Dict,
    wp_token: str,
    wp_api_url: str,
    username: str,
) -> bool:
    """Update an existing WordPress post."""
    post_id = post_data["wordpress_id"]

    headers = get_auth_headers(username, wp_token)
    headers["Content-Type"] = "application/json"

    current_user = verify_authentication(wp_token, wp_api_url, username)
    if not current_user:
        print("❌ Authentication failed")
        return False

    html_content = convert_markdown_to_html(post_data["content"], post_data)
    taxonomy_ids = resolve_categories_and_tags(
        post_data, wp_token, wp_api_url, username
    )
    yoast_meta = prepare_yoast_meta_fields(post_data)

    data = {"content": html_content, "title": post_data["title"]}

    if post_data.get("status"):
        data["status"] = post_data["status"]
    if taxonomy_ids["category_ids"]:
        data["categories"] = taxonomy_ids["category_ids"]
    if taxonomy_ids["tag_ids"]:
        data["tags"] = taxonomy_ids["tag_ids"]
    if yoast_meta:
        data["meta"] = yoast_meta

    response = requests.put(
        f"{wp_api_url}/posts/{post_id}", headers=headers, json=data, timeout=30
    )

    if response.status_code in [200, 201]:
        result = response.json()
        print(f"✅ Updated WordPress post {post_id}: {result.get('link', 'Unknown')}")
        return True
    else:
        print(f"❌ Failed to update WordPress post {post_id}")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:200]}...")
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
        preview_url = wp_post["link"]
        base_domain = wp_api_url.replace("/wp-json/wp/v2", "")
        slug_for_url = wp_post.get("slug") or post_data.get("slug") or ""
        final_url = f"{base_domain}/{slug_for_url}/" if slug_for_url else base_domain

        print(f"Draft URL: {preview_url}")
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
