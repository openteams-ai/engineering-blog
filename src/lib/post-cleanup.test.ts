import { describe, expect, it } from "vitest";
import { cleanupPost, type Node } from "./post-cleanup";

const text = (value: string) => ({ type: "text", value });
const heading = (depth: number, value: string) => ({ type: "heading", depth, children: [text(value)] });
const para = (value: string) => ({ type: "paragraph", children: [text(value)] });
const root = (...children: Node[]): Node => ({ type: "root", children });

describe("cleanupPost", () => {
	it("drops a leading heading that repeats the post title", () => {
		const tree = root(heading(1, "My Post"), para("Intro."));
		cleanupPost(tree, "My Post");
		expect(tree).toEqual(root(para("Intro.")));
	});

	it("drops horizontal rules", () => {
		const tree = root(para("Before."), { type: "thematicBreak" }, para("After."));
		cleanupPost(tree, "T");
		expect(tree).toEqual(root(para("Before."), para("After.")));
	});

	it("strips #| directive lines from code blocks", () => {
		const tree = root({ type: "code", lang: "dockerfile", value: "#| highlight: 4\nFROM ubi\n# a comment" });
		cleanupPost(tree, "T");
		expect(tree).toEqual(root({ type: "code", lang: "dockerfile", value: "FROM ubi\n# a comment" }));
	});

	it("turns an HTML img with a relative src, linked or not, into a markdown image", () => {
		const linked = '<a href="images/p/plot.png"><img src="images/p/plot.png" alt="A plot"></a>';
		const tree = root({ type: "html", value: linked }, { type: "html", value: '<img src="https://example.com/a.png">' });
		cleanupPost(tree, "T");
		expect(tree).toEqual(
			root(
				{ type: "paragraph", children: [{ type: "image", url: "images/p/plot.png", alt: "A plot" }] },
				{ type: "html", value: '<img src="https://example.com/a.png">' },
			),
		);
	});

	it("converts a linked img that markdown parsed as a paragraph of inline HTML", () => {
		const html = (value: string) => ({ type: "html", value });
		const tree = root({
			type: "paragraph",
			children: [html('<a href="images/p/plot.png">'), html('<img src="images/p/plot.png" alt="A plot">'), html("</a>")],
		});
		cleanupPost(tree, "T");
		expect(tree).toEqual(
			root({ type: "paragraph", children: [{ type: "image", url: "images/p/plot.png", alt: "A plot" }] }),
		);
	});

	it("points bare-slug links at that post's URL and leaves other links alone", () => {
		const link = (url: string): Node => ({ type: "link", url, children: [text("x")] });
		const tree = root({
			type: "paragraph",
			children: [link("other-post"), link("https://example.com/a"), link("#section"), link("images/p/a.png")],
		});
		cleanupPost(tree, "T", (slug) => `/blog/${slug}`);
		expect(tree).toEqual(
			root({
				type: "paragraph",
				children: [link("/blog/other-post"), link("https://example.com/a"), link("#section"), link("images/p/a.png")],
			}),
		);
	});

	it("makes tables keyboard-focusable, since wide ones scroll in their own box", () => {
		const tree = root({ type: "table", children: [] });
		cleanupPost(tree, "T");
		expect(tree).toEqual(root({ type: "table", children: [], data: { hProperties: { tabIndex: 0 } } }));
	});
});
