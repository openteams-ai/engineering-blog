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
import yaml
import markdown
from pathlib import Path
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, field_validator

from dotenv import load_dotenv

# Load .env from project root (two levels up from scripts/wordpress/)
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(os.path.dirname(os.path.dirname(script_dir)), ".env")
load_dotenv(env_path, override=True)

# API request timeouts (seconds)
DEFAULT_TIMEOUT = 10
UPLOAD_TIMEOUT = 60


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
    author: Optional[str] = None
    wordpress_id: Optional[int] = None
    categories: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    meta_description: Optional[str] = None
    focus_keyword: Optional[str] = None
    featured_image: Optional[str] = None

    @field_validator(
        "title", "slug", "author", "meta_description", "focus_keyword",
        "featured_image", mode="before"
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

    meta = {}
    if yaml_content:
        meta = yaml.safe_load(yaml_content) or {}

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
        "author": validated_meta.author,
        "content": markdown_content,
        "categories": validated_meta.categories,
        "tags": validated_meta.tags,
        "slug": validated_meta.slug,
        "wordpress_id": validated_meta.wordpress_id,
        "meta_description": validated_meta.meta_description,
        "focus_keyword": validated_meta.focus_keyword,
        "featured_image": validated_meta.featured_image,
    }


def get_auth_headers(username: str, wp_token: str) -> Dict[str, str]:
    """Create authentication headers for WordPress Application Password."""
    credentials = f"{username}:{wp_token}"
    encoded_credentials = base64.b64encode(credentials.encode("utf-8")).decode("utf-8")
    return {
        "Authorization": f"Basic {encoded_credentials}",
        "User-Agent": "OpenTeams-Engineering-Blog/1.0",
    }


def _matches_author(user: Dict, author_lower: str) -> bool:
    """Check if a WordPress user matches the given author string."""
    return (
        user["slug"] == author_lower
        or user["name"].lower() == author_lower
        or user.get("username", "").lower() == author_lower
    )


def get_user_id(
    author: str, wp_token: str, wp_api_url: str, auth_username: str
) -> Optional[int]:
    """Look up a WordPress user ID by display name, slug, or username."""
    headers = get_auth_headers(auth_username, wp_token)
    response = requests.get(
        f"{wp_api_url}/users",
        headers=headers,
        params={"search": author},
        timeout=10,
    )

    if response.status_code != 200:
        print(f"⚠️  Failed to search users: {response.status_code}")
        return None

    users = response.json()
    author_lower = author.lower()

    for user in users:
        if _matches_author(user, author_lower):
            return user["id"]

    if len(users) == 1:
        return users[0]["id"]

    print(f"⚠️  User '{author}' not found")


def lookup_post_id_by_slug(
    slug: str, wp_token: str, wp_api_url: str, username: str
) -> Optional[int]:
    """Return the WordPress post ID for a given slug, or None if not found.

    Searches across all statuses (draft, publish, private, etc.) so that a
    publish run can locate posts it previously created, regardless of their
    current state.
    """
    headers = get_auth_headers(username, wp_token)
    response = requests.get(
        f"{wp_api_url}/posts",
        headers=headers,
        params={"slug": slug, "status": "any"},
        timeout=DEFAULT_TIMEOUT,
    )
    if response.status_code != 200:
        return None
    results = response.json()
    return results[0]["id"] if results else None


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


def _preprocess_markdown(content: str) -> str:
    """Normalize Quarto/custom markdown syntax to standard markdown."""
    # Remove code blocks with #| echo: false
    echo_false_pattern = r"```\{(\w+)\}\s*\n\s*#\|\s*echo:\s*false\s*\n.*?```"
    content = re.sub(echo_false_pattern, "", content, flags=re.DOTALL)

    # Label unmarked code fences as ```text for consistent styling
    lines = content.split("\n")
    for i, line in enumerate(lines):
        if line.strip() == "```":
            if (
                i + 1 < len(lines)
                and lines[i + 1].strip()
                and not lines[i + 1].strip().startswith("```")
            ):
                lines[i] = "```text"
    content = "\n".join(lines)

    # Convert Quarto-style ```{python} to ```python
    content = re.sub(r"```\{(\w+)\}", r"```\1", content)
    return content


def _stash_mermaid_blocks(content: str) -> tuple[str, Dict[str, str]]:
    """Replace mermaid code blocks with placeholders before markdown conversion.

    Returns the modified content and a dict mapping placeholders to diagrams.
    """
    blocks = {}
    pattern = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)

    def replacer(m):
        key = f"MERMAIDBLOCK{len(blocks)}MERMAIDBLOCK"
        blocks[key] = m.group(1).strip()
        return key

    return pattern.sub(replacer, content), blocks


