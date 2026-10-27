// Reads PyCoder's Weekly pages to find issues that featured a blog post.
// PyCoder's sends clicks through its own redirect without UTM tags, so most
// of its readers arrive as Direct in GA4. Knowing when a post was featured
// lets the traffic report credit those visits to the newsletter.

export interface Issue {
	number: number;
	/** YYYY-MM-DD, the day the issue was sent. */
	date: string;
}

export interface Feature extends Issue {
	slug: string;
}

/** Issues listed on pycoders.com/issues, newest first. */
export function parseIssueList(html: string): Issue[] {
	const issues: Issue[] = [];
	for (const m of html.matchAll(/href="\/issues\/(\d+)"[\s\S]*?<em>\((\d{4}-\d{2}-\d{2})\)<\/em>/g)) {
		issues.push({ number: Number(m[1]), date: m[2] });
	}
	return issues;
}

/**
 * A title reduced to lowercase letters and digits, so "OpenTeams&rsquo;"
 * in a PyCoder's page matches "OpenTeams'" in a post's frontmatter.
 */
export function titleKey(text: string): string {
	return text
		.replace(/&[a-z]+;|&#\d+;/gi, "")
		.toLowerCase()
		.replace(/[^a-z0-9]/g, "");
}

/** Slugs of the posts whose title appears in an issue's page. */
export function featuredSlugs(issueHtml: string, posts: { slug: string; title: string }[]): string[] {
	const page = titleKey(issueHtml);
	return posts.filter((p) => titleKey(p.title).length > 10 && page.includes(titleKey(p.title))).map((p) => p.slug);
}
