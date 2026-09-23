# Social briefs

One `social/<slug>.yml` per post, keyed by the post's `slug`. It holds four short answers about the article, which the OpenTeams team uses to write the article's LinkedIn post.

When a PR adds a post, CI commits an empty brief with the questions (`.github/workflows/social-brief.yml`). The author answers them, by hand or with any AI assistant (see Social Brief in the top-level `README.md`), and the required `social-brief` check blocks merge until every answer is filled in. To create it locally first, run `uv run scripts/social/create_brief.py posts/<file>`.

This directory sits outside `posts/`, so the WordPress publish workflow never ingests it.
