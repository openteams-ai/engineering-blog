// Screenshot one in-article figure where the post shows it, at desktop and
// phone widths in light and dark mode, so a new figure can be checked in
// place before it is pushed. Uses the dev server on port 4321 when one is
// running (Astro allows one per project), and starts its own otherwise.
//
//   node scripts/figure-preview.ts <slug> <figure file> [out-dir]
//   node scripts/figure-preview.ts planted-bugs-build-eval eval-signs.svg /tmp
import { spawn } from "node:child_process";
import { chromium } from "playwright";
import { pageUrl } from "../src/lib/blog-path.ts";

const [slug, file, outDir = "."] = process.argv.slice(2);
if (!slug || !file) throw new Error("usage: node scripts/figure-preview.ts <slug> <figure file> [out-dir]");

const PORT = 4321;
const url = `http://localhost:${PORT}${pageUrl(`/${slug}`)}`;
const running = await fetch(url).then(() => true, () => false);
const dev = running ? undefined : spawn("node_modules/.bin/astro", ["dev", "--port", String(PORT)], { stdio: "ignore" });

const views = [
	{ name: "desktop", width: 1280 },
	{ name: "phone", width: 390 },
];

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
	for (const scheme of ["light", "dark"] as const) {
		for (const view of views) {
			const page = await browser.newPage({ viewport: { width: view.width, height: 900 }, colorScheme: scheme });
			// The first visit can reload the page while Vite prepares dependencies.
			await page.goto(url);
			await page.waitForLoadState("networkidle");
			const res = await page.goto(url);
			if (res?.status() !== 200) throw new Error(`no post at ${url}`);
			const figure = page.locator(`.editorial-content img[src*="${encodeURIComponent(`/${file}`)}"]`);
			if ((await figure.count()) === 0) throw new Error(`the post has no image ending in "${file}"`);
			await figure.scrollIntoViewIfNeeded();
			// Raster images are lazy-loaded and converted on request, so wait until one has drawn.
			await figure.evaluate((img: HTMLImageElement) => img.decode());
			// The figure's drawn width and the body text size, to compare its text with the prose.
			const sizes = await figure.evaluate((img: HTMLImageElement) => {
				const p = document.querySelector(".editorial-content p");
				return { width: Math.round(img.getBoundingClientRect().width), body: p ? getComputedStyle(p).fontSize : "?" };
			});
			const out = `${outDir}/figure-${file.replace(/\.\w+$/, "")}-${view.name}-${scheme}.png`;
			await figure.screenshot({ path: out });
			console.log(`${out}  drawn ${sizes.width}px wide, body text ${sizes.body}`);
			await page.close();
		}
	}
} finally {
	await browser.close();
	dev?.kill();
}
