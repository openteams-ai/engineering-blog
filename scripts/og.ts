// Fill dist/ with every share card the build links to (dist<BLOG_PATH>/og-manifest.json).
// Card files are named by a fingerprint of their content, so a card the live
// site already serves is downloaded as is; only new or changed cards are
// rendered, by screenshotting the dev-only og-card pages. With nothing to
// render, no browser or dev server starts. A card that draws an author's
// name partly in a system font is not saved, and the run fails.
//
//   npm run build && npm run og
//   OG_LIVE=https://example.com npm run og     reuse cards from another origin
import { execFileSync } from "node:child_process";
import { copyFileSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname } from "node:path";
import authors from "../authors.json" with { type: "json" };
import { BLOG_PATH } from "../src/lib/blog-path.ts";
import { inSystemFonts } from "./system-fonts.ts";

const LIVE = process.env.OG_LIVE ?? "https://openteams.com";
const DIST = `dist${BLOG_PATH}`;
const manifestPath = `${DIST}/og-manifest.json`;
if (!existsSync(manifestPath)) throw new Error(`${manifestPath} missing: run npm run build first`);

const cards: { key: string; file: string }[] = JSON.parse(readFileSync(manifestPath, "utf8"));
const missing: typeof cards = [];
const broken: string[] = [];
let reused = 0;

await Promise.all(
	cards.map(async (card) => {
		const dest = DIST + card.file;
		if (existsSync(dest)) return void reused++;
		const res = await fetch(LIVE + BLOG_PATH + card.file).catch(() => null);
		if (res?.ok && res.headers.get("content-type")?.startsWith("image/png")) {
			mkdirSync(dirname(dest), { recursive: true });
			writeFileSync(dest, Buffer.from(await res.arrayBuffer()));
			reused++;
		} else {
			missing.push(card);
		}
	}),
);
console.log(`share cards: ${reused} reused, ${missing.length} to render`);

if (missing.length) {
	const { chromium } = await import("playwright");
	const browser = await chromium.launch().catch(() => {
		console.log("installing Chromium for rendering");
		execFileSync("npx", ["playwright", "install", ...(process.env.CI ? ["--with-deps"] : []), "chromium"], {
			stdio: "inherit",
		});
		return chromium.launch();
	});
	// The og-card pages exist only in dev, so render from a dev server.
	const { dev } = await import("astro");
	const server = await dev({ root: process.cwd(), logLevel: "error", server: { port: 0 } });
	try {
		const page = await browser.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 2 });
		for (const card of missing) {
			const started = performance.now();
			await page.goto(`http://localhost:${server.address.port}${BLOG_PATH}/og-card/${card.key}`, {
				waitUntil: "networkidle",
			});
			await page.evaluate(() => document.fonts.ready);
			const problems = await inSystemFonts(page, authors.map((a) => a.name));
			if (problems.length) {
				broken.push(...problems.map((p) => `  ${card.key}: ${p}`));
				continue;
			}
			mkdirSync(dirname(DIST + card.file), { recursive: true });
			await page.screenshot({ path: DIST + card.file, clip: { x: 0, y: 0, width: 1200, height: 630 } });
			console.log(`  rendered ${card.file} in ${((performance.now() - started) / 1000).toFixed(1)}s`);
		}
	} finally {
		await browser.close();
		await server.stop();
	}
}
if (broken.length) throw new Error(`share cards not saved:\n${broken.join("\n")}`);

// A stable name for the blog's card, for places that can't follow the
// fingerprint (the README banner).
const home = cards.find((c) => c.key === "home");
if (home) copyFileSync(DIST + home.file, `${DIST}/og/og-home.png`);
