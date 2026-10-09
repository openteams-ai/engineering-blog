---
name: draw-card-art
description: >
  Draw the card art for an engineering-blog post: the small SVG illustration shown on the post's card on the home page, topic pages and related posts. Use when the author asks to "draw the card art", "make a featured image", "make a thumbnail", "add card art", or when a new post's card shows a generic pattern. Operates on a posts/<file> path or a bare slug. Writes src/components/art/<slug>.astro and checks it with screenshots at every card size.
user-invocable: true
---

# Draw Card Art

Suggest three ideas for one post's card art, then draw the one the author picks in the style of the existing cards, check it at every size the site shows it, and fix what the screenshots show before handing it to the author.

**Usage:** `/draw-card-art posts/article-name.md`

## Step 1: Read the post

- Resolve a bare slug to `posts/<slug>.md`.
- Read the whole post, including the frontmatter. The art is named by the frontmatter `slug`, which can differ from the filename.
- If `social/<slug>.yml` has answers, read `remember_one_thing`: it is often the idea the card should show.

## Step 2: Suggest three ideas and let the author choose

A card shows one thing: the post's headline number, its main comparison, or the mechanism it explains. Examples from existing cards:

- `benchmark-python-package-managers`: install times as six bars.
- `pixi-ubi-micro-containers`: a large image shrinking to a small one, 803 MB to 511 MB.
- `lint-rules-for-ai-agents`: agent, lint error and fix as a loop.

Every label and number must come from the post. Use at most four short labels, since the card is drawn as small as 266 by 150 pixels.

Suggest three different ideas, each as an ASCII sketch of the card with one line on what it shows and which part of the post it comes from. Make them differ in kind (for example a number, a comparison and a mechanism), not three layouts of one idea. Name the background family each would use. For example:

```text
A. The headline number                        soft blue
┌────────────────────────────────────────┐
│  laptop              CI                │
│  ┌────────┐   =   ┌────────┐           │
│  │ ▂▅▇▃▆  │       │ ▂▅▇▃▆  │           │
│  └────────┘       └────────┘           │
│        55 min -> 15 min                │
└────────────────────────────────────────┘
Same pixels locally and on CI, and the suite's run time ("Before and after").
```

Then stop and ask the author to pick one, combine them, or ask for others. Don't draw until they choose.

## Step 3: Learn the style

- Read the rules at the top of `src/components/art/style.ts`: the background families, inks, fonts and minimum text sizes. Import colors, fonts and `sparkle` from there instead of writing new hex values.
- Read two or three cards in `src/components/art/` that are close to the chosen idea, and match their structure.

## Step 4: Write the card

Create `src/components/art/<slug>.astro`. The site picks it up by its file name, so nothing else needs changing.

- Start from a copy of a similar card, so the `<svg>` root keeps the same attributes: `viewBox="0 0 720 380"`, `class="h-full w-full"`, `preserveAspectRatio="xMidYMid meet"` and `role="img"`.
- Write an `aria-label` that describes what the card shows.
- Fill the background with the oversized rect the other cards use, so the color reaches the edges at every card shape.
- Keep the drawing within the middle of the canvas, with about 40 units of margin.
- Logos go in `public/blog-logos/` and are referenced with `blogUrl("/blog-logos/<file>")`.

## Step 5: Check the screenshots

```bash
node scripts/card-preview.ts <slug> /tmp/card-<slug>.png
```

It starts the dev server, screenshots the card at the four sizes the site uses (featured on desktop and on a phone, grid, related) and stops the server. Read the PNG and check:

- Every label is readable on the related card (266 pixels wide). If not, make it larger or remove it.
- Nothing overlaps, and no arrow misses its target.
- Nothing is cut off on the phone card.
- The idea is clear from the related card alone.

Fix what you find and run the script again. Stop after three rounds and show the author what is still wrong.

## Step 6: Show the author

Show the author the final screenshot and say in one sentence what the card shows. Ask whether they want anything changed: an idea, a label, or a color. Their post's card is theirs to approve.
