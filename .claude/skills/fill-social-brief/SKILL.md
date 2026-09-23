---
name: fill-social-brief
description: >
  Fill in the social brief (social/<slug>.yml) for an engineering-blog post: the four short answers that the PR's `social-brief` check asks for. Use when the author asks to "fill the social brief", "answer the brief", "fix the social-brief check", or when a PR adding a post fails that check. Operates on a posts/<file> path or a bare slug. This skill only answers the brief; it does not write the LinkedIn post.
user-invocable: true
---

# Fill Social Brief

Answer the questions in `social/<slug>.yml` from the post, so the author only has to check them.

**Usage:** `/fill-social-brief posts/article-name.md`

## Step 1: Find the brief

- Resolve a bare slug to `posts/<slug>.md` (or `.qmd`).
- If the brief doesn't exist yet, create it:

  ```bash
  uv run scripts/social/create_brief.py posts/<file>
  ```

  It prints the brief's path. The filename comes from the post's frontmatter `slug`, which can differ from the post's filename.
- If the brief already has answers, the author may have edited them. Only change answers the author asked you to change, and don't overwrite the rest.

## Step 2: Read the post

Read the whole post in `posts/`, including the frontmatter. Don't answer from the title or `meta_description` alone.

## Step 3: Answer the questions

Follow the answer guidance in the **Social Brief** section of `README.md`. The comment above each field in the brief is its question, and the allowed values are listed for `audience`. Use only those values. See [Examples](#examples) below for filled briefs from real posts.

Also:

- For an essay or opinion piece, `what_it_does` says what it argues. Don't describe an experiment that isn't there.
- Don't invent results. If the article is exploratory, say so.
- Don't use em dashes.
- Edit only the answer values. Keep the comments, and keep each value on one line in double quotes, as the template has it.

## Step 4: Verify

```bash
uv run scripts/social/check_brief.py posts/<file>
```

It should print ✅. Fix anything it reports.

Then show the author the four answers and ask them to check the framing before they push. The LinkedIn post is written from these answers, so the author should agree with them.

## Examples

Filled briefs from three posts in this repo, one of each common shape. Match their specificity, not their wording.

### An experiment: `posts/llm-review-reliability.md`

```yaml
problem: "Using a second model to review a first model's output might not be a reliable safety layer, as the second model can also be wrong."
what_it_does: "Tests six local reviewer models on 35 hand-labeled claims from MeetingBank summaries, scoring how many unsupported claims each catches and how many true claims it wrongly deletes."
remember_one_thing: "Ensure you test a reviewer model on a few samples yourself before relying on it as a safety layer in production."
audience: ["ml-ai-engineers", "data-scientists"]
```

### An essay: `posts/slow-down-youre-already-shipping-faster.md`

```yaml
problem: "AI coding tools speed developers up so much that you might miss subtle bugs and security gaps."
what_it_does: "Argues for a handful of habits: start from a reviewed plan, keep PRs small, make small edits by hand, keep instruction files lean, and have a different agent review the PR."
remember_one_thing: "It is worth it to spend some time to ensure the AI did a good job instead of spending more time fixing the mistakes it makes later."
audience: ["ml-ai-engineers", "engineering-leaders"]
```

`what_it_does` says what the essay argues. It doesn't invent an experiment.

### A benchmark: `posts/benchmark-python-package-managers.md`

```yaml
problem: "ML projects need packages from both conda-forge and PyPI, and conda is slow to solve while pip and poetry can't use conda-forge at all."
what_it_does: "Benchmarks six package managers on one ML project with 25 direct dependencies split across conda-forge and PyPI, timing installs and lockfile generation."
remember_one_thing: "Which tool is fastest depends on your project needs."
audience: ["ml-ai-engineers", "python-developers"]
```

`remember_one_thing` points at the finding without giving the ranking away, so the article still has something to deliver.

### Too vague vs. specific

| Too vague | Specific |
| --- | --- |
| "LLMs can hallucinate." | "Using a second model to review a first model's output might not be a reliable safety layer, as the second model can also be wrong." |
| "Compares package managers." | "Benchmarks six package managers on one ML project with 25 direct dependencies split across conda-forge and PyPI." |
| "AI is powerful but needs care." | "It is worth it to spend some time to ensure the AI did a good job instead of spending more time fixing the mistakes it makes later." |
