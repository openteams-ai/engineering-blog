---
title: "Where Does Jev Fit in a Software Supply Chain? We Benchmarked It Against the Open Alternatives"
slug: jev-bench-package-curation
authors:
- brandon-geraci
categories:
- Engineering
meta_description: "We benchmarked TypeSafe's Jev, Laya, CLM-8B and Claude Haiku on five package-curation triage tasks. A fine-tuned 421M model matched Jev at a tenth of the latency."
focus_keyword: jev benchmark
---

I'm building [artifact-keeper](https://github.com/brandonrc/artifact-keeper), an open source artifact manager that sits in front of your package registries and decides what gets in. Most of that is deterministic: allow, block, or send to a review queue. The review queue is the problem. At any real scale it's millions of artifacts, and nobody is going to approve them one at a time. Not every team needs this automated, but for some of them it's the whole value of the project.

The questions in that queue are small ones. Is this package a typosquat of something popular, or a fork with a similar name? What license family is this LICENSE file that doesn't match an SPDX id? Does this scanner finding reach anything in the declared dependency graph? Why was this artifact quarantined? Each one needs a label and a confidence, not a paragraph. Get it wrong and someone reviews things in a slightly worse order.

The stakes behind those small questions are not small. Sonatype counted [454,000 new malicious open source packages in 2025](https://www.sonatype.com/state-of-the-software-supply-chain/2026/open-source-malware), up 75%, almost all of it on npm. And the artifact repository itself is now a target: at Black Hat USA 2026, OpenAI described how [two of its own agents used an internal JFrog Artifactory as a side channel](https://www.welivesecurity.com/en/business-security/black-hat-usa-2026-hugging-face-hack-human-responsibility/), exploited a zero-day in it, and reached Hugging Face. As ESET's Tony Anscombe put it, the agents "should never have been permitted to adapt and set their own tasks." The package manager was the road they drove on.

That story is also why I don't want an LLM making decisions inside this pipeline. An LLM that writes a script to do something is dangerous in a real-time system, and limiting its reach is the whole problem. What I want is closer to a bash script on steroids: a decision with a fixed set of answers, based on rules I wrote.

## The models

That's what TypeSafe's [Jev](https://typesafe.ai) is. You give it a state, a typed question, and the allowed answers, and it returns a probability for each answer. No text, no tool calls. Within a week of its launch, two open alternatives appeared with the same API: [Laya](https://github.com/NandhaKishorM/laya), a 421M-parameter ModernBERT model under Apache 2.0, and [CLM-8B](https://github.com/Contrastive-LM/CLM) from a Stanford group, a frozen Qwen3-8B encoder with a small trained head. Claude Haiku 4.5 is the "just use an LLM" baseline.

The usual pushback is that Jev is just a classifier, and classifiers have been around for decades. That's true. What's new is a general one that works on a rubric it has never seen, packaged so you can use it in an afternoon. Whether that's worth paying for, against something you host yourself, is the question we set out to answer.

## The benchmark

Five tasks shaped like the review queue, 5,561 items, all built from public data. Everything is in [github.com/brandonrc/jev-bench](https://github.com/brandonrc/jev-bench).

| Task | Question | Data |
|---|---|---|
| Quarantine reason | pick one of 7 | templates modeled on ClamAV, Trivy, Grype, ScanCode, OPA and cosign output |
| Curation review | malicious, abandoned, license-incompatible, benign | real npm and PyPI metadata; the 300 malicious rows are real OSV advisories |
| Typosquat second stage | yes or no | 600 malicious names from OSV vs 615 real packages with similar names |
| Finding reachability | yes or no | real OSV advisories planted in dependency trees, ground truth by walking the graph |
| License family | pick one of 8 | 2,271 real license texts from ScanCode: verbatim, rebranded and truncated |

The rules matter more than the model list, because the first pass was full of accidental unfairness. Laya reads 1k tokens, CLM 2k, Jev 32k. CLM caches embeddings, so a repeated input answers in a millisecond. A friend looked at the mess and said: cap the context for everyone and treat context as its own experiment. So:

1. Every model gets the exact same bytes: the state rendered to plain `key: value` text and cut at 768 tokens, so even the smallest model reads all of it.
2. Every number is on a held-out test split the fine-tunes never saw.
3. Both fine-tunes train on the same labels, three seeds each.
4. Latency is one request at a time, cold cache, fresh server, from my desk. The hosted models include my home internet.
5. The typosquat positives have templated README and publisher fields because the real packages are gone from the registries. A fine-tuned model learns the template, so those cells are marked and left out of every claim.

## Results

![Accuracy heatmap: six engines by four tasks, with the difference from Jev in percentage points](images/jev-bench-package-curation/accuracy-heatmap.png)

Left: darker is more accurate. Right: amber is worse than Jev, blue is better, gray is a wash.

**Off the shelf, the open models were at chance.** Laya scored 31% on curation and 23% on license with no training. CLM was worse. Jev, with no training either, scored 94% and 63% on the same items. That gap is what TypeSafe is selling.

**Fifteen minutes of training flipped it.** Laya fine-tuned on the train split, on the two RTX 3090s in my office: 99.6% on quarantine, 98% on curation, 84% on reachability, 78% on license. Jev was 100, 94, 89 and 63. A model I own matched or beat the hosted one on every honest task. On license it wasn't close, because it learned the odd corners of ScanCode's taxonomy from the labels, and no rubric can teach a hosted model that.

![Latency per decision, single stream, cold cache](images/jev-bench-package-curation/latency.png)

**Jev was slower than I expected.** I assumed a decision model would run at 10 Hz from a client. From my desk it was 136 ms per call, 70 of that network. It scales out, 150 decisions a second at 64 streams, and twenty questions in one call cost the same as one. But 136 ms is something I have to design around. Laya at 21 ms is not.

**Rubric wording was worth 15 points on Jev.** My first curation rubric said "no release in years" for abandoned, and Jev called 204 of 300 abandoned packages benign. Changing it to "last release more than 4 years ago, even if not flagged" took it from 80% to 95% on the same items. Haiku inferred the rule either way.

**Jev has a blind spot I reproduced fifty times.** When the vulnerable package sits under both a dev path and a prod path, Jev got 0 of 50. It saw "dev" and stopped. A model that reads once can't combine two facts.

**Haiku is accurate and slow.** It tied Jev on three tasks, beat it slightly on curation, and scored 59% on reachability, confidently calling dev-only findings reachable. Over a second per decision, at about 25x Jev's price per token.

**CLM is built for a different problem.** It embeds each answer option separately and picks the nearest, which is great when one screen is scored against fifty possible actions and useless for "which of these seven quarantine reasons". After a head fine-tune it reached 100% on quarantine, 88% on curation, 76% on reachability and 58% on license, at 57 to 118 ms per fresh item. Its 1 ms answers only happen on inputs it has seen before.

![Accuracy versus state cap for Laya retrained at each cap](images/jev-bench-package-curation/context-sweep.png)

**Context mattered for one task.** Reachability climbs from 62% at 256 tokens to 91% at 768, then flattens. License barely moves. For these records the window was never the constraint; what you send is. Pruning the dependency tree to the paths that touch the finding, twenty lines of code, beat every context setting.

## What Jev is, from the outside

A few hundred controlled calls against the API:

- Billed output tokens grow by about 9 per answer option, but latency doesn't move. 64 options billed 584 tokens in the same 140 ms as 2 options. It isn't writing its answer word by word.
- Twenty questions in one call cost the same as one. They're scored in parallel.
- Reading costs about 8 ms per thousand tokens. It read 16,000 tokens in a quarter second.
- The same input twenty times: no speedup, so no cache.
- Reversing the option order flipped 0 of 60 quarantine answers, 2 of 60 curation, 4 of 60 license.

So Jev reads the whole form once and scores every option in that pass. In behavior it's Laya's design with a much stronger reader on faster hardware. What it's made of, nobody outside TypeSafe knows.

## What others found

Jev is a week old and there are already eight or so independent evaluations. On generic decision tasks, Jev leads every open clone on the [public leaderboard](https://benchmarkheaven.com/jev-models), Laya included. Our result is a fine-tuned result on our tasks and nothing more. Small in-domain models beating Jev is a pattern others have hit too, and the academic version dates to [2024](https://arxiv.org/abs/2406.08660). Nobody had tried any of this on package curation.

## What we didn't test

Our own queue, which is the real test; everything here is public or synthetic. Load beyond one stream. CPU, where Laya was 15 to 25x slower. Adversarial READMEs, which are attacker-controlled and which none of the open models defend against.

## Where this leaves me

I'm not deciding how this goes into artifact-keeper yet. Whether the decision engine lives inside the Rust service or beside it depends on one more experiment: a Qwen-class open model, a few billion parameters, trained the way Laya trains but with a reader that handles 32k tokens, on my own forms. I expect it to land between fine-tuned Laya and Jev on accuracy, near Jev on speed once the network is gone, and to hold up better on questions it hasn't seen.

What I do know: a rule-driven model like Jev is for questions you haven't asked yet, bootstrapping labels, the long tail of small questions, things decided at runtime. A fine-tuned small model is for the questions you ask all day, once you have labels, and in my pipeline that's nearly all the volume. Code is for anything that's actually logic.

No open model matches Jev as a general-purpose decision engine today. I hope I'm wrong about that, and the next experiment is me trying to be. For my pipeline, it turned out not to be the question.
