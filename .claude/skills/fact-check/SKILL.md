---
name: fact-check
description: >
  Verify the factual claims in a blog post against authoritative web sources
  before publishing. Extracts concrete, checkable claims (statistics, version
  numbers, benchmark results, dates, tool capabilities) and verifies each with
  web search. Advisory only, never blocks a merge. Use when the user says
  "fact-check", "verify claims", "is this accurate", or before publishing a
  post that makes factual or numeric claims.
user-invocable: true
---

# Fact-check

Verify the **factual claims** in a post against authoritative sources, and
report what's confirmed, contradicted, outdated, or unverifiable.

This is **advisory**. It does not edit the post and does not gate publishing —
unlike `/check-post`, which is the deterministic structural/SEO gate. Use both:
`/check-post` answers "will this publish cleanly," `/fact-check` answers "is
this true."

**Usage:**

```text
/fact-check posts/article-name.md            # print a report
/fact-check posts/article-name.md --comment  # also post it to the PR
/fact-check posts/article-name.md --fix      # apply high-confidence corrections
```

`--comment` and `--fix` can be combined. By default the skill only reports and
never changes the post.

## Step 1: Read the post

Read the full file. Ignore the YAML frontmatter — it's metadata, not claims.
Note the publish date / `last_synced` if present; recency matters for whether
a fact is "current."

## Step 2: Extract verifiable claims

Pull out only **concrete, externally checkable** statements. A claim qualifies
when it could be proven right or wrong by an authoritative source:

- **Statistics & numbers** — "uv is 10x faster than pip", "reduces build time by 40%"
- **Version numbers & release facts** — "Python 3.13 added free-threading", "released in 2024"
- **Tool capabilities & behavior** — "Docling extracts merged table cells", "Marker supports OCR"
- **Dated / historical facts** — "X was acquired by Y in 2023"
- **Comparative claims** — "X is faster / cheaper / smaller than Y"
- **Attributed quotes & citations** — quotes, paper references, linked sources

**Do NOT flag** (these are not externally verifiable facts):

- Opinions, recommendations, predictions ("we think", "you should", "likely will")
- The author's **own** original measurements — e.g. a post whose point *is* a
  benchmark the author ran. You can't verify these against the web; they are
  primary data. Instead, **sanity-check plausibility** and note them as
  "author's own measurement — not externally verifiable" rather than
  contradicting them.
- Hypotheticals, analogies, and illustrative examples.

For each claim, record the **exact quote** and its section/heading so the
report points to a precise location.

## Step 3: Verify each claim

For each claim, use WebSearch (and WebFetch to read a promising source) to find
authoritative evidence. Prefer primary sources: official docs, release notes,
changelogs, the project's own repo, peer-reviewed or vendor-published data.

Be **adversarial and conservative**:

- Try to *refute* the claim, not just confirm it. A claim survives only when a
  credible source supports it.
- When sources disagree or you can't find authoritative evidence, mark it
  **Unverifiable** — do not guess, and never invent a source URL.
- Watch for **outdated** facts: a claim true at write-time may be stale now
  (new version released, capability changed). Flag these explicitly.

Assign one verdict per claim:

| Verdict | Meaning |
| --- | --- |
| ✅ **Verified** | A credible source confirms it. Cite the URL. |
| ❌ **Contradicted** | A credible source disproves it. Cite the URL and the correct fact. |
| ⏰ **Outdated** | Was true, but no longer current. Cite what changed. |
| ❓ **Unverifiable** | No authoritative source found, or it's the author's own data. |

> For a deep, multi-source pass on a heavily-researched post, you may invoke
> the `deep-research` skill on individual high-stakes claims. For a normal
> post, direct WebSearch/WebFetch per claim is enough.

## Step 4: Report

Print a summary line, then group findings by verdict. **Lead with
Contradicted and Outdated** — those are what the author must act on. Every
Verified/Contradicted/Outdated item must include a source URL.

```markdown
## Fact-check: <post title>

**N claims checked — X verified, Y contradicted, Z outdated, W unverifiable.**

### ❌ Contradicted
- **Claim:** "<exact quote>" *(section: …)*
  - **Finding:** <what's actually true>
  - **Source:** <url>
  - **Suggested fix:** <concrete edit>

### ⏰ Outdated
- …

### ❓ Unverifiable
- **Claim:** "<exact quote>" *(section: …)* — <why: no source / author's own benchmark>

### ✅ Verified
- "<exact quote>" — <source url>
```

