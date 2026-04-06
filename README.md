# Engineering Blog

Source repository for engineering blog posts published on [openteams.com/blog](https://openteams.com/blog) under the **Engineering** category.

## Overview

Posts are authored in Markdown (`.md`) or Quarto Markdown (`.qmd`) and automatically published to the OpenTeams WordPress blog when merged to `main`.

## How It Works

1. Write your post as a `.md` file in `posts/`.
2. Open a pull request for review.
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

3. Submit a PR, get it reviewed, and merge.

See [CLAUDE.md](CLAUDE.md) for the full writing guide: frontmatter fields, code block syntax, image handling, and examples.
