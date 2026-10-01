// Capture a post's OG card (the dev-only og-card page) as public/og/og-<slug>.png.
// Run with the dev server up:
//   npm run capture-og -- <slug> [http://localhost:4321]
import { chromium } from "playwright";
import { BLOG_PATH } from "../src/lib/blog-path.ts";

const slug = process.argv[2] ?? "home";
const base = process.argv[3] ?? "http://localhost:4321";

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 2 });
await page.goto(`${base}${BLOG_PATH}/og-card/${slug}`, { waitUntil: "networkidle" });
await page.evaluate(() => document.fonts.ready);
await page.screenshot({ path: `public/og/og-${slug}.png`, clip: { x: 0, y: 0, width: 1200, height: 630 } });
await browser.close();
console.log(`captured public/og/og-${slug}.png`);
