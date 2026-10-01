---
title: Your AI Agent Ignored AGENTS.md. Your Linter Won't Let It.
slug: lint-rules-for-ai-agents
date: 2026-10-01T13:11:08+05:45
authors:
- darshan-paudyal
categories:
- Engineering
meta_description: Use lint rules for AI agents to enforce project conventions. Custom ESLint rules like @jupyter/eslint-plugin give agents clear errors they can fix on their own.
focus_keyword: Lint rules for AI agents
wordpress_id: 42025
wordpress_url: https://openteams.com/lint-rules-for-ai-agents/
---

AI agents now write a large share of new code: 42% of committed code, according to [Sonar's 2026 survey](https://www.sonarsource.com/blog/state-of-code-developer-survey-report-the-current-reality-of-ai-coding/). When that code is for JupyterLab, it often looks fine. It compiles, and the tests pass. But it quietly breaks Jupyter's conventions, because those conventions are rare in the public code that models learn from.

The usual fix is to write the conventions down in AGENTS.md. That helps, but an agent can still skip an instruction, and when it does, nothing fails.

This post shows how [`@jupyter/eslint-plugin`](https://www.npmjs.com/package/@jupyter/eslint-plugin), which we [announced on the Jupyter Blog](https://blog.jupyter.org/catching-jupyter-specific-bugs-before-ci-does-announcing-jupyter-eslint-plugin-fc65ae414630), catches these mistakes and tells the agent which Jupyter pattern to use instead.

## Agents are great at common code, shaky on rare APIs

Models are best at what they have seen most. The [CloudAPIBench](https://arxiv.org/abs/2407.09726) study found a strong link between how often an API appears in public code and how often models call it correctly.

However, for **rarely seen APIs**, GPT-4o got it right only 38.58% of the time.

Playwright and React fill millions of repositories. Galata helpers, Lumino signals and JupyterLab plugin IDs are a thin slice of the internet. So agents write the nearest pattern they know. Invented APIs get caught by TypeScript in seconds.

The dangerous mistakes are the ones that *work*: code that passes today and flakes tomorrow, code that works for you and breaks someone downstream, or code that quietly slows startup for every user.

These rules are not about code style. The plugin's 23 rules catch memory leaks from Lumino signals nobody disconnects ([`require-signal-cleanup`](https://eslint-plugin.readthedocs.io/en/latest/rules/require-signal-cleanup/)), user-facing text that never reaches translators ([`no-untranslated-string`](https://eslint-plugin.readthedocs.io/en/latest/rules/no-untranslated-string/)), plugin IDs that quietly break admin configuration ([`plugin-id-convention`](https://eslint-plugin.readthedocs.io/en/latest/rules/plugin-id-convention/)) and more. The next three sections walk through examples of how an agent makes these mistakes, and how the linter catches each one.

## Example 1: the test that flakes next month

**In short:** JupyterLab's UI tests use Galata, a layer on top of Playwright with helpers that know how JupyterLab works. Agents often skip those helpers and write raw Playwright instead. The test passes today, but it depends on internal markup and skips Galata's readiness checks, so it starts failing at random when the markup changes or CI runs slower.

Agents have seen far more plain Playwright than Galata, so "type into the first cell and run it" often comes out like this:

```ts
await page
  .locator('.jp-Cell-inputArea >> .cm-editor >> .cm-content[contenteditable="true"]')
  .first()
  .fill('print("hello")');
await page.keyboard.press('Control+Enter');
```

The Galata way:

```ts
await page.notebook.setCell(0, 'code', 'print("hello")');
await page.notebook.runCell(0);
```

The first version passes on your laptop. But as the [rule docs](https://eslint-plugin.readthedocs.io/en/latest/rules/galata-prefer-notebook-cell-helper/) note, raw selectors depend on notebook markup and skip Galata's readiness checks. Change the markup or slow down the CI runner, and a green test turns flaky weeks after the PR merged. The plugin now has five Galata rules that spot these patterns and name the helper to use.

## Example 2: the URL that breaks someone else's Monday

**In short:** any extension that talks to the Jupyter server needs the server's base URL. JupyterLab keeps the current one in its server settings, because the backend URL can change at runtime. Agents often read it from `PageConfig.getBaseUrl()` instead. That works locally, but breaks in deployments that switch the backend URL, which your CI never tests.

The obvious way to get the URL, and the one we have watched frontier agents write, looks like this:

```ts
const url = URLExt.join(PageConfig.getBaseUrl(), 'api', 'contents');
return ServerConnection.makeRequest(url, {}, serverSettings);
```

It works on your machine, and every test passes. But JupyterLab can switch backend URLs at runtime, and downstream distributions rely on that. The right source is the server settings you already have:

```ts
const url = URLExt.join(serverSettings.baseUrl, 'api', 'contents');
return ServerConnection.makeRequest(url, {}, serverSettings);
```

As the [`no-pageconfig-base-url`](https://eslint-plugin.readthedocs.io/en/latest/rules/no-pageconfig-base-url/) docs explain, calling `PageConfig.getBaseUrl()` bypasses those settings. Your CI never runs against a switched backend. Someone else's deployment does, right after your release.

## Example 3: the import that slows everyone down

**In short:** JupyterLab loads heavy packages like `@lumino/datagrid` and `mermaid` only when a feature needs them, so they do not slow down startup. One static import in an extension pulls them back into startup. Nothing fails, but every user waits longer for JupyterLab to open.

It is an easy mistake for humans and agents alike.

Loads the grid at startup, for every user
```ts
import { DataGrid } from '@lumino/datagrid';
async function onClick() {
  const grid = new DataGrid();
  // ...
}
```

Loads it only when a grid is actually needed
```ts
async function onClick() {
  const { DataGrid } = await import('@lumino/datagrid');
  const grid = new DataGrid();
  // ...
}
```

Humans and agents make this mistake equally easily. No test fails and nothing flakes. Every user just waits a little longer for JupyterLab to open, because top-level imports are downloaded and evaluated before it can start. [`prefer-lazy-imports`](https://eslint-plugin.readthedocs.io/en/latest/rules/prefer-lazy-imports/) catches the static import and points at the lazy version.

## "Just put it in AGENTS.md"

The obvious fix is [AGENTS.md](https://agents.md), a "README for agents" that over 60,000 open-source projects use. You should write one, and agents do read it. But for conventions, it has three weaknesses:

- **It competes for attention.** In the [IFScale benchmark](https://arxiv.org/abs/2507.11538), even the best model followed only 68% of instructions when given 500 at once.
- **More instructions are not free.** A 2026 study, [Evaluating AGENTS.md](https://arxiv.org/abs/2602.11988), found context files did not generally improve task success and raised cost by over 20%.
- **Nobody finds out when it is skipped.** A missed line fails nothing. You learn about it in review, or in a bug report.

AGENTS.md is probabilistic, and it has no error channel.

## Linters turn a knowledge problem into a feedback problem

A lint rule does not ask the model to remember anything. It runs on every file, every time, and when it fires the agent sees something like this:

```
ui-tests/tests/run-cell.spec.ts
  12:3  error  Use page.notebook.setCell() / runCell() instead of raw cell selectors
               jupyter/galata-prefer-notebook-cell-helper
```

A file, a line, a rule and the fix. The agent no longer needs to have seen thousands of Galata tests. It only needs to read an error and act on it, which agents are *very* good at. [Factory made the same case](https://factory.ai/news/using-linters-to-direct-agents) in 2025, and our experience in Jupyter points the same way.

## What happened when we turned it on

Day to day, the pattern we see is simple. An agent writes raw Playwright, an eager import or a hard-coded English label, the lint run goes red, the agent reads the rule, and it swaps in the Jupyter way before a human reviewer ever looks. Our reviews, especially of code from weaker models, have shifted from "please use the helper" and "please add a translation wrapper" to the parts of the change that actually need a human.

New contributors get the same treatment. Few people know Jupyter's conventions on their first PR, and they should not have to. Pre-commit hooks and CI flag the mistake with the rule name and the fix, so the correction comes from a tool in seconds instead of a maintainer days later. Nobody has to be the reviewer who asks for the helper or the translation wrapper again.

## Should your codebase get one?

A custom rule is worth it when a convention:

- lives above the type system,
- is rare in public code, so models have not learned it,
- breaks silently, and
- has a correct alternative you can name in an error message.

If you have typed the same review comment three times, you already have the spec. And here is the fun part: agents are great at *writing* ESLint rules, because rule APIs and AST tooling are everywhere in public code, even when your conventions are not.

Keep AGENTS.md, but give it a new job: pointing at the enforcer.

```markdown
## Before you finish
- Run `jlpm eslint` and fix every `jupyter/*` error.
```

Now it holds one easy instruction, and the linter holds the rest.

## Wrapping up

Agents will keep getting better, but they will still be best at the code they have seen most. For ecosystems like Jupyter, the most reliable teacher is a fast failure with a message that says exactly what to do next.

Maintain a Jupyter extension? Install [`@jupyter/eslint-plugin`](https://www.npmjs.com/package/@jupyter/eslint-plugin) and run it once. Have a convention you wish your agent knew? [Open an issue](https://github.com/jupyterlab/eslint-plugin/issues).

## Acknowledgments

The creation of ESlint plugin was funded by the Jupyter Foundation under the first round of [Jupyter Community Funded Proposals](https://blog.jupyter.org/announcing-our-first-jupyter-community-funded-proposals-dd5263c19be3). Thank you to the Foundation and everyone who set up this funding mechanism.
And a big thank you to the Jupyter community for engaging with the rules, testing them in real codebases and adopting the plugin across Jupyter projects.

### Useful links

- [Catching Jupyter-specific bugs before CI does (Jupyter Blog)](https://blog.jupyter.org/catching-jupyter-specific-bugs-before-ci-does-announcing-jupyter-eslint-plugin-fc65ae414630)
- [Rules reference](https://eslint-plugin.readthedocs.io/en/latest/category/rules/)
