---
title: "We Tried Lean on Our Rust Registry. Writing the Rules Down Found 15 Bugs."
slug: lean-rust-registry-bugs
date: 2026-11-10
topic: ai-engineering
authors:
  - brandon-geraci
meta_description: "We modeled seven security rules of a Rust artifact registry in Lean 4. The prover found 1 bug. Writing each rule down as one sentence found 14 more bugs."
focus_keyword: Lean Rust
---

In late October, two researchers [modeled CPython in Lean](https://broyojo.com/python-formalization/), a theorem prover, and turned up 415 bug reports in the interpreter. I maintain [Artifact Keeper](https://github.com/artifact-keeper/artifact-keeper), an open source artifact registry written in Rust. Its job is to decide which packages are safe to hand to a build, so when one of its rules is wrong, it becomes a supply-chain problem. I wanted to know whether the same idea would pay off on my code. Working with Claude Code, we spent one day on it and confirmed 15 defects. Lean found one of them. The other 14 came from cheaper techniques, and I only reached for those because Lean made me write the rules down first. This post covers how that happened and what I would do the same way again.

## Why we couldn't copy the CPython approach

The CPython project had something most backends do not have: a second implementation of everything. Each Lean model could be run against real Python on tens of thousands of inputs, and 131 of the 415 reports came from the C and Python implementations disagreeing with each other.

A registry only has that for part of its code. PyPI versions have [`packaging`](https://github.com/pypa/packaging), npm has `semver` and `validate-npm-package-name`, and Maven has `ComparableVersion`. Nothing upstream defines the right answer to "may this user download this quarantined artifact?"

There is a second problem. A Lean proof is about a model you wrote by hand, not about your Rust. If you translate a whole codebase, the model starts drifting from the code the day after you finish.

So we did not translate the codebase. We used four techniques instead, starting with the cheapest:

1. **Reference tests.** Where an upstream tool defines the answer, we generated fixtures from that tool and failed on any disagreement.
2. **Property tests.** For each pure decision function, we wrote down what must always be true and let [`proptest`](https://github.com/proptest-rs/proptest) search for a counterexample. An ordering must be transitive. A matcher must finish in bounded time. A state the code does not recognize must never mean "allowed."
3. **Lean models.** We used these only for small security rules where the guarantee spans more than one step, so a test of single steps cannot see the problem. Every model is paired with a Rust test that checks the same statement against the real code.
4. **Reading the code against one property.** We picked a property, read the code looking only for a violation, and then wrote a test that reproduced it. Nothing counted until the test failed.

## The results

| Technique | Pointed at | Confirmed defects |
| --- | --- | --- |
| Lean model | 7 security rules | 1 |
| Reference tests | upstream implementations | 4 |
| Property tests | pure decision functions | 6 |
| Reading against a property, then reproducing | one property at a time | 4 |

Lean's one is a security bug, in one of the seven rules we pointed it at. Most of the public bugs below are correctness and hardening fixes, and several of them had no production impact yet. I call that out where it applies.

Eight of the 15 are public issues, and all eight are fixed in `main`. The other seven are security fixes that have not shipped yet, including the one Lean found. I will write those up after the release. Everything below comes from the public set.

## What the reference tests found

Comparing our code against the upstream tools found four of the 15.

**Maven version ordering** ([#5713](https://github.com/artifact-keeper/artifact-keeper/issues/5713)). Our comparator was described as a port of Maven's `ComparableVersion`. It ordered `1.0-SNAPSHOT` above `1-SNAPSHOT`, which Maven treats as equal, and that comparator picks `<latest>` in the `maven-metadata.xml` we generate. A property test flagged this one first (the comparator has to be a total order), so the table counts it under property tests, but the comparison against the Java class is what pinned it down. After the fix, all 3.2 million pairs from 1,799 versions agree with it.

**PEP 440 parsing** ([#5723](https://github.com/artifact-keeper/artifact-keeper/issues/5723)). We compared our parser with `packaging` on 2,368 version strings and found three problems:

- A number too large for `u64` was read as `0`, so `99999999999999999999` was the same version as `0`.
- 89 valid spellings were rejected, such as `1.0a2-1`.
- Nine invalid strings were accepted, such as `1..0`.

**npm `latest`** ([#5724](https://github.com/artifact-keeper/artifact-keeper/issues/5724)). When a package had no recorded `latest` tag, we picked one by comparing only `major.minor.patch`, which ignores pre-releases. For `[1.0.0-rc.1, 1.0.0-alpha]` we returned `1.0.0-alpha`. Against npm's own `semver`, 509 of 1,518 test sets disagreed.

**npm name validation** ([#5725](https://github.com/artifact-keeper/artifact-keeper/issues/5725)). We accepted `node_modules` and `favicon.ico`, which npm blocks, and rejected scoped names like `@_scope/name`, which npm allows. The fix touched path-safety reasoning, so it took longer than the others ([#5846](https://github.com/artifact-keeper/artifact-keeper/pull/5846)).

## What the property tests found

**A comparator with a cycle** ([#5714](https://github.com/artifact-keeper/artifact-keeper/issues/5714)). The CVE range matcher compared version segments as numbers when both parsed and as strings otherwise. That gives `2 < 10`, `10 < 1a` and `1a < 2`, which is a circle, not an order. The test that found it says only one thing: the comparator is a total order. Nothing in production called the matcher yet, and it was fixed before anything did.

**An unknown state that meant "allowed"** ([#5715](https://github.com/artifact-keeper/artifact-keeper/issues/5715)). A scan row with a status the build did not recognize fell through to "not applicable," which passes the block-unscanned gate. A database constraint keeps this unreachable today. It becomes reachable the first time a newer node writes a new status during a rolling upgrade.

**A glob matcher that backtracks** ([#5716](https://github.com/artifact-keeper/artifact-keeper/issues/5716)). Six `*` in a pattern against a 120-character name took 10 seconds on a release build. Administrators write these patterns, so this is hardening rather than an exposure. The fix is the standard linear matcher.

**A wildcard that stopped being one** ([#5739](https://github.com/artifact-keeper/artifact-keeper/issues/5739)). In the conda allowlist, the pattern `*` did not match the name `*abc`, because the literal comparison ran before the wildcard case. We found it by comparing the matcher with a regex. Conda names never contain `*`, so it had no effect in practice.

What each of these needed was one sentence about what the function guarantees. Once that sentence existed, the test was not hard to write.

## Where Lean fits

The models live in [`formal/`](https://github.com/artifact-keeper/artifact-keeper/tree/main/formal). There are six public ones, each a page or two, with no Mathlib dependency, and CI builds them with warnings treated as errors.

Here is an example of what they prove. Artifact Keeper lets a token mint another token, and a token restricted to some repositories must never produce one that reaches more:

```lean
/-- Through any chain of mints, the last token reaches only what the original
credential reached. -/
theorem mint_chain_never_widens (cred : Scope)
    (chain : List (Option (List Repo) × Scope))
    (hchain : MintChain cred chain) (r : Repo)
    (hgrant : (lastToken cred chain).grants r) : cred.grants r
```

The important words are "any chain." A test can only check the chains we thought of.

The same file explains why one unremarkable `if` in the Rust matters. An empty allowlist is stored as "no restriction," so "restricted to nothing" and "not restricted" look the same once they are stored. Without a check that refuses to mint from a credential restricted to nothing, you get this:

```lean
/-- Without it, a credential restricted to nothing mints a token that reaches
everything. -/
theorem without_the_check_nothing_becomes_everything :
    mintWithoutEmptyCheck (.restricted []) none = some .unrestricted := by
  decide
```

That check was already in the code. The model explains why it has to stay, and a Rust property test ([#6067](https://github.com/artifact-keeper/artifact-keeper/pull/6067)) checks the same rule against the real minting code. With the check deleted, the test fails with the model's counterexample.

Five of the six public models proved their guarantee as written, and two of them also record an edge case as a theorem. The sixth, the scan-state model, reproduces [#5715](https://github.com/artifact-keeper/artifact-keeper/issues/5715) with `decide`, but the property test got there first, so the table credits the test. A proof that goes through still gives us something a test cannot: the statement holds for every input and every chain, and it is checked again whenever the model changes.

The one defect Lean did find has the shape the prover is built for. The rule was correct for every single step and wrong for two steps in a row. The backend has about 22,000 unit tests, and every single-step test passed. The proof would not go through, and the goal it got stuck on was the counterexample. It is a security fix that has not shipped, so I will show it after the release.

I want to be honest about how much of the code this covers. Seven rules is a small slice. The backend has roughly 200 functions that make decisions like these, and seven hand-picked rules are not a sample, so I will not guess how many of the rest are wrong. Most of those functions decide a single step, where a property test is the right tool. The ones worth a model are the few whose guarantee spans a sequence.

## Lessons learned

If I started over, I would begin with reference tests. When an upstream tool already defines the right answer for something you reimplemented, comparing against it is the cheapest check there is, and it found four of our 15.

The bigger lesson is to write the guarantee down before choosing a tool. Fourteen of the 15 findings fell to a test or a careful read once the property was a sentence. Lean forced those sentences to exist, and then it found the one bug no single-step test saw.

Lean is worth the effort where a guarantee spans more than one step: token minting, or policy changes over time. Those are the places where every step looks fine and the combination does not.

Every model needs a paired test. A proof says the rule is sound. It does not say the Rust still matches the rule, and the paired test is what connects the two. We learned this one the hard way. The minting model above had no paired test until a review of this post pointed it out, and the Lean job only runs when the `formal/` folder changes, so deleting that `if` would have passed CI.

Finally, keep the models small. A model nobody can read gets deleted the first time it blocks a merge.

The security bugs we found had two shapes: a rule that fails over a sequence, and a rule implemented in several places that drifted apart. Lean handles the first. The second needs structure in the code, and that is separate work.

## What's next: making it faster without changing a decision

This post used Lean to check whether a rule was right. The next one uses it the other way around: to make the code do less work and prove it still makes the same decision.

We have been measuring the upcoming 1.12 release against 1.11.13 with a load harness that runs several Artifact Keeper instances against one shared Postgres server and one object store, the way a hosted fleet runs. At this load, 1.12 is not slower for clients. It does more work per artifact on the parts every instance shares, with more Postgres statements and more write-ahead log for the same uploads. On a shared database server, that cost is paid once for every instance.

Each fix goes through the same loop. We measure, write the rule the faster code must still follow as a sentence, prove it in Lean when a security decision depends on it, change the Rust, and measure again.

The first fix did not need a proof. The RPM repodata builder wrote to the database every two seconds, even on instances with no RPM repositories at all. Skipping that work when nothing is queued cut write-ahead log by 83% across three idle instances ([#6056](https://github.com/artifact-keeper/artifact-keeper/issues/6056)). The next one does need a proof. A Maven download checked the same security gate twice, once for the jar and once for its checksum file, and sharing one answer between those two reads must never let through anything the gate would refuse. That proof, and the numbers before and after, are the next post.

If you maintain a registry, a package manager, or anything else that decides what is safe to install, I would like to hear how you approach this. The models are in [`formal/`](https://github.com/artifact-keeper/artifact-keeper/tree/main/formal), and I would welcome anyone who wants to poke holes in them. Let's start the discussion.
