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
	if (from("hs_email") || med === "email") return "Email";
	if (med === "ai-assistant" || from("chatgpt", "perplexity", "claude.ai", "gemini.google", "copilot.microsoft"))
		return "AI assistants";
	if (from("news.ycombinator")) return "Hacker News";
	// "t.co" exactly: as a substring it also matches "reddit.com".
	if (src === "x" || src === "t.co" || from("twitter")) return "X";
	if (from("reddit")) return "Reddit";
	if (from("github")) return "GitHub";
	// Teams shows up as several Microsoft hosts. Slack hides its referrer,
	// so Slack shares land in Direct.
	if (from("teams.", "engage.cloud.microsoft")) return "Chat";
	if (med === "organic" || from("search.brave")) return "Search";
	// No referrer and no tag: typed links, but also apps that strip the
	// referrer (Slack, email, LinkedIn's app) and staff checking the site.
	if (src === "(direct)") return "Direct / unknown";
	return "Other";
}
