---
title: Your AI Agent Didn't Read AGENTS.md. Your Linter Doesn't Care.
slug: lint-rules-for-ai-agents
authors:
- darshan-paudyal
categories:
- Engineering
meta_description: Use lint rules for AI agents to enforce project conventions. Custom ESLint rules like @jupyter/eslint-plugin give agents clear errors they can fix on their own.
focus_keyword: Lint rules for AI agents
---

A markdown file full of instructions is a polite request. A lint rule is a law. With AI now behind 42% of committed code ([Sonar, 2026](https://www.sonarsource.com/blog/state-of-code-developer-survey-report-the-current-reality-of-ai-coding/)), that difference matters.

Agents are fluent in anything they have seen a million times. Ask for a React component or a Playwright test and you get clean code in seconds. Ask for a JupyterLab extension and you get code that *looks* clean. It compiles, the tests pass, and then it breaks in ways no compiler would notice.

That is because JupyterLab runs on conventions that live one level above the type system. In June, we [announced `@jupyter/eslint-plugin`](https://blog.jupyter.org/catching-jupyter-specific-bugs-before-ci-does-announcing-jupyter-eslint-plugin-fc65ae414630) to catch them, starting with eight rules. The [rules reference](https://eslint-plugin.readthedocs.io/en/latest/category/rules/) now lists 23. We wrote it for human contributors. It turns out the contributors who benefit most might not be human.

## Agents are brilliant at the average codebase

Models are best at what they have seen most. The [CloudAPIBench](https://arxiv.org/abs/2407.09726) study found a strong link between how often an API appears in public code and how often models call it correctly. For rarely seen APIs, GPT-4o got it right only 38.58% of the time.

Playwright and React fill millions of repositories. Galata helpers, Lumino signals and JupyterLab plugin IDs are a thin slice of the internet. So agents write the nearest pattern they know. Invented APIs get caught by TypeScript in seconds. The dangerous mistakes are the ones that *work*: code that passes today and flakes tomorrow, or code that works for you and breaks someone downstream.

## Exhibit A: the test that flakes next month

JupyterLab's UI tests use Galata, a layer on top of Playwright with helpers like `page.notebook` that know how JupyterLab works. Agents have seen far more plain Playwright, so "type into the first cell and run it" often comes out like this:

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

## Exhibit B: the string that breaks someone else's Monday

Plugin IDs look like `@my-org/my-extension:plugin`. To TypeScript, that is just a string. To JupyterLab, the part before the `:` is the extension's name, used when admins disable, defer or lock an extension ([`plugin-id-convention`](https://eslint-plugin.readthedocs.io/en/latest/rules/plugin-id-convention/)).

Say an agent tidies up a plugin ID during a refactor. Every test passes. After release, a `disabledExtensions` entry silently stops matching, users' saved settings seem to vanish, and `overrides.json` quietly stops applying. None of that shows up in your CI. It shows up in someone else's issue tracker.

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

Day to day, the pattern we see is simple. An agent writes raw Playwright or an eager import, the lint run goes red, the agent reads the rule, and it swaps in the Jupyter way before a human reviewer ever looks. Our reviews have shifted from "please use the helper" to the parts of the change that actually need a human.

New contributors get the same treatment. Few people know Jupyter's conventions on their first PR, and they should not have to. Pre-commit hooks and CI flag the mistake with the rule name and the fix, so the correction comes from a tool in seconds instead of a maintainer days later. Nobody has to be the reviewer who asks for the helper again.

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

### Useful links

- [Catching Jupyter-specific bugs before CI does (Jupyter Blog)](https://blog.jupyter.org/catching-jupyter-specific-bugs-before-ci-does-announcing-jupyter-eslint-plugin-fc65ae414630)
- [Rules reference](https://eslint-plugin.readthedocs.io/en/latest/category/rules/)
