---
title: The Best Code Review Says Less
slug: best-code-reviews-say-less
authors:
  - johnny-bouder
categories:
  - Engineering
meta_description: "Far too many AI code review comments are noise. Pair a human editor with AI, surface only the findings that matter, and encode that discipline in a reusable skill."
focus_keyword: AI code review
---

*Your AI reviewer talks too much.*

You open a pull request and there are 40 inline comments waiting for you, all from the AI reviewer. It has opinions about a variable name. It wants you to extract three lines into a helper. It found a null that can't actually occur, on a path that never runs. It's suggesting a micro-optimization on code that executes twice a day.

Maybe three of those comments matter. The rest are noise, and now it's your job to figure out which three.

This is where AI-assisted code review is right now, and I think we've optimized for the wrong thing.

## Chatty by default

Most AI reviewers are tuned to find *something*. Coming back empty-handed looks like failure, so they fill the space instead: style preferences, speculative refactors, defensive checks, a pile of "consider" comments that nobody needs to consider. You get a review that looks thorough and is practically useless, because the one comment about a broken invariant is buried under thirty about naming.

Volume is not rigor. When a review flags everything, it flags nothing, because sorting out what actually matters lands right back on the human it was supposed to help. I've seen reviews with more lines of prose than the diff had lines of code. Impressive, in a way. Not what we were going for.

## The over-engineering tax

There's a second problem hiding behind the verbosity, and it's more expensive: these tools don't just talk too much, they push you to *write* too much.

Handle this edge case. Add a guard here. Wrap that in a try/catch. What if the input is negative, empty, unicode, a leap second? Every one of those suggestions sounds reasonable on its own. Take them all and you end up with more branches than behavior, with error handling for conditions that can't happen and guards for callers that don't exist.

Not every edge case needs handling. Some inputs are impossible by construction. Some failures *should* crash loudly instead of getting swallowed by a helpful catch block. An AI optimizing for coverage will never tell you to write less.

Mission-critical systems are the exception here. When a silent failure makes headlines, the paranoia is worth it. But most code isn't flying a plane, and we've been reviewing all of it like it is.

## Long PRs cost twice

All that extra code has to go somewhere, and where it goes is the diff. A defensive, edge-case-hardened, maximally-reviewed PR is a long PR, and long PRs are worse on both ends.

They're harder to review now, because past a certain length reviewers start skimming and real problems slip through. That's not a hunch, it's the most-cited finding in code review research (numbers at the bottom of this post). And they're harder to understand later, because whoever is debugging this at 2 a.m. eight months from now has to work out which branches are load-bearing and which ones only exist because a linter had opinions. Every unnecessary line is a line somebody has to read, trust, and maintain. Simplicity is what keeps a codebase legible. It's not a nice-to-have.

## Human + AI: the human is the editor

None of this means turn the tools off. AI is genuinely good at surfacing candidates. It reads the whole diff, it never gets tired, and it catches things a human skims right past. The mistake is letting it publish directly.

So change the workflow: the AI drafts, the human edits. Your job as the reviewer isn't to relay every finding. It's to curate. Pull out the two or three items that actually matter, put them in the PR as a short discussion, and throw the rest away. Correctness, security, data loss, a broken contract, an abstraction that will genuinely confuse people... those get a comment. A variable you would have named differently does not.

Good senior reviewers already work this way. They don't dump their whole stream of consciousness into the PR. They decide what's worth the author's attention and say only that. AI should feed into that judgment, not replace it.

## Encode it in a skill

AI reviews are noisy because the default instruction is basically "review this," and you get what you ask for. So ask for something better, and make it reusable while you're at it.

A lightweight code-review skill can carry the philosophy so nobody has to re-explain it every time:

- **Default to silence on style.** Naming, formatting, and structure are the linter's job. Don't comment unless it's a correctness or clarity problem.
- **Only surface high-value findings:** Bugs that produce wrong behaviors, security holes, paths that can lose data, changes that quietly break an API contract, and abstractions the next reader won't be able to follow.
- **Cap the output.** A hard ceiling on comments forces prioritization. If everything's important, nothing is.
- **Treat over-engineering as a finding, not a fix.** Flip the tool's instinct. Instead of suggesting more guards and more branches, have it challenge complexity: "Can this edge case actually occur? If not, delete the handling."
- **Be terse.** One or two sentences per comment. No preamble, no "consider," no essays.

The nice part is that this fits tooling we already use. It's a small, versioned artifact, same as an `AGENTS.md` or a skill, so the review standard lives in the repo and travels with the team instead of living in someone's head.

## The short version

AI reviewers are verbose because we tuned them that way, and they push us toward bloated, over-defensive code for the same reason. The fix isn't abandoning them. Put a human editor in front of the output, surface only what's critical, and encode that discipline in a reusable skill. Write less code, review shorter PRs, and save the paranoia for the systems that have earned it.

The best review isn't the one that finds the most. It's the one that says the least and still catches what matters.

## By the numbers

A few figures that make the case better than opinion can:

- **AI reviewers are noisy by default.** [Graphite's guide to AI review false positives](https://graphite.com/guides/ai-code-review-false-positives) puts even the best tools at a 5–15% false-positive rate. And that's the good end: when [Augment Code benchmarked review agents](https://www.augmentcode.com/blog/how-we-built-high-quality-ai-code-review-agent) on real pull requests, its own agent scored 47% precision and ranked second, meaning more than half of the comments from most tools were noise.
- **Most AI comments get ignored.** [CodeAnt's analysis of review overload](https://www.codeant.ai/blogs/prevent-ai-code-review-overload) describes teams seeing 200–400 AI comments a week with 70–90% dismissed as false positives, and warns of the credentials leak that ships because the real warning was comment #43 of 60. That "cry wolf" effect is the most common reason teams abandon these tools.
- **A right-sized review catches 70–90% of defects.** [SmartBear's study at Cisco](https://static0.smartbear.co/support/media/resources/cc/book/code-review-cisco-case-study.pdf), the largest of its kind at ~2,500 reviews across 3.2 million lines of code, found that a properly sized, unhurried review surfaces the large majority of defects present. Detection drops sharply past [200–400 lines of code](https://smartbear.com/learn/code-review/best-practices-for-peer-code-review/), and effectiveness collapses after 60–90 minutes of continuous reading regardless of size.
