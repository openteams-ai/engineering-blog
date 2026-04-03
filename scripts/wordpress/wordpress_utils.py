#!/usr/bin/env python3
"""
WordPress Utilities - Shared functions for WordPress integration

Contains common functionality for publishing and syncing blog posts
to WordPress via the REST API.
"""

import os
import argparse
import re
import requests
import base64
import markdown
from pathlib import Path
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, field_validator

from dotenv import load_dotenv

# Load .env from project root (two levels up from scripts/wordpress/)
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(os.path.dirname(os.path.dirname(script_dir)), ".env")
load_dotenv(env_path, override=True)


def setup_common_args(description: str) -> argparse.ArgumentParser:
    """Create ArgumentParser with common WordPress script arguments."""
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", help="Path to a .md or .qmd file to process")
    return parser


def is_valid_slug(slug: str) -> bool:
    """Validate WordPress slug format."""
    pattern = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    return bool(re.match(pattern, slug)) and 3 <= len(slug) <= 50


class PostMetadata(BaseModel):
    """Validated post metadata with type safety."""

    title: Optional[str] = None
    slug: Optional[str] = None
    wordpress_id: Optional[int] = None
    categories: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    meta_description: Optional[str] = None
    focus_keyword: Optional[str] = None
    seo_keywords: List[str] = Field(default_factory=list)

    @field_validator("seo_keywords", mode="before")
    @classmethod
    def ensure_list(cls, v: Any):
        return v if isinstance(v, list) else []

    @field_validator(
        "title", "slug", "meta_description", "focus_keyword", mode="before"
    )
    @classmethod
    def ensure_optional_str(cls, v: Any):
        return v if isinstance(v, str) else None

    @field_validator("wordpress_id", mode="before")
    @classmethod
    def ensure_optional_int(cls, v: Any):
        return v if isinstance(v, int) else None

    @classmethod
    def from_yaml(cls, meta: dict) -> "PostMetadata":
        """Create instance with type validation from YAML dict."""
        return cls.model_validate(meta or {})


def extract_post_data(file_path: str) -> Dict:
    """Extract post data from .md or .qmd file."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Split frontmatter and body
    if content.startswith("---"):
        parts = content.split("---", 2)
        yaml_content = parts[1]
        markdown_content = parts[2].strip() if len(parts) >= 3 else content
    else:
        yaml_content = ""
        markdown_content = content

    import yaml as _yaml

    meta = {}
    if yaml_content:
        meta = _yaml.safe_load(yaml_content) or {}

    validated_meta = PostMetadata.from_yaml(meta)

    title = validated_meta.title

    # Remove first H1 heading if exists
    if markdown_content.strip().startswith("# "):
        lines = markdown_content.split("\n")
        remaining_lines = lines[1:]
        while remaining_lines and remaining_lines[0].strip() == "":
            remaining_lines.pop(0)
        markdown_content = "\n".join(remaining_lines)

    return {
        "title": title,
        "content": markdown_content,
        "categories": validated_meta.categories,
        "tags": validated_meta.tags,
        "slug": validated_meta.slug,
        "wordpress_id": validated_meta.wordpress_id,
        "meta_description": validated_meta.meta_description,
        "focus_keyword": validated_meta.focus_keyword,
        "seo_keywords": validated_meta.seo_keywords,
    }


def get_auth_headers(username: str, wp_token: str) -> Dict[str, str]:
    """Create authentication headers for WordPress Application Password."""
    credentials = f"{username}:{wp_token}"
    encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
    return {"Authorization": f"Basic {encoded_credentials}"}


def get_user_id(username: str, wp_token: str, wp_api_url: str) -> Optional[int]:
    """Get WordPress user ID from username."""
    headers = get_auth_headers(username, wp_token)
    response = requests.get(
        f"{wp_api_url}/users?search={username}", headers=headers, timeout=10
    )

    if response.status_code == 200:
        users = response.json()
        for user in users:
            if user["slug"] == username:
                return user["id"]

    print(f"⚠️  User '{username}' not found")


def get_categories_map(wp_token: str, wp_api_url: str, username: str) -> Dict[str, int]:
    """Return a mapping of category name (lowercased) -> ID from WordPress."""
    headers = get_auth_headers(username, wp_token)
    response = requests.get(
        f"{wp_api_url}/categories?per_page=100",
        headers=headers,
        timeout=10,
    )
    if response.status_code == 200:
        categories = response.json()
        return {cat["name"].lower(): cat["id"] for cat in categories}
    else:
        print(f"⚠️  Could not fetch categories: {response.status_code}")
        return {}


def get_or_create_tag(
    tag_name: str, wp_token: str, wp_api_url: str, username: str
) -> Optional[int]:
    """Get tag ID by name, create if it doesn't exist."""
    headers = get_auth_headers(username, wp_token)

    response = requests.get(
        f"{wp_api_url}/tags?search={tag_name}", headers=headers, timeout=10
    )

    if response.status_code == 200:
        tags = response.json()
        for tag in tags:
            if tag["name"].lower() == tag_name.lower():
                return tag["id"]

    # Tag doesn't exist, create it
    create_data = {
        "name": tag_name,
        "description": f"Auto-created tag for {tag_name}",
    }

    response = requests.post(
        f"{wp_api_url}/tags", headers=headers, json=create_data, timeout=10
    )

    if response.status_code in [200, 201]:
        new_tag = response.json()
        return new_tag["id"]
    else:
        print(f"    ❌ Failed to create tag '{tag_name}': {response.status_code}")
        print(f"       Response: {response.text[:100]}...")
        return None


