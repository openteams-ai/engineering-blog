// What Slack is told when a post goes live: the same three fields the old
// WordPress publish step sent, so the Slack workflow behind
// SLACK_PUBLISH_WEBHOOK keeps working unchanged.
import { parse } from "yaml";
import { pageUrl } from "./blog-path.ts";
import { plainTitle } from "./title.ts";

const HOST = "https://openteams.com";

export interface Announcement {
	post_title: string;
	post_url: string;
	author: string;
}

interface AuthorName {
	slug: string;
	name: string;
}

export function frontmatter(markdown: string): Record<string, unknown> {
	const block = /^---\n([\s\S]*?)\n---/.exec(markdown)?.[1];
	return block ? (parse(block) ?? {}) : {};
}

/** The announcement for one post file's text. Authors are named as on the site. */
export function announcement(markdown: string, authors: AuthorName[]): Announcement {
	const data = frontmatter(markdown);
	const names = new Map(authors.map((a) => [a.slug, a.name]));
	const slugs = Array.isArray(data.authors) ? data.authors.map(String) : [];
	return {
		post_title: plainTitle(String(data.title ?? "")),
		post_url: `${HOST}${pageUrl(`/${data.slug}`)}`,
		author: slugs.map((s) => names.get(s) ?? s).join(", "),
	};
}
