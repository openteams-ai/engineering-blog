// Finds blog posts featured in PyCoder's Weekly since a date, by reading
// pycoders.com. If the site can't be read, it warns and returns nothing: the
// traffic numbers still work, with PyCoder's readers left under Direct.
import { blogSlug, type Feature, featuredSlugs, openteamsLinks, parseIssueList } from "../src/lib/pycoders.ts";

const SITE = "https://pycoders.com";

async function page(path: string): Promise<string> {
	const res = await fetch(`${SITE}${path}`, { signal: AbortSignal.timeout(20_000) });
	if (!res.ok) throw new Error(`${SITE}${path} answered ${res.status}`);
	return res.text();
}

/** Where a pycoders.com/link redirect goes, read without following it. */
async function redirectTarget(link: string): Promise<string> {
	const res = await fetch(link, { method: "HEAD", redirect: "manual", signal: AbortSignal.timeout(20_000) });
	return res.headers.get("location") ?? "";
}

/** Posts an issue features: by full title, and by following its openteams.com links. */
async function issueSlugs(issueHtml: string, posts: { slug: string; title: string }[]): Promise<string[]> {
	const known = new Set(posts.map((p) => p.slug));
	const slugs = new Set(featuredSlugs(issueHtml, posts));
	for (const link of openteamsLinks(issueHtml)) {
		const slug = blogSlug(await redirectTarget(link));
		if (slug && known.has(slug)) slugs.add(slug);
	}
	return [...slugs];
}

export async function pycodersFeatures(posts: { slug: string; title: string }[], since: string): Promise<Feature[]> {
	try {
		const issues = parseIssueList(await page("/issues")).filter((i) => i.date >= since);
		const features: Feature[] = [];
		for (const issue of issues) {
			for (const slug of await issueSlugs(await page(`/issues/${issue.number}`), posts)) features.push({ ...issue, slug });
		}
		return features;
	} catch (err) {
		console.log(`::warning::Could not read PyCoder's Weekly, so its readers stay under Direct: ${err}`);
		return [];
	}
}

/** The source name the traffic report gives visits credited to an issue. */
export const pycodersSource = (issue: number) => `pycoders.com (estimated, #${issue})`;
