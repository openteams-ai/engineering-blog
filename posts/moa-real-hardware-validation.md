---
title: "Validating Memory-Optimal Transformer Kernels on Real Hardware"
slug: moa-real-hardware-validation
authors:
    - lenore-mullin
categories:
    - Engineering
meta_description: "Paper V of MoA series - first attention kernel proven minimal BEFORE code, validated across two HPC clusters including Stampede3. 2.4MB artifact."
focus_keyword: "MoA attention kernel"
---

# Validating Memory-Optimal Transformer Kernels on Real Hardware

This is **Paper V** of the Mathematics of Arrays (MoA) series — the first attention kernel **proven minimal BEFORE code was written**, then validated on real hardware.

## What this solves

Attention implementations waste memory because minimality is measured after the fact. MoA derives the lower bound formally, then constructs the kernel that achieves it.

## Paper series

1. **Paper I** - Foundation: MoA formalism & memory lower bounds
2. **Paper II** - Fused Kernels
3. **Paper III** - CPU Verification
4. **Paper IV** - GPU Verification
5. **Paper V - Real Hardware Validated (Sep 2026)** — this post

## Validation

- Two HPC clusters, including **TACC Stampede3**
- CPU + GPU sweeps
- `run_cpu_sweep.sh` reproduces the measurements

## Artifact — 2.4MB (2026-09-26)

**https://github.com/womenflyplanes/moa-attention-verified-mullin**

Contains:
- `moa_attention/` - pip-installable package
- `paper_V_software/attention/` - core kernels: `moa_backward.c`, `moa_cost_model.c`, `moa_decode.c`, `moa_flash_tiling.c`, `moa_kv_cache.c`
- `paper_V_software/experiments/` - CPU+GPU benchmarks
- `paper_V_software/verification/` - verification code
- `paper/` - PDF + TeX + 20 figures


Authors: **Lenore Mullin & Peilun Ju**

> From formal derivation to measured performance.

### How to cite while on hold

Mullin, L. & Ju, P. (2026). Validating Memory-Optimal Transformer Kernels on Real Hardware. HAL:05734881. arXiv:2609.xxxxx (pending moderation, submit/8132497).