def resolve_categories_and_tags(
    post_data: Dict, wp_token: str, wp_api_url: str, username: str
) -> Dict[str, List[int]]:
    """Resolve category and tag names to WordPress IDs.

    Categories are matched by name (case-insensitive) against existing WP categories.
    Tags are matched by name; missing tags are auto-created.
    """
    cat_map = get_categories_map(wp_token, wp_api_url, username)

    return {
        "category_ids": [
            cat_map[c.lower()]
            for c in post_data.get("categories", [])
            if c and c.lower() in cat_map
        ],
        "tag_ids": [
            tag_id
            for t in post_data.get("tags", [])
            if t and (tag_id := get_or_create_tag(t, wp_token, wp_api_url, username))
        ],
    }


def convert_markdown_to_html(
    markdown_content: str, post_data: Optional[Dict] = None
) -> str:
    """Convert markdown content to HTML for WordPress."""
    # Remove code blocks with #| echo: false
    echo_false_pattern = r"```\{(\w+)\}\s*\n\s*#\|\s*echo:\s*false\s*\n.*?```"
    processed_content = re.sub(
        echo_false_pattern, "", markdown_content, flags=re.DOTALL
    )

    # Convert plain code blocks to ```text for consistent styling
    def fix_plain_code_blocks(content):
        lines = content.split("\n")
        for i, line in enumerate(lines):
            if line.strip() == "```":
                if (
                    i + 1 < len(lines)
                    and lines[i + 1].strip()
                    and not lines[i + 1].strip().startswith("```")
                ):
                    lines[i] = "```text"
        return "\n".join(lines)

    processed_content = fix_plain_code_blocks(processed_content)

    # Convert Quarto-style code blocks to standard markdown
    processed_content = re.sub(r"```\{(\w+)\}", r"```\1", processed_content)

    # Extract mermaid blocks before markdown processing
    mermaid_blocks = {}
    mermaid_pattern = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)

    def stash_mermaid(m):
        key = f"MERMAIDBLOCK{len(mermaid_blocks)}MERMAIDBLOCK"
        diagram = m.group(1).strip()
        if not diagram.startswith("%%{init"):
            diagram = '%%{init: {"theme": "dark"}}%%\n' + diagram
        mermaid_blocks[key] = diagram
        return key

    processed_content = mermaid_pattern.sub(stash_mermaid, processed_content)

    # Convert markdown to HTML
    md = markdown.Markdown(
        extensions=[
            "tables",
            "fenced_code",
            "nl2br",
            "attr_list",
            "def_list",
            "abbr",
            "footnotes",
            "md_in_html",
        ]
    )
    html_content = md.convert(processed_content)

    # Restore mermaid blocks as renderable HTML
    for key, diagram in mermaid_blocks.items():
        html_content = html_content.replace(
            f"<p>{key}</p>",
            f'<!-- wp:html --><pre class="mermaid" style="text-align:center;">{diagram}</pre><!-- /wp:html -->',
        )
        html_content = html_content.replace(
            key,
            f'<!-- wp:html --><pre class="mermaid" style="text-align:center;">{diagram}</pre><!-- /wp:html -->',
        )

    # Wrap tables in scrollable containers
    html_content = re.sub(
        r"(<table.*?</table>)",
        r'<div style="overflow-x: auto;">\1</div>',
        html_content,
        flags=re.DOTALL,
    )

    # Inject mermaid.js if any diagrams are present
    if mermaid_blocks:
        mermaid_script = (
            "\n<!-- wp:html -->\n"
            '<style>pre.mermaid { background: transparent !important; padding: 0 !important; } '
            "pre.mermaid svg { background: transparent !important; } "
            "pre.mermaid .cluster rect { fill: transparent !important; stroke: #555 !important; }</style>\n"
            '<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>\n'
            "<script>mermaid.initialize({startOnLoad:true});</script>\n"
            "<!-- /wp:html -->"
        )
        html_content += mermaid_script

    return html_content


