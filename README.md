# Engineering Blog

Source repository for engineering blog posts published on [openteams.com/engineering-blog](https://openteams.com/engineering-blog/).

## Overview

Posts are authored in Markdown (`.md`) or Quarto Markdown (`.qmd`) and automatically published to the OpenTeams WordPress blog when merged to `main`.

## How It Works

1. Write your post as a `.md` file in `posts/`.
2. Check it locally with `uv run scripts/wordpress/check.py posts/your-article.md`.
3. Open a pull request for review. CI validates the changed posts automatically.
4. Once merged to `main`, a GitHub Actions workflow automatically publishes it to WordPress.

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

## Quick Start

1. Create a branch from `main`.
2. Add a `.md` file under `posts/` with frontmatter:

   ```yaml
   ---
   title: "Your Post Title"
   slug: your-post-slug
   author: wordpress-username
   categories:
     - Engineering
   ---
   ```

3. Run `uv run scripts/wordpress/check.py posts/your-post.md` and fix any errors.
4. Submit a PR, get it reviewed, and merge.

See [CLAUDE.md](CLAUDE.md) for the full writing guide: frontmatter fields, code block syntax, image handling, and examples. The checker is documented under [Check](CLAUDE.md#check).