def _restore_mermaid_blocks(html: str, blocks: Dict[str, str]) -> str:
    """Replace mermaid placeholders with renderable WordPress HTML."""
    for key, diagram in blocks.items():
        mermaid_html = f'<!-- wp:html --><pre class="mermaid" style="text-align:center;">{diagram}</pre><!-- /wp:html -->'
        html = html.replace(f"<p>{key}</p>", mermaid_html)
        html = html.replace(key, mermaid_html)
    return html


_DIRECTIVE_PATTERNS = [
    (r"#\|\s*highlight:\s*(.+)", "data-line"),
    (r"#\|\s*data-output:\s*(.+)", "data-output"),
    (r"#\|\s*data-filter-output:\s*(.+)", "data-filter-output"),
]


def _parse_key_value_pairs(text: str) -> Dict[str, str]:
    """Parse 'key=value key2=value2' into a dict."""
    attrs = {}
    for part in text.split():
        if "=" in part:
            k, v = part.split("=", 1)
            attrs[k] = v.strip("\"'")
    return attrs


def _match_directive(line: str) -> Optional[tuple[str, str]]:
    """Match a line against known #| directives.

    Returns (directive_type, matched_value) or None.
    """
    for pattern, attr_name in _DIRECTIVE_PATTERNS:
        m = re.match(pattern, line)
        if m:
            return attr_name, m.group(1).strip()

    cmd_match = re.match(r"#\|\s*command-line(?:\s+(.+))?", line)
    if cmd_match:
        return "command-line", cmd_match.group(1) or ""

    return None


def _parse_code_directives(code: str) -> tuple[str, Dict[str, str], List[str], bool]:
    """Extract #| directives from code block content.

    Returns (cleaned_code, pre_attrs, extra_classes, is_command_line).
    """
    pre_attrs = {}
    extra_classes = []
    is_command_line = False
    kept_lines = []

    for line in code.split("\n"):
        result = _match_directive(line.strip())
        if not result:
            kept_lines.append(line)
            continue

        directive_type, value = result
        if directive_type == "command-line":
            extra_classes.append("command-line")
            is_command_line = True
            pre_attrs.update(_parse_key_value_pairs(value))
        else:
            pre_attrs[directive_type] = value

    return "\n".join(kept_lines), pre_attrs, extra_classes, is_command_line


def _enhance_code_blocks_for_prism(html: str) -> tuple[str, set, bool, bool]:
    """Add Prism.js attributes to code blocks based on #| directives.

    Returns (enhanced_html, detected_languages, has_line_highlight, has_command_line).
    """
    detected_languages = set()
    has_line_highlight = False
    has_command_line = False

    code_block_pattern = re.compile(
        r"<pre><code\s+class=\"language-(\w+)\">(.*?)</code></pre>",
        re.DOTALL,
    )

    def process_block(match):
        nonlocal has_line_highlight, has_command_line
        lang = match.group(1)
        detected_languages.add(lang)

        cleaned_code, pre_attrs, extra_classes, is_cmd = _parse_code_directives(
            match.group(2)
        )

        if "data-line" in pre_attrs:
            has_line_highlight = True
        if is_cmd:
            has_command_line = True

        classes = [f"language-{lang}"] + extra_classes
        attrs_str = f'class="{" ".join(classes)}"'
        for k, v in pre_attrs.items():
            attrs_str += f' {k}="{v}"'

        return f'<!-- wp:html --><pre {attrs_str}><code class="language-{lang}">{cleaned_code}</code></pre><!-- /wp:html -->'

    enhanced = code_block_pattern.sub(process_block, html)
    return enhanced, detected_languages, has_line_highlight, has_command_line


PRISM_LANGUAGE_MAP = {
    "python": "python",
    "bash": "bash",
    "shell": "bash",
    "sh": "bash",
    "sql": "sql",
    "yaml": "yaml",
    "yml": "yaml",
    "json": "json",
    "javascript": "javascript",
    "js": "javascript",
    "typescript": "typescript",
    "ts": "typescript",
    "html": "markup",
    "xml": "markup",
    "css": "css",
    "go": "go",
    "rust": "rust",
    "java": "java",
    "c": "c",
    "cpp": "cpp",
    "r": "r",
    "toml": "toml",
    "docker": "docker",
    "dockerfile": "docker",
    "makefile": "makefile",
}


