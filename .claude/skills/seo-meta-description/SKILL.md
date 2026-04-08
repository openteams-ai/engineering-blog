---
name: seo-meta-description
description: >
  SEO optimization for blog articles — tags, focus keyword, meta description, and SmartCrawl checklist.
  Use proactively before publishing articles, when the user mentions "SEO", "meta description",
  "focus keyword", "optimize SEO", or wants to improve search rankings.
user-invocable: true
---

# SEO Optimization

Optimize an article's SEO frontmatter and content before publishing.

**Usage:** `/seo-meta-description posts/article-name.md`

## Step 1: Read and Analyze Content

1. Read the full article content
2. Assume `title`, `slug`, `tags`, `focus_keyword`, and `meta_description` are **not yet set**. Generate all of them from the content.
3. Identify from the content:
   - **Main topic** and tools covered
   - **Search intent**: comparison ("X vs Y"), tutorial ("how to"), informational ("what is"), or tool overview
   - **Unique value**: what makes this article worth clicking over competitors
   - **Target audience**: who would search for this

## Step 2: Generate Title and Slug

1. **Title**: Generate an SEO-friendly title (50-65 characters). Include the primary topic and a hook. Present 2-3 options and ask the user to choose.
2. **Slug**: Derive from the chosen title — lowercase, hyphens, 3-50 characters, no stop words.

## Step 3: Generate Focus Keyword

Identify the primary search term the article should rank for:

- Should match what the target audience would actually search for
- 2-4 words, specific to the article's main topic
- Check that it appears naturally in the article title and content
- For comparisons: `"tool-a vs tool-b"`
- For tutorials: `"how to [task] with [tool]"`
- For overviews: `"[tool] [primary use case]"`

Pick the best focus keyword and apply it directly.

## Step 4: Write Meta Description

Generate 3 SEO-optimized meta description options using the **Action + Benefit + Keywords** formula.

### The Formula

```
[Action verb] + [Benefit to reader] + [Focus keyword / specific detail]
```

The action tells users what they'll do, the benefit explains why it matters, and the keyword ensures search relevance. This order works because searchers scan left-to-right — the action catches attention, the benefit holds it, and the keyword confirms relevance.

### Rules

| Rule | Detail |
| --- | --- |
| **Length** | 120-155 characters ideal. Never exceed 160. Mobile truncates at ~136 chars on average, so front-load key info in the first 120 characters |
| **Focus keyword** | Include naturally, ideally in the first half. Google bolds matching terms in SERPs, which draws the eye |
| **Action verbs** | Open with: Learn, Discover, Compare, See how, Find out, Get, Build, Master. These signal usefulness and set expectations |
| **Specifics** | Include tool names, numbers, or concrete outcomes. "5 key differences" beats "key differences" |
| **Intent match** | Comparison → use "vs" language. Tutorial → "how to" or "step by step". Tool overview → lead with what it solves |

### What to Avoid

These patterns hurt CTR because they waste precious characters on filler instead of value:

- "In this article we explore..." — searchers can see it's an article
- "Read more about..." or "This guide covers..." — generic, tells nothing specific
- "Click here to learn..." — feels like spam
- Keyword stuffing — repeating the same term multiple times
- Em dashes — they eat characters and fragment the message

### Patterns by Article Type

**Comparison articles:**
- `[Tool A] vs [Tool B]: [specific differentiator]. [Benefit or outcome].`
- `Compare [Tool A] and [Tool B] for [use case]. See which handles [specific problem] better.`

**Tutorial / How-to:**
- `Learn how to [achieve outcome] with [tool]. [Specific scope or detail].`
- `[Tool] simplifies [task]. [What the reader will build or learn].`

**Standalone tool overview:**
- `[Tool] [solves what problem]. [Key feature] + [benefit].`
- `Discover how [tool] handles [specific challenge] with [feature].`

### Variety

Make the 3 options genuinely different in approach — not just rephrased versions of the same idea:
- One that **leads with the problem** the reader faces
- One that **leads with the tool/solution**
- One that **leads with the benefit or outcome**

### Present Options

Show the current description (if any) for comparison, then the 3 options:

```
**Current** (155 chars):
> [existing meta description]

---

**Option 1** (148 chars) — Leads with the problem:
> [meta description text]

**Option 2** (153 chars) — Leads with the solution:
> [meta description text]

**Option 3** (158 chars) — Benefit-driven:
> [meta description text]
```

**Let the user choose their preferred option.**

## Step 5: Apply Changes

Use Edit to update the YAML frontmatter with all confirmed fields:

- `title`
- `slug`
- `focus_keyword`
- `meta_description`

## Step 6: SmartCrawl SEO Checklist

After applying all SEO fields, audit the article against SmartCrawl's checks and fix any issues:

| Check | How to Fix |
| --- | --- |
| Focus keyphrase in SEO title | Ensure `title` frontmatter contains the `focus_keyword` |
| SEO title length | Title should be 50-65 characters |
| Focus keyphrase in URL | Ensure `slug` contains the focus keyword (hyphenated) |
| Meta description not autogenerated | Ensure `meta_description` is explicitly set (done in steps above) |
| Focus keyphrase in meta description | Ensure `meta_description` contains the `focus_keyword` |
| Meta description length | 120-160 characters |
| Focus keyphrase in first paragraph | Ensure the focus keyword appears naturally in the opening paragraph |
| Focus keyphrase in subheadings | Include the focus keyword in at least 1-2 H2/H3 headings |
| Image alt text contains keyphrase | At least one image alt text should include the focus keyword |
| Internal/external links | Article should contain at least one relevant link |
| Article length | Minimum 300 words recommended |
| Focus keyphrase usage | Use the focus keyword 2-3 times naturally throughout the content |

Present the checklist results to the user and offer to fix any failing checks.

## Completion Checklist

| Field | Status |
| --- | --- |
| Title |  |
| Slug |  |
| Focus keyword |  |
| Meta description |  |
| SmartCrawl checklist |  |
