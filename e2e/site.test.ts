import AxeBuilder from "@axe-core/playwright";
import { chromium, type BrowserContext, type BrowserContextOptions, type Page } from "playwright";
import { afterAll, describe, it } from "vitest";
import { BLOG_PATH } from "../src/lib/blog-path";
import { bylineNames } from "../src/lib/byline";
import { PORT } from "./server";

const ORIGIN = process.env.E2E_ORIGIN ?? `http://localhost:${PORT}`;

// Remote author photos get a 1x1 PNG and Google Fonts an empty stylesheet, so
// pages load without waiting on the internet. The mermaid CDN is let through
// because diagram pages need it.
const PIXEL = Buffer.from(
	"iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=",
	"base64",
);

/** Every page reachable from the index by same-site links, read from the HTML. */
async function crawl(): Promise<string[]> {
	const seen = new Set<string>([`${BLOG_PATH}/`]);
	const queue = [`${BLOG_PATH}/`];
	while (queue.length) {
		const html = await (await fetch(ORIGIN + queue.shift()!)).text();
		for (const [, href] of html.matchAll(/<a\s[^>]*href="([^"#]+)/g)) {
			const url = new URL(href, ORIGIN);
			if (url.origin !== ORIGIN || !url.pathname.startsWith(BLOG_PATH)) continue;
			if (/\.(xml|json|png|svg)$/.test(url.pathname)) continue;
			const path = url.pathname.endsWith("/") ? url.pathname : `${url.pathname}/`;
			if (!seen.has(path)) {
				seen.add(path);
				queue.push(path);
			}
		}
	}
	return [...seen].sort();
}

// The mermaid library is fetched from its CDN once per run and replayed from
// memory, so parallel diagram pages don't each wait on the network.
const cdnCache = new Map<string, Promise<{ status: number; headers: Record<string, string>; body: Buffer }>>();

async function newContext(options: BrowserContextOptions = {}): Promise<BrowserContext> {
	const context = await browser.newContext(options);
	// Each page records what it copies instead of using the system clipboard,
	// which every page in the run would share.
	await context.addInitScript(() => {
		Object.defineProperty(navigator, "clipboard", {
			value: { writeText: async (text: string) => void ((window as { copied?: string }).copied = text) },
		});
	});
	await context.route(/^https?:\/\//, async (route) => {
		const url = new URL(route.request().url());
		if (url.origin === ORIGIN) return route.continue();
		if (url.hostname === "cdn.jsdelivr.net") {
			if (!cdnCache.has(url.href)) {
				cdnCache.set(
					url.href,
					fetch(url).then(async (r) => ({
						status: r.status,
						headers: { "content-type": r.headers.get("content-type") ?? "text/javascript", "access-control-allow-origin": "*" },
						body: Buffer.from(await r.arrayBuffer()),
					})),
				);
			}
			return route.fulfill(await cdnCache.get(url.href)!);
		}
		if (url.hostname.endsWith("fonts.googleapis.com")) return route.fulfill({ contentType: "text/css", body: "" });
		if (route.request().resourceType() === "image") return route.fulfill({ contentType: "image/png", body: PIXEL });
		return route.fulfill({ body: "" });
	});
	return context;
}

/** Open a page in a fresh context and hand it to `fn`; always clean up. */
async function withPage<T>(fn: (page: Page) => Promise<T>, options?: BrowserContextOptions): Promise<T> {
	const context = await newContext(options);
	try {
		return await fn(await context.newPage());
	} finally {
		await context.close();
	}
}

/** Load a page once: lazy images forced in, diagrams given time to draw. */
async function open(page: Page, path: string): Promise<string[]> {
	const problems: string[] = [];
	page.on("console", (m) => m.type() === "error" && problems.push(`console: ${m.text()}`));
	page.on("pageerror", (e) => problems.push(`error: ${e.message}`));
	page.on("response", (r) => {
		const url = new URL(r.url());
		if (url.origin !== ORIGIN) return;
		if (!url.pathname.startsWith(BLOG_PATH)) problems.push(`outside ${BLOG_PATH}: ${url.pathname}`);
		if (r.status() >= 400) problems.push(`${r.status()} ${url.pathname}`);
	});
	await page.goto(ORIGIN + path, { waitUntil: "load" });
	await page.evaluate(async () => {
		for (const img of document.querySelectorAll("img")) img.loading = "eager";
		await Promise.all([...document.images].map((i) => i.decode().catch(() => {})));
	});
	if (await page.$("code.language-mermaid, .doodle-diagram")) {
		await page.waitForSelector(".doodle-diagram svg", { timeout: 20_000 });
	}
	return problems;
}

