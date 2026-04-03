# Engineering Blog

Source repository for engineering blog posts published on [openteams.com/blog](https://openteams.com/blog) under the **Engineering** category.

## Overview

This repo contains the source files for OpenTeams engineering articles. Posts are authored in Markdown (`.md`) or Quarto Markdown (`.qmd`) and published to the OpenTeams WordPress blog.

## Repository Structure

```text
engineering-blog/
├── posts/                          # Blog post directories
│   └── <post-slug>/
│       ├── index.md                # or index.qmd
│       └── images/                 # Post-specific images
├── scripts/
│   └── wordpress/
│       ├── publish.py              # Unified create/sync script
│       └── wordpress_utils.py      # Shared WordPress utilities
├── .env.example                    # WordPress credentials template
├── pyproject.toml                  # Python dependencies
└── README.md
```

Each post lives in its own directory under `posts/`, named with a URL-friendly slug (e.g., `posts/building-ml-pipelines/`).

## Setup

1. Copy `.env.example` to `.env` and fill in your WordPress credentials:
   ```
   WP_TOKEN=your-application-password
   WP_API_URL=https://openteams.com/wp-json/wp/v2
   USERNAME=your-wordpress-username
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

## Writing a Post

1. Create a new directory under `posts/` with a descriptive slug.
2. Add an `index.md` or `index.qmd` file with YAML frontmatter:

   ```yaml
   ---
   title: "Your Post Title"
   slug: your-post-slug
   categories:
     - Engineering
   tags:
     - python
     - data-engineering
   meta_description: "A short summary for SEO (150-160 chars)."
   focus_keyword: "main keyword"
   seo_keywords:
     - "keyword one"
     - "keyword two"
   ---
   ```

   **Required fields:** `title`, `slug`, `categories`

   **Optional fields:** `tags`, `meta_description`, `focus_keyword`, `seo_keywords`

   **Auto-added after publishing:** `wordpress_id`, `wordpress_url`, `last_synced`

3. Place any images in an `images/` subdirectory and reference them with relative paths:
   ```markdown
   ![diagram](images/architecture.png)
   ```

## File Formats

| Format | Extension | When to Use |
|--------|-----------|-------------|
| Markdown | `.md` | Standard prose, code snippets, conceptual articles |
| Quarto Markdown | `.qmd` | Posts with executable code, data visualizations, or reproducible analysis |

## Publishing

A single script handles both creating new posts and syncing updates:

```bash
uv run scripts/wordpress/publish.py posts/<slug>/index.md
```

- **No `wordpress_id` in frontmatter** → creates a new WordPress draft
- **Has `wordpress_id`** → syncs updates to the existing post

Both paths automatically:
- Upload local images to WordPress media library
- Convert markdown to HTML (with code highlighting, mermaid diagrams, tables)
- Resolve categories and tags against WordPress
- Set Yoast SEO metadata
- Update the file's frontmatter with `wordpress_id`, `wordpress_url`, and `last_synced`

### Publishing Workflow

1. Write your post on a feature branch.
2. Open a pull request for review.
3. Once approved and merged to `main`, publish:
   ```bash
   uv run scripts/wordpress/publish.py posts/<slug>/index.md
   ```

## Contributing

1. Create a branch from `main`.
2. Add your post following the structure above.
3. Submit a PR with a clear title and summary.
4. Address review feedback, then merge.
