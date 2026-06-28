# OpenTeams Social Post Style

Voice, structure, and sourcing rules for OpenTeams engineering-blog social posts.

## Local Source (Preferred Over Web Extraction)

OpenTeams articles are authored in this repo. Always read the local file rather than fetching
the web page:

- Source folder: `posts/` (repo-relative).
- File pattern: `posts/<slug>.md`, where `<slug>` is the article slug or the last path segment
  of an `https://openteams.com/<slug>/` URL.
  - Example: `https://openteams.com/from-skill-to-agent/` → `posts/from-skill-to-agent.md`
- If the exact `posts/<slug>.md` is missing, grep `posts/` for a frontmatter `wordpress_url:`
  match before any web fallback.

The local frontmatter is authoritative:

- `authors:` is a list of author slugs (e.g. `- adam-lewis`). Resolve each slug to a display
  name using this repo's `authors.yml` (match the `slug:` field, use its `name:`). Do not just
  title-case the slug; `authors.yml` is the source of truth for names.
- If multiple authors are listed, mention each one naturally, or use "the OpenTeams engineering
  team" when listing all of them gets clumsy.
- Use `title`, `meta_description`, and the body text directly. They will not match the rendered
  web page exactly, but they are the source of truth.

Only fall back to web extraction if the local file is missing and the slug truly cannot be
resolved.

## Reference Examples (Read Before Drafting)

Before writing the three options, read 2-3 bundled examples to calibrate hook style, paragraph
rhythm, bullet usage, and CTA shape:

- Folder: `references/examples/` (in this skill).
- Pick the example whose intent matches the new article:
  - Walkthrough of a tool or workflow → `plugin_playground_ai_integration.md`
  - Comparison or evaluation → `python_package_managers.md`, `pdf_table_extraction.md`
  - Experiment, argument, or announcement → `local_llm_agent_work.md`, `code_mode_sandboxing.md`, `from_skill_to_agent.md`, `slow_down_ship_better_code.md`, `engineering_blog_intro.md`
- These are shipped OpenTeams LinkedIn posts. Match the framework they use (typically pain
  point, the solution the article provides, then an article-URL CTA followed by 3-4 hashtags).
- Do not copy phrasing wholesale. The goal is to match cadence and structure, not to recycle
  sentences.

## Post Shape

- Create three options with different angles, not three light rewrites of the same post.
- Use angle differences like problem framing, workflow comparison, practical takeaway,
  implementation detail, and strategic tradeoff.
- Keep every paragraph under 50 words.
- Avoid excessive one-sentence paragraphs. Prefer 2-4 related sentences in a paragraph when it
  improves readability and flow.
- Create curiosity without giving away the article's key findings, final recommendations, or
  main lessons.
- Use bullets only when they make comparison or scanning easier.

A strong option often follows this shape (a guide, not a rigid template):

1. State the core problem or tension.
2. Show why the current approach is hard.
3. Name the tool, article, or workflow.
4. Highlight the useful insight.
5. Close with what the article shows.

## Voice

- Treat OpenTeams posts as company-account posts.
- Do not use first-person singular, such as `I`, `my`, or `I tested`.
- Use objective third person or company-plural voice.
- Use `we` only when referring to OpenTeams as a company, not as the article author.

## Author Handling

- If the article has an author, mention the author by name in each option.
- Use the author name naturally, usually when introducing the experiment, tutorial, or argument.

Good patterns include:

- `Adam Lewis explored this by...`
- `In the article, Adam Lewis shows...`
- `Adam Lewis tested...`

- Do not imply the OpenTeams social account personally performed the experiment.
- If no author is available, write in objective company voice without inventing one.

## CTA Patterns

Prefer article-focused endings:

- `This article walks through...`
- `This article compares...`
- `This article shows...`
- `This article shares...`

Avoid generic endings like `Read more` or `Check it out`.

## Accuracy

- Do not invent benchmarks, outcomes, or product claims.
- Ground the post in the article's actual examples.
- If the article is exploratory, use exploratory language.
- If the article is a tutorial, make the workflow clear.

## Tone

- Keep the tone clear, grounded, and useful.
- Avoid hype around AI, open source, or product names.

## Formatting

- Use the markdown structure from `SKILL.md`.
- Use up to four hashtags.
- The source URL lives in the frontmatter `source_document`; do not repeat it in the post body.
