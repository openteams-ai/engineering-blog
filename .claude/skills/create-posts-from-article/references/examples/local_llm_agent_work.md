---
title: "Making Local LLM Agents More Reliable"
status: "done"
source_document: "https://openteams.com/what-i-learned-making-a-local-llm-do-real-work/"
---

Running LLM agents locally gives teams more control over cost, data, and infrastructure.

But local execution does not remove the hard parts of building reliable agents.

Adam Lewis explored this by building a Harvest time-tracking agent with Pydantic AI, then switching the agent from Claude to a local model.

The experiment exposed a familiar AI challenge: a model can understand the request but still fail on the precise details that real workflows depend on.

This article shares what Adam learned about building agents that stay useful even when the model is imperfect.

**Hashtags:**

#AIEngineering #LLM #OpenSource #LocalAI
