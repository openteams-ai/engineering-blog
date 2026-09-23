# Engineering Blog

Source repository for engineering blog posts published on [openteams.com/engineering-blog](https://openteams.com/engineering-blog/).

## Overview

Posts are authored in Markdown (`.md`) or Quarto Markdown (`.qmd`) and automatically published to the OpenTeams WordPress blog when merged to `main`.

## How It Works

1. Write your post as a `.md` file in `posts/`.
2. Open a pull request for review, and answer the social brief CI adds to it.
3. Once merged to `main`, a GitHub Actions workflow automatically publishes it to WordPress.

Contributors do not need WordPress credentials.

## Repository Structure

```text
posts/
├── building-ml-pipelines.md        # Article files (.md or .qmd)
├── scaling-with-duckdb.md
└── images/
    ├── building-ml-pipelines/      # Images per article
    │   └── architecture.png
    └── scaling-with-duckdb/
        └── benchmark.png
```

## Writing Guide

Full reference for contributors writing engineering blog posts.

### Creating a Post

1. Create a `.md` or `.qmd` file under `posts/` (e.g., `posts/building-ml-pipelines.md`).
2. Write your content in standard markdown.
3. Add YAML frontmatter at the top of the file (see [Frontmatter](#frontmatter) below).
4. *Optional:* If you use Claude Code, run `/seo-meta-description posts/your-article.md` to auto-generate title, slug, focus keyword, and meta description.
5. Open a PR. CI commits a social brief to `social/<slug>.yml`: four short questions used to write the LinkedIn post. Answer them yourself or with your AI assistant, and push. The PR can't merge until you do. See [Social Brief](#social-brief).

### Preview

Two levels, in increasing fidelity.

#### Local preview

Render a post locally to check code blocks, Mermaid diagrams, tables, and the Quarto/Prism directives. No WordPress credentials are required.

```bash
uv run scripts/wordpress/preview.py posts/your-article.md
```

This watches the file and reloads the browser on every save. Press Ctrl+C to stop, or pass `--no-watch` to render once and exit.

The rendered HTML is written to `.preview/<slug>.html` (gitignored) and opened in your default browser. Pass `--no-open` to write the file and print its path without opening a browser.

**Accurate:** anything the markdown pipeline produces, since it is the same pipeline publishing uses. Code blocks and Prism directives, Mermaid diagrams, tables, image placement.

**Absent:** anything the theme supplies. Author box, navigation, featured-image hero, brand fonts, content column width, and the Elementor lightbox that gives click-to-zoom. Use the PR draft preview below for those.

#### Draft preview on your PR

Open a pull request. CI publishes each changed post as a WordPress draft and comments the preview link on the PR, refreshing that comment on every push.

This renders in the real theme, so it is the only way to verify theme behaviour: lightbox zoom, brand fonts, content column width, and whether images survived the upload.

**Preview links expire within a week.** The PR comment states the exact date each one is good until, and always holds the current link. Pushing anything to the PR reissues them.

### Frontmatter

```yaml
---
title: "Your Post Title"
slug: your-post-slug
authors:
  - wordpress-username
categories:
  - Engineering
meta_description: "A short summary for SEO (150-160 chars)."
focus_keyword: "main keyword"
---
```

**Required fields:** `title`, `slug`, `authors`, `categories`, `meta_description`, `focus_keyword`

`authors` is a list of author slugs from `authors.yml`. The first slug is the primary author shown in the byline; any additional slugs are co-authors. If this is your first post, add yourself to `authors.yml` with your name, slug, email, and bio before publishing.

For a co-authored post, list every contributor:

```yaml
authors:
  - primary-author-slug
  - second-author-slug
```

The publish script matches posts to WordPress by `slug`, so do not change the slug of a live post. Renaming it orphans the existing WordPress post and creates a new draft under the new slug.

### Social Brief

Every new post needs an answered `social/<slug>.yml` before its PR can merge. It seeds the LinkedIn post for the article. CI commits it to your PR with the questions and empty answers. To create it earlier, run `uv run scripts/social/create_brief.py posts/your-article.md`.

The comment above each field is its question, and the allowed values are listed for `audience`. The three written answers need at least 8 words each, so they carry the article's specifics. Good answers:

- **`problem`:** What problem does this article solve? (1-2 sentences)
- **`what_it_does`:** What does the article build, test, compare, or argue? (1-2 sentences)
- **`remember_one_thing`:** If readers remember one thing, what should it be? (1 sentence)
- **`audience`:** Who should read this? Pick one or more, usually the 1-3 groups the article is written for:
  - `data-scientists`
  - `ml-ai-engineers`
  - `python-developers`
  - `platform-devops-engineers`
  - `security-compliance-engineers`
  - `oss-maintainers`
  - `engineering-leaders`

You can either answer the questions yourself or with your AI assistant. To have your AI assistant answer them, run `/fill-social-brief posts/your-article.md`.

#### Examples

Here are some examples of social briefs from real posts in this repo:

**An experiment** (`posts/llm-review-reliability.md`):

```yaml
problem: "Using a second model to review a first model's output might not be a reliable safety layer, as the second model can also be wrong."
what_it_does: "Tests six local reviewer models on 35 hand-labeled claims from MeetingBank summaries, scoring how many unsupported claims each catches and how many true claims it wrongly deletes."
remember_one_thing: "Ensure you test a reviewer model on a few samples yourself before relying on it as a safety layer in production."
audience: ["ml-ai-engineers", "data-scientists"]
```

**An essay** (`posts/slow-down-youre-already-shipping-faster.md`):

```yaml
problem: "AI coding tools speed developers up so much that you might miss subtle bugs and security gaps."
what_it_does: "Argues for a handful of habits: start from a reviewed plan, keep PRs small, make small edits by hand, keep instruction files lean, and have a different agent review the PR."
remember_one_thing: "It is worth it to spend some time to ensure the AI did a good job instead of spending more time fixing the mistakes it makes later."
audience: ["ml-ai-engineers", "engineering-leaders"]
```

**A benchmark** (`posts/benchmark-python-package-managers.md`):

```yaml
problem: "ML projects need packages from both conda-forge and PyPI, and conda is slow to solve while pip and poetry can't use conda-forge at all."
what_it_does: "Benchmarks six package managers on one ML project with 25 direct dependencies split across conda-forge and PyPI, timing installs and lockfile generation."
remember_one_thing: "Which tool is fastest depends on your project needs."
audience: ["ml-ai-engineers", "python-developers"]
```

### File Formats

| Format | Extension | When to Use |
|--------|-----------|-------------|
| Markdown | `.md` | Standard prose, code snippets, conceptual articles |
| Quarto Markdown | `.qmd` | Posts with executable code, data visualizations, or reproducible analysis |

### Images

Place images in `posts/images/<post-slug>/` and reference them with relative paths.

#### Syntax

```markdown
![diagram](images/building-ml-pipelines/architecture.png)
```

- Supported formats: `.png`, `.jpg`, `.jpeg`, `.gif`, `.webp`
- To make an image open a page instead of zooming, wrap it in a markdown link:

  ```markdown
  [![Chart description](images/my-post/chart.png)](https://example.com)
  ```

#### What publishing does with them

- Uploads each image to WordPress and rewrites the path.
- Wraps each image in a link to itself, so readers can click it open at full size.
- Matches uploads by filename. **Editing an image that is already published? Give it a new filename** (`hero.png` to `hero-v2.png`) and update the reference.

### Markdown Syntax Reference

The publish script converts markdown to HTML with support for Prism.js plugins. Use `#|` directives inside code blocks to control rendering.

#### Standard Code Block

````markdown
```python
def hello():
    print("Hello, world!")
```
````

#### Executable Code Block (.qmd only)

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

#### Line Highlighting

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

#### Command-Line Prompt

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

#### Mermaid Diagrams

Rendered automatically:

````markdown
```mermaid
graph LR
    A[Start] --> B[End]
```
````

**Output:**

![Mermaid diagram example](images/mermaid-diagram.png)

#### Other Supported Elements

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
