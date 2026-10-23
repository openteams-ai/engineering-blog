// Finds blog posts featured in PyCoder's Weekly since a date, by reading
// pycoders.com. If the site can't be read, it warns and returns nothing: the
// traffic numbers still work, with PyCoder's readers left under Direct.
import { type Feature, featuredSlugs, parseIssueList } from "../src/lib/pycoders.ts";

const SITE = "https://pycoders.com";

async function page(path: string): Promise<string> {
	const res = await fetch(`${SITE}${path}`, { signal: AbortSignal.timeout(20_000) });
	if (!res.ok) throw new Error(`${SITE}${path} answered ${res.status}`);
	return res.text();
}

export async function pycodersFeatures(posts: { slug: string; title: string }[], since: string): Promise<Feature[]> {
	try {
		const issues = parseIssueList(await page("/issues")).filter((i) => i.date >= since);
		const features: Feature[] = [];
		for (const issue of issues) {
			for (const slug of featuredSlugs(await page(`/issues/${issue.number}`), posts)) features.push({ ...issue, slug });
		}
		return features;
	} catch (err) {
		console.log(`::warning::Could not read PyCoder's Weekly, so its readers stay under Direct: ${err}`);
		return [];
	}
}

/** The source name the traffic report gives visits credited to an issue. */
export const pycodersSource = (issue: number) => `pycoders.com (estimated, #${issue})`;
