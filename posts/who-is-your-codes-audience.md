---
title: "Who Is Your Code's Audience? An Engineering Team Talks AI-Written Code"
slug: who-is-your-codes-audience
authors:
- amelia-thurdekoos
categories:
- Engineering
meta_description: "Learn why your code's audience decides how much readability matters, as an engineering team debates AI-written code, review, and accountability."
focus_keyword: "code's audience"
---

# Who Is Your Code's Audience? An Engineering Team Talks AI-Written Code

*From the OpenTeams engineering team*

A team meeting got hijacked the other week. The plan was to talk about a dispatcher. Instead, one of our engineers set that aside and asked a question that turned out to be the most contentious thing anyone had put to the group in a long while: now that AI writes so much of our code, does readability still matter?

The honest answer the room converged on is *yes*, but the interesting part wasn't the verdict. It was the reasoning underneath it, and where people disagreed. What follows is our attempt to write that reasoning down, because the question isn't going away and the easy answers are wrong in both directions.

## The wrong question, and a better one

"Does readability matter?" is the wrong question because it has no single answer. The better framing came from thinking about *audience*. All code is meant to be read. The real question is: read by whom?

When you're writing a throwaway automation script to save yourself ten minutes, the audience is essentially no one. Let the model write the whole thing; nobody cares about the architecture of a script that runs once. One of us cheerfully admitted to vibe-coding a front end in a file format they'd never bothered to look up, on a tool no one is using yet, and just checking that the buttons landed where they asked the model to put them. That's a defensible use of the tools.

But the moment your audience is *another human who will have to reason about this code*, whether a reviewer, a future maintainer, or someone three years from now trying to fix a bug at 2 a.m., the calculus flips entirely. Code is a communication tool between people. If we can't reason about our own code, or hand it to someone else to reason about, it becomes very hard to extend or to collaborate on. Writing code purely for an AI to read defeats the thing source code is for.

So the rule we keep coming back to isn't "use AI" or "don't use AI." It's: **know who you're writing for, and write to that audience.** A maintained library and a single-use script don't deserve the same standard, and pretending they do just wastes everyone's effort in one direction or the other.

## Readability is still for humans (and for the model)

For codebases that are meant to be read, the case for structure holds up, and there are two reasons, not one.

The first is the obvious human one. Several of us have lately been reviewing pull requests that are unmistakably AI-generated: hundred-plus-line functions, control flow nested four or five `if` statements deep, the kind of code that is *possible* to understand but might cost you half a day to do it. It's not that the author didn't understand it. It's that the structure makes verifying it expensive for everyone downstream. The typical workflow that survives this is straightforward: let the model draft, because it types faster than you do, then do a heavy rewrite, splitting the long functions, fixing the docstrings, and getting the object model right, before it goes anywhere near review.

The second reason is less obvious and worth sitting with: **legibility matters for the AI too.** If you let a model rewrite functions to be arbitrarily long, you eventually blow past its context window, and the code becomes unreadable even to the tool that wrote it. Length isn't free. Every time you stuff that context back in, you're burning tokens, which costs money, and, at scale, burns energy for no good reason. The pattern shows up in miniature in an old story from the GPT-3.5 days: someone wanted to plot a 3D NumPy array as a heatmap with a slider, nudged the model along with small tweaks, and ended up with a three-to-five-thousand-line file for something an expert would write in under a hundred. Models are better now. The failure mode isn't.

There's an architectural version of the same point. Architecture encodes intent. A bad object model means the next change won't slot in cleanly, and the next person who shows up with an AI assistant ends up rewriting your code wholesale to make room for theirs. Each contribution becomes a full rewrite by a fresh model with a slightly different objective. A little forethought about structure is what stops a codebase from churning in place.

## What we actually do

None of this is anti-AI. Most of us use these tools every day. What the conversation surfaced was a set of working practices, most of them about *where* to spend scrutiny rather than whether to use the tools at all:

- **Draft with AI, own the result.** Using a model to write a first pass is fine. Shipping a pull request you haven't personally read and understood is not. If a contributor submits code they can't explain, the kind thing and the correct thing is often to close the PR rather than coach line-by-line through code nobody on the author's side has read.
- **Vary scrutiny by what the code is.** New production code that goes into a library gets the fine-tooth comb on every line. A test suite gets a lighter touch: do the tests make sense, do they cover the behavior? That's usually enough. Modifying existing, readable code is easier to review than landing a brand-new AI-generated structure, because the surrounding code anchors what "correct" looks like.
- **Use AI as a second reviewer.** Pointing a separate model at a PR and asking it to find problems a human might miss is genuinely useful, a cheap second opinion that occasionally catches something real.
- **Drive, don't release the wheel.** A useful observation from working through an AI-assisted PR on the Apache Arrow project: the model is good at generating code but thinks linearly, so it tends to *expand*, adding new functions where an existing one should have been adjusted. Point out that a new function could fold into an existing one with a couple of branches, and it'll usually do exactly that. The leverage is in steering.

