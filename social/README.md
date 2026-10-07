# Social briefs

One `social/<slug>.yml` per post, keyed by the post's `slug`. It holds four short answers about the article, which the OpenTeams team uses to write the article's LinkedIn post.

When a PR adds a post, CI commits an empty brief with the questions (`.github/workflows/social-brief.yml`). The author answers them, by hand or with any AI assistant (see Social Brief in the top-level `README.md`), and the `social-brief` check fails until every answer is filled in. To create it locally first, run `node scripts/social/create-brief.ts posts/<file>.md`.
