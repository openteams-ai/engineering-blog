#!/usr/bin/env python3
"""
Render the PR comment body for a WordPress draft preview run.

Reads the JSON-lines file preview_draft.py appends to and writes markdown to
stdout. The workflow hands the result to sticky-pull-request-comment, which
owns finding and updating its own comment on each push.

Usage:
    uv run scripts/wordpress/build_preview_comment.py results.jsonl
"""

import argparse
import json
from pathlib import Path
from typing import Dict, List

SHADOW_NOTE = (
    "Posts marked *shadow copy* are already live, so the preview is a "
    "throwaway duplicate under a different slug. The published article is "
    "untouched, and the duplicate is trashed when this PR closes."
)

THEME_NOTE = (
    "These render in the live theme, so the Elementor lightbox, brand fonts, "
    "and content column all behave as they will on publish."
)

LOGIN_NOTE = (
    "**Opening these requires signing in to WordPress.** Public links need "
    "the Public Post Preview plugin and the openteams/v1/public-preview "
    "route, both configured on openteams.com."
)


def read_results(path: str) -> List[Dict]:
    """Load one result record per non-blank line."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def preview_table(previews: List[Dict]) -> List[str]:
    """Return the markdown table rows for successful previews."""
    rows = ["| Post | Preview |", "| --- | --- |"]
    for result in previews:
        note = " (shadow copy)" if result.get("shadow") else ""
        rows.append(f"| `{result['file']}`{note} | [Open preview]({result['url']}) |")
    return rows


def access_note(previews: List[Dict]) -> str:
    """Explain who can open these links and for how long.

    Falls back to the login-required wording unless every link is public, so
    a partial failure never overstates what a reviewer can do.
    """
    if not all(result.get("public") for result in previews):
        return LOGIN_NOTE

    expiry = next((r["expires"] for r in previews if r.get("expires")), "")
    deadline = f" They stay valid until **{expiry}**." if expiry else ""
    return (
        "Anyone with the link can open them, no WordPress account needed."
        f"{deadline} Push anything to this PR to reissue them."
    )


def render(results: List[Dict]) -> str:
    """Return the full comment body for a set of results."""
    blocks = ["### WordPress draft preview"]

    previews = [r for r in results if r["state"] == "ok"]
    problems = [r for r in results if r["state"] != "ok"]

    if previews:
        blocks.append("\n".join(preview_table(previews)))
        if any(r.get("shadow") for r in previews):
            blocks.append(SHADOW_NOTE)
        blocks.append(THEME_NOTE)
        blocks.append(access_note(previews))

    for result in problems:
        label = "Skipped" if result["state"] == "skipped" else "Failed"
        blocks.append(f"- **{label}** `{result['file']}`: {result['reason']}")

    if not results:
        blocks.append("No posts to preview.")

    return "\n\n".join(blocks) + "\n"


def main():
    parser = argparse.ArgumentParser(
        description="Render the PR comment body for a draft preview run."
    )
    parser.add_argument("results", help="JSON-lines file written by preview_draft.py")
    args = parser.parse_args()

    print(render(read_results(args.results)), end="")


if __name__ == "__main__":
    main()
