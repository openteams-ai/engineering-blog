export interface Node {
	type: string;
	value?: string;
	url?: string;
	alt?: string;
	lang?: string;
	depth?: number;
	children?: Node[];
	data?: { hProperties?: Record<string, unknown> };
}

const textOf = (node: Node): string =>
	node.value ?? (node.children ?? []).map(textOf).join("");

/**
 * Clean a post's markdown tree in place before it renders. `postUrl` maps a
 * post slug to its URL, for links written as a bare slug (`](other-post)`).
 */
export function cleanupPost(tree: Node, title: string, postUrl: (slug: string) => string = (s) => s): void {
	const first = tree.children?.[0];
	if (first?.type === "heading" && first.depth === 1 && textOf(first).trim() === title.trim()) {
		tree.children!.shift();
	}
	tree.children = (tree.children ?? [])
		.filter((n) => n.type !== "thematicBreak")
		.map((n) => {
			if (n.type === "html") return htmlImage(n.value ?? "") ?? n;
			// A one-line <a><img></a> parses as a paragraph of inline HTML pieces.
			const parts = n.type === "paragraph" ? (n.children ?? []) : [];
			if (parts.length > 0 && parts.every((c) => c.type === "html" || (c.type === "text" && !c.value?.trim()))) {
				return htmlImage(parts.map((c) => c.value ?? "").join("")) ?? n;
			}
			return n;
		});
	walk(tree, postUrl);
}

// A standalone HTML <img> (optionally wrapped in a link) with a relative src
// becomes a markdown image, so Astro resolves and optimises the file like
// any other post image instead of passing a broken relative path through.
function htmlImage(html: string): Node | null {
	const m = /^\s*(?:<a\s[^>]*>\s*)?<img\s[^>]*?src="(images\/[^"]+)"[^>]*?>(?:\s*<\/a>)?\s*$/.exec(html);
	if (!m) return null;
	const alt = /\salt="([^"]*)"/.exec(html)?.[1] ?? "";
	return { type: "paragraph", children: [{ type: "image", url: m[1], alt }] };
}

function walk(node: Node, postUrl: (slug: string) => string): void {
	if (node.type === "code" && node.value) {
		node.value = node.value
			.split("\n")
			.filter((line) => !/^\s*#\|/.test(line))
			.join("\n");
	}
	if (node.type === "link" && node.url && /^[a-z0-9][a-z0-9-]*\/?$/.test(node.url)) {
		node.url = postUrl(node.url.replace(/\/$/, ""));
	}
	if (node.type === "table") {
		node.data = { ...node.data, hProperties: { ...node.data?.hProperties, tabIndex: 0 } };
	}
	node.children?.forEach((child) => walk(child, postUrl));
}
