---
title: "You Don't Drive AI. You Ride It."
slug: you-dont-drive-ai-you-ride-it
authors:
  - amelia-thurdekoos
categories:
  - Engineering
meta_description: "AI is stochastic, not deterministic. You don't drive it, you ride it: make documents the memory, use the variation to prototype, and verify every public claim."
focus_keyword: "riding AI"
---

Most people try to operate AI the way they operate software. They issue a command, expect the same output every time, and get annoyed when the thing wanders off. That model is wrong, and the wrongness is not a detail. It is the whole reason this is hard.

It is a horse, not a train. A train follows the same track every day. A horse never will. If you have ever been on a horseback ride, you know the shape of it: the horse follows the trail for a bit, then it sees a squirrel, and you never quite know where you end up.

So you do not drive it. You ride it. And before you trust where it took you, you go check.

There is a build behind that claim, not a metaphor floating on its own. In about a week, riding this way turned a single large strategy meeting video into a customer-reviewed React landing page, two traceable requirements documents, a footnoted credibility document, and [a published site](https://openteams.com/python-security-remediation/). Every public claim got checked before it left the building. Here is how that worked, and what I would steal from it.

## A Horse, Not a Train

A deterministic system repeats. Same input, same output, every time: calculators, compilers, spreadsheets. A stochastic system wanders. Ask it twice and you get two different answers.

You don't drive AI. It is not deterministic. It is stochastic, probabilistic. When you guide it, you are not handing it a procedure. You are not telling it to do X, Y, and Z. You are guiding it, the way you would ride a bull or a rhino: don't go here, go in that direction, and expect it to go its own way.

That property is a feature and a risk at once, and the whole method comes out of refusing to pick just one. Free variation is exactly what you want when you are exploring. Ask for a website three times and you get three genuinely different websites to choose between. Free variation is exactly what you do not want when the output is a factual claim that a customer will read.

So the split is not a problem to solve. It is the hinge. Use the randomness where it helps. Bolt deterministic checks on where it hurts. Every claim that becomes public gets adversarial verification, `[[CONFIRM]]` markers, footnotes, and git history.

Keep both halves of that in view. The rest of this follows from taking each one seriously.

## Context Is the Saddle Bags

If the model wanders, the one real lever you have is what you pack before the ride.

Context is the AI's saddle bags. Empty bags mean generic guesses. So I never start a session from memory. I clear sessions often, and I hand it the documents at the start of each one. The documents are the memory, not the chat. A chat session disappears. A document is something a person can open six months later and audit.

That reframes the skill. Writing things down is a management skill, not a coding skill, and that is how you have to treat it. You are not really coding with the tool. You are managing it the way you would manage a junior or mid-level employee. Tell it the constraints, tell it where not to go, then check what it did.

The raw input here was our CTO's strategy meeting, recorded as a single large video. It was too big to live in the repo, so it sits outside it. A notetaking app would have given me the audio and missed half the meaning, because people point at things on a screen while they talk. So I had `Claude Code` take screenshots and analyze what our CTO was pointing at when he reviewed a site, not just what the microphone caught. Out of that came a requirements document: a numbered, traceable list of requirements, each one carrying a verbatim quote, a timestamp, and a status, plus a precedence table for when two meetings conflict.

The stable IDs are the trick. Every later artifact (the design prompt, the site copy, the credibility doc) traces back to a specific `DR-##` and the real sentence it came from. When someone asks why the page says a thing, the answer is a requirement ID and a timestamped quote, not "the AI decided."

## Three Rides in a Week

Early on, the wandering is the asset. Because the model does not repeat itself, you can generate genuinely different directions fast and then pick. I did three full generations of the website in a week.

The first prototype was beautiful, and it over-claimed. It leaned on language we could not back up, and the accuracy needed work. The second was a tighter, more focused framing, a real step up. The third was a larger leap, a broader strategic reframing, and that one became the site the customer reviewed.

The jump to the third was not a whim. It was a requirement. It traces straight back to our CTO in the strategy meeting, making the case that the framing should lead with where the work is going, not where it came from. That direction, captured as a requirement and tied to a timestamp, drove the headline of the final design. That headline ended up leading with "Security for the AI stack," the forward-looking framing the requirement asked for.

I was not the one steering the look of any of this. The last front-end design I did before this was MySpace. For those of you old enough to remember MySpace, that was it. I do not really know front-end design. I trust `Claude` to do it, I guide it, and I ride it a little.

## The Redline Loop

Riding is continuous steering, not a single command. The working loop was visual and tight.

When something on the site was wrong, I drew a red circle on a screenshot of it, pasted that straight back into `Claude`, and got a revision. More than twenty of those pasted screenshots and sketches are in the repo. That is the iteration loop made literal: circle, paste, revise.

The steering is constrained, not freeform, and the constraint is written down. The instruction is always a change request, never a rebuild. The design prompt says it directly: "This is a change request, not a rebuild. Preserve what already works, apply the change set below, stay on-brand, and honor every hard constraint exactly." That prompt is its own packed-context artifact, a long and detailed brief. It covers pinned versions, load order, the brand tokens, per-section content rules, and the same honesty constraints the requirements doc captures. The brand source was the `Figma` files from the marketing team, fed in directly.

Prompting at this scale is just writing a good brief. The better the brief, the less you redo.

## Verify Before It Leaves the Building

Here is the risk half of the horse, and it is the part I care most about getting right.

The common fear about AI is that it invents claims. Used this way, it does the opposite. A whole block of the requirements are explicit prohibitions: no unearned certifications, no invented numbers, no absolute claims. The first prototype had cheerfully invented its own marketing claims: a guaranteed-fix service promise, a precise running tally of issues resolved, and a specific turnaround commitment, none of which we were willing to put in writing. Every one of those was killed by the requirements doc before the customer ever saw it.

One requirement is the cleanest example, straight from our CTO: "we're not going to put that there." A specific service-level commitment did not belong on the page, he reasoned, because terms like that get worked out per engagement and stating a hard number up front could box us in. The model's job there was not to write a confident claim. It was to remember the claim we were forbidden to make and enforce that.

The best single illustration is a number. Someone on the call offered a rough estimate of the catalog size from memory. Rather than take that figure and run with it, `Claude` derived the number from public sources and wrote down how it got there. The published claim was the one the public record could actually support, with the methodology attached. The model did not inflate the number to flatter anyone, and it did not just repeat a figure it had been handed. It worked the claim back to what could be verified, and the verified version held up better than the guess would have. A separate draft claim about our standing in an open-source community got the same treatment. The model held it to what the public record could support rather than to the more generous version in the draft.

That discipline lives in the credibility document, footnoted throughout to public sources, with several places where the AI argued our own claims down to what the record supports. The doc states its own authority in plain text: every client-facing claim is bound by the requirements doc, and every number is footnoted to a public source. Git carries the rest of the proof. Every requirement resolution and every version of the copy is a commit, a run of them over two days just to resolve open markers, each one a readable diff.

The requirements doc went through adversarial verification, a second pass that tried to disprove each requirement against the transcript. All but two of the requirements survived, and the two that did not are on record. We did not quietly drop them to make a clean number. Do not lower the bar on human review just because AI is involved.

## When the Input Is Squishy

The hardest case for any of this is bad input, and it is where the only real disagreement of the day showed up. I am going to leave that disagreement standing, because it is right.

The review call came back as a long transcript, and the speech-to-text had mangled it. The real feedback was buried under transcription errors, and a handful of tool and library names had come through garbled. Rather than guess freely, `Claude` scored its confidence on each unclear term and reconstructed the names from context, flagging the shaky ones to check by hand. It followed one rule: low-confidence decodes never drive a page edit on their own.

The point is that confidence score. The model says what it is sure of and what it is guessing, which is more than most meeting notes manage. My stance going in was that good enough is great for rapid prototyping in a case like this. The transcript was accurate enough, and the iterative loop would catch the rest.

Dillon Roach pushed back, and he was not wrong. He has gone back and read those automated meeting transcripts and found his own words twisted. "The way that it twisted my words is frustrating," he said, "because you're like, oh, if somebody comes and reads that later and thinks that's what I actually said." There is, in his phrase, "that AI jiggle room that's just, it's squishy."

I agree with Dillon 100%. The distortion is real, and it matters most when the record will be read later by someone who was not in the room. I still would not let that stop you from starting with messy input. It is better than nothing. There are enough words in the context for the model to get you somewhere, and "it'll come out in the wash a little bit as you do that iterative cycle." Both of those things are true at once. The fix for squishy input is not cleaner input you do not have. It is making the model publish its own uncertainty, then running the loop that catches the distortion.

## What People Asked

When you describe riding this way, the questions that come back are practical, and each one lands on a different part of the stance.

Johnny Bouder asked whether I was using Claude Desktop. I am not. I run `Claude Code` through the terminal for everything, specifically so I keep complete control. I want to know what it is doing, and I want to be able to revert quickly. I also run everything in a sandbox. You are not going to find a more paranoid developer.

Christopher Farrow watched the conflict markers and saw something I had not phrased out loud. Sales, he pointed out, is in many ways an alignment problem. What the review document does is surface every point where alignment might be missing, from the customer side or from ours. The flags are not just bookkeeping. They are a map of where the deal could go sideways.

Johnny also asked the question everyone running a pipeline this size eventually asks: did I keep running out of tokens? Constantly. I have a personal `Claude` account that I use for anything public-facing that does not touch sensitive data, and I keep sensitive work on a separate internal account. Even so, I was maxing it out, especially after a model update that nuked my tokens faster than I had planned for. (It is a good update. It is also hungry.)

And the document is not a static source of truth. Because there are multiple meetings, it is a living one, updated after each meeting by an automation I run on my own machine. The record stays current, which is the only way the requirement IDs stay accurate as the opportunity moves.

Riding this way means you end up somewhere real. The site that week produced is live: [Security for the AI stack](https://openteams.com/python-security-remediation/), and every public claim on it went through the loop above before it shipped.

## Three Things to Steal

A stochastic model is a horse. So ride it where it is useful, and verify it where it is dangerous. That is the rule the week came down to. Here is the portable version.

- **Make the document the memory, not the chat.** Hand the model the requirements doc at the start of every session. Stable IDs (`DR-01`, `RR-07`) let every later artifact trace back to a real quote, and a precedence table means the model never has to guess how to resolve a conflict.
- **Use the variation, then verify.** Let it wander while you prototype: three site generations in a week came out of exactly that. Then make every public claim survive adversarial checks, `[[CONFIRM]]` markers, footnotes, and git history before it ships. The verified number that replaced the guess on the call is the whole stance in one number.
- **Treat it like managing a person, not running a program.** Write things down. Tell it where not to go. Go check where it ended up.
