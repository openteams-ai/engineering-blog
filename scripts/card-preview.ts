// Screenshot one post's card art at every size the site shows it, so new art
// can be checked before it is pushed. Starts `astro dev` for the run.
//
//   node scripts/card-preview.ts <slug> [out.png]
import { spawn } from "node:child_process";
import { chromium } from "playwright";
import { pageUrl } from "../src/lib/blog-path.ts";

const [slug, out = `card-preview-${slug}.png`] = process.argv.slice(2);
if (!slug) throw new Error("usage: node scripts/card-preview.ts <slug> [out.png]");

const PORT = 4398;
const url = `http://localhost:${PORT}${pageUrl(`/card-preview/${slug}`)}`;
const dev = spawn("node_modules/.bin/astro", ["dev", "--port", String(PORT)], { stdio: "ignore" });

async function waitForServer(): Promise<void> {
	for (let i = 0; i < 60; i++) {
		try {
			await fetch(url);
			return;
		} catch {
			await new Promise((r) => setTimeout(r, 500));
		}
	}
	throw new Error(`astro dev did not start on port ${PORT}`);
}

const browser = await chromium.launch();
try {
	await waitForServer();
	const page = await browser.newPage({ viewport: { width: 1000, height: 800 } });
	// The first visit can reload the page while Vite prepares dependencies.
	await page.goto(url);
	await page.waitForLoadState("networkidle");
	const res = await page.goto(url);
	if (res?.status() !== 200) throw new Error(`no card art for "${slug}": add src/components/art/${slug}.astro`);
	await page.evaluate(() => document.fonts.ready);
	await page.locator("#cards").screenshot({ path: out });
	console.log(`Saved ${out}`);
} finally {
	await browser.close();
	dev.kill();
}
