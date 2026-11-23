// Fills the Engineering newsletter template (newsletter/template.html) with
// one month's posts. Pure: scripts/newsletter.ts reads the files and the
// live site, this only turns that data into HTML.
import { titleParts } from "./title.ts";

export interface IssuePost {
	url: string;
	/** As written in frontmatter, with backticks around code. */
	title: string;
	summary: string;
	authors: string[];
	image: string;
}

/** The tinted section behind each post, taking turns: Day Blue, then Orange (10% tints). */
const BACKGROUNDS = ["#EDF1FF", "#FFF3F0"];
const MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];

const escapeHtml = (text: string) =>
	text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

/** "2026-11" → "November 2026". */
export function monthName(month: string): string {
	const [year, m] = month.split("-").map(Number);
	return `${MONTHS[m - 1]} ${year}`;
}

/** The month before "YYYY-MM", as "YYYY-MM". */
export function previousMonth(month: string): string {
	const [year, m] = month.split("-").map(Number);
	return m === 1 ? `${year - 1}-12` : `${year}-${String(m - 1).padStart(2, "0")}`;
}

/** Posts whose `date` (YYYY-MM-DD...) falls in "YYYY-MM", oldest first. */
export function postsInMonth<T extends { date: string }>(posts: T[], month: string): T[] {
	return posts.filter((p) => p.date.startsWith(`${month}-`)).sort((a, b) => a.date.localeCompare(b.date));
}

/** A title as email HTML: code parts in the code font, the rest escaped. */
export function titleHtml(title: string): string {
	return titleParts(title)
		.map((part) =>
			part.code
				? `<span style="font-family:'JetBrains Mono', 'Courier New', monospace; font-weight:500; color:#022791;">${escapeHtml(part.text)}</span>`
				: escapeHtml(part.text),
		)
		.join("");
}

/** "A", "A and B", "A, B and C". */
export function authorList(names: string[]): string {
	return names.length < 2 ? (names[0] ?? "") : `${names.slice(0, -1).join(", ")} and ${names.at(-1)}`;
}

/** The inbox preview line: the post titles, cut to fit what inboxes show. */
export function preheader(posts: IssuePost[], max = 140): string {
	const text = posts.map((p) => titleParts(p.title).map((part) => part.text).join("")).join(" · ");
	return text.length <= max ? text : `${text.slice(0, max - 1).trimEnd()}…`;
}

const fill = (html: string, values: Record<string, string>) =>
	html.replace(/\[\[(\w+)\]\]/g, (marker, name: string) => {
		if (!(name in values)) throw new Error(`newsletter template: no value for ${marker}`);
		return values[name];
	});

/** The finished issue: the template with its POST block repeated per post. */
export function renderIssue(template: string, month: string, posts: IssuePost[]): string {
	const match = /\t<!-- POST -->\n([\s\S]*?)\n\t<!-- \/POST -->\n/.exec(template);
	if (!match) throw new Error("newsletter template: no POST block");
	const blocks = posts.map((post, i) =>
		fill(match[1], {
			background: BACKGROUNDS[i % BACKGROUNDS.length],
			url: escapeHtml(post.url),
			title_html: titleHtml(post.title),
			summary: escapeHtml(post.summary),
			authors: escapeHtml(authorList(post.authors)),
			image: escapeHtml(post.image),
			image_alt: "",
		}),
	);
	const name = monthName(month);
	return fill(template.replace(match[0], `${blocks.join("\n\n")}\n`), {
		month: escapeHtml(name),
		month_upper: escapeHtml(name.toUpperCase()),
		preheader: escapeHtml(preheader(posts)),
	});
}
