#!/usr/bin/env python3
"""
Create an empty social/<slug>.yml for each post that does not have one yet.

The brief holds four short questions about the post. The author answers them,
by hand or with whatever AI assistant they use; check_brief.py blocks merge
until all four are answered. An existing brief is never
overwritten, since it may already hold the author's answers.

Usage:
    uv run scripts/social/create_brief.py posts/my-post.md [more posts...]
"""

import argparse
import sys
from pathlib import Path

from brief_schema import brief_path, render_template


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("posts", nargs="+", type=Path)
    args = parser.parse_args()

    for post_path in args.posts:
        target = brief_path(post_path)
        if target.exists():
            print(f"Keeping existing {target}")
            continue
        target.parent.mkdir(exist_ok=True)
        target.write_text(render_template(post_path), encoding="utf-8")
        print(f"Created {target}. Answer its questions, then push.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