def verify_authentication(
    wp_token: str, wp_api_url: str, username: str
) -> Optional[Dict]:
    """Verify authentication and return current user info."""
    headers = get_auth_headers(username, wp_token)

    auth_check = requests.get(f"{wp_api_url}/users/me", headers=headers, timeout=10)
    if auth_check.status_code == 401:
        print("  ❌ Authentication failed - token may be invalid")
        return None
    elif auth_check.status_code == 200:
        return auth_check.json()


def update_qmd_metadata(
    file_path: str, metadata_updates: Dict, mode: str = "create"
) -> bool:
    """Update WordPress metadata in .md/.qmd file frontmatter."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if not content.startswith("---"):
        print(f"⚠️  No YAML frontmatter found in {file_path}")
        return False

    parts = content.split("---", 2)
    if len(parts) < 3:
        print(f"⚠️  Invalid YAML frontmatter in {file_path}")
        return False

    yaml_content = parts[1]
    after_yaml = parts[2]

    import yaml as _yaml

    meta = _yaml.safe_load(yaml_content) or {}

    for field, value in metadata_updates.items():
        meta[field] = value

    updated_yaml = _yaml.safe_dump(meta, sort_keys=False)
    new_content = f"---\n{updated_yaml}---{after_yaml}"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    return True


def prepare_yoast_meta_fields(post_data: Dict) -> Dict[str, str]:
    """Convert SEO fields to Yoast SEO meta field format."""
    import json

    yoast_meta = {}

    if post_data.get("meta_description"):
        yoast_meta["_yoast_wpseo_metadesc"] = post_data["meta_description"]

    if post_data.get("focus_keyword"):
        yoast_meta["_yoast_wpseo_focuskw"] = post_data["focus_keyword"]

    if post_data.get("seo_keywords"):
        keywords_json = json.dumps(
            [
                {"keyword": keyword.strip(), "score": 0}
                for keyword in post_data["seo_keywords"]
            ]
        )
        yoast_meta["_yoast_wpseo_focuskeywords"] = keywords_json

    return yoast_meta


def has_wordpress_id(file_path: str) -> bool:
    """Check if file already has wordpress_id in frontmatter."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return bool(re.search(r"^wordpress_id:", content, re.MULTILINE))


def upload_image_to_wordpress(
    file_path: str | Path,
    wp_token: str,
    wp_api_url: str,
    username: str,
) -> Optional[str]:
    """Upload an image to WordPress media library if not already uploaded.

    Returns the WordPress URL (source_url) or None on failure.
    """
    file_path = Path(file_path)
    filename = file_path.name

    headers = get_auth_headers(username, wp_token)

    # Check if already uploaded
    search_url = f"{wp_api_url}/media?search={file_path.stem}&per_page=10"
    try:
        response = requests.get(search_url, headers=headers, timeout=15)
        if response.status_code == 200:
            for item in response.json():
                if item.get("source_url", "").endswith(f"/{filename}"):
                    return item["source_url"]
    except requests.exceptions.RequestException:
        pass

    # Upload the image
    content_types = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".gif": "image/gif",
        ".webp": "image/webp",
        ".svg": "image/svg+xml",
    }
    content_type = content_types.get(
        file_path.suffix.lower(), "application/octet-stream"
    )

    upload_headers = get_auth_headers(username, wp_token)
    upload_headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    upload_headers["Content-Type"] = content_type

    try:
        with open(file_path, "rb") as f:
            response = requests.post(
                f"{wp_api_url}/media",
                headers=upload_headers,
                data=f.read(),
                timeout=60,
            )
        if response.status_code in [200, 201]:
            return response.json().get("source_url")
        else:
            print(f"  Failed to upload {filename}: {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"  Error uploading {filename}: {e}")
        return None


def upload_and_replace_article_images(
    content: str,
    file_path: str,
    wp_token: str,
    wp_api_url: str,
    username: str,
) -> str:
    """Find relative images in markdown, upload to WordPress, and replace paths."""
    file_dir = Path(file_path).parent

    def replace_match(match):
        full_match = match.group(0)
        alt = match.group(1)
        src = match.group(2)
        if src.startswith(("http://", "https://", "data:", "//")):
            return full_match
        local_path = file_dir / src
        if not local_path.exists():
            print(f"  Warning: image not found: {local_path}")
            return full_match
        wp_url = upload_image_to_wordpress(local_path, wp_token, wp_api_url, username)
        if wp_url:
            print(f"  Image: {src} -> {wp_url}")
            return f"![{alt}]({wp_url})"
        return full_match

    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace_match, content)
