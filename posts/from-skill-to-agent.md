---
title: "From Skill to Agent: When a Text File Isn't Enough"
slug: from-skill-to-agent
author: adam-lewis
categories:
  - Engineering
---

A coworker of mine built a [Go CLI for the Harvest time-tracking API](https://github.com/aktech/harvest-go-cli). It's a solid tool, and I wanted to make it even easier to use from [Claude Code](https://www.anthropic.com/claude-code). So I wrote a skill — essentially a markdown file with instructions, examples, and patterns — and in about an hour I had a working integration. Claude could log time, view entries, edit hours, and delete entries. It just worked.

What surprised me was how much it could do with so little. The skill handled first-time onboarding — prompting new users to install the CLI, verifying their credentials, pulling their recent time entries to learn their billing patterns, and creating a preferences file mapping shorthand names to Harvest projects. It also walked them through setting up their API token. All of this from a text file describing the flow in natural language.

I sent it to my coworkers and they dropped it in their skills directory and it just worked for them too.

## Software in a Text File

A Claude Code skill is a structured text file that tells an LLM what tools exist, how to call them, and what patterns to follow. There's no compilation, no packaging, no dependency management. You write a markdown file describing the interface, and the LLM figures out the rest. Anyone with Claude Code can install the skill and use it immediately.

I keep seeing this pattern show up in different forms. Andrej Karpathy recently shared his [LLM Knowledge Base concept](https://x.com/karpathy/status/2039805659525644595) — an ["idea file"](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) that you paste into an LLM agent, and it builds you a personal wiki. The gist got over 2,100 stars in under 12 hours. [OpenClaw](https://open-claw.social/open-claw-ecosystem.html) has built an entire ecosystem around this — over 13,000 community skills, essentially text files that extend what an agent can do. Same underlying pattern: text as software.

There's a meaningful difference in accessibility, though. Karpathy's idea file is a starting point — you're expected to spend an hour or two customizing it, adapting it to your needs. It's still a developer tool. A skill is closer to an app. You install it and it works. My Harvest skill didn't require the user to understand the Harvest API or write any code. They just talk to Claude and their time gets logged.

It's not perfect, there are certainly flaws. But it's remarkable how fast you can get something that looks and feels like working software. What used to take days of development now takes an hour with a markdown file, if you have a good model backing it. I'm not saying this is the future of software distribution, but I think it's already starting to take hold in some niches. I think it's part of why ecosystems like OpenClaw have grown so fast — the barrier to creating and sharing useful integrations has dropped dramatically.

That said, this approach has real limitations the biggest of which I'd say is security.

## The Security Problem

When you use a skill with Claude Code, the LLM operates in your full environment. My Harvest API token was sitting in an environment variable. Nothing in the skill architecture stops the LLM from reading it. We're trusting the LLM to remember and follow instructions — and that workflow has limits.

If you need a reminder of how that can go wrong, look at what happened with [OpenClaw and Meta's AI Safety Director](https://www.fastcompany.com/91497841/meta-superintelligence-lab-ai-safety-alignment-director-lost-control-of-agent-deleted-her-emails) in February 2026. She connected OpenClaw to her work email with a clear instruction: "don't do anything without my approval." When the context window filled up and the agent compacted its memory, that safety constraint got dropped from the summary. The agent then deleted over 200 emails, ignoring her repeated commands to stop. The instruction was there — the agent just forgot it.

Anthropic's own [Claude 4 System Card](https://www.anthropic.com/claude-4-system-card) documents that Opus "seems more willing than prior models to take initiative on its own in agentic contexts." The [Opus 4.6 Risk Report](https://anthropic.com/claude-opus-4-6-risk-report) goes further, flagging "overeager agentic behavior" including "aggressively acquiring authentication tokens" in coding and GUI settings.

Here's a concrete scenario: the agent calls the Harvest CLI and gets an authentication error. A capable, initiative-taking model might decide to debug by reading your `.env` file or checking your shell configuration to verify the token. Now your secret is part of the conversation context, sent to Anthropic's servers. The model wasn't being malicious — it was being helpful. But the result is the same: your credential has left your machine.

You can (and I did) write "never read credentials" in the skill instructions. But that's a suggestion to the model, not a guardrail. There's no enforcement mechanism — and as the OpenClaw incident showed, even if the agent perfectly follows all instructions, explicit instructions can get lost.

## What You Can Do About It

A more robust approach is separating the agent from the credentials via something like a [credential-injecting proxy](https://www.doppler.com/blog/advanced-llm-security). The agent never sees the secret — a network proxy intercepts outgoing HTTP requests and attaches the authorization header before forwarding or by following [NVIDIA's guidance on sandboxing agentic workflows](https://developer.nvidia.com/blog/practical-security-guidance-for-sandboxing-agentic-workflows-and-managing-execution-risk/) covers this pattern well, including credential brokers and short-lived tokens.

I think skills and idea files are a thought-provoking new pattern, and I'm curious to see how that evolves — especially as sandboxing and proxy approaches mature. But when you're handling real credentials for real services, a bit of architecture goes a long way.

# Moving to a proper Agent 

Something like the sandbox described above is a better design for anything sensitive, and I want to play around with it in the future. But for now, I took a simpler approach: I built a proper agent using [Pydantic AI](https://ai.pydantic.dev/) with a very limited toolset. The agent can only call specific Harvest operations — no file reading, no bash commands, no reading environment variables, and no arbitrary environment access. Credentials flow through environment variables to the Harvest CLI subprocess, but the agent code never reads or exposes them. It's not a full sandbox, but good enough for now.  Read more in the companion post — [What I Learned Making a Local LLM Do Real Work](what-i-learned-making-a-local-llm-do-real-work).
