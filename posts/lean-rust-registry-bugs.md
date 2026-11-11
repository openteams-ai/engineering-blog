---
title: "Lean Found 1 Bug in Our Rust Registry. Tests Found 14."
slug: lean-rust-registry-bugs
date: 2026-11-10
topic: ai-engineering
authors:
  - brandon-geraci
meta_description: "See what Lean 4 proofs, reference tests and property tests each caught in a Rust artifact registry: 15 confirmed bugs in a day, and only one from the prover."
focus_keyword: Lean Rust
---

A few weeks ago someone [modeled CPython in Lean](https://broyojo.com/python-formalization/), a theorem prover, and filed 418 bug reports against the interpreter. I maintain [Artifact Keeper](https://github.com/artifact-keeper/artifact-keeper), an open source artifact registry written in Rust. Its job is to decide which packages are safe to hand to a build, so a wrong decision there is a supply-chain problem. I wanted to know whether the same idea would pay off on my code.

It did, but not the way I expected. In one day, working with Claude Code, we confirmed 15 defects. The Lean proofs found one of them. The other 14 came from much cheaper techniques that I only reached for because Lean made me write the rules down first.

## Why the CPython approach doesn't transfer directly

The CPython project had something most backends don't: a second implementation of everything. Each Lean copy could be run against real Python on tens of thousands of inputs, and 129 of the 418 reports were the C and Python implementations disagreeing with each other.

A registry backend only has that for part of its code. PyPI versions have [`packaging`](https://github.com/pypa/packaging). npm has `semver` and `validate-npm-package-name`. Maven has `ComparableVersion`. But nothing upstream defines the right answer for "may this user download this quarantined artifact?"

There is a second problem. A Lean proof is about a model you wrote by hand, not about your Rust. Translate a whole codebase and the model drifts from the code the day after you finish.

So we did not translate the codebase. We used four techniques, cheapest first.

## The four techniques

**1. Reference tests.** Where an upstream tool defines the answer, generate a fixture from that tool and fail on any disagreement.

**2. Property tests.** For each pure decision function, state what must always be true and let [`proptest`](https://github.com/proptest-rs/proptest) search for a counterexample. An ordering must be transitive. A matcher must finish in bounded time. A state the code doesn't recognize must never mean "allowed".

**3. Lean models.** Only for small security rules that must hold over a sequence of operations, where a test of single steps can't see the problem. Every model is paired with a Rust property test that checks the same statement against the real code.

**4. Reading code against one stated property.** Pick a property, read the code looking only for a violation, then write a test that reproduces it. Nothing counts until the test fails.

## The results

| Technique | Confirmed defects |
| --- | --- |
| Lean model | 1 |
| Reference tests | 5 |
| Property tests | 5 |
| Reading against a property, then reproducing | 4 |

Eight of the 15 are public issues, and seven of those are already fixed in `main`. The other seven are security fixes that haven't shipped yet, including the one Lean found. I'll write those up after the release. Everything below is from the public set.

## What reference tests caught

These took an afternoon per format and found a third of everything.

**Maven version ordering** ([#5713](https://github.com/artifact-keeper/artifact-keeper/issues/5713)). Our comparator was described as a port of Maven's `ComparableVersion`. It ordered `1.0-SNAPSHOT` above `1-SNAPSHOT`, which Maven treats as equal, and that comparator picks `<latest>` in generated `maven-metadata.xml`. After the fix, all 3.2 million pairs from 1,799 versions agree with the Java class.

**PEP 440 parsing** ([#5723](https://github.com/artifact-keeper/artifact-keeper/issues/5723)). Compared with `packaging` on 2,368 version strings:

- A number too large for `u64` was read as `0`, so `99999999999999999999` was the same version as `0`.
- 89 valid spellings were rejected, such as `1.0a2-1`.
- Nine invalid strings were accepted, such as `1..0`.

**npm `latest`** ([#5724](https://github.com/artifact-keeper/artifact-keeper/issues/5724)). When a package had no recorded `latest` tag, we picked one by comparing only `major.minor.patch`. For `[1.0.0-rc.1, 1.0.0-alpha]` we returned `1.0.0-alpha`. Against npm's own `semver`, 509 of 1,518 test sets disagreed.

**npm name validation** ([#5725](https://github.com/artifact-keeper/artifact-keeper/issues/5725)). We accept `node_modules` and `favicon.ico`, which npm blocks, and reject scoped names like `@_scope/name`, which npm allows. This one is still open because the fix touches path-safety reasoning.

## What property tests caught

**A comparator with a cycle** ([#5714](https://github.com/artifact-keeper/artifact-keeper/issues/5714)). The CVE range matcher compared segments as numbers when both parsed and as strings otherwise. That gives `2 < 10`, `10 < 1a` and `1a < 2`. The test that found it says one thing: the comparator is a total order.

**An unknown state that meant "allowed"** ([#5715](https://github.com/artifact-keeper/artifact-keeper/issues/5715)). A scan row with a status the build didn't recognize fell through to "not applicable", which passes the block-unscanned gate. A database constraint keeps this unreachable today. It becomes reachable the first time a newer node writes a new status during a rolling upgrade.

**A glob matcher that backtracks** ([#5716](https://github.com/artifact-keeper/artifact-keeper/issues/5716)). Six `*` in a pattern against a 120-character name took 10 seconds on a release build. The fix is the standard linear matcher.

**A wildcard that stopped being one** ([#5739](https://github.com/artifact-keeper/artifact-keeper/issues/5739)). In the conda allowlist, the pattern `*` did not match the name `*abc`, because the literal comparison ran before the wildcard case. Found by comparing the matcher with a regex.

None of these needed a prover. Each one needed a single sentence about what the function guarantees.

## What Lean is for

The models live in [`formal/`](https://github.com/artifact-keeper/artifact-keeper/tree/main/formal). There are six public ones, each a page or two, with no Mathlib dependency. CI builds them with warnings as errors.

Here is the kind of statement they prove. Artifact Keeper lets a token mint another token, and a token restricted to some repositories must never produce one that reaches more:

```lean
/-- Through any chain of mints, the last token reaches only what the original
credential reached. -/
theorem mint_chain_never_widens (cred : Scope)
    (chain : List (Option (List Repo) × Scope))
    (hchain : MintChain cred chain) (r : Repo)
    (hgrant : (lastToken cred chain).grants r) : cred.grants r
```

"Any chain" is the part a test can't cover. A test checks the chains you thought of.

The same file shows why one unremarkable `if` in the Rust matters. An empty allowlist is stored as "no restriction", so without a check that refuses to mint from a credential restricted to nothing, you get this:

```lean
/-- Without it, a credential restricted to nothing mints a token that reaches
everything. -/
theorem without_the_check_nothing_becomes_everything :
    mintWithoutEmptyCheck (.restricted []) none = some .unrestricted := by
  decide
```

That check was already in the code. Now the reason it must stay is checked on every build, and nobody can tidy it away without a red build.

Five of the six public models proved the rule sound as written. That is the result you want, and it is still worth having.

The one defect Lean did find has the shape the prover is built for: a rule that was correct for every single step and wrong for two steps in a row. Every single-step test passed. The proof would not go through, and the goal it got stuck on was the counterexample.

## What I'd tell another maintainer

**Start with reference tests.** If an upstream tool defines the right answer for something you reimplemented, compare against it before you do anything cleverer.

**Write the guarantee down before you choose a tool.** Fourteen of the 15 findings fell to a test or a careful read once the property was a sentence. The prover's biggest contribution was forcing that sentence to exist.

**Use Lean where the rule is about a sequence.** Token minting, policy changes over time, verdicts across repeated scans. Those are the places where every step looks fine and the composition isn't.

**Pair every model with a test.** A proof says the rule is sound. It doesn't say the Rust still matches the rule. The paired property test is what connects the two.

**Keep the models small.** A model nobody can read gets deleted the first time it blocks a merge.

The security bugs had two shapes: a rule that fails over a sequence, and a rule implemented in several places that drifted apart. Lean handles the first. The second needs structure, so the next piece of work is making the download gate return a value that is the only way to reach an artifact's bytes. A handler that skips the gate then fails to compile, which is cheaper than any proof.
