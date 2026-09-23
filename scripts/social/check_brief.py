#!/usr/bin/env python3
"""
Fail unless every given post has a fully answered social/<slug>.yml.

Runs as the required `social-brief` check on pull requests. Inside GitHub
Actions each problem is also emitted as an error annotation on the brief file.

Usage:
    uv run scripts/social/check_brief.py posts/my-post.md [more posts...]
"""

import argparse
import os
import sys
from pathlib import Path
from typing import List

import yaml
from pydantic import ValidationError

from brief_schema import SocialBrief, brief_path, is_blank


def edit_link(target: Path) -> str:
    """A GitHub web-editor link for the brief on this PR's branch, if in CI."""
    repo = os.environ.get("GITHUB_REPOSITORY")
    branch = os.environ.get("GITHUB_HEAD_REF")
    if not (repo and branch):
        return ""
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    return f" Edit it in the browser: {server}/{repo}/edit/{branch}/{target.as_posix()}"


def find_problems(post_path: Path) -> List[str]:
    """Return one fix-it message per problem with this post's brief."""
    target = brief_path(post_path)
    if not target.exists():
        return [
            f"{target} is missing. Create it with "
            f"`uv run scripts/social/create_brief.py {post_path}`."
        ]

    data = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if is_blank(data):
        return [
            f"{target} needs answers. Answer its 4 questions yourself or with your "
            "AI assistant, then push."
            + edit_link(target)
        ]
    try:
        SocialBrief.model_validate(data)
    except ValidationError as error:
        return [
            f"{target}: `{'.'.join(map(str, e['loc']))}` {e['msg'].removeprefix('Value error, ')}"
            for e in error.errors()
        ]
    return []


def report(post_path: Path, problems: List[str]) -> None:
    in_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    for problem in problems:
        print(f"❌ {problem}")
        if in_actions:
            print(f"::error file={brief_path(post_path)}::{problem}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("posts", nargs="*", type=Path)
    args = parser.parse_args()

    failed = False
    for post_path in args.posts:
        problems = find_problems(post_path)
        if problems:
            report(post_path, problems)
            failed = True
        else:
            print(f"✅ {brief_path(post_path)}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
