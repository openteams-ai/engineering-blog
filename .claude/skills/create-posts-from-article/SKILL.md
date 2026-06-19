---
name: create-posts-from-article
description: >
  Create a LinkedIn/social post draft from a published or drafted engineering-blog
  article. Use when the user asks to "create a social post", "LinkedIn post", "social
  media post", or "cross-post" for an article, or wants the social copy that goes with
  a blog post. Operates on a posts/<slug>.md path, a bare slug, or an openteams.com URL,
  and writes three options to social/<slug>.md.
user-invocable: true
---

# Create Posts From Article

Turn an engineering-blog article into a three-option LinkedIn post draft for the OpenTeams
company account. The output is `social/<slug>.md` with options A, B, and C. The author picks
and edits one later, then posts it to LinkedIn manually after the article goes live.

**Usage:** `/create-posts-from-article posts/article-name.md`

This is an authoring-time companion (like `/seo-meta-description`). It does not publish
anything and does not touch the WordPress pipeline. The draft lives in `social/`, outside
`posts/`, so the publish workflow never ingests it.

## Inputs

Accept any of these and resolve to a local article in this repo:

- A repo path: `posts/<slug>.md` (read directly).
- A bare slug: `<slug>` (read `posts/<slug>.md`).
- An OpenTeams URL: `https://openteams.com/<slug>/` (read `posts/<slug>.md`).

## Load Style Guidance

Before writing post options, read `references/style.md` (sourcing, post shape, voice, author
handling, tone). Then read 2-3 bundled examples from `references/examples/` to calibrate voice
(see `references/style.md` for which example matches which article shape).

## Step 1: Read The Source

Resolve the source to a local file in this repo. Do not use absolute machine paths.

- For `posts/<slug>.md` → read it directly.
- For a bare `<slug>` → read `posts/<slug>.md`.
- For `https://openteams.com/<slug>/` → extract the slug (last path segment) and read
  `posts/<slug>.md`.
- If the exact `posts/<slug>.md` is missing, grep `posts/` for a frontmatter `wordpress_url:`
  that matches the URL before considering any web fallback.

The local frontmatter is authoritative: use `title`, `meta_description`, `authors`, and the
body text directly.

## Step 2: Analyze The Source

- Identify the core problem, audience, tools, and takeaways.
- Capture named people, organizations, libraries, products, and the article author(s).
- Separate deterministic facts from interpretation so the post does not overclaim.

## Step 3: Resolve The Author(s)

`authors:` in the frontmatter is a list of slugs (e.g. `- adam-lewis`). Resolve each slug to a
display name using this repo's `authors.yml` (match the `slug:` field, use its `name:` field).
This is more reliable than title-casing the slug.

- Mention the article author by name in **each** option.
- If multiple authors, name each one naturally, or use "the OpenTeams engineering team" when
  listing all of them gets clumsy.
- If no author resolves, write in objective company voice without inventing one.

## Step 4: Generate Three Options

- Create three distinct post options with different angles, not light rewrites.
- Make each option complete enough to choose without more context.
- Avoid repeating the same hook, CTA, or bullet structure across all options.
- Follow `references/style.md` for voice (company account, no first-person singular) and
  author handling.
- Make the last sentence of each option explain the article's practical value based on how it
  is written: actual outputs, side-by-side comparisons, diagrams, cost/runtime details,
  practical examples, architecture walkthroughs, or an honest breakdown of what worked and
  what did not.

## Step 5: Determine The Source URL

Used for the frontmatter `source_document` field (the post body does not repeat it).

- Prefer the frontmatter `wordpress_url` when present.
- Otherwise construct `https://openteams.com/<slug>/`.
- Use the plain URL. Do not shorten it.

## Step 6: Create The Markdown File

- Write to `social/<slug>.md`, where `<slug>` matches the article's slug (1:1 with
  `posts/<slug>.md`).
- For hashtags, use broad topic or audience tags. Do not include the specific tool, library,
  product, or model name featured in the article. Maximum four.
- Use this structure:

```markdown
---
title: "{article_title}"
status: "unpublished"
created_date: "{today}"
source_document: "{source_url}"
---

## Option A

{post_content_a}

---

## Option B

{post_content_b}

---

## Option C

{post_content_c}

---

**Hashtags:**

{hashtags_max_4}
```

## Quality Check

Before finishing, read the generated file once and verify:

- Every paragraph stays under 50 words.
- The output follows `references/style.md`.
- The article author is mentioned in each option when one exists.
- Voice is objective company voice with no first-person singular (`I`, `my`, `I tested`).
- No more than four hashtags.
- Run diagnostics or lints on the generated file when available.
