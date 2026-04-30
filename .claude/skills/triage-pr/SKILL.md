---
name: triage-pr
description: >
  Triage a new blog post PR by checking it out, reading the post, and applying a topic label
  so the right expert reviewer can be pulled in. Use when the user says "triage", "label PR",
  or gives a PR number to triage.
user-invocable: true
---

# PR Triage

Triage a pull request that adds or edits a blog post. Pick the topic label that best matches the post's subject matter and apply it via `gh`.

**Usage:** `/triage-pr <PR number> [CONFIRM]`

Pass the literal word `CONFIRM` as a second argument to require confirmation before any mutating `gh` command (creating a label, applying a label). Without it, the skill runs end-to-end and just reports what it did. Read-only commands (`gh pr view`, `gh pr diff`, `gh label list`) and `gh pr checkout` always run without prompting.

## Step 1: Load the topic list

Read `.github/topics.yml` from the repo root. Each entry maps a GitHub label to a short description, keywords, and a list of reviewers. The file is shared with the reviewer-assignment GitHub Actions workflow in `.github/workflows/`, which is why it lives in `.github/` rather than under the skill.

This list is **human-maintained** — never apply a label that isn't on the list. If nothing fits, say so and suggest an addition for the maintainer to add.

## Step 2: Check out the PR

```bash
gh pr checkout <PR-number>
gh pr view <PR-number> --json title,body,files,author
```

Capture the PR author's login from the `author` field — it's needed in step 5.

## Step 3: Identify the post file

From the PR's changed files, look **only** for `.md` or `.qmd` files under `posts/`.

If none are found, tell the user "This doesn't look like a post PR — no `.md`/`.qmd` files changed under `posts/`" and stop. Do nothing else.

If one is found, continue. If multiple are found and they clearly share a topic, triage as one; otherwise ask which to triage.

## Step 4: Read and match

Read the post. Prioritize this signal, in order:

1. Title and frontmatter (`title`, `focus_keyword`, `categories`, `meta_description`).
2. H2/H3 headings — they show the post's structure.
3. Intro paragraph — states the real subject.
4. A skim of the body for topic reinforcement.

Match on **subject matter**, not incidental mentions. A post about CI pipelines that happens to use Python is an `infrastructure` post, not a `python-tooling` post. The question to answer: *which expert should review this for technical accuracy?*

Pick exactly **one** label from `topics.yml`. If nothing fits, stop and suggest a new entry (name + description + keywords) that the maintainer can add — do not apply an off-list label.

## Step 5: Validate reviewers for the chosen topic

From the matched label's `reviewers` list in `topics.yml`, filter out the PR author. If the result is empty, **do not apply the label** — stop and explain which subcase fired:

- **`reviewers` is empty or missing in `topics.yml`** → "Topic `<label>` has no reviewers listed. Add at least one reviewer to `topics.yml` before applying this label."
- **The only reviewer is the PR author** → "The only reviewer for `<label>` is the PR author (`<login>`). Either add another reviewer to `topics.yml`, or this post was written by the expert and the label is wrong — reconsider the match from step 4."

This mirrors the guard the `triage-pr` GHA workflow enforces on `labeled` events. Catching it here avoids applying a label only to see the workflow fail seconds later.

## Step 6: Ensure the label exists on the repo

```bash
gh label list --limit 200
```

If the chosen label is already on the repo, continue to step 7.

If it's missing, create it from the `topics.yml` entry:

```bash
gh label create "<label>" --description "<description from topics.yml>"
```

This is a mutating command — if `CONFIRM` was passed, ask the user before running it.

## Step 7: Apply the label

```bash
gh pr edit <PR-number> --add-label "<label>"
```

This is a mutating command — if `CONFIRM` was passed, ask the user before running it. Show: post title/slug, chosen label, and a 1–2 sentence reason for the match.

On success, print a one-liner:

> Applied `<label>` to PR #<N>.
