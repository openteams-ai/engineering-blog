#!/usr/bin/env python3
"""
Fail unless every given post has a fully answered social/<slug>.yml.

Runs as the required `social-brief` check on pull requests. Inside GitHub
Actions each problem is also emitted as an error annotation on the brief file,
and --comment writes the body of the PR comment that asks the author to fill
the brief in.

Usage:
    uv run scripts/social/check_brief.py posts/my-post.md [more posts...]
    uv run scripts/social/check_brief.py --comment comment.md posts/my-post.md
"""

import argparse
import os
import sys
from pathlib import Path
from typing import Dict, List

import yaml
from pydantic import ValidationError

from brief_schema import SocialBrief, brief_path, is_blank

COMMENT_HEADER = "### Social brief"
# The comment's link already says to answer the questions, so it skips this one.
UNANSWERED = "Its 4 questions are unanswered."


def github_url(path: str) -> str:
    """A github.com URL for this repo, or "" outside GitHub Actions."""
    repo = os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        return ""
    server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    return f"{server}/{repo}/{path}"


def edit_url(target: Path) -> str:
    """The GitHub web-editor URL for the brief on this PR's branch."""
    branch = os.environ.get("GITHUB_HEAD_REF")
    return github_url(f"edit/{branch}/{target.as_posix()}") if branch else ""


def find_problems(post_path: Path) -> List[str]:
    """Return one fix-it message per problem with this post's brief."""
    target = brief_path(post_path)
    if not target.exists():
        return [
            "The brief is missing. Create it with "
            f"`uv run scripts/social/create_brief.py {post_path}`."
        ]

    data = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if is_blank(data):
        return [UNANSWERED]
    try:
        SocialBrief.model_validate(data)
    except ValidationError as error:
        return [describe(e) for e in error.errors()]
    return []


def describe(error: dict) -> str:
    """Turn a pydantic error into a sentence an author can act on."""
    field = ".".join(map(str, error["loc"]))
    if error["type"] == "too_short" and field == "audience":
        return "`audience` needs at least one group from the list in the brief."
    return f"`{field}` {error['msg'].removeprefix('Value error, ')}"


def report(post_path: Path, problems: List[str]) -> None:
    """Print problems to the log, plus annotations when in GitHub Actions."""
    target = brief_path(post_path)
    in_actions = os.environ.get("GITHUB_ACTIONS") == "true"
    link = edit_url(target)
    for problem in problems:
        message = f"{target}: {problem}" + (f" Edit it: {link}" if link else "")
        print(f"❌ {message}")
        if in_actions:
            print(f"::error file={target}::{message}")


def render_comment(results: Dict[Path, List[str]]) -> str:
    """The PR comment: what to fill in while problems remain, thanks once done."""
    pending = {post: problems for post, problems in results.items() if problems}
    if not pending:
        briefs = ", ".join(f"`{brief_path(post)}`" for post in results)
        return f"{COMMENT_HEADER} ✅\n\nThanks! {briefs} is filled in, so this check passes.\n"

    # A PR comment resolves relative links against the PR's URL, not the repo,
    # so the README link has to be absolute.
    readme = github_url("blob/main/README.md#social-brief")
    guide = f"[Social Brief]({readme})" if readme else "Social Brief"
    lines = [
        f"{COMMENT_HEADER} needed",
        "",
        "Before this PR can merge, please answer 4 short questions about your post. "
        "We use them to write its LinkedIn post.",
        "",
    ]
    for post, problems in pending.items():
        target = brief_path(post)
        link = edit_url(target)
        action = f"Answer the questions in `{target}`"
        lines.append(f"👉 **[{action}]({link})**" if link else f"👉 **{action}**")
        lines += [f"- {problem}" for problem in problems if problem != UNANSWERED]
        lines.append("")

    lines += [
        "To fill it in, either:",
        "",
        "- **In the browser:** click the link above, answer the questions, and commit.",
        "- **With an AI assistant:** `git pull`, then run `/fill-social-brief "
        f"{next(iter(pending))}` (or ask any agent to fill in the brief from the post). "
        "Check its answers, then push.",
        "",
        f"See {guide} in the README for what each question means, with examples. "
        "This comment updates on every push.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("posts", nargs="*", type=Path)
    parser.add_argument("--comment", type=Path, help="also write the PR comment here")
    args = parser.parse_args()

    results = {post: find_problems(post) for post in args.posts}
    for post, problems in results.items():
        if problems:
            report(post, problems)
        else:
            print(f"✅ {brief_path(post)}")

    if args.comment and results:
        args.comment.write_text(render_comment(results), encoding="utf-8")
    return 1 if any(results.values()) else 0


if __name__ == "__main__":
    sys.exit(main())
