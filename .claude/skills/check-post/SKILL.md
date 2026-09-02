---
name: check-post
description: >
  Pre-flight validation for a blog post before opening a PR. Checks required
  frontmatter, slug format, authors against authors.yml, meta_description
  length, focus keyword placement, and image links. Use before pushing a post,
  or when the user says "check my post", "is this post ready", "validate", or
  "lint" a post.
user-invocable: true
---

# Check Post

Validate a post against everything `publish.py` requires, locally, before it
ever reaches a PR. Catches the errors that would otherwise only surface after
merge, when the publish workflow runs.

**Usage:** `/check-post posts/article-name.md`

## Step 1: Run the checker

```bash
uv run scripts/wordpress/check.py posts/article-name.md
```

No WordPress credentials are needed. Pass `--all` to check every post, or
`--strict` to treat warnings as failures.

The script reports, per post:

- **errors** (block publishing): missing required frontmatter, invalid slug,
  author not in `authors.yml`, broken/missing image links.
- **warnings** (SEO/convention): `meta_description` length outside 120-160,
  focus keyword missing from title or slug, slug not matching the filename,
  images outside `images/<slug>/`, empty image alt text.

Exit code is non-zero when any error is found.

## Step 2: Report and fix

1. Show the user the checker output.
2. **Fix every error** — these break publishing. Edit the frontmatter or move
   images as needed. If an author is missing, add them to `authors.yml`
   (name, slug, email, bio) per the writing guide.
3. Walk through the **warnings** and offer to fix them. For SEO warnings
   (meta description length, focus keyword placement), suggest invoking
   `/seo-meta-description` for a deeper pass.
4. Re-run the checker until it is clean (or only intentional warnings remain).

## Notes

- A slug that does not match the filename is only a warning, but never change
  the slug of an already-published post (it has a `wordpress_id`): renaming the
  slug orphans the live WordPress post and creates a new draft.
- This check is also enforced on every PR by the `check-posts` GitHub Actions
  workflow, so fixing it locally first avoids a failed CI run.
