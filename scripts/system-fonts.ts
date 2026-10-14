// Text drawn partly in a system font. A web font loads only the subsets set
// in src/lib/fonts.ts, so a letter outside them (the "ł" in Michał) is drawn
// in whatever font the machine has. Chromium reports the font it used for
// each glyph, so this needs a Chromium page.
import type { Page } from "playwright";

/** One line per element whose text contains one of `texts` and is drawn partly in a system font. */
export async function inSystemFonts(page: Page, texts: string[]): Promise<string[]> {
	await page.evaluate(async (texts) => {
		const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
		while (walker.nextNode()) {
			const text = walker.currentNode.textContent!;
			const parent = walker.currentNode.parentElement;
			if (parent && texts.some((t) => text.includes(t))) {
				const tag = [parent.localName, parent.classList[0]].filter(Boolean).join(".");
				parent.dataset.fontCheck = `"${text.trim().replace(/\s+/g, " ")}" in ${tag}`;
			}
		}
		// Lay the page out, so the fonts it needs start loading, and wait for them.
		void document.body.offsetHeight;
		await document.fonts.ready;
	}, texts);
	const cdp = await page.context().newCDPSession(page);
	try {
		await cdp.send("DOM.enable");
		await cdp.send("CSS.enable");
		const { root } = await cdp.send("DOM.getDocument", { depth: 0 });
		const { nodeIds } = await cdp.send("DOM.querySelectorAll", { nodeId: root.nodeId, selector: "[data-font-check]" });
		const problems: string[] = [];
		for (const nodeId of nodeIds) {
			const { fonts } = await cdp.send("CSS.getPlatformFontsForNode", { nodeId });
			const system = fonts.filter((f) => !f.isCustomFont);
			if (!system.length) continue;
			const { attributes } = await cdp.send("DOM.getAttributes", { nodeId });
			const where = attributes[attributes.indexOf("data-font-check") + 1];
			problems.push(`${where} drawn partly in ${system.map((f) => f.familyName).join(", ")}`);
		}
		return problems;
	} finally {
		await cdp.detach();
	}
}