/**
 * Accessibility problems in the page as it is right now, at any severity:
 * WCAG 2 A/AA plus axe's best-practice rules, the set Lighthouse reports
 * (heading order, unique landmarks and the like).
 */
async function a11yProblems(page: Page): Promise<string[]> {
	const { violations } = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "best-practice"]).analyze();
	return violations.map((v) => `a11y ${v.id} (${v.nodes.length}): ${v.nodes[0]?.target.join(" ")}`);
}

/** Everything wrong with one page on desktop and on a phone, from one load. */
async function check(page: Page, path: string): Promise<string[]> {
	const problems = await open(page, path);
	const broken = await page.$$eval("img", (imgs) =>
		imgs.filter((i) => i.naturalWidth === 0).map((i) => i.getAttribute("src")),
	);
	problems.push(...broken.map((src) => `image did not load: ${src}`));

	// Link previews need a share image that exists. It is an absolute
	// production URL, so check the same path on the origin under test.
	const ogImage = await page.getAttribute('meta[property="og:image"]', "content");
	if (!ogImage) problems.push("no og:image");
	else if (!(await fetch(ORIGIN + new URL(ogImage).pathname)).ok) problems.push(`og:image does not load: ${ogImage}`);
	const author = path.match(/\/author\/([^/]+)/)?.[1];
	if (author && !new RegExp(`/og-author-${author}-[0-9a-f]{8}\\.png$`).test(ogImage ?? "")) {
		problems.push(`author page share image is not the author's own card: ${ogImage}`);
	}

	problems.push(...(await a11yProblems(page)));

	await page.setViewportSize({ width: 390, height: 844 });
	const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
	if (overflow > 0) problems.push(`scrolls sideways on a phone by ${overflow}px`);
	return problems;
}

const browser = await chromium.launch();
const pages = await crawl();
console.log(`testing ${pages.length} pages under ${ORIGIN}${BLOG_PATH}`);

afterAll(() => browser.close());

