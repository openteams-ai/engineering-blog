---
title: "LLMs: Intelligence vs. cost"
slug: intelligence-vs-cost
author: guido-imperiale
categories:
  - Engineering
  - Management
---

[ArtificialAnalysis](https://artificialanalysis.ai) is a website that benchmarks the
intelligence of various LLM models. They publish a headline _Intelligence Index_, which is
calculated as the mean output of the curated selection of benchmarks they run on each
models. It's a decent finger-in-the-air measure of how smart a model is overall.

AA also records useful information — namely, how much it cost them to run the
benchmarks. Since the benchmarks are the same across all models, this offers a good
indicator of how much it will cost a user to run each model, in relative terms.

One of their main plots is the [Intelligence vs. cost
plot](https://artificialanalysis.ai/#intelligence-comparison-tabs), which shows the
Pareto frontier, that is the cheapest model that can achieve each intelligence score.
This frontier is important, because using a super-intelligent and super-expensive model
to accomplish menial tasks that could be done by a much dumber and cheaper one is just a
waste of money.

Over time, I became progressively more irritated by this plot, for a few reasons.

## Why AA's plot is misleading

The first issue I have with it is that it uses a logarithmic scale on the cost axis.
Using a log scale is the only way to make you spot the difference between a model that
costs $0.05 per task and one that costs $0.09, while you have on the same plot model
that cost $3 — 60 times as expensive. However, the net result is that the viewers can no
longer appreciate the immensity of the price difference between the cheap models and the
heavy ones; nor they can realize how inconsequential the price differences are between
the cheap models.

The second thing that irks me is that it uses the official pricing from the model
developers' own API offering. This is fine in most cases, but for some open-source
models, namely GLM and DeepSeek, it can be a lot more expensive than what the exact same
model can be rented for from third party API providers.
[OpenRouter](https://openrouter.ai) makes it very easy to switch providers on the fly
and always get the cheapest offer.

The third and final issue is that local models — those that can fit on consumer hardware
— appear on the plot at their datacenter pricing, which is always very expensive in
proportion to the intelligence you buy with it and ultimately not something any real
user will actively want to buy.

## I made my own plots

All intelligence index scores are from ArtificialAnalysis.
All points are benchmarked at maximum thinking effort where not explicitly stated otherwise.
All cost scores are from ArtificialAnalysis too, except where noted below.

In the first plot we see today's situation with intelligent (and expensive) models.

A good rule of thumb for reading the intelligence axis: a one-point difference is
unlikely to be noticeable by most, while a 5-point gap is substantial. It's important to
point out that an intelligence score of 50, which is the rock bottom in this first plot,
is more than what the smartest models ever invented by humankind could deliver in
Feburary 2026 (Sonnet 4.6 or Gemini 3.1 Pro Preview, both rated at 48).

![Intelligence vs. Cost per Task (High Intelligence)](images/intelligence-vs-cost/high_intelligence.png)

The green area at the bottom left is where models become _extremely_ cheap. Let's zoom
into it and extend the intelligence plot a bit lower, down to what can run today on a
smartphone.

Some models are marked with a ⚡ symbol. It means that the cost was calculated as the
electricity to run the model locally (details on the calculation below), since the model
is so small that it makes no sense to serve it from a datacenter. This also offer a
scale of the speed at which each model completes tasks, given the same hardware.

![Intelligence vs. Cost per Task (Low Cost)](images/intelligence-vs-cost/cheap.png)

Finally, let's merge the two plots together to better visualize the diminishing returns in
performance/cost. Again the area that's common to all plots is highlighted in green:

![Intelligence vs. Cost per Task (All Models)](images/intelligence-vs-cost/all_models.png)

## All the differences between AA's plot and mine

- Changed X scale from logarithmic to linear, because people's money is not logarithmic
- Changed DeepSeek V4 Flash 0731, GLM-5.3-Flash, and Hy3 to the price you can get them
  for on OpenRouter (excessively slow or unreliable providers and those without
  Zero Data Retention policies are excluded). Note that you don't get these prices with
  OpenCode Go/Zen.
- Added GLM-5.3 as it is expected to be priced by third party providers on OpenRouter in
  September 2026, assuming no license changes from 5.2.
- Extrapolated points for GLM-5.3-Flash at High reasoning effort by crossing AA scores
  at Max with [Z.ai's coding scores](https://z.ai/blog/glm-5.3-flash) at different
  effort levels
- Changed cost of sub-35 billion parameters models from datacenter pricing to cost to
  run locally.
- Added Ornith-1.5-35B. The intelligence score is extrapolated from _self-reported_
  benchmark results by the model authors and should be taken with a healthy dose of
  skepticism.

## Cost calculation for local models

Cost per task for models marked with ⚡ was crudely calculated as follows:

- Take Output tokens per task [from
  artificialanalysis.ai](https://artificialanalysis.ai/#intelligence-comparison-tabs)
- Crudely observe decode speed (tok/s) on local hardware. Most measures were taken on
  the same RTX 3090 video card, which when it was released in 2021 was the best money
  could buy but today is relatively affordable.
- Measure delta between peak and idle energy draw on said hardware
- Price electricity at $0.2049/kWh, which is the US residential electricity price,
  weighted average by population, as of May 2026.
- Add 15% (finger-in-the-air) for uncached input tokens and waiting for tools
- Hardware is priced at 0, on the basis that both a RTX 3090 PC and a 64GB Strix Halo
  are desirable gaming/work machines anyways.

Note that there isn't a material difference in electricity costs between different
hardware platforms: a Strix Halo draws less power than a RTX3090, but it's slower so it
needs to run longer to complete the same tasks.

## Larger local models

Not including the cost of hardware stops being defensible once you upgrade beyond 64 GB
RAM, as almost nobody needs that much RAM if not for AI.

Qwen3.8-Flash needs, as a minimum, a 128GB Strix Halo; it's on the plot as electricity
only (in addition to as a datacenter offering), but it already hides a substantial
hardware cost: a 64 GB Strix Halo, which is a very desirable general purpose mini PC,
costs $2,000; a 128 GB one costs $3,600 and doesn't enable anything other than AI models
in the ~120B parameters class.

The following models _can_ be ran locally, but carry a very steep up-front hardware
cost:

| Memory | Hardware | Models |
| --- | --- | --- |
| 128 GB RAM | Strix Halo ($3,600)<br>DGX Spark ($4k)<br> | Qwen3.8-Flash<br>GLM-5.3-Flash (degraded intelligence; very tight fit)<br>DeepSeek-V4-Flash (degraded intelligence; very tight fit) |
| 256 GB RAM | 2x DGX Spark ($8k)<br>Mac Studio M5 Ultra ($11k) | GLM-5.3-Flash<br>DeepSeek-V4-Flash |
| 512 GB RAM | 4x DGX Spark ($16k)<br>2x Mac Studio M5 Ultra ($22k) | GLM-5.3 |
