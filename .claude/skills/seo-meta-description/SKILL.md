---
name: seo-meta-description
description: >
  SEO optimization for blog articles: focus keyword, meta description, and on-page checklist.
  Use proactively before publishing articles, when the user mentions "SEO", "meta description",
  "focus keyword", "optimize SEO", or wants to improve search rankings.
user-invocable: true
---

# SEO Optimization

Optimize an article's SEO frontmatter and (when needed) content before publishing.

**Usage:** `/seo-meta-description posts/article-name.md`

## Step 1: Read and analyze

1. Read the full article.
2. Identify from the content:
   - **Main topic** and tools covered
   - **Search intent**: comparison ("X vs Y"), tutorial ("how to"), informational ("what is"), or tool overview
   - **Unique value**: what makes this article worth clicking
   - **Target audience**: who would search for this

## Step 2: Review title and slug

Use the existing title and slug from the frontmatter. Suggest improvements if either falls short:

| Field | Good when |
| --- | --- |
| **Title** | 50 to 65 characters; primary topic front-loaded; has a hook (specific number, action verb, or compelling claim); reads naturally, not clickbait |
| **Slug** | Lowercase, hyphenated; 3 to 50 characters; no stop words (the, a, of, in); mirrors the title's main topic |

If the title doesn't meet the criteria, present **3 alternative titles** using different angles and let the user choose. Derive a new slug from the chosen title.

## Step 3: Generate focus keyword

The primary search term the article should rank for. **It must appear in both the title and slug** so the keyword, headline, and URL reinforce each other.

- 2 to 4 words, specific to the article's main topic
- Should match what the target audience would actually search for
- For comparisons: `"tool-a vs tool-b"`
- For tutorials: `"how to [task] with [tool]"`
- For overviews: `"[tool] [primary use case]"`

## Step 4: Write meta description

Generate 3 options using the **Action + Benefit + Keyword** formula.

### Formula

```text
[Action verb] + [Benefit to reader] + [Focus keyword / specific detail]
```

Searchers scan SERPs in milliseconds, looking for the result that promises to solve their problem. Each component does specific work:

- **Action verb**: signals "this page will do something for you." Passive openers like "This article discusses..." fail the scan because they offer no clear payoff.
- **Benefit**: answers the searcher's implicit "what's in it for me?" Without it, the action is hollow.
- **Keyword**: closes the loop. Google bolds matching terms in the SERP, and seeing the exact phrase the searcher typed confirms "yes, this page is about my query."

Drop any one and the description becomes generic, vague, or off-topic.

### Rules

| Rule | Detail |
| --- | --- |
| **Length** | 120 to 155 characters ideal. Never exceed 160. Mobile truncates at ~136, so front-load key info. |
| **Focus keyword** | Include naturally in the first half. Google bolds matching terms in SERPs. |
| **Action verbs** | Use direct, imperative language. Verbs like Learn, Discover, Compare, See how, Find out, Get, Build, Master work well as openers, but a strong specific claim can substitute. |
| **Specifics** | Include tool names, numbers, or concrete outcomes. "5 key differences" beats "key differences". |
| **Intent match** | Comparison: "vs". Tutorial: "how to" or "step by step". Tool overview: lead with what it solves. |

### What to avoid

- "In this article we explore..." (searchers can see it's an article)
- "Read more about..." or "This guide covers..." (generic)
- "Click here to learn..." (spammy)
- Keyword stuffing
- Em dashes (eat characters and clash with the project's writing style)

### Patterns by article type

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

Make the 3 options genuinely different in approach, not rephrased versions of the same idea.

### Present options

Show the current description (if any), then the 3 options with character counts:

```markdown
**Current** (155 chars):
> [existing meta description, or "(none)"]

---

**Option 1** (148 chars):
> [meta description text]

**Option 2** (153 chars):
> [meta description text]

**Option 3** (144 chars):
> [meta description text]
```

Let the user choose.

## Step 5: Apply changes

Edit the YAML frontmatter to add `meta_description` and `focus_keyword`. Insert them after `categories:` and before any `wordpress_*` fields, matching the ordering in [CLAUDE.md](CLAUDE.md).

## Step 6: On-page checklist

Report ✅ or ❌ for each check. **Do not edit the title, slug, or body.**

| Check | Notes |
| --- | --- |
| Focus keyphrase in title | Pass after Step 3 |
| Focus keyphrase in URL/slug | Pass after Step 3 |
| Meta description set | Pass after Step 5 |
| Focus keyphrase in meta description | Pass after Step 5 |
| Meta description length 120 to 160 chars | Pass after Step 5 |
| Focus keyphrase in first paragraph | Report only |
| Focus keyphrase in 1+ subheading | Report only |
| Focus keyphrase used 2 to 3+ times | Report only (with count) |
| Image alt contains keyphrase | Report only |
| Internal/external links | Report only (with count) |
| Article length ≥ 300 words | Report only (with count) |