If there are no contradicted or outdated claims, say so plainly up front.

## What counts as a "correction"

A correction is only generated for a **❌ Contradicted** or **⏰ Outdated**
claim that is **high-confidence**: a single authoritative source clearly
disproves the current text, and the fix is an unambiguous swap (a wrong number,
version, date, or name). Everything else stays in the report as a note only:

- **Never** auto-correct **Unverifiable** claims, opinions, or the author's own
  measurements. The author may have non-public information; your job is to
  surface, not overrule.
- Each correction is a precise **before → after** edit of the smallest span of
  text (ideally the exact phrase or line), so the author can accept or reject it
  in isolation.

Corrections are **always delivered as GitHub-style `suggestion` blocks**, never
as silent in-place edits — on the PR and locally alike — so the author reviews
each one and can ignore any where they know better.

## Step 5: Post the report to the PR (`--comment`)

Post the Step 4 summary report as a single PR issue comment so the findings
live in review.

1. Find the PR for the current branch:
   ```bash
   gh pr view --json number,url -q '.number'
   ```
   If there's no PR yet, tell the user and just print the report.
2. Post it (write to a temp file first to preserve formatting), prefixed with
   an advisory header so reviewers know it is not a blocking gate:
   ```bash
   gh pr comment <number> --body-file <report.md>
   ```
   First line of the body: `> 🔎 Automated fact-check — advisory, not a merge gate.`

This posts the **summary only**. Actionable corrections are delivered by
`--fix` (below), which can be combined with `--comment`.

## Step 6: Deliver corrections (`--fix`)

Turn each high-confidence correction into a reviewable `suggestion` so the
author commits or dismisses it individually. The delivery differs by context:

### In a PR — inline review comments with suggestions

Post one **review** whose inline comments each carry a `suggestion` block
anchored to the exact changed line(s). GitHub renders a one-click
**"Commit suggestion"** button per comment, and the author can resolve or
ignore each independently.

1. Resolve the post's line numbers in the file's current (RIGHT) version — the
   suggestion replaces exactly the line range it is anchored to.
2. Build the review as a **JSON file** and POST it with `--input`. Do not pass
   the comments as repeated `-f 'comments[][…]'` form fields: `gh api` form
   syntax cannot express an array of objects, so it can't tell where one
   comment ends and the next begins — it appears to work for a single
   correction and silently breaks with two or more. JSON makes the `comments`
   array explicit and keeps each multi-line `body` (newlines and the
   ` ```suggestion ` fence) safely inside the file instead of on the shell
   command line.

   Write `review.json` — one object per correction in `comments`. Each `body`
   holds the finding, the source, and a fenced `suggestion` block with the
   replacement text (use `\n` for newlines within the JSON string):

   ```json
   {
     "event": "COMMENT",
     "body": "🔎 Fact-check suggestions — advisory. Commit any that are correct; ignore any where you have better information.",
     "comments": [
       {
         "path": "posts/your-article.md",
         "line": 42,
         "side": "RIGHT",
         "body": "Released in 2024, not 2023 ([source](https://…)).\n\n```suggestion\nPython 3.13 was released in 2024 and introduced experimental free-threading.\n```"
       }
     ]
   }
   ```

   For a multi-line span, add `"start_line"` (first line) alongside `"line"`
   (last line) in that comment object. Then post it:

   ```bash
   gh api -X POST repos/{owner}/{repo}/pulls/<number>/reviews --input review.json
   ```
3. If any correction's lines fall outside the PR diff (e.g. an unchanged line),
   it can't be a line-anchored suggestion — list those in the `--comment`
   summary under "Corrections that need a manual edit" instead.

Report the review URL back to the user.

### Locally (no PR, working on the file) — mirror the same review flow

Do **not** edit the file in place. Present every correction the same way, as a
numbered list of `suggestion` blocks the author opts into one at a time:

```markdown
**Correction 1** — `posts/your-article.md` line 42
Finding: released in 2024, not 2023 ([source](https://…)).

```suggestion
Python 3.13 was released in 2024 and introduced experimental free-threading.
```
```

Then ask which to apply (e.g. "apply 1, 3, 4" or "all" or "none"). Apply
**only** the approved ones with the Edit tool, leaving the rest untouched so the
author can keep text where their information beats the public record. After
applying, show what changed and remind them to re-read the surrounding prose.

Without `--fix`, never modify the post and never post suggestions — just report.
Without `--comment`, never touch the PR.
