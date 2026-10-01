# OpenTeams Engineering Blog

```bash
npm install
npm run dev          # http://localhost:4321/sandbox-4af53e-engineering-blog
npm run build
npm test             # unit tests
npm run test:e2e     # browser tests against the build
```

## New post

Add `src/content/posts/<name>.md` with `title`, `slug`, `date`, `authors`,
`categories: [Engineering]` and `meta_description` in the frontmatter, and
images under `src/content/posts/images/`. Authors are in
`src/data/authors.json`.

Then add:

- its topic in `src/data/topics.ts`
- card art in `src/components/PostArt.astro`, listed in `BlogThumb.astro`
- a share image in `public/og/og-<slug>.png`, listed in `src/data/og-images.json`

## Deploy

Merging to `main` deploys to openteams.com; pull requests get a preview link.
