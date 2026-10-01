import type { APIRoute } from "astro";
import { BLOG_PATH } from "../lib/blog-path";
import { getPosts } from "../lib/posts";

function escapeXml(value: string): string {
	return value
		.replace(/&/g, "&amp;")
		.replace(/</g, "&lt;")
		.replace(/>/g, "&gt;")
		.replace(/"/g, "&quot;");
}

export const GET: APIRoute = async ({ site }) => {
	const base = new URL(BLOG_PATH, site).href;
	const items = (await getPosts())
		.slice(0, 20)
		.map((post) => {
			const postUrl = `${base}/${post.slug}`;
			return `    <item>
      <title>${escapeXml(post.title)}</title>
      <link>${postUrl}</link>
      <guid isPermaLink="true">${postUrl}</guid>
      <pubDate>${post.date.toUTCString()}</pubDate>
      <description>${escapeXml(post.excerpt)}</description>
    </item>`;
		})
		.join("\n");

	return new Response(
		`<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>OpenTeams Engineering Blog</title>
    <link>${base}</link>
    <description>Benchmarks, systems deep dives, and hard-won lessons from OpenTeams engineers.</description>
${items}
  </channel>
</rss>`,
		{ headers: { "Content-Type": "application/rss+xml; charset=utf-8" } },
	);
};
