---
title: "I Planted 5 Bugs in an Eval. Claude's build-eval Found All 5"
slug: planted-bugs-build-eval
date: 2026-10-07
topic: ai-engineering
authors:
  - khuyen-tran
tags:
  - llm-evaluation
  - claude-code
  - llm-as-judge
  - evals
meta_description: "I hid 5 bugs in an LLM eval and ran Claude Code's build-eval on it once. It found all 5, four before running the app, and showed what it changes in your eval."
focus_keyword: "build-eval"
---

Have you ever built an eval to measure how good your LLM app is, then tuned your prompt until the score went up?

A high score might not mean your app is good if the eval itself is not correct. A wrong label, an unfair grader, or test cases that are too easy can make a weak app look strong, or a strong one look weak.

Claude Code recently added a command, `/claude-api build-eval`, that checks an eval for these problems. I wanted to know how much it would actually catch.

To find out, I built a small eval for an email router, hid 5 bugs in it, and handed it to the command without telling it about any of them.

This article shows what it found, and when you should run it on your own eval.

> 💻 **Get the Code**: The broken eval, the answer key, and the eval the skill left behind are in the [companion folder](https://github.com/khuyentran1401/codecut-articles/tree/main/notebooks/planted-bugs-build-eval).

## What makes an eval good

An eval is the LLM version of a unit test suite: inputs paired with expected answers, a grader that scores each output, and a script that runs them all.

![One unit test and one eval case side by side: add(2, 3) expects 5 and an assert passes; "I forgot my password" expects account and a grader passes](images/planted-bugs-build-eval/unit-test-vs-eval.svg)

An eval can have bugs too, and with hundreds of cases you can't read them all. The [post that introduced build-eval](https://claude.dev/blog/automating-eval-design-and-hillclimbing/) gives 4 signs of a well-designed eval instead. In plain words:

1. **The test cases look like what users send.** If the cases are easier than real ones, a high score only proves the app can handle easy cases.
2. **Better models score higher.** A stronger model should do better. When it doesn't, the problem is often the eval, not the model.
3. **Leave room to improve.** Include cases hard enough that even the best model scores well below 100%. Otherwise a better prompt can't raise the score.
4. **The same answer gets the same verdict.** Scores shouldn't jump between runs. When they do, the cause is often an unclear case or a grader that scores the same answer differently each time.

![Score against effort for three model sizes: the strongest model scores highest but stays below a perfect score, and each score has a short error bar](images/planted-bugs-build-eval/eval-signs.svg)

*Adapted from Figure 1 in [Automating eval design and hillclimbing with Claude](https://claude.dev/blog/automating-eval-design-and-hillclimbing/).*

This article tests the first, third, and fourth signs.

## Meet build-eval

`build-eval` is part of [claude-api](https://github.com/anthropics/skills/tree/main/skills/claude-api), the built-in Claude Code skill for apps built on the Claude API.

To run it, open Claude Code in your app's folder and type:

```bash
/claude-api build-eval
```

If you already have an eval, it reads your cases and grader, suggests a fix for each problem it finds, and applies the ones you approve.

## Setup

I tested an email router for a bank's support team. It reads a customer email and sends it to one of 5 queues: cards, billing, account, transfers, or top-up.

The eval I handed over has 15 questions from the [Banking77](https://huggingface.co/datasets/PolyAI/banking77) dataset, each mapped to one of the 5 queues. 15 is the smallest set the skill accepts.

These are the 5 bugs I planted:

```text
eval/
  cases.json        15 questions + expected queue
  router.py         the app: system prompt + 3 worked examples
  grader.py         an LLM judge
  run_eval.py       runs the router over the cases and prints a score

cases.json
  case_09  "I forgot my password"            -> billing   <- bug 1: wrong label (should be account)
  case_12  "i was charged when i used a us   -> top-up    <- bug 2: fits two queues (billing too)
            issued card. why and what cards
            are free to use to add money"
  12 of 15 are short, with a word that gives
  away the queue ("How do I track my card?")              <- bug 3: too easy

grader.py
  rates the queue and the reason together
  on a 1-5 scale, and passes only a 5                     <- bug 4: same answer, different verdicts

router.py system prompt
  worked examples = case_03, case_07, case_11,
  copied word for word                                    <- bug 5: answers in the prompt
```

Before handing the eval over, I checked that each bug was real. For example, I regraded the same 15 answers 4 times, and 8 of them switched between pass and fail. I also wrote down what would count as catching each bug before running anything.

| Item | Value |
| --- | --- |
| Skill | `claude-api` `build-eval`, Claude Code 2.1.289 |
| Model running the skill | Claude Opus 5.5 |
| Router and original judge | Claude Haiku 4.5, called through `claude -p` |
| Cases | 15 Banking77 questions on 5 queues |
| Runs of `build-eval` | 1 |
| Date | 2026-10-07 |

`build-eval` never saw my answer key. I copied the eval to a folder outside my repo so the session could not find my notes, and I answered every question the way a real owner would, with no hint about any bug.

## Step 1: it reads your files

`build-eval` started by reading every file in the folder. Before running the router once, it found 3 of the 5 bugs.

### Bug 1: the wrong label

The first question it asked was about case_09:

```text
case_09 "I forgot my password" is labeled billing. Change it?
1. Relabel to account (Recommended)
   Password/login issues belong with account management.
2. Keep billing
   Your bank genuinely routes password resets to billing.
```

It named the exact case and proposed the right fix. It also left room for the label to be intentional, in case a bank really does route password resets to billing.

### Bug 5: the answers hidden in the prompt

The next question caught the cases copied into the router's prompt:

```text
case_03, case_07, case_11 are copied word for word from the prompt's examples.
How should I handle them?
1. Replace with new cases (Recommended)
2. Keep, tag as in-prompt
3. Change the prompt examples
```

These 3 cases pass every time, because the router has already seen their answers. That inflates the score without testing anything.

I chose to replace them, which left the app untouched. The skill wrote 3 new emails covering the same queues.

### Bug 2: the case that fits two queues

After rewriting the cases, it listed the ones where the right answer could be argued:

```text
2 cases where the right queue could be argued:
  - case_11 "Do you charge a monthly fee for the account?" could also go to account.
  - case_12 mentions a charge but is about adding money, so it could go to either billing or top-up.

Are these 15 representative of what your router actually sees?
```

I planted case_12. The skill had just written case_11, so it also flagged a weak spot in its own work.

It kept case_12's label and marked it as arguable rather than changing it. That mattered: in the final run, the router missed only case_12.

## Step 2: it picks a grader

Next, `build-eval` turned to how answers are scored. I handed over this grader:

```python
JUDGE_PROMPT = """You are grading an email router for a bank's support team.
You will see a customer email, the correct queue chosen by a person, and the router's answer.
Rate the router's answer as a whole from 1 (poor) to 5 (excellent),
considering both whether it picked the correct queue and how helpful its reason is to the support agent who receives the email.
Reply with the number only."""

PASS_SCORE = 5
```

Two lines carry the bug. The judge mixes two qualities into one score, and only a perfect 5 passes. A correct answer the judge rates 4 one time and 5 the next flips between fail and pass.

The skill named both problems in one question:

```text
How should the queue choice be graded?
1. Code check (Recommended)
   Parse the `Queue:` line, normalize case/whitespace, exact-match expected.
   Free, deterministic.
2. Keep the LLM judge
   Current 1-5 holistic score, pass only at 5.
   Non-deterministic and blends queue with reason quality.
```

For a router, the right queue has one correct answer, so comparing it to the expected label in code is enough. The new check is free, gives the same verdict every time, and reports format errors separately from wrong queues.

That made 4 of the 5 bugs, all found before the router answered a single email.

## Step 3: it runs a pilot and the full set

With the cases and grader fixed, `build-eval` ran the router on 5 cases first, then on all 15 cases 3 times each.

The score counts the share of emails the grader marked as sent to the right team.

After the 5-case pilot, it raised the last bug:

```text
The scores may be too close to perfect. If the full run also lands near 100%,
the eval can't show whether a change made things better. It would only show
cost and latency moving. If that happens, I'll suggest harder cases rather
than hill-climbing on it.
```

The full run confirmed it. The router got 44 of 45 answers right, and the skill said so plainly:

```text
This eval is close to its ceiling. There are 2 points of room above the
baseline, but the margin of error is ±4 points. That means it can catch a
change that makes routing worse, so it works as a regression check before you
change the prompt or model. It can't show a change that makes routing better.
```

This exposed bug 3, which only a real run could show. Before the fixes, the strict judge failed so many correct answers that the eval looked hard:

- **Before:** the old grader passed 9 of 15 answers. 4 of the 6 failures were correct answers it scored 4 instead of 5.
- **After:** the new grader passed 44 of 45. It missed only case_12, on 1 of 3 runs.

The router barely changed, but the score went from 0.60 to 0.98.

## What it left behind

When it finished, the eval looked like this:

| | Before (handed over) | After `build-eval` |
| --- | --- | --- |
| Cases | 15, with 3 copied into the prompt | 15: 1 relabeled, 3 replaced |
| Grader | Haiku 1-5 judge, pass only at 5 | Exact match on the `Queue:` line |
| Metrics | Pass rate | Accuracy and format errors |
| Runs per case | 1 | 3 |
| Score | 0.60 | 0.98 ± 0.04 |
| Router prompt | 3 worked examples | Unchanged |

It also built a runner, an HTML report linking each case to its transcript, and a folder of results. It committed the result to git only when I asked.

## Final thoughts

`build-eval` found all 5 bugs I planted, 4 of them before running the app once. Here is when I would reach for it.

**Use it when:**

- You have an eval you built yourself and never checked. It found 4 of the 5 bugs just by reading the files.
- Your grader is an LLM judge. It read the judge, named both problems, and replaced it with an exact match.
- Your cases came from a public dataset or sit in your prompt. It caught the mislabeled Banking77 case and the 3 cases copied into the prompt.
- You are about to tune a prompt against the score. It told me the fixed eval was too close to 100% to show an improvement.

**Expect it to:**

- Change your eval. Here it relabeled 1 case, replaced 3, swapped the grader, and ran every case 3 times.
- Ask you questions throughout. The run took 32 minutes, with stops to approve the inputs, the grader, and the runner.

**Use something else when:**

- There is no fixed set of cases to score, such as a one-off demo of what a tool can do.
- Your app does not call Claude. The skill is written for Claude apps, and I did not test other providers.
- You need to know how reliably it catches a kind of bug. I ran it once on one eval, and all 5 bugs are the kind its checklist names.

To try it yourself, copy the broken eval out of the [companion folder](https://github.com/khuyentran1401/codecut-articles/tree/main/notebooks/planted-bugs-build-eval) and run the command in a fresh Claude Code session:

```bash
cp -r notebooks/planted-bugs-build-eval/eval ~/router-eval
cd ~/router-eval
python3 run_eval.py         # the starting score, about 0.60
claude                      # then run /claude-api build-eval
```

Every model call goes through `claude -p`, so it runs on a Claude subscription without an API key. Compare what it finds against `answer_key.md` in the companion folder.

## References

- **[Automating eval design and hillclimbing with Claude](https://claude.dev/blog/automating-eval-design-and-hillclimbing/)** (Lance Martin, 2026): introduces `build-eval` and the checks it runs; every example in it starts from an eval the authors trusted.
- **[claude-api skill](https://github.com/anthropics/skills/tree/main/skills/claude-api)** (Anthropic, 2026): `build-eval.md` runs the `eval-audit.md` checklist on existing cases, runner, and grader.
- **[Banking77](https://huggingface.co/datasets/PolyAI/banking77)** (PolyAI, CC-BY-4.0): the source of the 15 customer questions.