That last point connects to something concrete: Apache Arrow's contribution guidelines now spell this out. Contributors are expected to review all generated code and understand every detail, to disclose AI usage, and PRs "fully generated by AI with little to no engagement from the author may be closed without further review." It's a reasonable template for any project wondering how to write this down.

## Where it gets uncomfortable: binaries, black boxes, and the buck

The forward-looking part of the discussion is where people genuinely disagreed, and we want to preserve that rather than smooth it over.

One view: context windows will keep scaling until the limits that make AI bad at low-level work today simply go away, and we reach a frontier where code is treated like a binary artifact, something we test the behavior of but don't read. The reference point here is Mark Saroufim, who runs GPU MODE and is giving a keynote at MLSys 2026 titled "When AI Starts Writing Systems Code," about AI generating GPU kernels and the work of building robust, hard-to-game evaluators for them. The argument is that today AI struggles to manipulate something like PTX, NVIDIA's low-level GPU instruction set, directly, because the instruction set is huge and underdocumented, so it eats context. In kernel competitions, hand-written raw CUDA still tends to win on absolute performance, while higher-level DSLs like Triton do better once you normalize for human effort. The claim is that these are temporary limitations, and that eventually a model could emit the compiled binary directly, with test suites standing in for human review.

(Worth noting: even the person making this argument agreed that generating binaries with AI is *absolutely not* a good idea right now. The disagreement is about the long run, not today.)

The pushback came from two directions. The first is technical: the best results people report from AI code generation tend to come from languages with the *strictest* safeguards, strong type systems like Rust, where a whole class of mistakes becomes a compile error. Deterministic guardrails guide a model toward correct output more reliably than raw assembly ever could. So if the goal is AI-generated systems code, betting on stricter languages looks smarter than betting on raw binaries, which lines up neatly with the "build better evaluators" thread: the language *is* part of the evaluator.

The second pushback is that binaries are black boxes, and some code is supposed to be readable forever. PyTorch is the example we kept returning to, a codebase whose audience includes researchers who need to muck around in the internals, experiment, and build things that haven't been built before. Python famously doesn't really enforce private data; you can reach in and touch anything. A lot of people treat that as a flaw. Others treat it as the feature that lets people on the bleeding edge learn by poking at the implementation. Source code there has value *alongside* the docs and tests, as something to read and learn from. (We'd heard this framed as a Barbara Liskov critique of Python, invoking encapsulation and the substitution principle that bears her name; we couldn't find her actually saying it about Python, so we'll let the point stand on its own merits rather than borrow her authority for it.)

And underneath all of it sits the question nobody has a clean answer to: **accountability.** If an AI system causes harm, who is responsible: the user, the prompter, or the lab that built the model? German law has a long-standing principle for activities that generate profit: whoever reaps the benefits should also bear the burdens, and liability has to rest on an identifiable party. AI makes it tempting to wave that away (*the model did it*), but you can't penalize a model, take it down, or send it to jail. Someone has to be the place the buck stops, and we mostly haven't decided who.

For high-stakes fields, this isn't abstract. When NumPy and SciPy sit at the foundation of medical-device work and scientific research, those codebases have to be rock solid, and the amount of unreviewed AI in them should be very small. Companies that ship those devices are already legally accountable for how they behave; people can be harmed, incidents get reported, and the responsibility is real and personal. The policies follow from that. Some organizations lock AI usage down hard, others are far more permissive, and the right answer genuinely depends on the stakes of the context you're working in. As a field, we still have to figure out the general case.

## What we landed on

No grand resolution, and we're suspicious of anyone offering one. The through-line is the audience question. Decide who your code is for. If the answer is "a human who will maintain this," then readability, architecture, and review aren't nostalgia; they're how the work stays workable, for people and increasingly for the models too. If the answer is "no one," use the fast path and don't feel guilty about it. And for the code the world leans on, the standard is highest precisely because the accountability is real, and that part we can't automate away yet.

One of us put the long view about as well as it can be put: it's a little scary, and no individual is going to move the trajectory of any of this, but the value we get from the work can change without the work losing its value. That seems like the right posture: clear-eyed about where the tools help, honest about what they can't yet be trusted with, and unwilling to pretend the hard questions are settled.

---

*This piece grew out of an internal engineering discussion. Thanks to the team for an unusually good argument.*

*Special thanks to the engineers whose arguments shaped this piece: Yukio Siraichi, Benjamin Glass, Drew Hubley, Hameer Abbasi, Pearu Peterson, Erik Postma, and Andrew James.*
