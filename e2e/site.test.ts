import AxeBuilder from "@axe-core/playwright";
import { chromium, type Browser, type Page } from "playwright";
import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { BLOG_PATH } from "../src/lib/blog-path";
import { PORT } from "./server";

const ORIGIN = process.env.E2E_ORIGIN ?? `http://localhost:${PORT}`;
let browser: Browser;
let pages: string[] = [];

/** Every page reachable from the index by same-site links. */
async function crawl(page: Page): Promise<string[]> {
	const seen = new Set<string>([`${BLOG_PATH}/`]);
	const queue = [`${BLOG_PATH}/`];
	while (queue.length) {
		const path = queue.shift()!;
		await page.goto(ORIGIN + path);
		const links = await page.$$eval("a[href]", (as) => as.map((a) => (a as HTMLAnchorElement).href));
		for (const href of links) {
			const url = new URL(href);
			if (url.origin !== ORIGIN || !url.pathname.startsWith(BLOG_PATH)) continue;
			if (/\.(xml|json|png|svg)$/.test(url.pathname)) continue;
			const p = url.pathname.endsWith("/") ? url.pathname : `${url.pathname}/`;
			if (!seen.has(p)) {
				seen.add(p);
				queue.push(p);
			}
		}
	}
	return [...seen].sort();
}

/** Load a page fully: lazy images forced in, diagrams given time to draw. */
async function open(page: Page, path: string) {
	const problems: string[] = [];
	page.on("console", (m) => m.type() === "error" && problems.push(`console: ${m.text()}`));
	page.on("pageerror", (e) => problems.push(`error: ${e.message}`));
	page.on("response", (r) => {
		const url = new URL(r.url());
		if (url.origin === ORIGIN && !url.pathname.startsWith(BLOG_PATH)) problems.push(`outside ${BLOG_PATH}: ${url.pathname}`);
		if (r.status() >= 400) problems.push(`${r.status()} ${r.url()}`);
	});
	await page.goto(ORIGIN + path, { waitUntil: "networkidle" });
	await page.evaluate(async () => {
		for (const img of document.querySelectorAll("img")) img.loading = "eager";
		await Promise.all([...document.images].map((i) => i.decode().catch(() => {})));
	});
	if (await page.$("code.language-mermaid, .doodle-diagram")) {
		await page.waitForSelector(".doodle-diagram svg", { timeout: 30_000 });
	}
	return problems;
}

beforeAll(async () => {
	browser = await chromium.launch();
	const page = await browser.newPage();
	pages = await crawl(page);
	await page.close();
});

afterAll(() => browser?.close());

describe("built site", () => {
	it("links every post, topic page and the index", () => {
		// index + 18 posts + 4 topics
		expect(pages.length).toBeGreaterThanOrEqual(23);
	});

	it("loads every page with no errors, no broken files and nothing outside BLOG_PATH", async () => {
		const failures: string[] = [];
		for (const path of pages) {
			const page = await browser.newPage();
			const problems = await open(page, path);
			const broken = await page.$$eval("img", (imgs) =>
				imgs.filter((i) => i.naturalWidth === 0).map((i) => i.getAttribute("src")),
			);
			problems.push(...broken.map((src) => `image did not load: ${src}`));
			failures.push(...problems.map((p) => `${path}: ${p}`));
			await page.close();
		}
		expect(failures).toEqual([]);
	});

	it("does not scroll sideways on a phone", async () => {
		const wide: string[] = [];
		for (const path of pages) {
			const page = await browser.newPage({ viewport: { width: 390, height: 844 } });
			await open(page, path);
			const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
			if (overflow > 0) wide.push(`${path}: ${overflow}px`);
			await page.close();
		}
		expect(wide).toEqual([]);
	});

	it("has no serious accessibility problems", async () => {
		const found: string[] = [];
		for (const path of pages) {
			const context = await browser.newContext();
			const page = await context.newPage();
			await open(page, path);
			const { violations } = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa"]).analyze();
			for (const v of violations.filter((v) => v.impact === "serious" || v.impact === "critical")) {
				found.push(`${path}: ${v.id} (${v.nodes.length})`);
			}
			await context.close();
		}
		expect(found).toEqual([]);
	});
});
