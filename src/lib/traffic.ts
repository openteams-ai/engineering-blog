// Turns GA4 report rows into blog traffic rows the dashboard reads: which
// post a visit landed on and which channel sent it. GA4 only sees referrers
// (no UTM tags), so a channel is a guess from session source and medium.
import { BLOG_PATH } from "./blog-path.ts";

export interface TrafficRow {
	date: string;
	slug: string;
	channel: string;
	source: string;
	medium: string;
	sessions: number;
	users: number;
	engagedSessions: number;
	engagementSec: number;
}

/**
 * The post slug a landing page belongs to, or null for pages that aren't a
 * post (home, tag and author pages, files). Query strings are ignored.
 */
export function slugFromLandingPage(landingPage: string): string | null {
	const path = landingPage.split("?")[0];
	if (!path.startsWith(`${BLOG_PATH}/`)) return null;
	const parts = path.slice(BLOG_PATH.length).split("/").filter(Boolean);
	if (parts.length !== 1 || parts[0].includes(".")) return null;
	return parts[0];
}

/**
 * Visits per day, oldest first, counting only landing pages that are posts
 * (as the dashboard does). Rows are GA4 date + landingPage + sessions.
 */
export function dailyVisits(rows: { date: string; landingPage: string; sessions: number }[]) {
	const byDate = new Map<string, number>();
	for (const { date, landingPage, sessions } of rows) {
		if (slugFromLandingPage(landingPage)) byDate.set(date, (byDate.get(date) ?? 0) + sessions);
	}
	return [...byDate].map(([date, visits]) => ({ date, visits })).sort((a, b) => a.date.localeCompare(b.date));
}

/** The middle value, so one spike doesn't move "a typical day". 0 when empty. */
export function median(values: number[]): number {
	if (!values.length) return 0;
	const sorted = [...values].sort((a, b) => a - b);
	const mid = Math.floor(sorted.length / 2);
	return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

/**
 * Whether the last day should raise an alert: it went over the threshold, and
 * either the day before didn't (a new spike) or it beats every earlier day of
 * the same spike by `newHigh` times (the spike is still climbing). Keeps a
 * spike that lasts several days to one message, or two if it grows.
 */
export function shouldAlert(days: { visits: number }[], threshold: number, newHigh = 1.5): boolean {
	const latest = days.at(-1);
	if (!latest || latest.visits <= threshold) return false;
	const spike: number[] = [];
	for (let i = days.length - 2; i >= 0 && days[i].visits > threshold; i--) spike.push(days[i].visits);
	return !spike.length || latest.visits >= newHigh * Math.max(...spike);
}

const DIRECT = "Direct / unknown";
const DAY_MS = 864e5;
const addDays = (date: string, n: number) => new Date(Date.parse(date) + n * DAY_MS).toISOString().slice(0, 10);

/**
 * Credits a newsletter with the Direct visits it most likely sent: on the
 * issue day and the day after, a featured post's Direct visits above its
 * usual level (the median of up to 14 days before the issue, counting from
 * the post's first visit) move to a
 * "Newsletters" row marked as estimated. The post's usual Direct visits stay
 * Direct. Returns new rows and leaves the given ones unchanged.
 */
export function creditNewsletterDirect(
	rows: TrafficRow[],
	features: { slug: string; date: string; source: string }[],
): TrafficRow[] {
	const out = rows.map((r) => ({ ...r }));
	// A post's usual level only counts days since its first visit: days before
	// it was published (or before the blog moved) would read as zero.
	const firstSeen = new Map<string, string>();
	for (const r of rows) if (r.date < (firstSeen.get(r.slug) ?? "9999")) firstSeen.set(r.slug, r.date);
	const directOn = (slug: string, date: string) =>
		out.find((r) => r.slug === slug && r.date === date && r.channel === DIRECT);

	for (const { slug, date, source } of features) {
		const first = firstSeen.get(slug) ?? date;
		const before = Array.from({ length: 14 }, (_, i) => addDays(date, -14 + i)).filter((d) => d >= first);
		const usual = Math.round(median(before.map((d) => directOn(slug, d)?.sessions ?? 0)));
		for (const day of [date, addDays(date, 1)]) {
			const direct = directOn(slug, day);
			if (!direct || direct.sessions <= usual) continue;
			const extra = direct.sessions - usual;
			const share = extra / direct.sessions;
			const moved = {
				users: Math.round(direct.users * share),
				engagedSessions: Math.round(direct.engagedSessions * share),
				engagementSec: Math.round(direct.engagementSec * share),
			};
			direct.sessions -= extra;
			direct.users -= moved.users;
			direct.engagedSessions -= moved.engagedSessions;
			direct.engagementSec -= moved.engagementSec;
			out.push({ date: day, slug, channel: "Newsletters", source, medium: "estimated from direct", sessions: extra, ...moved });
		}
	}
	return out;
}

/** GA4 dates come as YYYYMMDD. */
export const isoDate = (gaDate: string) => `${gaDate.slice(0, 4)}-${gaDate.slice(4, 6)}-${gaDate.slice(6, 8)}`;

/**
 * The promotion channel a session came from, as the dashboard groups it.
 * `source` and `medium` are GA4's sessionSource and sessionMedium, e.g.
 * ("linkedin.com", "referral"), ("lnkd.in", "referral"), ("google", "organic"),
 * ("(direct)", "(none)"), ("news.ycombinator.com", "referral").
 */
export function channelFor(source: string, medium: string): string {
	// Hand-typed UTM tags vary in case ("LinkediN", "Sociaal").
	const src = source.toLowerCase();
	const med = medium.toLowerCase();
	const from = (...names: string[]) => names.some((n) => src.includes(n));

	// Only a UTM tag sets a "social"-type medium on LinkedIn, and the company
	// page's scheduler is what tags its links. Untagged links from people's
	// own posts arrive as a plain referral.
	if (from("linkedin") && med.startsWith("soci")) return "LinkedIn (company)";
	if (from("linkedin", "lnkd.in")) return "LinkedIn (personal)";
	if (from("tldr")) return "TLDR";
	if (from("codecut")) return "CodeCut";
	// OpenTeams marketing emails, sent from HubSpot.
	if (from("hs_email")) return "Email";
	// Other people's newsletters tag their links with medium "email"
	// (Software Testing Weekly sends "softwaretestingweekly" / "email").
	if (med === "email" || from("pycoders")) return "Newsletters";
	if (med === "ai-assistant" || from("chatgpt", "perplexity", "claude.ai", "gemini.google", "copilot.microsoft"))
		return "AI assistants";
	if (from("news.ycombinator")) return "Hacker News";
	// "t.co" exactly: as a substring it also matches "reddit.com".
	if (src === "x" || src === "t.co" || from("twitter")) return "X";
	if (from("reddit")) return "Reddit";
	if (from("github")) return "GitHub";
	// Teams shows up as several Microsoft hosts. Slack hides its referrer,
	// so Slack shares land in Direct.
	if (from("teams.", "engage.cloud.microsoft")) return "Microsoft Teams";
	if (med === "organic" || from("search.brave")) return "Search";
	// No referrer and no tag: typed links, but also apps that strip the
	// referrer (Slack, email, LinkedIn's app) and staff checking the site.
	if (src === "(direct)") return "Direct / unknown";
	return "Other";
}
