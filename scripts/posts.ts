// The blog's posts as the traffic scripts need them, read from posts/.
import { readdirSync, readFileSync } from "node:fs";
import authors from "../authors.json" with { type: "json" };
import { frontmatter } from "../src/lib/new-posts.ts";
import { plainTitle } from "../src/lib/title.ts";

export interface Post {
	slug: string;
	title: string;
	authors: string[];
	date: string;
	topic: string;
}

export function readPosts(): Post[] {
	const names = new Map(authors.map((a) => [a.slug, a.name]));
	return readdirSync("posts")
		.filter((f) => f.endsWith(".md"))
		.map((f) => frontmatter(readFileSync(`posts/${f}`, "utf8")))
		.map((data) => ({
			slug: String(data.slug),
			title: plainTitle(String(data.title ?? "")),
			authors: (Array.isArray(data.authors) ? data.authors.map(String) : []).map((s) => names.get(s) ?? s),
			date: String(data.date ?? "").slice(0, 10),
			topic: String(data.topic ?? ""),
		}));
}