describe.concurrent("site", () => {
	it("links every post, topic page, author page and the index", ({ expect }) => {
		// index + 20 posts + 5 topics
		expect(pages.length).toBeGreaterThanOrEqual(26);
	});

	it("shows each search suggestion's author photo, name and date", async ({ expect }) => {
		const result = await withPage(async (page) => {
			await open(page, `${BLOG_PATH}/`);
			await page.click("[data-search-trigger]");
			const row = page.locator(".search-result").first();
			await row.waitFor();
			const photo = row.locator("img.sr-avatar");
			return {
				meta: await row.locator(".sr-crumb").innerText(),
				photoLoaded: await photo.evaluate((i: HTMLImageElement) => i.decode().then(() => i.naturalWidth > 0)),
				photoRadius: await photo.evaluate((i) => getComputedStyle(i).borderTopLeftRadius),
			};
		});
		expect(result.photoLoaded).toBe(true);
		expect(result.meta).toMatch(/\p{L}+ \p{L}+ · [A-Z][a-z]{2} \d{1,2}, \d{4}/u);
		expect(result.photoRadius).not.toBe("0px");
	});

	it("copies a code block's exact code with its copy button", async ({ expect }) => {
		const result = await withPage(async (page) => {
			await open(page, `${BLOG_PATH}/pixi-ubi-micro-containers/`);
			const block = page.locator(".editorial-content pre.astro-code").first();
			const button = page.locator("[data-copy-code]").first();
			await block.hover();
			await button.click();
			return {
				code: await block.evaluate((pre) => pre.textContent),
				copied: await page.evaluate(() => (window as { copied?: string }).copied),
				label: await button.getAttribute("aria-label"),
				buttons: await page.locator("[data-copy-code]").count(),
				blocks: await page.locator(".editorial-content pre.astro-code").count(),
			};
		});
		expect(result.copied).toBe(result.code);
		expect(result.label).toBe("Copied");
		expect(result.buttons).toBe(result.blocks);
	});

	it("shares a post on X, Hacker News, LinkedIn and Bluesky, and copies its link", async ({ expect }) => {
		const path = `${BLOG_PATH}/pixi-ubi-micro-containers/`;
		const result = await withPage(async (page) => {
			await open(page, path);
			const links = await page.$$eval("[data-share] a", (as) =>
				Object.fromEntries(as.map((a) => [a.getAttribute("aria-label"), (a as HTMLAnchorElement).href])),
			);
			const button = page.locator("[data-share-copy]");
			await button.click();
			return {
				links,
				title: await page.locator("article h1").innerText(),
				copied: await page.evaluate(() => (window as { copied?: string }).copied),
				label: await button.getAttribute("aria-label"),
			};
		});
		const url = `https://openteams.com${path}`;
		const u = encodeURIComponent(url);
		const t = encodeURIComponent(result.title);
		expect(result.links).toEqual({
			"Share on X (opens in a new tab)": `https://x.com/intent/post?text=${t}&url=${u}`,
			"Share on Hacker News (opens in a new tab)": `https://news.ycombinator.com/submitlink?u=${u}&t=${t}`,
			"Share on LinkedIn (opens in a new tab)": `https://www.linkedin.com/sharing/share-offsite/?url=${u}`,
			"Share on Bluesky (opens in a new tab)": `https://bsky.app/intent/compose?text=${encodeURIComponent(`${result.title} ${url}`)}`,
		});
		expect(result.copied).toBe(url);
		expect(result.label).toBe("Link copied");
	});

	// A post card: the link to the post, then the byline beside it.
	const CARD = "div:has(> a[href]):has(> div .post-byline)";

	it("names every author of a post on its index card", async ({ expect }) => {
		const cards = await withPage(async (page) => {
			await open(page, `${BLOG_PATH}/`);
			return page.$$eval(CARD, (cards) =>
				cards.map((card) => ({
					href: card.querySelector<HTMLAnchorElement>(":scope > a[href]")!.href,
					byline: card.querySelector(".post-byline")!.textContent!.trim().replace(/\s+/g, " "),
					photos: card.querySelectorAll(".post-byline-faces > *").length,
				})),
			);
		});
		const mismatches: string[] = [];
		for (const card of cards) {
			// Author links are in the server-rendered HTML; no browser needed.
			const html = await (await fetch(card.href)).text();
			const header = html.slice(html.indexOf("<header"), html.indexOf("</header>", html.indexOf("<article")));
			const names = [...header.matchAll(/href="[^"]*\/author\/[^"]*"[^>]*>[\s\S]*?font-semibold[^>]*>([^<]+)</g)].map(
				([, name]) => ({ name: name.trim() }),
			);
			if (card.byline !== bylineNames(names) || card.photos !== Math.max(names.length, 1)) {
				mismatches.push(`${card.href}: "${card.byline}" with ${card.photos} photos, page lists ${names.length}`);
			}
		}
		expect(cards.length).toBeGreaterThan(0);
		expect(mismatches).toEqual([]);
	});

	it("renders backtick code in a title as code on its card, post page and in search", async ({ expect }) => {
		const result = await withPage(async (page) => {
			await open(page, `${BLOG_PATH}/`);
			const titles = page.locator(`${CARD} :is(h2, h3)`);
			const rawBackticks = (await titles.allInnerTexts()).filter((t) => t.includes("`"));
			const card = page.locator(`${CARD}:has(.title-code)`).first();
			const code = await card.locator(".title-code").first().innerText();
			const href = await card.locator(":scope > a[href]").getAttribute("href");
			await page.click("[data-search-trigger]");
			await page.fill("[data-search-input]", code);
			const searchCode = await page.locator(".search-result .sr-title .title-code").first().innerText();
			await open(page, href!);
			return {
				rawBackticks,
				code,
				searchCode,
				pageCode: await page.locator("article h1 .title-code").first().innerText(),
				tabTitle: await page.title(),
			};
		});
		expect(result.rawBackticks).toEqual([]);
		expect(result.pageCode).toBe(result.code);
		expect(result.searchCode.toLowerCase()).toContain(result.code.toLowerCase());
		expect(result.tabTitle).toContain(result.code);
		expect(result.tabTitle).not.toContain("`");
	});

	it("opens a diagram full screen on click or Enter, and closes it on Escape", async ({ expect }) => {
		let diagramPage: string | undefined;
		for (const path of pages) {
			if ((await (await fetch(ORIGIN + path)).text()).includes("language-mermaid")) {
				diagramPage = path;
				break;
			}
		}
		expect(diagramPage).toBeDefined();
		const result = await withPage(async (page) => {
			await open(page, diagramPage!);
			// The page wires up click and Enter only after every diagram has
			// rendered, and marks each one role="button" when it does; clicking
			// before that opens nothing.
			const diagram = page.locator('.doodle-wrap[role="button"]').first();
			await diagram.waitFor();
			const inline = (await diagram.locator("svg").first().boundingBox())!;
			const dialog = page.locator("dialog.diagram-zoom");
			await diagram.click();
			await dialog.locator("svg").first().waitFor();
			const zoomed = (await dialog.locator("svg").first().boundingBox())!;
			const openAfterClick = await dialog.evaluate((d: HTMLDialogElement) => d.open);
			const zoomedVisible = await dialog.locator("svg").first().isVisible();
			const zoomedVisibility = await dialog.locator("svg").first().evaluate((s) => getComputedStyle(s).visibility);
			await page.keyboard.press("Escape");
			const openAfterEscape = await dialog.evaluate((d: HTMLDialogElement) => d.open);
			await diagram.focus();
			await page.keyboard.press("Enter");
			const openAfterEnter = await dialog.evaluate((d: HTMLDialogElement) => d.open);
			return { inline, zoomed, openAfterClick, zoomedVisible, zoomedVisibility, openAfterEscape, openAfterEnter };
		});
		expect(result.openAfterClick).toBe(true);
		expect(result.zoomedVisible).toBe(true);
		expect(result.zoomedVisibility).toBe("visible");
		expect(result.zoomed.width * result.zoomed.height).toBeGreaterThan(result.inline.width * result.inline.height);
		expect(result.openAfterEscape).toBe(false);
		expect(result.openAfterEnter).toBe(true);
	});
});