def _build_prism_injection(
    languages: set, has_line_highlight: bool, has_command_line: bool
) -> str:
    """Build the Prism.js CDN script/style tags for detected languages and plugins."""
    prism_base = "https://cdn.jsdelivr.net/npm/prismjs@1"

    lang_scripts = [
        f'<script src="{prism_base}/components/prism-{PRISM_LANGUAGE_MAP.get(lang, lang)}.min.js"></script>'
        for lang in languages
        if PRISM_LANGUAGE_MAP.get(lang, lang) != "text"
    ]

    plugin_assets = [
        f'<link rel="stylesheet" href="{prism_base}/plugins/toolbar/prism-toolbar.min.css"/>',
        f'<script src="{prism_base}/plugins/toolbar/prism-toolbar.min.js"></script>',
        f'<script src="{prism_base}/plugins/copy-to-clipboard/prism-copy-to-clipboard.min.js"></script>',
        f'<script src="{prism_base}/plugins/show-language/prism-show-language.min.js"></script>',
    ]
    if has_line_highlight:
        plugin_assets.append(
            f'<link rel="stylesheet" href="{prism_base}/plugins/line-highlight/prism-line-highlight.min.css"/>'
        )
        plugin_assets.append(
            f'<script src="{prism_base}/plugins/line-highlight/prism-line-highlight.min.js"></script>'
        )
    if has_command_line:
        plugin_assets.append(
            f'<link rel="stylesheet" href="{prism_base}/plugins/command-line/prism-command-line.min.css"/>'
        )
        plugin_assets.append(
            f'<script src="{prism_base}/plugins/command-line/prism-command-line.min.js"></script>'
        )

    return (
        '\n<!-- wp:html -->\n'
        f'<link rel="stylesheet" href="{prism_base}/themes/prism.min.css"/>\n'
        f'<script src="{prism_base}/prism.min.js" data-manual></script>\n'
        + "\n".join(lang_scripts) + "\n"
        + "\n".join(plugin_assets) + "\n"
        '<script>Prism.highlightAll();</script>\n'
        '<!-- /wp:html -->'
    )


_MERMAID_SCRIPT = (
    "\n<!-- wp:html -->\n"
    '<style>pre.mermaid { background: transparent !important; padding: 0 !important; }</style>\n'
    '<script src="https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js"></script>\n'
    "<script>mermaid.initialize({startOnLoad:true});</script>\n"
    "<!-- /wp:html -->"
)

_MARKDOWN_EXTENSIONS = [
    "tables",
    "fenced_code",
    "nl2br",
    "attr_list",
    "def_list",
    "abbr",
    "footnotes",
    "md_in_html",
]


def convert_markdown_to_html(
    markdown_content: str, post_data: Optional[Dict] = None
) -> str:
    """Convert markdown content to WordPress-ready HTML."""
    content = _preprocess_markdown(markdown_content)
    content, mermaid_blocks = _stash_mermaid_blocks(content)

    html = markdown.Markdown(extensions=_MARKDOWN_EXTENSIONS).convert(content)

    html = _restore_mermaid_blocks(html, mermaid_blocks)
    html, languages, has_hl, has_cmd = _enhance_code_blocks_for_prism(html)

    # Wrap tables in scrollable containers
    html = re.sub(
        r"(<table.*?</table>)",
        r'<div style="overflow-x: auto;">\1</div>',
        html,
        flags=re.DOTALL,
    )

    if mermaid_blocks:
        html += _MERMAID_SCRIPT
    if languages:
        html += _build_prism_injection(languages, has_hl, has_cmd)

    return html


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

    meta = yaml.safe_load(yaml_content) or {}

    for field, value in metadata_updates.items():
        meta[field] = value

    updated_yaml = yaml.safe_dump(meta, sort_keys=False)
    new_content = f"---\n{updated_yaml}---{after_yaml}"

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    return True


def prepare_seo_meta_fields(post_data: Dict) -> Dict[str, str]:
    """Convert SEO fields to SmartCrawl meta field format."""
    meta = {}

    if post_data.get("meta_description"):
        meta["_wds_metadesc"] = post_data["meta_description"]

    if post_data.get("focus_keyword"):
        meta["_wds_focus-keywords"] = post_data["focus_keyword"]

    return meta


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
) -> Optional[Dict]:
    """Upload an image to WordPress media library if not already uploaded.

    Returns a dict with ``id`` and ``source_url`` keys, or None on failure.
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
                    return {"id": item["id"], "source_url": item["source_url"]}
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
            data = response.json()
            return {"id": data["id"], "source_url": data["source_url"]}
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
        media = upload_image_to_wordpress(local_path, wp_token, wp_api_url, username)
        if media:
            wp_url = media["source_url"]
            print(f"  Image: {src} -> {wp_url}")
            return f"![{alt}]({wp_url})"
        return full_match

    return re.sub(r"!\[([^\]]*)\]\(([^)]+)\)", replace_match, content)
