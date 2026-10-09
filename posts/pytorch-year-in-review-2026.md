---
title: "PyTorch Year in Review: OpenTeams' Contributions in 2026"
slug: pytorch-year-in-review-2026
authors:
  - andrew-james
categories:
  - Engineering
topic: "ai-engineering"
date: 2026-10-07
meta_description: "See what our PyTorch year in review covers: a CPython-faithful Dynamo, Python 3.15 on day one, fused linear cross-entropy, MPS ops and a new build backend."
focus_keyword: "PyTorch year in review"
---

If you have been following along, you may have noticed that there was no year in review post last year. That's not
because we took the year off. In May 2025, Quansight 
[transitioned to a Public Benefit Corporation](https://quansight.com/post/quansight-is-now-a-public-benefit-corporation/): 
the not-for-profit Labs side became Quansight PBC, and the consulting division, including the engineering team that has
been contributing to PyTorch since 2019, was acquired by 
[OpenTeams](https://openteams.com/), a partner organization also founded by Travis Oliphant.
We kept working on PyTorch through the move; but were not quite set up to publish this post last year. This year we are
back, so I am happy to present our 2026 year in review! This post focuses on 2026, though some of the work started in
2025. It runs through the release of PyTorch 2.14 in September, along with some things that have landed on `main` and
will ship in 2.15 at the end of this month.

The PyTorch project looked different at the end of this period than it did at the start. The release cadence sped up,
from quarterly in 2025 to roughly every two months in 2026, with nine feature releases from 2.6 to 2.14. More striking
was the shift in how code arrives. In the first nine months of 2026 the repo received about 22,000 pull requests,
roughly 58% more than over the same stretch of 2025, and a growing share of them were written with AI coding agents.
Code got cheap. Review did not.[^review-bottleneck]

The project has been adapting in real time. An AI-assisted development policy landed in `CONTRIBUTING.md` in January and
moved into its own [`AI_POLICY.md`](https://github.com/pytorch/pytorch/blob/main/AI_POLICY.md) in July. PRs now need an
associated *actionable* issue, and
[RFC-0058](https://github.com/pytorch/rfcs/blob/master/RFC-0058-issue-pr-workflow.md), merged at the end of September,
reworks the issue and PR lifecycle to be "AI and LLM aware,". I will refer readers to those announcements and the latest
version of maintainers and contributors guidelines for the precise details. The tl;dr in my words would be recognizing
that the volume has increased we have adapted with more automation and quick human pre-review steps at the opening of
the funnel, new issues and new PRs. We have not eliminated regular human code review but added new steps in front of it
to make sure those cycles are spent where they are needed and let automation/strict process do the heavy lifting in the
new stages in front of those human heavy stages. The end goal is for contributors to get some direction and signal
early, and reserve human time expensive stuff for after automated gates are cleared. For a team like ours, which sits
between the core maintainers and the broader community, this changed what useful work looks like. Fixing bugs one at a
time is still useful, but there are far more people who can pick up work like that, and new things that experienced
contributors can do (and need to be doing) to help move things forward. That can mean a structure that tells people (and
agents) where a fix belongs, a test suite that finds gaps before users do, issues scoped tightly enough that a new
contributor can pick one up and land it, or tooling that keeps working when the details underneath it change. You will
see that theme running through most of what follows.

## torch.compile

`torch.compile` is still where a large part of our team's effort goes.[^compile-refresher] This year the bulk of it went
to the front of that pipeline, in Dynamo, with a significant new feature in AOTAutograd and a steady stream of work in
Inductor.

### TorchDynamo

Dynamo is a symbolic Python interpreter, responsible for capturing your program, guarding it for correctness, and
producing the trace that is handed off to the backend for generating optimized code and fused kernels that give you
performance wins.  It runs your function's bytecode against "variable trackers" that stand in for
real Python objects, modeling their behavior and recording the PyTorch operations it sees into the FX graph it produces.
Whenever it meets something it can't model, it breaks the graph and falls back to regular Python. 

The more faithfully Dynamo models Python, the fewer graph
breaks users hit. The clear distinction between something we break on *now* vs something we will *always* break on gives
users clarity around what they should avoid vs what we working on dynamo want to get fixed. This and other issues like
excessive recompiles have motivated much of the team's work in 2026.

#### The slots migration

Over the years Dynamo collected a lot of ad hoc fixes. Need `|` to work on a dict? Add a branch to the `|` handler. Need
`len()` on some new object? Special-case it in the builtin. We found some instances where there was no functional change
required to the actual operation code, just the conditions which we used to select the implementation had gaps that a
particular pattern might slip through. Instead of tracing we would surface a graph break! Each fix was reasonable on its
own, but together they made an architecture that was hard to navigate, had plenty of places for bugs to hide, and gave
no clear answer to the question "where should this fix go?"[^implementation-by-accident] 

CPython already answers that question. Every type has a table of slots (`tp_richcompare`, `tp_hash`, `tp_iter`,
`tp_as_number->nb_add`, and so on), and the interpreter's abstract object protocol dispatches through them. So, together
with Animesh Jain and William Wen at Meta, we have been migrating Dynamo's object model to work the same way. Each
variable tracker implements the slots for the type it represents. Generic protocol functions like `PyObject_Size`,
`PyIter_Next` and `binary_op1` are reproduced in Dynamo, including details like subclass-priority ordering for reflected
operators. Method and attribute lookup moved off long `if name == "..."` chains in `call_method` and `var_getattr` and
onto declarative `tp_methods`, `tp_getset` and `tp_members` tables, the analogs of CPython's `PyMethodDef` and friends.
The arity of each method is derived from the real CPython method's flags, so Dynamo raises the same `TypeError` CPython
would.

In practice this was a long series of PRs. First came the generic protocol helpers, then the full set of `tp_as_number`
binary operators, then sequence and mapping assignment, `tp_call`, `tp_init`, descriptors and `property`, and finally
the move to declarative method tables and dispatch through the `tp_as_*` sub-structs. If you want a closer look at one
corner of it, we wrote up how 
[`tp_as_number` and binary operation dispatch work](https://openteams.com/tp-as-number-slot-and-binary-dispatch/) 
in CPython and how Dynamo mirrors them.

The payoff is a structure where the answer to "where does this fix go?" is "the same place it lives in CPython." That
makes the code easier for humans to review and, as Animesh's devlog argues, much easier for coding agents to work in
correctly. Mirroring CPython eliminates whole classes of graph breaks instead of patching them one at a time. The
migration is now far enough along that it can be split into well-scoped pieces: the 
[remaining migrations](https://github.com/pytorch/pytorch/issues/195165) are tracked as an `OSS contribution wanted`
issue, and community contributors have already landed most of the first batch.

#### CPython's test suite as a spec

How do you know whether Dynamo models Python correctly? Historically, you waited for users to hit bugs. That's a slow
and noisy signal, and it only shows you the parts of the language people happen to use inside compiled regions. We took 
a more systematic approach: [run CPython's own unit tests](https://github.com/pytorch/pytorch/pull/150787) under Dynamo
with `fullgraph=True`.

The infrastructure landed in 2025 with an initial batch of modules. Each test file is a lightly patched copy of the
CPython 3.13 test, tagged with the CPython release it came from, and every test that doesn't pass yet is tracked as an
expected failure. That makes it a ratchet: when a change makes a test start passing, CI tells you, and the xfail gets
removed, from that point on it gives coverage preventing regression. It also feeds a
[dashboard](https://guilhermeleobas.github.io/dynamo-skips/) that tracks the results over time. At the start
of 2026 we were running 32 CPython test modules, about 2,500 tests, with roughly 1,070 passing. Today it is 83 modules
and nearly 6,800 tests, with over 3,650 passing.

<!-- TODO(review): fact-check on the paragraphs above:
- Guilherme: Please review for factual accuracy, agent notes below what it could not verify/could dispute.
- Richard Zou's idea is UNVERIFIED. Nothing in #150787 attributes it to him; zou3519 reviewed and approved it.
  Confirm with Guilherme.
- The "initial batch" list is DISPUTED. #150787 merged 2025-05-07. By June 1 the modules were dict, list, set, tuple,
  iter, sort, complex, ordered_dict, userdict and userlist. test_math came in mid-June, and test_exceptions and
  test_generators by July 1. Swap in e.g. `test_tuple`, `test_iter`, `test_sort`, or drop "spring".
- "tagged with the CPython commit" is minor DISPUTED: the file headers cite the tag v3.13.5, not a commit. Use
  "tagged with the CPython release it came from".
- The dashboard link is UNVERIFIED: it redirects to a Streamlit login and is not publicly viewable. Make it public or
  drop the link. It seems to be dead/broken, I can leave it out, but the history may be helpful in putting the timeline
  of progress together.
- 32 modules at the start of 2026 is SUPPORTED. 83 modules today is minor DISPUTED: main on 2026-10-06 has 85.
- The test and pass counts (2,500/1,070, 6,800/3,650) are UNVERIFIED and can't be counted statically. The static
  counts are 4,220 `def test_` and 2,776 xfail files now. Get them from the dashboard or a CI run.
- 37% -> 50% is UNVERIFIED, and on its face inconsistent with the numbers above, which give 43% -> 54%. Say which
  fixed module set it refers to, or align the numbers. -->

The pass rate is the headline number for the slots migration. On the same set of modules, each slot PR tended to flip a
handful of tests to passing, and the pass rate climbed from 37% to 50% as the object model work landed. That is about as
clear a signal as you can get that mirroring CPython was the right call. It has also become the starting point for
finding what's left: a [meta-issue](https://github.com/pytorch/pytorch/issues/195901) groups the remaining graph breaks
from the suite by root cause.

Porting a CPython test module is a self-contained, mostly mechanical task, which makes it a good first issue, or a good
task for a new contributor to point their agent at. In September we opened a
[meta-issue](https://github.com/pytorch/pytorch/issues/196238) listing candidate modules for the next round of tests to
port over. Within a couple of weeks several community contributors had landed 21 new modules, from `test_unary` and
`test_bisect` to `test_fstring` and `test_grammar`. In a year where increased volume of external contributors has been a 
large source of stress on the development community, this is a great example of how that activity can absolutely be made
to benefit the project by indicating where actionable work is, documenting how it should be done, and dedicating the
cycles to review and land that work.

Want to hear more? Come see Guilherme's poster, *More Than Meets the Eyes: Mirroring CPython's Object Protocol in
Dynamo*, at the 
[PyTorch Conference](https://events.linuxfoundation.org/pytorch-conference-north-america/program/schedule-posters/) 
in San Jose later this month.

#### Exceptions and generators

Exceptions and generators are idiomatic Python, and for a long time they were also a reliable way to get a graph break.
Their semantics are hard to model symbolically: a generator suspends a frame mid-execution, an exception unwinds through
handler tables that differ between CPython versions, and the interactions between the two (`throw()` into a suspended
generator, a `finally` block in a generator that is never exhausted, an exception's `__context__` chain) are full of
corner cases. Users learned to avoid them inside compiled regions, which is exactly the kind of workaround we want to
make unnecessary.

Work that started in late 2024 landed in early 2025. It made lazy, faithful generator tracing the default and added
support for the full generator protocol (`send()`, `throw()`, `close()`) along with the bytecode that implements it.
Exception support followed:

- bare `raise` and `raise ... from ...`
- `sys.exc_info()` and `sys.exception()`
- `__context__`, `__cause__` and `__suppress_context__`
- user-defined exception classes
- `contextlib.suppress` and `contextlib.ExitStack`
- later, exception tracebacks

In mid-2026 we went back and rewrote much of this to follow CPython more closely: each generator gets its own exception
stack, linked while the generator is active; `.send()`, `.throw()` and `.close()` follow CPython's implementation,
including delegation to subgenerators via `yield from`; and Dynamo now closes any open generators when it compiles a
subgraph, so pending `finally` blocks run just as they would under CPython's finalizer. With the old eager-exhaustion
path no longer needed, `enable_faithful_generator_behavior` is now a deprecated no-op.

One thing that makes this area tricky is that you are not working with Python semantics directly but with the bytecode
sequences a given CPython version emits for them. Those differ from release to release, and from bytecode alone you
can't always see all the code you are trying to model. For example, some CPython versions produce bytecode that won't
show you a `try/except` has a `finally` clause until you hit it. This is where the CPython test suite earned its keep.
Expected failures for `test_exception_variations` and `test_generator_stop` are down to zero, `test_raise` went from 15
to 4, `test_contextlib` from 79 to 31, and `test_baseexception` from 10 to 1. `test_exceptions` and `test_generators`
still have work left, but they are now tracked as a list of specific failures rather than a general sense that
exceptions are risky.

<!-- TODO(review): test_contextlib "79 -> 31" is partly DISPUTED. 31 now is correct, but the earlier counts found were 57
(Sep 2025) and 72 (Jan 2026), never 79. The other xfail numbers in this paragraph are SUPPORTED. -->
<!-- review note: omit numbers which are disputed or update numbers to match evidence -->

#### Python 3.15 support on day one

Every new Python release brings new bytecode to route, new language features to support, and usually the discovery that
some piece of CPython internals has moved underneath us. In the past, Dynamo compatibility work started after, or very
close to, the CPython final release. For 3.14, Dynamo was enabled about five weeks after Python 3.14.0 shipped.

For 3.15 we started early. We built Dynamo against CPython's development branch in spring 2026 and tracked it through
the betas and release candidates. The fixes were real but far fewer than in the 3.13 or 3.14 cycles: about twenty PRs,
compared with nearly seventy for 3.14. Highlights include:

- **Virtual iterators:** `GET_ITER` now represents some iterators as two stack entries instead of one.
- **Lazy imports:** `IMPORT_NAME`'s oparg now carries the lazy/eager bits used by [PEP 810](https://peps.python.org/pep-0810/).
- **Sentinels:** partial support for the new sentinel objects.[^sentinels]
- **Frame APIs:** we moved to the CPython frame push/pop APIs, including `_PyThreadState_PushFrame`, which is public in 3.15.


The [PR that enables Dynamo testing on 3.15 and lifts the version check](https://github.com/pytorch/pytorch/pull/178393)
in `torch.compile` landed on September 21, about ten days before the scheduled Python 3.15.0 final release and ahead of
the PyTorch 2.15 branch cut. That means PyTorch 2.15, the first PyTorch release after Python 3.15, will support
`torch.compile` on 3.15 from day one.

<!-- TODO(review): DISPUTED. #178393 merged 2026-09-22 (08:29 UTC, 01:29 PT), not Sep 21. PEP 790 schedules 3.15.0 final
for 2026-10-09, so the merge was about 17 days early, not ten: suggest "landed on September 22, more than two weeks
before...". "Nearly seventy for 3.14" is loose: about 75 PRs have 3.14 in the title, but only about 45 are
Dynamo/compile. Maybe "more than twice as many". Could cite PEP 661 for sentinels. -->
<!-- review note: Either make the specifics less specific or update to be accurate here -->

#### Helping agents help users

In keeping with the year's theme, we also worked on the user side of AI-assisted development. Coding agents are already
the first stop for many people debugging `torch.compile`, and out of the box they don't always give good advice. Often
they disable compilation around the problem rather than fixing it. We have been contributing agent skills to
[meta-pytorch/skills](https://github.com/meta-pytorch/skills): improvements to the `debug-graph-breaks` skill, new
skills for collecting compile logs, debugging recompilations and dynamic shapes, and skills that teach agents when and
how to reach for custom ops and higher-order ops as workarounds. Rob will be presenting this work in a poster,
*Improving the torch.compile user experience*, in the same session at the PyTorch Conference.

<!-- TODO(review): Rob's skills PRs (meta-pytorch/skills #24-#27) are all still open. "We have been contributing" is
accurate, but if they haven't merged by publish, avoid implying the skills are in the repo, or link the PRs. -->

### Complex numbers, real kernels

Complex numbers have long been a gap in `torch.compile`. Inductor has no lowering path for complex dtypes, and even if
it did, the hardware wouldn't help much. GPUs have dedicated matrix-multiply instructions for real dtypes but not for
complex ones. We could, of course, take strided views over the buffer that alias the real and imaginary parts and
operate on those real-valued views, but that would mean specializing lowering pathways, kernel templates and parts of
code generation in Inductor, and even then it would be difficult to access the full power of modern hardware. Instead,
we took a different tack.

A [`ComplexTensor` subclass](https://github.com/pytorch/pytorch/pull/167621) stores the real and imaginary parts as two
separate real tensors and decomposes each complex op into real-valued ops on those parts. Then a 
[graph rewrite in AOTAutograd](https://github.com/pytorch/pytorch/pull/169832) runs after functionalization and before
lowering, retracing the graph with `ComplexTensor` dispatch active. Complex inputs are unpacked into real and imaginary
parts at the top of the graph and repacked at the bottom, and everything in between consists of real-valued ops that Inductor
already knows how to lower to Triton, including matmuls that can use tensor cores. The cost is a one-time conversion
between the interleaved and split layouts when entering and leaving the compiled region. This works for any native
codegen backend, will work for any codegen backend added in the future, and would also work for any out-of-tree compile
backend that doesn't bypass
AOTAutograd.

This ships as an experimental, opt-in feature in PyTorch 2.14, with around 150 ATen ops covered so far:

```python
import torch

with torch._functorch.config.patch(enable_complex_wrapper=True):
    out = torch.compile(fn)(a, b)
```

See the [complex number support docs](https://docs.pytorch.org/docs/main/user_guide/torch_compiler/torch.compiler_complex_number_support.html) 
for details and current limitations. What's left is the usual path from experimental to default. We need to harden it, round
out op coverage (with a particular eye on autograd), and add integration tests on real workloads before switching the
flag on by default. There is a lot of potential for this system to unlock functionality in the compiler beyond eager
execution on native complex types. For example,  an [RFC for a `bcomplex32` dtype](https://github.com/pytorch/rfcs/pull/87) 
proposes bfloat16-based complex numbers. Subclass decomposition to `bfloat16` hits existing implementations for that
datatype without needing custom kernels to cover gaps in BLAS. Under compile we hit existing pathways for lowering ops
on the same real dtype, and all without adding any code[^code] particular compiled code that adds size to the binary,
and maintenance overhead.

### Inductor

In Inductor, our biggest piece of work was correctness rather than speed. After Inductor's post-grad passes rewrite the
FX graph, `FakeTensorUpdater` re-propagates shape, stride and dtype metadata so later passes see accurate information.
It didn't look inside higher-order ops like `invoke_subgraph`, `cond`, `while_loop` and `scan`, so their subgraphs could
end up with stale metadata, which could cause silent incorrectness. [Fixing it](https://github.com/pytorch/pytorch/pull/185962) 
meant recursing into subgraphs, updating their callers, and handling subgraphs reused at several call sites with
different input shapes. It took about ten months and several rounds of reverts against large internal models before it
stuck. It also exposed at least one latent bug in the `scan` backward along the way.

Correctness work also reached outside the compiler. `native_group_norm` gave different answers depending on where it
ran, so we added an OpInfo test for it, fixed precision issues in the CUDA forward and backward so eager mode matches
Inductor's decomposition, and made it handle non-contiguous inputs instead of throwing. Together with the native MPS
kernel described [below](#apple-silicon), group norm now behaves consistently across backends, eager and compile.

Most recently we have been shaving microseconds off warm-cache `torch.compile` overhead, the fixed cost paid on every
call to a compiled function even when nothing needs recompiling. The guard functions Inductor relies on are about 50%
faster, device index lookups about 4x faster, and caching a single Python string removed about 3 µs, roughly 20% of the
remaining Dynamo overhead in our microbenchmark. Along with graph breaks, overhead like this is one of the frustrations
that come up most often when users talk about `torch.compile`.

## Core PyTorch

### A new operator: fused linear cross-entropy

The output layer of a language model is a linear projection into the vocabulary followed by a cross-entropy loss, and in
between sits the logits tensor: one row per token, one column per vocabulary entry. With a vocabulary of 128k and a
large token batch, that is tens of gigabytes in bf16, often the single largest allocation in training. The solution is
well known: fuse the two and process the logits in chunks so the full tensor never exists. The 
[user request](https://github.com/pytorch/pytorch/issues/124480) to have this in core had been open since 2024, while
implementations multiplied across Liger-Kernel, xformers, Unsloth, torchtune, torchtitan and others.

PyTorch 2.13 added `torch.nn.LinearCrossEntropyLoss` and `torch.nn.functional.linear_cross_entropy`. The first
implementation is deliberately composite: rather than a custom CUDA kernel, it composes existing PyTorch operators,
chunking along the batch dimension and computing the backward terms together with the forward. It is device-generic,
adds no compiled code, and still cuts peak memory by up to 4x for large vocabularies. It is also fast. On an A100 with a
131k vocabulary, the default path runs about 2.3x faster than Liger-Kernel's Triton kernel at under half its peak
memory. That was the result we found most interesting. Composing PyTorch ops well is enough to match hand-written
kernels on this problem, and we saw the same picture across three GPU generations.

Plain `Linear` followed by `CrossEntropyLoss` is still faster in raw time when the logits fit in memory. The fused
operator is for when they don't, or when you'd rather spend that memory on something else.

#### A fused kernel written in Python

Then we went further. Per chunk, the composite backward did three matrix multiplications, five passes over a large
intermediate buffer, and a scatter. A [new fused kernel](https://github.com/pytorch/pytorch/pull/195829) does all of
that in a single launch and writes the gradient into the same buffer in place. That removes both the scatter and a whole
buffer allocation, and as a bonus makes the backward deterministic. The results, against the operator's own composite
path:

- **H100:** 1.15-1.6x faster, at lower peak memory in every measured shape.
- **B200:** up to 3.3x faster.
- **Against Liger-Kernel:** 1.25-6x faster at equal peak memory on H100, and up to 6.8x on B200.

The advantage grows with vocabulary size and was still rising at the largest vocabulary we measured. On B200 in bf16 it
went from 1.3x at 8k classes to 2.0x at 16k, 3.0x at 32k and 4.9x at 65k. Production vocabularies are larger still.

If the performance gains and reduced memory pressure are not enough, you might find the implementation details exciting
too. The kernel is written in [CuTeDSL](https://docs.nvidia.com/cutlass/latest/media/docs/pythonDSL/overview.html), the
Python front end to CuTe, the layout and tensor algebra underneath CUTLASS 4. It is just-in-time compiled to device code
at its first call rather than at build time, so it adds nothing to the size of the PyTorch wheel. It plugs into
`torch._native`, PyTorch's registry of DSL-written overrides for existing operators. The registry already carried
CuTeDSL implementations of core ATen ops such as `scatter_add`, `topk` and the fused RMS norm. To make it work here we
generalized it to operators defined in Python rather than C++, so every future kernel for a Python-defined operator
inherits that support. Each override handles only the inputs it claims, and anything else falls back to the existing
path.

The fused kernel has landed on `main` and will ship in PyTorch 2.15.

#### What's next

The recipe generalizes beyond this operator. Wherever a backward pass materializes a large intermediate and then walks
it several times, those passes can often collapse into one kernel that writes its result in place. That pattern is
common in loss functions and in chunked operators whose element-wise work surrounds their matmuls. Because each override
is additive, opt-in per shape and dtype, and reversible, accelerating the next operator is an increment with a bounded
blast radius, not a rewrite. Closest at hand are a further fusion for this same operator and retuning its kernel
constants for Blackwell (they were chosen on H100).

### Apple Silicon {#apple-silicon}

The MPS backend got a lot of attention this period, with more than 60 PRs landed. Several ops that previously fell back
to the CPU, or weren't available at all, now have native MPS implementations:

- **Pooling and sampling:** 3D max and average pooling, `max_unpool`, `grid_sampler_3d`
- **Embeddings, indexing and regularization:** `embedding_bag`, `index_reduce`, `native_dropout`
- **Special functions:** `igamma`/`igammac`, `mvlgamma`
- **Distributions:** `binomial`, `_sample_dirichlet` and `_dirichlet_grad`
- **Loss:** CTC loss, forward and backward
- **Upsampling:** the anti-aliased bilinear and bicubic upsampling backwards
- **Linear algebra:** `linalg.householder_product`, `linalg.lu`, `linalg.lu_solve` and `geqrf`

Other ops moved to hand-written Metal kernels, which is usually where the speed comes from:

- [`native_group_norm`](https://github.com/pytorch/pytorch/pull/183830) previously ran as a Python decomposition. The
  native version is more than 10x faster on average on an M4.
- [`norm`](https://github.com/pytorch/pytorch/pull/177328) moved to Metal with a roughly 2x speedup in most cases.
- `torch.cat`, `clamp`, `elu`, `logaddexp`, `abs` and `max_pool2d` also moved to Metal.

Complex dtype support filled in across `scatter`/`gather`, `repeat`, `cumsum`, `cumprod`, `logcumsumexp`, `norm` and
`nn.functional.linear`.

Two infrastructure changes stand out. First, 
[`test_ops.py` now runs on MPS](https://github.com/pytorch/pytorch/pull/169018), backed by a long series of OpInfo dtype and skip annotations. MPS
operators now get the same systematic coverage as CPU and CUDA. Second, MPS now has multi-stream support. A 
[pool of MPS streams](https://github.com/pytorch/pytorch/pull/190375), a stream-aware allocator, and a 
[`torch.mps.Stream` API](https://github.com/pytorch/pytorch/pull/191415) modeled on CUDA's let users submit work to
separate GPU command queues that execute concurrently. `Tensor.record_stream` and a stream-aware profiler round it out.
The stream API landed after the 2.14 branch cut, so look for it in 2.15.

## Infrastructure

### spin

PyTorch's development community is big and moves fast. Developers have to stay on top of their own modules while keeping
an eye on the rest of the codebase evolving around them, and a lot of thought and effort goes into any infra change that
would break their muscle memory for common tasks like starting a build, running tests or running the linters. When those
commands change because the tooling behind them changes or is replaced, it is painful for everyone. What if we could
break that pattern? What if we could pin the developer CLI and change the tooling underneath it, reaping the benefits
of updating things without changing the ergonomics? Following other projects like
[NumPy, SciPy and scikit-image](https://github.com/pytorch/pytorch/issues/164469), PyTorch now has
[spin](https://github.com/scientific-python/spin), a developer CLI that gives you one stable set of commands and hides
the details behind them.

Some of the commands added so far:

- `spin lint`, `spin fixlint`, `spin quicklint` and `spin quickfix` run lintrunner in a dedicated environment via `uvx`,
  so there's no guesswork and no version skew with CI.
- `spin develop` does an editable build, replacing `python setup.py develop` (more on that below). `spin install` does a
  regular, non-editable install. Both prefer `uv pip` when it's available.
- `spin test` runs pytest, or with `--ci`, the `test/run_test.py` driver that CI uses.
- `spin docs` builds the documentation.
- `spin pyrefly infer` generates type annotations using pyrefly's experimental inference engine.
- `spin clean` cleans the build, and `spin regenerate-*` regenerates version files, type stubs and GitHub workflows.

If part of your development workflow seems to be missing, let us know by filing an issue. We will keep adding commands
as new tooling comes up, but the most-used commands were the first priority.

### scikit-build-core

As of PyTorch 2.14, PyTorch builds with [scikit-build-core](https://scikit-build-core.readthedocs.io/) instead of
setuptools. The trigger was setuptools' deprecation and announced removal of direct `setup.py` commands like `develop`
and `install`, which PyTorch's build had leaned on for years. We 
[chose scikit-build-core](https://github.com/pytorch/pytorch/issues/157807) over alternatives like meson-python because
it fit most naturally with PyTorch's existing CMake build.

The migration was done in phases. In 2025, the build and release process moved off direct `setup.py` calls to `pip
install` and `python -m build`. In 2026,  PyTorch began publishing a standards-compliant source distribution, and  the
custom logic that had accumulated in `setup.py` moved, piece by piece, into CMake: environment handling, pre-build
steps, package data, Windows DLL bundling, macOS OpenMP and the `torch._C` extension itself. The switch 
[landed in July](https://github.com/pytorch/pytorch/pull/180247), producing wheels whose contents are identical to the
setuptools-built ones. `setup.py` is now only a shim that forwards `develop` and `install` to the correct commands.
After the 2.15 release is cut, the shim will start raising a hard error instead, and after the 2.17 release is cut it
will be removed completely.

Downstream extension builds are unaffected for now. `torch.utils.cpp_extension` and `BuildExtension` still work as
before, because the on-disk wheel layout they depend on is preserved, and the implementation for these APIs have not
changed at all.  What's next:

- continued consolidation in CI
- single sources of truth for build knobs, dependencies and build/test environments;
- a hardened, documented, tested `find_package(Torch)` CMake path for downstream projects, with 
  [utilities and examples](https://github.com/pytorch/pytorch/issues/180624) to go with it.

That last point is a pre-requisite for any discussion about deprecation and removal of our exporting downstream build
helpers. We do not have any concrete plan to remove them at this point. If that comes up down the line it will be
considered as any backward incompatible change, with clear battle tested migration targets and a long warning cycle
before ultimate removal.

## TorchAO

[TorchAO](https://github.com/pytorch/ao) is PyTorch's native library for quantization and low-precision training and
inference. It covers float8 and MXFP8 training, int4 inference, structured sparsity and more, and it works with
`torch.compile` and FSDP2 out of the box. A lot of its performance comes from custom kernels, and a lot of those kernels
were C++/CUDA and CUTLASS extensions. Those extensions carried real costs. They tied each TorchAO build to a specific
PyTorch version ([mismatched versions crash on import](https://github.com/pytorch/ao/issues/2919)), complicated the
build and the wheel matrix, and made kernel development slow. TorchAO is 
[moving closer to Python-only](https://github.com/pytorch/ao/issues/3516), and CuTeDSL is how the performance-critical
CUTLASS kernels get there.

Our work this period sat on both sides of that line:

- **Grouped matmul in Inductor:** Grouped matmul is the core of mixture-of-experts training, running every expert's GEMM
  in one kernel. We continued developing and optimizing grouped and scaled grouped matmul in Inductor. That included
  making `_grouped_mm` autotunable, moving the Triton kernel to TMA loads, fixing loop pipelining (up to 1.8x over
  CUTLASS on some 2D/2D shapes), and fixing 64-bit indexing for very large inputs.
- **CuTeDSL MXFP8 kernels in TorchAO:** we wrote CuTeDSL kernels for MXFP8 quantization of 3D tensors, which beat the
  existing CUDA kernel and run close to B200's peak memory bandwidth, along with the transposed and 32x32 weight-scaling
  variants used in MXFP8/MoE training. A follow-up stack, now in review, ports the remaining scale-rearrangement and
  padding kernels, makes CuTeDSL the default for MoE and `MXFP8Linear` training, and removes the legacy CUDA and Triton
  paths.
- **FP8 2:4 sparsity:** we ported the FP8 2:4 structured sparsity kernels, which we originally wrote in CUTLASS, to
  CuTeDSL. The conversion kernel runs about 6x faster than the legacy path on real model shapes, and the sparse GEMM
  holds or improves performance at training-sized batches. This work is under review but should land soon!
- **Scaled grouped matmul for Blackwell and Hopper:** we wrote CuTeDSL kernels in PyTorch core targeting quantized MoE
  workloads, covering MXFP8, MXFP4 and NVFP4 on Blackwell and DeepSeek-style blockwise scaling on Hopper. These are in
  review. They are also a test case for the open questions in writing eager-mode PyTorch kernels in a DSL: how to pin
  the DSL as a runtime dependency without hurting downstream libraries, how to register kernels with the dispatcher, and
  how to cache JIT-compiled kernels.


Next up is [Gluon](https://github.com/triton-lang/triton/tree/main/python/tutorials/gluon), Triton's lower-level
dialect. Early experiments with a Gluon grouped matmul for Blackwell get close to CUTLASS performance at large shapes,
where the Triton kernel falls behind. We are starting to work these experiments into production kernels while other work
is going on to support Gluon as a torch.compile codegen target.

## TorchAudio

TorchAudio is not under active feature development. There are no plans to sunset it, but no constant feature
additions/improvements going on either. In April 2025, a plan was announced to cut its maintenance burden by 
[making it Python-only](https://github.com/pytorch/audio/issues/3902). Some C++ and CUDA extensions (RNN-T loss, forced
alignment) would be dropped, and others (`lfilter`, `overdrive`) would move to pure-Python implementations. The goal was
to reduce the work required to finalize a release by limiting the dependency surface and removing build issues entirely.
The community objected loudly, and with good reason: for many users, those optimized routines were the whole reason to
use TorchAudio.

The [LibTorch stable ABI](https://docs.pytorch.org/docs/stable/notes/libtorch_stable_abi.html) came to the rescue. It is
a limited C and C++ interface for building extensions that aren't tied to a specific PyTorch version, and C shim APIs
come with a compatibility window of at least two years. Instead of deleting the native code, we ported it.

We ported all five extensions (`lfilter`, `overdrive`, RNN-T
loss, `forced_align` and the CUDA CTC decoder) to the stable ABI, with no loss of functionality or performance. Along
the way, the port kept hitting things the stable ABI didn't offer yet, so we added them to PyTorch itself:

- `torch::stable::Tensor` methods like `copy_`, `clone` and typed data pointers
- CUDA stream shims
- header-only versions of the dispatch macros and `TensorAccessor`
- other pieces any extension author would eventually need

TorchAudio was one of the first real-world exercises of the stable ABI, and the gaps it found are now filled for
everyone.

[TorchAudio 2.10](https://github.com/pytorch/audio/releases/tag/v2.10.0) shipped in January 2026 with all five
extensions preserved, marking the end of the migration. Starting with 2.11, TorchAudio no longer pins an exact PyTorch
version, and it doesn't need a new build and release for every PyTorch release. It works so far: TorchAudio 2.11 has
carried users through PyTorch 2.12, 2.13 and 2.14 without a new release. What started as a maintenance-reduction project
ended up refining and battle-testing a new integration surface in the core project, while still hitting the original
goal of cutting down the work required at release time.

## conda-forge

With PyTorch 2.5, the PyTorch team 
[deprecated its official Anaconda channel](https://github.com/pytorch/pytorch/issues/138506). Anaconda builds accounted
for more than half of the maintenance cost for under 5% of downloads, so the effort went to PyPI wheels instead. For
people who want PyTorch from conda, the answer is now the community-maintained 
[conda-forge feedstock](https://github.com/conda-forge/pytorch-cpu-feedstock), which our team helps maintain alongside other
conda-forge maintainers.

That work is mostly invisible when it goes well. It includes:

- version bumps and release candidates;
- keeping up with CUDA versions and pins for cuDNN, NCCL and CUPTI, and bringing new versions of dependencies to conda-forge as needed;
- fixing Windows linking errors and macOS cross-compilation issues, often upstream in PyTorch's CMake;
- managing a minimal set of tests that balances limited CI infrastructure against good coverage.

It goes best when we can stage ahead of the release. The 2.10 release candidates were on conda-forge before the final
release, and 2.10.0 followed three days after upstream. Other releases took longer, sometimes much longer. Right now the
feedstock is working through the scikit-build-core migration described above for 2.14, which is a nice reminder that
build system changes ripple well beyond the main repo. Getting each release onto conda-forge as quickly as possible
remains the goal.

## Closing remarks

Yearly reviews are a good excuse to step back. Looking at this one, much of the work has been about making PyTorch
easier to work on correctly, not just adding features:

- an object model that tells you where a fix goes;
- a test suite that finds gaps before users do;
- issues small enough for a first-time contributor to land;
- developer commands that stay put while the build system changes underneath them;
- extensions that survive PyTorch upgrades.

In a year when code got cheap and review didn't, that felt like the right place to put our effort.

None of this would have happened without our fantastic PyTorch team, now part of OpenTeams: Rob Timpe,
Guilherme Leobas, Hameer Abbasi, Pearu Peterson, Kurt Mohler, Aleksandar Samardžić and Benjamin Glass. The same goes
for our colleagues at Quansight PBC: Michał Górny, Klaus Zimmermann and Ralf Gommers.
<!-- TODO(review): check with Ralf for full list of CF contributors -->

The other part of the story is the great team of PyTorch engineers at Meta and across the community. Without their
dedication and openness to collaboration, none of this would have been possible. In particular, we would like to thank
Animesh Jain, William Wen, Elias Ellison, Edward Yang, Richard Zou, Alban Desmaison, Simon Layton, Driss Guessous,
Daniel Vega-Myhre, Jerry Zhang, Nicolas Hug, Scott Schneider, Mikayla Gawarecki, Jane Xu, Andrey Talman, Peng Wu,
Supriya Rao, and Joe Isaacson from Meta, as well as Brian Hirsh, Nikita Shulga and Aaron Gokaslan from the wider PyTorch
developer community along with the conda-forge maintainers. Thank you all for making this collaboration so fruitful and
enjoyable.
<!-- TODO(review): check both name lists. Thank-you list drawn from PR reviewers and collaborators found during research. 
Check with meta regarding those who are no longer there (Brian) those no longer on the PyTorch team (mikayla) and those
still associated with the community (Nikita) -->

*Looking for earlier years? See our reviews of 
[2023/2024](https://quansight.com/post/a-year-in-review-quansights-contributions-to-pytorch-in-2023-early-2024/),
[2022](https://quansight.com/post/a-year-in-review-quansights-contributions-to-pytorch-in-2022/) and
[2021](https://quansight.com/post/a-year-in-review-quansights-contributions-to-pytorch-in-2021/). Still available on the
Quansight blog archives!*

<small>PyTorch Foundation and the PyTorch Foundation logo design are registered trademarks of the Linux Foundation.</small>

[^review-bottleneck]: As Edward Yang put it in PyTorch's 
  [AI coding playbook](https://docs.pytorch.org/devlogs/ai-agents/2026-05-30-ai-coding-playbook/), "In an age of cheap
  code, we are human review bottlenecked."

[^compile-refresher]: If you want a refresher on how the pieces fit together (Dynamo captures a graph from Python
  bytecode, AOTAutograd traces it down to core ATen ops and adds the backward, Inductor generates the code), our
  [2023/2024 post](https://quansight.com/post/a-year-in-review-quansights-contributions-to-pytorch-in-2023-early-2024/)
  has a fuller walkthrough.

[^implementation-by-accident]: As Animesh Jain describes it in his 
  [devlog on agent-friendly Dynamo](https://docs.pytorch.org/devlogs/dynamo/2026-05-13-agent-friendly-dynamo/), the
  supported surface area had become "implementation-by-accident," to the point where "we don't even know which parts are
  unsupported."

[^sentinels]: Sentinels can be used inside a compiled region, but declaring a new one inside a compiled region will
  cause a graph break.

[^code]: It is not quite free, you must add an entry in the table mapping the complex dtype onto its real counter part,
  which is a single line change (still pretty good!)
