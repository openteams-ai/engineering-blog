import type { APIRoute } from "astro";
import { pageUrl } from "../lib/blog-path";
import { bylineNames } from "../lib/byline";
import { shortDate } from "../lib/dates";
import { getPosts } from "../lib/posts";
import { plainText } from "../lib/plain-text";

/** Fuse.js index for the command-palette search (same shape as Darby's index.json). */
export const GET: APIRoute = async () => {
	const items = (await getPosts()).map((p) => ({
		title: p.title,
		titleParts: p.titleParts,
		section: p.topic.label,
		byline: bylineNames(p.authors),
		faces: p.authors.map((a) => ({ name: a.name, src: a.avatarUrl })),
		date: shortDate(p.date),
		url: pageUrl(`/${p.slug}`),
		content: plainText(p.entry.body ?? ""),
	}));
	return new Response(JSON.stringify(items), {
		headers: { "Content-Type": "application/json; charset=utf-8" },
	});
};
