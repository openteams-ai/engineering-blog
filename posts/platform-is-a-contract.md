---
title: "A Platform Is a Contract"
slug: platform-is-a-contract
date: 2026-11-18
topic: infrastructure
authors:
  - chuck-mcandrew
meta_description: "A platform is a contract between the team that builds it and the teams that build on it. What we learned writing one down for Nebari, and how to start smaller."
---

There's an [xkcd comic](https://xkcd.com/1172/) where a software update fixes a bug that caused the CPU to overheat when the spacebar was held down. A longtime user complains that the update broke their workflow. Their control key is hard to reach, so they hold the spacebar instead, and they configured Emacs to read a rapid temperature rise as a press of control. They would like an option to re-enable spacebar heating.

It's a joke, but it is a joke that anyone who has run a platform gets. [Hyrum's Law](https://www.hyrumslaw.com/) says: "With a sufficient number of users of an API, it does not matter what you promise in the contract: all observable behaviors of your system will be depended on by somebody."

Hyrum's Law usually gets quoted as a reason promises don't matter, but let's look at it from the other direction. The law assumes there is a contract. People will depend on things you never promised, and you can't stop that. What you can control is whether anyone can tell, when it happens, which behavior was promised and which was an accident.

## What a platform actually is

Platform engineering is the closest thing I've seen to DevOps principles working in practice. DevOps asked teams to own their software all the way to production without filing a ticket with ops at every step. A platform team makes that possible by building the shared pieces once, so product teams can use them without having to understand them. They provide a layer of abstraction for the users.

Most talk about platforms stays at the level of tooling: a portal, golden paths, a GitOps setup. Tooling matters the way an implementation matters behind an interface. It has to work, but consumers never build against it. They build against the interface, and for a platform, that interface is the contract.

At its core, a platform is a contract. The platform team's job is to fulfill the promises that the contract makes. Consumers build things that rely on those promises. Neither side needs to know how the other does its job, as long as both keep to the contract. If that sounds like spec-driven API design, it's the same discipline applied to a whole platform instead of a single endpoint.

Before we go any further, I need to define a couple of terms as I am using them in this context. They are both somewhat overloaded terms, so I want to clarify. First, a *promise* is one specific behavior the platform team commits to keep working through every upgrade and every swap of the software underneath. "A pack that declares a NebariApp gets a route, a TLS certificate and single sign-on" is a promise. It says what consumers get, not which tools provide it. Second, a *contract* is the whole written agreement: the promises and how stable each one is, the things that exist on the platform but aren't promised, and the rules for how promises get added, changed and retired.

None of this is new. The [Go 1 compatibility promise](https://go.dev/doc/go1compat) and the [Kubernetes deprecation policy](https://kubernetes.io/docs/reference/using-api/deprecation-policy/) are contracts of exactly this kind, and they are a big part of why people trust those projects enough to build on them.

## Where this came from

I work on [Nebari](https://nebari.dev), an open source platform for running AI workloads on infrastructure you control. The original Nebari, now called Nebari Classic, shipped JupyterHub, Dask, conda-store and the rest as a single opinionated stack. It was a batteries included data science platform that shipped everything to everyone, every time. What it wasn't was composable.

I'd worked on Classic for about a year when we started a [clean-break redesign](https://github.com/nebari-dev/nebari-infrastructure-core/blob/main/docs/design-doc/architecture/01-introduction.md) grounded in seven years of developing and deploying Nebari Classic. The new platform, the [Nebari Kubernetes Platform](https://nebari.dev/docs/explanations/nkp-architecture/) (NKP), gives you a Kubernetes cluster with the shared pieces already wired up: login through Keycloak, routing through Envoy Gateway, TLS through cert-manager, and telemetry through an OpenTelemetry collector. Everything users actually work with ships as a [software pack](https://nebari.dev/docs/explanations/software-packs/), a git repository of Kubernetes manifests that Argo CD deploys on top. This is a much more flexible design with clearer ownership of the important pieces. The design doc states the goal this way: "platform teams can upgrade infrastructure without affecting applications, and application teams can deploy new services without understanding infrastructure details."

That sentence describes a contract, though at the start we didn't call it one.

## The interface we never declared

Nebari Infrastructure Core is written in Go. It is the tool that deploys the Nebari platform to the cloud of your choice or on-prem. Its design leans heavily on Go interfaces for extensibility and loose coupling. Each cloud provider sits behind a `Provider` interface, and as the design doc says, "the `cluster.Provider` interface is the contract, not a single IaC tool." AWS uses OpenTofu, Hetzner uses a k3s installer, and local development uses Kind. None of that leaks past the interface.

The same thinking shows up at the pack boundary. A pack includes a `NebariApp` custom resource, and the Nebari operator gives it routing, TLS and single sign-on in return. The pack describes what it needs in platform terms, and the operator works out how to provide it. That's interface-shaped.

What we never did was say so. Go interfaces are satisfied implicitly: a type never declares that it implements one. Someone still has to write the interface type down, though, and that declaration tells everyone what methods are available and what their signatures are. At the pack boundary we had code on both sides and no interface type in the middle. Moving from a monolith to composable packs created a boundary between our work and everyone else's.

## The contract grew anyway

The NebariApp promise was a good starting contract. It was small, it was useful and a pack could ship something real with nothing else. We also said, correctly, that everything was pre-1.0 and not stable. Building things and watching people use them is how we learned what the contract needed to be.

Over time it became clear we were offering a lot more than routing, TLS and login: a default storage class, Postgres through CloudNativePG, an Argo CD project to deploy into, a predictable format for group claims in login tokens, and a trust bundle for internal certificates. Each of those was real and useful. None of them was written down as a promise.

The first packs that we wrote for our new platform depended on things we never explicitly promised. Several of our first-party packs referenced a certificate issuer that only exists when a cluster runs in self-signed mode. Our pack template deployed into Argo CD's default project. Nobody was being careless. The packs used what was on the cluster, and without a written contract there was no way to tell what was a promise and what just happened to be there. We were our own spacebar heaters.

The other cost was quieter. "Pre-1.0" told people not to rely on anything, but it didn't say what 1.0 would be. Without a contract, there was no definition of done. We couldn't really answer when asked when Nebari would be "stable" or "ready."

We're working on that now with a [proposed pack platform contract](https://github.com/nebari-dev/nebari-infrastructure-core/pull/781). It includes seventeen promises based on observed needs, lists of what exists but is not promised, and compatibility, deprecation and security policies modeled closely on Go's. To be plain about where it stands: it isn't a contract yet. Only two of the seventeen promises are fully built, and the conformance tests that would prove the rest don't exist. It's a roadmap to a contract, and that's fine. You start where you are. It also finally gives 1.0 a definition: every required promise built and passing its conformance test on every supported target.

The roadmap also doesn't follow the advice in the next section. It launches with nine stable promises, three of them not fully built, and two of them, Postgres through CloudNativePG and the Argo CD project, are tied to a single product. That's what writing a contract late looks like. By the time we wrote it down, packs already depended on all nine, and labeling them experimental wouldn't have changed that. We could have avoided this if we had named the tiers on day one and made each of those promises a deliberate choice when it first came up.

## Start with the smallest contract that does real work

So what's the smallest contract you can offer that still does real work? Rob Pike's [Go proverb](https://go-proverbs.github.io/) applies: "The bigger the interface, the weaker the abstraction." I'd start with three parts.

The first is one or two stable promises, enough that a consumer can ship one real thing to production while relying on nothing else. For us that would have been the NebariApp promise. If a consumer can't build something useful from the stable promises alone, then you don't have a useful contract. The goal is to provide everything they need and nothing more for your initial offering.

The second is everything else marked experimental, by name. This is the part we skipped. "We're pre-1.0, nothing is stable" sounds honest, but Hyrum's Law doesn't care. People build on whatever works, and when you reach 1.0 you end up auditing what everyone already depends on instead of choosing what to promise. A named experimental tier turns the instability into a list you can track. Kubernetes has done this for years with alpha, beta and GA APIs.

The third is a do-not-rely-on list. This answers xkcd's spacebar user before they show up. Ours includes the shared gateway's name, the Keycloak admin secrets, chart-generated resource names, every certificate issuer name, and Keycloak's bootstrap `admin` user, which collides with local `admin` users in packs like Harbor. Our proposed compatibility policy puts the rule in one sentence: "If a promise page is silent on something, it is not promised."

That's the full answer to the spacebar user. A contract doesn't stop anyone from relying on the CPU heating up. It decides whose problem it is when the heat goes away.

## Deciding when to extend it

A small contract only stays useful if there's a deliberate way to grow it. Otherwise the written contract stays small while the real contract grows around it, which is what happened to us. However, accepting features into your contract is a real cost that implies a real commitment of maintainer time. It pays to be conservative when extending your contract. These are the tests I'd apply before promoting anything to a stable promise:

- More than one consumer needs it. One user asking is a feature request. Two is a signal. More than that becomes a pattern. This isn't a hard and fast rule. If a single project needs something, and you can see a very clear broader use case, you can choose to adopt it without waiting. However, the general rule is that without a clear pattern of need, it doesn't get a yes.
- People already depend on it. Hyrum's Law cuts both ways here: if consumers rely on an experimental promise, or on something unpromised, that's evidence of a need. It doesn't mean you need to implement it in exactly the same way as a hacky workaround did, but there is user signal there which is very valuable.
- You could keep it through a replacement. A stable promise is a one-way door. You keep it working through every upgrade and every swap of the software underneath, so if you can't state it without naming a product, it isn't ready. The two stable promises in our roadmap that break this rule, Postgres through CloudNativePG and the Argo CD project, are marked as exceptions, and each has to name a path to a neutral interface. When we wrote down the platform facts we'd hand to packs, `keycloak-issuer-url` became `oidc-issuer-url` for this reason.
- Experiments have a deadline. In the roadmap for the Nebari contract, I propose that an experimental promise have 18 months after it's built to graduate, be renewed, or be deprecated. Without a clock, "experimental" becomes the place hard decisions go to wait.

This can look like bureaucracy, and the full contract does carry a lot of policy. The answer is to keep the list of promises short. The process is only expensive when you promise a lot. Being conservative about promises keeps your platform from becoming an unmaintainable spaghetti monster. No is temporary, yes is forever.

## A contract nobody tests is a wish

Natural language is gloriously imprecise, which means that promises written in prose drift. Every stable promise in the roadmap has to name a conformance test that runs on every supported target, and CI fails when a built promise doesn't. The suite itself doesn't exist yet, so today most of those entries say "pending." CI can check that the contract is internally consistent and that every change to a stable promise links to the decision behind it. It can't prove the platform does what a page says. Until the conformance suite runs, those promises are commitments we can't yet demonstrate.

This is also where the contract idea meets DevOps practice most directly. A promise is as real as the automated check that fails when someone breaks it.

## Every platform has a spacebar heater

Somebody is depending on your platform's overheating CPU right now. When you fix it, you'll need to point at what you promised. If your platform has consumers, it already has a contract. You can write it down while it's small, or you can discover it later by finding out what you're no longer allowed to change.

The [contract proposal](https://github.com/nebari-dev/nebari-infrastructure-core/pull/781) is open for review. If you build on Nebari, or you've written a platform contract of your own and can see where ours is wrong, we'd like to hear from you.
