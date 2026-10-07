// Posts that moved here from the main site keep their old address in their
// frontmatter (`wordpress_url`). That address answers with a permanent
// redirect to the post, so old links and search results keep working.
import { readdirSync, readFileSync } from "node:fs";
import { pageUrl } from "./blog-path.ts";

export interface Move {
	/** The old path on the site, without a trailing slash: `/my-post`. */
	from: string;
	/** The post's page in the blog. */
	to: string;
}

const field = (markdown: string, name: string): string | undefined => {
	const frontmatter = /^---\n([\s\S]*?)\n---/.exec(markdown)?.[1] ?? "";
	return new RegExp(`^${name}:\\s*["']?([^"'\\s]+)`, "m").exec(frontmatter)?.[1];
};

/** The move of every post that has an old address, given each post file's text. */
export function movedPosts(markdownFiles: string[]): Move[] {
	return markdownFiles.flatMap((markdown) => {
		const slug = field(markdown, "slug");
		const old = field(markdown, "wordpress_url");
		if (!slug || !old) return [];
		return [{ from: new URL(old).pathname.replace(/\/$/, ""), to: pageUrl(`/${slug}`) }];
	});
}

/** The moves of the posts in this repository. */
export function postMoves(directory = "posts"): Move[] {
	const files = readdirSync(directory).filter((name) => name.endsWith(".md"));
	return movedPosts(files.map((name) => readFileSync(`${directory}/${name}`, "utf8")));
}

/**
 * Cloudflare's `_redirects` file for the moves. An exact rule answers a
 * move's old address with or without the trailing slash, a wildcard rule
 * anything under it (a feed, an AMP copy). Query strings carry over.
 * Cloudflare wants the exact rules listed before the wildcard ones.
 */
export function redirectsFile(moves: Move[]): string {
	const exact = moves.map(({ from, to }) => `${from} ${to} 301\n`);
	const under = moves.map(({ from, to }) => `${from}/* ${to} 301\n`);
	return [...exact, ...under].join("");
}

/**
 * The Cloudflare route patterns that hand the old addresses to the blog.
 * Each is exact (plus what sits under it), so a main-site page that merely
 * starts with the same words is never taken over. A pattern cannot match a
 * query string, so `/my-post?x=1` without its slash still goes to the main
 * site, which adds the slash and lands on the second pattern.
 */
export function oldRoutes(host: string, moves: Move[]): string[] {
	return moves.flatMap(({ from }) => [`${host}${from}`, `${host}${from}/*`]);
}