describe.concurrent("pages", () => {
	for (const path of pages) {
		it(`${path} loads cleanly, fits a phone, has no a11y issues`, async ({ expect }) => {
			expect(await withPage((page) => check(page, path))).toEqual([]);
		});
	}
});

// The page scans above see each page as it first loads. These open each
// interactive state, scan it again, and check its keyboard behaviour.
describe.concurrent("interactions", () => {
	/** A post with a diagram, found from the HTML so no slug is hard-coded. */
	async function diagramPage(): Promise<string> {
		for (const path of pages) {
			if ((await (await fetch(ORIGIN + path)).text()).includes("language-mermaid")) return path;
		}
		throw new Error("no post has a diagram");
	}

	it("search: open with results passes axe, Esc closes it and focus returns to the trigger", async ({ expect }) => {
		const result = await withPage(async (page) => {
			await open(page, `${BLOG_PATH}/`);
			await page.focus("[data-search-trigger]");
			await page.keyboard.press("Enter");
			const focusedInput = await page.evaluate(() => document.activeElement?.matches("[data-search-input]"));
			await page.keyboard.type("agent");
			await page.locator(".search-result").first().waitFor();
			const problems = await a11yProblems(page);
			await page.keyboard.press("Escape");
			return {
				focusedInput,
				problems,
				closed: await page.locator("#search-modal").isHidden(),
				focusBack: await page.evaluate(() => document.activeElement?.matches("[data-search-trigger]")),
			};
		});
		expect(result.problems).toEqual([]);
		expect(result.focusedInput).toBe(true);
		expect(result.closed).toBe(true);
		expect(result.focusBack).toBe(true);
	});

	it("diagram: full screen view passes axe, Esc closes it and focus returns to the diagram", async ({ expect }) => {
		const path = await diagramPage();
		const result = await withPage(async (page) => {
			await open(page, path);
			const diagram = page.locator(".doodle-wrap").first();
			await diagram.focus();
			await page.keyboard.press("Enter");
			const problems = await a11yProblems(page);
			await page.keyboard.press("Escape");
			return {
				problems,
				focusBack: await diagram.evaluate((d) => d === document.activeElement),
			};
		});
		expect(result.problems).toEqual([]);
		expect(result.focusBack).toBe(true);
	});

	it("mobile menu: opening it updates aria-expanded and the open menu passes axe", async ({ expect }) => {
		const result = await withPage(
			async (page) => {
				await open(page, `${BLOG_PATH}/`);
				const toggle = page.locator("#ot-menu-toggle");
				await toggle.focus();
				await page.keyboard.press("Enter");
				return {
					expanded: await toggle.getAttribute("aria-expanded"),
					visible: await page.locator("#ot-mobile-menu").isVisible(),
					problems: await a11yProblems(page),
				};
			},
			{ viewport: { width: 390, height: 844 } },
		);
		expect(result.expanded).toBe("true");
		expect(result.visible).toBe(true);
		expect(result.problems).toEqual([]);
	});

	it("header dropdowns: keyboard focus opens each one, Tab reaches its links, and it passes axe", async ({ expect }) => {
		const result = await withPage(
			async (page) => {
				await open(page, `${BLOG_PATH}/`);
				const menus = page.locator(".ot-header nav > ul > li");
				const failures: string[] = [];
				for (let i = 0; i < (await menus.count()); i++) {
					const menu = menus.nth(i);
					const label = (await menu.locator("button").innerText()).trim();
					await menu.locator("button").focus();
					await page.keyboard.press("Tab");
					const inMenu = await menu.evaluate((m) => m.contains(document.activeElement) && document.activeElement?.tagName === "A");
					const linkVisible = await page.evaluate(() => !!(document.activeElement as HTMLElement | null)?.checkVisibility?.());
					if (!inMenu || !linkVisible) failures.push(`${label}: Tab did not reach a visible link`);
					// The panel fades in; scan it once fully opaque, not mid-fade.
					await menu.locator(".group-focus-within\\:visible").first().evaluate(
						(panel) => new Promise((done) => {
							const check = () => (getComputedStyle(panel).opacity === "1" ? done(null) : requestAnimationFrame(check));
							check();
						}),
					);
					failures.push(...(await a11yProblems(page)).map((p) => `${label}: ${p}`));
				}
				return failures;
			},
			{ viewport: { width: 1440, height: 900 } },
		);
		expect(result).toEqual([]);
	});

	it("dark mode: the index, a diagram post and open search pass axe", async ({ expect }) => {
		const path = await diagramPage();
		const result = await withPage(
			async (page) => {
				const problems: string[] = [];
				await open(page, `${BLOG_PATH}/`);
				problems.push(...(await a11yProblems(page)).map((p) => `index: ${p}`));
				await page.click("[data-search-trigger]");
				await page.locator(".search-result").first().waitFor();
				problems.push(...(await a11yProblems(page)).map((p) => `search: ${p}`));
				await open(page, path);
				problems.push(...(await a11yProblems(page)).map((p) => `${path}: ${p}`));
				return problems;
			},
			{ colorScheme: "dark" },
		);
		expect(result).toEqual([]);
	});
});

