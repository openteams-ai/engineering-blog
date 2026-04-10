---
title: "What I Learned Making a Local LLM Do Real Work"
slug: what-i-learned-making-a-local-llm-do-real-work
author: adam-lewis
categories:
  - Engineering
---

In my [previous post](from-skill-to-agent), I described building an AI agent for Harvest time tracking using Pydantic AI — driven partly by security concerns with the skill-based approach. The agent worked perfectly with Claude. Then I tried running it locally.

It added a time entry on Tuesday instead of Monday. When I asked it to fix that, it added the Monday entry but forgot to delete the Tuesday one. This wasn't a damning verdict on local models — but it was a useful lesson about where to invest your time when building agents.

## Going Local

Why run locally? Partly practical — no API costs, no data leaving my machine. But honestly, partly just for fun. The dream of doing everything locally without worrying about privacy or third-party dependencies is appealing, even if it's not strictly necessary for a time-tracking tool.

I'd already been experimenting with running models locally for coding tasks, which I [wrote about previously](https://adam-d-lewis.github.io/blog/running-a-local-coding-agent-with-qwen3-coder-next/). Since then, llama.cpp has added built-in [router mode](https://github.com/ggml-org/llama.cpp/pull/17859) — you run a single server process that auto-loads and unloads models on demand based on the `model` field in your API request. With `--models-max 1` it evicts the current model when you request a different one, which works well for my setup with an RTX 3060 12GB where only one large model fits in VRAM at a time.

My first test model was Qwen3-Coder-Next — 80B total parameters but only [3B active](https://huggingface.co/Qwen/Qwen3-Coder-Next) per token (it's a Mixture-of-Experts model with 512 experts, 10 selected per token). I was using the Q4_K_M quantization, about 46GB on disk. It's built for coding tasks, not calendar math and time-tracking. So it wasn't exactly a fair fight from the start, and the quantization may have further degraded its reasoning on this kind of task.

## Where Things Went Wrong

I want to be careful here — this isn't a story about local models being bad. Local models can be very good, and they're getting better fast. [GLM-5.1](https://huggingface.co/zai-org/GLM-5.1), for example, is a 754B parameter model with reportedly near-Opus 4.6 capability under an MIT license. The fact that you can self-host something at that level at all is incredible, even if you need serious hardware to run it.

This was more of an exercise in seeing if I could make the agent robust to a poorly-performing model. The agent worked fine with Claude Sonnet 4.6 — I wanted to see what would break when I threw a much weaker model at it. Here's what I ran into:

**Date math:** I asked it to log time for "next Monday." It picked Tuesday. When dates crossed month boundaries, it got worse.

**Day-of-week hallucination:** Given the ISO date "2026-04-07," the model confidently identified it as Monday. It's Tuesday.

**Silent substitution:** I typed a project name with a slight typo. Instead of asking for clarification, the model quietly logged my time to a completely different real project.

These aren't exotic edge cases — dates and project names are the entire job of a time-tracking agent. Could it have been the model, the quantization, something in llama.cpp, or just that 3B active parameters isn't enough for this? Hard to say. Probably some combination.

## Pushing Logic Out of the LLM

Rather than guessing at fixes, I started by building evals — 22 test cases covering tool selection, date parsing, shortcut resolution, hallucination detection, and project validation. Evals are valuable regardless of model quality. Model life cycles are short; you're going to be swapping models regularly, and evals let you validate each swap quickly and catch regressions.

With the evals showing me exactly where the model was failing, I systematically moved deterministic work out of the LLM and into Python:

**Date parsing:** Instead of asking the model to calculate "next Friday," the tool code parses relative dates in Python. The system prompt includes a three-week calendar table — last week through next week — so the model just reads dates off the table instead of doing arithmetic.

**Project validation:** At startup, the agent builds an index of real Harvest projects. Every tool call validates the project name against this index before hitting the API. Typos get fuzzy-matched with suggestions ("did you mean Deep Learning?"). The model is explicitly told: never substitute a project the user didn't ask for.

**Shortcut resolution and hour rounding:** Lookup tables and rounding logic in Python, not left to the model.

The pattern behind all of these: **the LLM handles intent — understanding what the user wants. Code handles precision — getting the details exactly right.** Anything deterministic belongs in code, not in the prompt.

After these changes, Qwen3-Coder-Next passed 100% of my eval cases. But in real-world usage, it still had rough edges not covered by my (admittedly quick) test suite. A 100% pass rate means your test suite isn't comprehensive enough yet — not that you're production-ready.

## A Better Model Changes Everything

I tried a few other local options. Gemma 4 E4B (roughly 4B parameters, fits entirely in VRAM) was fast but just wasn't reliable enough for agent tasks.

Then I loaded [Gemma 4 26B-A4B](https://huggingface.co/ggml-org/gemma-4-26B-A4B-it-GGUF) — a Mixture-of-Experts model with about 4B active parameters out of 26B total. It fits on my 12GB GPU by offloading the MoE expert layers to CPU. And it just... worked. The rough edges I'd been fighting with Qwen largely disappeared. Not a frontier model, not even a huge model — but a better fit for this task, still running entirely on my hardware.

I'd spent a lot of time engineering around Qwen's weaknesses. A better model — still local, still on the same GPU — solved most of those problems without extra effort.

To be fair, the engineering work wasn't wasted. Moving deterministic logic to code made the agent better for *all* models, including Claude. That kind of improvement is worth making regardless. But the hours spent debugging model-specific failures? Those were mostly absorbed by a better model.

## Practical Takeaways

These are suggestions from my experience, not hard rules — your mileage will vary.

**Default to the best model you can use, then scale back with measurement.** Don't start by trying to make a weak model work. Get the product right first, validate the concept, then optimize if needed. In my case, going from a coding-specialized 3B-active model to a general-purpose 4B-active model made a dramatic difference — and both ran locally on the same hardware.

**Invest in evals early.** Even if you're using a frontier model, evals give you a regression safety net for when you swap models, update prompts, or change tool implementations. They're not just for debugging weak models.

**Think carefully before fine-tuning a smaller model.** I've done fine-tuning work on a separate project — training a small model for GitHub issue classification — and the maintenance burden is real. Adding a new label means regenerating your training dataset and retraining. Any requirement change means re-doing that work. For most use cases, I suspect the maintenance cost exceeds the inference savings. It might make sense at industrial scale — a company running chatbots for hundreds of clients, where a stable fine-tuned model is amortized across huge volume. But for most teams building agents, a better base model plus good engineering is probably the more practical path.

Before fine-tuning, consider the alternatives: better prompts, moving more logic to code (as I did here), structured output constraints, or honestly just waiting — small models are getting better fast. By the time you finish a fine-tuning pipeline, the next generation of base models might have closed the gap.

## The Bottom Line

The best agent architecture is one that doesn't depend on the model being brilliant. Push precision into code, let the LLM handle intent, invest in evals, and start with the best model available to you. You can always optimize later — and by the time you need to, there might be a better small model anyway.
