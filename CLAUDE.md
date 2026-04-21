# Writing Guide

Full reference for contributors writing engineering blog posts.

## Creating a Post

1. Create a `.md` or `.qmd` file under `posts/` (e.g., `posts/building-ml-pipelines.md`).
2. Write your content in standard markdown.
3. Add YAML frontmatter at the top of the file (see [Frontmatter](#frontmatter) below).
4. *Optional:* If you use Claude Code, run `/seo-meta-description posts/your-article.md` to auto-generate title, slug, focus keyword, and meta description.

## Frontmatter

```yaml
---
title: "Your Post Title"
slug: your-post-slug
author: wordpress-username
categories:
  - Engineering
meta_description: "A short summary for SEO (150-160 chars)."
focus_keyword: "main keyword"
---
```

**Required fields:** `title`, `slug`, `author`, `categories`

`author` is the author's slug from `authors.yml`. If this is your first post, add yourself to `authors.yml` with your name, slug, email, and bio before publishing.

**Optional fields:** `meta_description`, `focus_keyword`, `featured_image`

`featured_image` sets the post's hero/thumbnail image. Accepts either a local path relative to the post file (e.g., `images/my-post/hero.jpg`) or an absolute `https://` URL. Omit the field if the post has no featured image.

**Auto-added after publishing:** `wordpress_id`, `wordpress_url`, `last_synced`

## File Formats

| Format | Extension | When to Use |
|--------|-----------|-------------|
| Markdown | `.md` | Standard prose, code snippets, conceptual articles |
| Quarto Markdown | `.qmd` | Posts with executable code, data visualizations, or reproducible analysis |

## Images

Place images in `posts/images/<post-slug>/` and reference them with relative paths:

```markdown
![diagram](images/building-ml-pipelines/architecture.png)
```

Images are automatically uploaded to WordPress when the post is published.

Commits that only change files under `posts/images/<slug>/` (without touching the `.md`/`.qmd`) also trigger a republish of `posts/<slug>.md` or `posts/<slug>.qmd`. If no matching post file exists for the slug, the image change is skipped.

**Refreshing an existing image:** uploads are deduplicated by filename. If you edit an image's bytes but keep the same filename, WordPress will keep serving the old copy. To force a refresh, rename the file (e.g., `hero.png` to `hero-v2.png`) and update references, or delete the existing media from WordPress admin before republishing.

## Markdown Syntax Reference

The publish script converts markdown to HTML with support for Prism.js plugins. Use `#|` directives inside code blocks to control rendering.

### Standard Code Block

````markdown
```python
def hello():
    print("Hello, world!")
```
````

### Executable Code Block (.qmd only)

In `.qmd` files, use `{python}` to mark executable code blocks. These are converted to standard syntax-highlighted blocks on publish.

````markdown
```{python}
import pandas as pd

df = pd.read_csv("data.csv")
print(df.head())
```
````

Use `#| echo: false` to hide a code block from the published output:

````markdown
```{python}
#| echo: false
config = load_config()
```
````

### Line Highlighting

Highlight specific lines to draw attention. Uses the [Prism.js Line Highlight](https://prismjs.com/plugins/line-highlight/) plugin.

`#| highlight:` accepts single lines (`5`), ranges (`1-3`), and combinations (`1-3, 5, 9-12`).

````markdown
```python
#| highlight: 2-3, 5
import pandas as pd

df = pd.read_csv("data.csv")
df = df.dropna()
result = df.groupby("category").sum()
```
````

**Output:**

![Line highlighting example](images/line-highlight.png)

### Command-Line Prompt

Show terminal prompts with the [Prism.js Command Line](https://prismjs.com/plugins/command-line/) plugin. Use `data-filter-output` to mark output lines with a prefix (stripped on render).

````markdown
```bash
#| command-line
#| data-filter-output: (out)
echo "Hello from OpenTeams!"
(out)Hello from OpenTeams!
```
````

**Output:**

![Command-line prompt example](images/command-line-filter.png)

Optional attributes: `data-user`, `data-host`, `data-prompt`, `data-output`.

### Mermaid Diagrams

Rendered automatically:

````markdown
```mermaid
graph LR
    A[Start] --> B[End]
```
````

**Output:**

![Mermaid diagram example](images/mermaid-diagram.png)

### Other Supported Elements

| Element | Syntax |
|---------|--------|
| Bold | `**text**` |
| Italic | `*text*` |
| Inline code | `` `code` `` |
| Link | `[text](url)` |
| Image | `![alt](images/file.png)` |
| Blockquote | `> text` |
| Table | Standard markdown table syntax |
| Horizontal rule | `---` |
| Ordered list | `1. item` |
| Unordered list | `- item` |
| Nested list | Indent with 2 or 4 spaces |
