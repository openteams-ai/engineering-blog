import type { APIRoute } from "astro";
import { blogUrl } from "../lib/blog-path";
import { getPosts } from "../lib/posts";
import { plainText } from "../lib/plain-text";

/** Fuse.js index for the command-palette search (same shape as Darby's index.json). */
export const GET: APIRoute = async () => {
	const items = (await getPosts()).map((p) => ({
		title: p.title,
		section: p.topic?.label ?? "Engineering",
		url: blogUrl(`/${p.slug}`),
		content: plainText(p.entry.body ?? ""),
	}));
	return new Response(JSON.stringify(items), {
		headers: { "Content-Type": "application/json; charset=utf-8" },
	});
};
