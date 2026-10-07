import type { APIRoute } from "astro";
import { pageUrl } from "../lib/blog-path";
import { authorsOf, getPosts, topicsOf, type Post } from "../lib/posts";

/** When a page that lists posts last changed: when the newest of those posts did. */
const newest = (posts: Post[]): Date => new Date(Math.max(...posts.map((post) => post.changed.getTime())));

/**
 * Every page of the blog, for search engines: the index, posts, topics and
 * authors, each with the date it last changed.
 */
export const GET: APIRoute = async ({ site }) => {
	const posts = await getPosts();
	const pages = [
		{ path: pageUrl(), changed: newest(posts) },
		...posts.map((post) => ({ path: pageUrl(`/${post.slug}`), changed: post.changed })),
		...topicsOf(posts).map((topic) => ({
			path: pageUrl(`/tag/${topic.slug}`),
			changed: newest(posts.filter((post) => post.topic.slug === topic.slug)),
		})),
		...authorsOf(posts).map(({ author, posts: written }) => ({
			path: pageUrl(`/author/${author.slug}`),
			changed: newest(written),
		})),
	];
	const urls = pages
		.map(({ path, changed }) => `  <url><loc>${new URL(path, site).href}</loc><lastmod>${changed.toISOString()}</lastmod></url>`)
		.join("\n");

	return new Response(
		`<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls}
</urlset>
`,
		{ headers: { "Content-Type": "application/xml; charset=utf-8" } },
	);
};