describe.concurrent("table of contents", () => {
	/** A post long enough to get a table of contents (two or more section headings). */
	async function tocPage(): Promise<string> {
		for (const path of pages) {
			const html = await (await fetch(ORIGIN + path)).text();
			if (html.includes('id="toc"') && (html.match(/<h2 id="/g) ?? []).length >= 2) return path;
		}
		throw new Error("no post has a table of contents");
	}

	it("collapses to give the article the full width, stays collapsed on reload, and opens again", async ({ expect }) => {
		const path = await tocPage();
		const result = await withPage(
			async (page) => {
				await open(page, path);
				const content = page.locator(".editorial-content");
				const toc = page.locator("#toc");
				const before = (await content.boundingBox())!.width;
				await page.getByRole("button", { name: "Hide table of contents" }).click();
				const collapsed = { tocVisible: await toc.isVisible(), width: (await content.boundingBox())!.width };
				await open(page, path);
				const afterReload = { tocVisible: await toc.isVisible(), width: (await content.boundingBox())!.width };
				const show = page.getByRole("button", { name: "Show table of contents" });
				const showExpanded = await show.getAttribute("aria-expanded");
				const problems = await a11yProblems(page);
				await show.click();
				const reopened = { tocVisible: await toc.isVisible(), width: (await content.boundingBox())!.width };
				return { before, collapsed, afterReload, showExpanded, problems, reopened };
			},
			{ viewport: { width: 1440, height: 900 } },
		);
		expect(result.collapsed.tocVisible).toBe(false);
		expect(result.collapsed.width).toBeGreaterThan(result.before + 200);
		expect(result.afterReload).toEqual(result.collapsed);
		expect(result.showExpanded).toBe("false");
		expect(result.problems).toEqual([]);
		expect(result.reopened.tocVisible).toBe(true);
		expect(result.reopened.width).toBe(result.before);
	});
});
