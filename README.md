# OpenTeams Engineering Blog

Static Astro site for the posts in
[engineering-blog](https://github.com/openteams-ai/engineering-blog), served
under one path set in `src/lib/blog-path.ts` (`BLOG_PATH`).

```bash
npm install
npm run dev          # http://localhost:4321<BLOG_PATH>
npm run build        # dist<BLOG_PATH>/
npm test             # unit tests
npm run test:e2e     # browser tests against the build
```

## Posts

```bash
npm run sync-posts -- ../engineering-blog
```

Copies `posts/` into `src/content/posts/`, and writes author profiles and
publication dates to `src/data/`.

For a new post, also add:

- its topic in `src/data/topics.ts`
- card art in `src/components/PostArt.astro`, listed in `BlogThumb.astro`
- a share image: `npm run capture-og -- <slug>` with the dev server running,
  then an entry in `src/data/og-images.json`

## Deploy

CI deploys the `openteams-engineering-blog` Cloudflare Worker: a preview
version per pull request, and `openteams.com<BLOG_PATH>` on merge to `main`.
It needs the `CLOUDFLARE_API_TOKEN` repo secret.
