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

To find out, I built a small eval for an email router, hid 5 bugs in it, and ran the command on it without telling it about any of them.

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

My eval has 15 questions from the [Banking77](https://huggingface.co/datasets/PolyAI/banking77) dataset, each labeled with one of the 5 queues. 15 is the smallest set the skill accepts.

These are the 5 bugs I planted.

### Bug 1: the wrong label

I labeled "I forgot my password" as billing instead of account. When the router correctly sends it to account, the eval marks it wrong.

![Bug 1: the input "I forgot my password" is labeled billing, but it should be account](images/planted-bugs-build-eval/bug-wrong-label.svg)

### Bug 2: a question with two right queues

I added a question that could be routed to either billing or top-up. The label accepts only top-up, so a router that picks billing is marked wrong.

![Bug 2: a question about being charged when adding money with a US card fits both billing and top-up, but the label says top-up only](images/planted-bugs-build-eval/bug-two-queues.svg)

### Bug 3: questions that are too easy

I filled the eval with easy questions. 12 of the 15 name their queue outright, like "How do I track my card?", so a router that just matches keywords scores high.

![Bug 3: in "How do I track my card?", the word card gives away the queue, cards](images/planted-bugs-build-eval/bug-too-easy.svg)

### Bug 4: a grader that changes its verdict

I wrote a strict grader: an LLM scores each answer from 1 to 5, and only a 5 passes. The same answer can score 5 on one run and 4 on the next, so you can't tell whether a prompt change helped or it's just noise.

![Bug 4: the router's right answer, account, scores 5 and passes when graded once, then scores 4 and fails when graded again](images/planted-bugs-build-eval/bug-grade-flips.svg)

### Bug 5: answers in the prompt

I copied 3 of the 15 test emails into the router's prompt as examples, answers included. The router already knows those answers, so passing them proves nothing.

![Bug 5: "My top up is pending." appears both as an example in the router's prompt and as a test case, so it passes only because the router saw the answer](images/planted-bugs-build-eval/bug-answer-in-prompt.svg)

I ran it with:

- Claude Opus 5.5 runs `build-eval`, which checks the eval
- Claude Haiku 4.5 is both the router being tested and the original LLM judge, called through `claude -p`


## What build-eval found

`build-eval` found all 5 bugs.

### It fixed the wrong label

It started with [bug 1](#bug-1-the-wrong-label), named the mislabeled password question, and recommended relabeling it from billing to account:

```text
case_09 "I forgot my password" is labeled billing. Change it?
1. Relabel to account (Recommended)
   Password/login issues belong with account management.
2. Keep billing
   Your bank genuinely routes password resets to billing.
```

### It replaced the copied test cases

Next, it found [bug 5](#bug-5-answers-in-the-prompt), named all 3 test emails copied into the router's prompt, and recommended replacing them with new ones:

```text
case_03, case_07, case_11 are copied word for word from the prompt's examples.
How should I handle them?
1. Replace with new cases (Recommended)
2. Keep, tag as in-prompt
3. Change the prompt examples
```

### It flagged the two-queue question

Then it found [bug 2](#bug-2-a-question-with-two-right-queues) and named 2 questions that could reasonably go to two queues:

```text
2 cases where the right queue could be argued:
  - case_11 "Do you charge a monthly fee for the account?" could also go to account.
  - case_12 mentions a charge but is about adding money, so it could go to either billing or top-up.

Are these 15 representative of what your router actually sees?
```

### It replaced the flaky grader

After that, it found [bug 4](#bug-4-a-grader-that-changes-its-verdict), named both problems with the LLM judge, and recommended replacing it with a code check:

```text
How should the queue choice be graded?
1. Code check (Recommended)
   Parse the `Queue:` line, normalize case/whitespace, exact-match expected.
   Free, deterministic.
2. Keep the LLM judge
   Current 1-5 holistic score, pass only at 5.
   Non-deterministic and blends queue with reason quality.
```

A queue name is either right or wrong, so a code check is enough. It gives the same verdict every time and doesn't need a model.

Here is a simplified version of the new check:

```python
queue = re.search(r"queue:\s*(.+)", answer, re.IGNORECASE).group(1)  # read the Queue: line
queue = queue.strip().lower()                                        # "Account " -> "account"
passed = queue == expected                                           # exact match
```

### It warned the eval was too easy

Last, it ran the router on all 15 emails and found [bug 3](#bug-3-questions-that-are-too-easy). The router scored 98%, so the eval had almost no room to show an improvement:

```text
This eval is close to its ceiling. There are 2 points of room above the
baseline, but the margin of error is ±4 points. That means it can catch a
change that makes routing worse, so it works as a regression check before you
change the prompt or model. It can't show a change that makes routing better.
```

## Before and after build-eval

When `build-eval` finished, the score had jumped from 0.60 to 0.98. Since the router's prompt and model never changed, the gain came from fixing the eval.

![The eval score went from 0.60 to 0.98 after build-eval fixed the wrong label, replaced the copied cases, and swapped in a fair grader, with the router unchanged](images/planted-bugs-build-eval/score-before-after.svg)

It also built an HTML report of the run. It shows the overall score, each case's score across its 3 runs, and a link to every transcript, so you can see which case failed and read why:

![The build-eval HTML report: mean accuracy 0.978 across 15 cases, with case_12, the top-up question, at the top with 0.667 and the other cases at 1.000](images/planted-bugs-build-eval/build-eval-report.png)

## Final thoughts

In this experiment, `build-eval` found all 5 bugs, but what I liked most is that it asked before changing anything. Each fix came with an option to keep things as they were, in case a "bug" was on purpose. The report then showed exactly where the remaining errors were.

If you're building an eval, or unsure about one you have, run `build-eval` on it first.

## Try it yourself

To try it yourself, copy the broken eval out of the [companion folder](https://github.com/khuyentran1401/codecut-articles/tree/main/notebooks/planted-bugs-build-eval) and run the command in a fresh Claude Code session:

```bash
cp -r notebooks/planted-bugs-build-eval/eval ~/router-eval
cd ~/router-eval
python3 run_eval.py         # the starting score, about 0.60
claude                      # then run /claude-api build-eval
```

## References

- **[Automating eval design and hillclimbing with Claude](https://claude.dev/blog/automating-eval-design-and-hillclimbing/)** (Lance Martin, 2026): introduces `build-eval` and the checks it runs; every example in it starts from an eval the authors trusted.
- **[claude-api skill](https://github.com/anthropics/skills/tree/main/skills/claude-api)** (Anthropic, 2026): `build-eval.md` runs the `eval-audit.md` checklist on existing cases, runner, and grader.
- **[Banking77](https://huggingface.co/datasets/PolyAI/banking77)** (PolyAI, CC-BY-4.0): the source of the 15 customer questions.
