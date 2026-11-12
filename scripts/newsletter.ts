// Write one month's Engineering newsletter as HTML to paste into HubSpot.
//
//   npm run newsletter                       this month's issue, last month's posts
//   npm run newsletter -- 2026-11            the November issue (October's posts)
//   npm run newsletter -- 2026-11 a-slug b-slug   pick the posts yourself
//
// Each post's image is its art without the title (art-*.png next to its share
// card, made by `npm run og`), found through the live post's og:image. A post
// whose art isn't deployed yet gets its full share card, with a warning.
import { mkdirSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import authors from "../authors.json" with { type: "json" };
import { pageUrl } from "../src/lib/blog-path.ts";
import { type IssuePost, monthName, postsInMonth, previousMonth, renderIssue } from "../src/lib/newsletter.ts";
import { frontmatter } from "../src/lib/new-posts.ts";

const HOST = "https://openteams.com";
const TEMPLATE = "newsletter/template.html";
const OUT_DIR = "newsletter/out";

const [monthArg, ...slugArgs] = process.argv.slice(2);
const issueMonth = monthArg ?? new Date().toISOString().slice(0, 7);
if (!/^\d{4}-\d{2}$/.test(issueMonth)) throw new Error(`month must look like 2026-11, got "${issueMonth}"`);

const names = new Map(authors.map((a) => [a.slug, a.name]));
const posts = readdirSync("posts")
	.filter((f) => f.endsWith(".md"))
	.map((f) => frontmatter(readFileSync(`posts/${f}`, "utf8")))
	.map((data) => ({
		slug: String(data.slug),
		title: String(data.title ?? ""),
		summary: String(data.meta_description ?? ""),
		date: String(data.date ?? ""),
		authors: (Array.isArray(data.authors) ? data.authors.map(String) : []).map((s) => names.get(s) ?? s),
	}));

const chosen = slugArgs.length
	? slugArgs.map((slug) => posts.find((p) => p.slug === slug) ?? fail(`no post with slug "${slug}"`))
	: postsInMonth(posts, previousMonth(issueMonth));
if (!chosen.length) fail(`no posts published in ${monthName(previousMonth(issueMonth))}; pass slugs to pick posts`);

/** The post's art if it's live, else its share card, read from its og:image. */
async function imageFor(url: string, slug: string): Promise<string> {
	const html = await (await fetch(url)).text();
	const card = /<meta property="og:image" content="([^"]+)"/.exec(html)?.[1];
	if (!card) fail(`${url} has no og:image; is the post live?`);
	const art = card.replace("/og/og-", "/og/art-");
	const res = await fetch(art, { method: "HEAD" });
	if (res.ok) return art;
	console.log(`::warning::${slug}: art isn't deployed yet, using its share card (which repeats the title)`);
	return card;
}

const issuePosts: IssuePost[] = [];
for (const post of chosen) {
	const url = `${HOST}${pageUrl(`/${post.slug}`)}`;
	issuePosts.push({ url, title: post.title, summary: post.summary, authors: post.authors, image: await imageFor(url, post.slug) });
}

const html = renderIssue(readFileSync(TEMPLATE, "utf8"), issueMonth, issuePosts);
mkdirSync(OUT_DIR, { recursive: true });
const out = `${OUT_DIR}/${issueMonth}.html`;
writeFileSync(out, html);
console.log(`${monthName(issueMonth)} issue, ${issuePosts.length} posts:`);
for (const p of chosen) console.log(`  ${p.date.slice(0, 10)}  ${p.slug}`);
console.log(`Wrote ${out}`);

function fail(message: string): never {
	console.error(message);
	process.exit(1);
}
