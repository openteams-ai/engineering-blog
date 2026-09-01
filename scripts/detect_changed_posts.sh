#!/usr/bin/env bash
# List the post files a range of commits touched, one per line.
#
# A post is included when its own .md/.qmd changed, or when an image under
# posts/images/<slug>/ changed, since republishing the post is what pushes new
# image bytes to WordPress. Image directories with no matching post file are
# skipped.
#
# Usage:
#   scripts/detect_changed_posts.sh <base-ref> [head-ref]
set -euo pipefail

BASE="${1:?usage: detect_changed_posts.sh <base-ref> [head-ref]}"
HEAD_REF="${2:-HEAD}"

changed() {
  git diff --name-only --diff-filter=AM "$BASE" "$HEAD_REF" -- "$@"
}

{
  changed 'posts/*.md' 'posts/*.qmd'

  # posts/images/<slug>/file.png -> posts/<slug>.md or posts/<slug>.qmd
  changed 'posts/images/**' | cut -d/ -f3 | sort -u |
    while read -r slug; do
      for post in "posts/$slug.md" "posts/$slug.qmd"; do
        if [ -f "$post" ]; then
          echo "$post"
          break
        fi
      done
    done
} | sed '/^$/d' | sort -u
