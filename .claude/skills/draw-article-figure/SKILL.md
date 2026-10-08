---
name: draw-article-figure
description: >
  Draw an in-article figure (diagram, chart, or annotated illustration) for an engineering-blog post: suggest three ASCII sketches first, then draw the chosen one as a hand-written SVG, embed it in the post, and check it where the Astro site shows it, at desktop and phone widths in light and dark mode. Use when the author asks to "draw a figure", "make a diagram", "recreate this chart", "illustrate this section", or highlights a passage in posts/ and asks for a visual made in code rather than in Paper. Operates on a posts/<file> path or a bare slug, plus the passage or reference image to draw. For the post's card art use /draw-card-art.
user-invocable: true
---

# Draw Article Figure

Sketch three options in ASCII, draw the one the author picks as an SVG file, put it in the post, and check it in the running site before handing it to the author.

**Usage:** `/draw-article-figure posts/article-name.md <passage, section, or reference image>`

## Step 1: Read the post

- Resolve a bare slug to `posts/<slug>.md` and read the section the figure belongs to, plus the paragraphs around it.
- Write down in one sentence the single thing the figure should make visible. Every label and number on it must come from the post, or be marked illustrative.

## Step 2: Suggest three ASCII sketches

Before writing any SVG, show three ways to draw the figure as ASCII diagrams, and wait for the author to pick one. An ASCII sketch costs seconds to change; an SVG costs a render loop.

- Each option is a fenced code block of at most about 20 lines, with a bold name above it and one line below on what it makes clear and what it gives up.
- Make the three differ in form (for example a chart, a flow, a before/after), not just in labels.
- **The author gave a reference figure** (a screenshot from a paper or blog): option A recreates its layout faithfully: the same chart type, axes, series, annotation style and color mood. Change only what the author asks for, such as numbering that must match the post. A simplified redraw of a reference reads as a different figure. Options B and C may depart from it.
- When the figure maps to a list in the post, number its callouts to match the list. If an item cannot be drawn, say so in the legend or caption rather than skipping its number silently.
- Recommend one option, then stop. Do not start Step 3 until the author replies with a choice; if they ask for changes, redraw the ASCII first.

Once the author picks, draw that sketch as an SVG in the steps below, keeping its layout and labels.

## Step 3: Learn the constraints

The site shows post images with `w-full` (`.editorial-content img` in `src/styles/global.css`), so an image is stretched or shrunk to the column width. On desktop the column is about 792px; on a 390px phone it is about 342px.

| Setting | Value |
| --- | --- |
| `viewBox` width | `780`, so it renders at about 1:1 on desktop |
| Text | `18px` everywhere; badge numbers may be 15px. Body text is 17px, so smaller reads as fine print |
| Font | `"IBM Plex Sans", "Inter Tight", Helvetica, Arial, sans-serif`. An `<img>` cannot load the site's web fonts, so the fallback is what most readers see |
| Background | A full-size `<rect>`. An `<img>` cannot follow the site's theme toggle, so the figure carries its own background |
| Colors | Import nothing, but reuse the hex values in `src/components/art/style.ts` (`navy`, `darkNavy`, `softBlue`, `mut`, `gold`) and the brand Salmon `#FF8A69` and Day Blue `#4D75FE` |

- Keep text scarce: labels of a word or a few, since on a phone 18px shrinks to about 8px.
- Put shared styles in one `<style>` block and arrowheads in one `<marker>`, as `posts/images/planted-bugs-build-eval/eval-signs.svg` does.
- Give the root `role="img"` and an `aria-label` that states what the figure shows.
- Skip a title inside the figure unless the reference has one; the heading above it already names the idea.

## Step 4: Write and embed the figure

1. Save it as `posts/images/<slug>/<what-it-shows>.svg`, named after what it shows, not after the post.
2. Embed it where it belongs, with alt text that carries the same point, including any numbers:

   ```markdown
   ![Alt text stating what the figure shows](images/<slug>/<what-it-shows>.svg)
   ```

3. If it is adapted from someone else's figure, add an italic credit line under it: `*Adapted from Figure 1 in [Source title](url).*`

## Step 5: Check it in the site

```bash
node scripts/figure-preview.ts <slug> <what-it-shows>.svg <scratchpad dir>
```

It screenshots the figure inside the post at desktop and phone widths, in light and dark mode, and prints its drawn width and the body text size. It reuses the dev server on port 4321 if one is running, and starts one otherwise. Read every PNG and check:

- Every label is readable on the phone shot. If not, make it larger, shorten it, or remove it.
- Every arrow reaches its target, and nothing overlaps or is cut off.
- The figure looks intended against both the light and the dark page.
- It keeps the layout and labels of the ASCII sketch the author picked, and, if that sketch recreated a reference, it reads as the same figure side by side.

Fix what you find and run the script again. Stop after three rounds and show the author what is still wrong.

## Step 6: Show the author

Show the desktop screenshot, say in one sentence what the figure shows, and list anything you changed from the chosen sketch or the reference. Ask whether they want a label, a color, or the layout changed. Do not commit until they approve.
