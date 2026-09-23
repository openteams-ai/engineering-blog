---
title: "Social Brief Test Post"
slug: social-brief-test
authors:
  - khuyen-tran
categories:
  - Engineering
meta_description: "A throwaway post that tests the social brief workflow on a pull request. It should never be merged or published."
focus_keyword: "social brief test"
---

This post exists only to test the `social-brief` workflow. Do not merge it.

## What it checks

When a pull request adds a post, CI should commit an empty `social/social-brief-test.yml` to the branch and fail the `social-brief` check until every answer is filled in.
