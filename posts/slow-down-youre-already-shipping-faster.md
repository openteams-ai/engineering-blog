---
title: "Slow Down — You're Already Shipping Faster: Simple Lessons from the AI Coding Trenches"
slug: slow-down-youre-already-shipping-faster
author: jbouder
categories:
  - Engineering
meta_description: "Practical lessons for staying in control, keeping your skills sharp, and getting real value from AI coding tools without losing yourself in the hype."
focus_keyword: "AI coding lessons"
---

# Slow Down — You're Already Shipping Faster: Simple Lessons from the AI Coding Trenches

*How to stay in control, stay sharp, and actually benefit from the tools everyone's rushing to use.*

---

## AI is going to accelerate your throughput — so slow down a bit

You're already saving a week of work — take a day to make sure the AI did a good job. Use some of the time saved to thoroughly review proposed plans and code suggestions before accepting them. Speed is a gift; spending some of it on quality is how you stay in control.

---

## Always start with a plan

No need to write one yourself — ask the AI to draft it. Then take the time to actually read it, iterate on it, and push back where it doesn't match your intent. Ask the agent to capture the plan and todos in a markdown file so it can track progress as it goes. This also makes it much easier to pick up where you left off later.

---

## Be specific with your prompts

Clearly state the requirements, input/output format, edge cases, and performance expectations. Provide sample inputs and desired outputs when you can. The more concrete your requirements, the less the AI has to guess — and the less you have to fix.

---

## Don't ask AI to perform small changes

Small edits are a waste of tokens, premium requests, and energy. Update that padding yourself. If you're asking the AI to make a small change because you don't know where that code needs to be updated — that's a signal you need to spend more time understanding the codebase, not leaning harder on the AI.

---

## Make proper use of AI instruction files and skills

AI instruction files (like `AGENTS.md`, `CLAUDE.md`, `copilot-instructions.md`) are always loaded in full as context — keep them short and intentional. Skills are different: only the name and description are always included; the full skill content is only pulled in when needed. Use more skills, and keep your instruction files lean.

---

## Don't let yourself lose your coding skills

Stay in the loop on what your AI is actually writing — review it and understand it. Code the small things by hand. Every now and then, turn off your AI assistant entirely and see how you're doing. The goal is augmentation, not dependency.

---

## Ask AI to review your PRs

Ideally, have a *different* coding agent review the PR than the one that wrote it. A fresh agent brings no attachment to the implementation decisions and will surface issues the original agent rationalized away. You might be surprised what it finds even on code it helped produce — but a second agent with no prior context is the real stress test. Still get a human review when you can; that bar doesn't lower just because AI is involved. And use AI to augment your own process when reviewing others' code too. More eyes, even artificial ones, means fewer things slipping through.
