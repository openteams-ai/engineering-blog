// Pull the last 90 days of blog visits from GA4, by landing post and the
// channel that sent them, and write them to ga-report.json for the traffic
// dashboard.
//
//   node --env-file-if-exists=.env scripts/ga-report.ts [days]
//
// Needs GA_PROPERTY_ID (the numeric property ID, not the G- measurement ID).
// Signs in with GA_SERVICE_ACCOUNT_JSON (a service account's key, as JSON
// text) when set, else with your own login from
// `gcloud auth application-default login`. The GA4 property is shared with
// openteams.com, so only blog landing pages count.
import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { BetaAnalyticsDataClient } from "@google-analytics/data";
import authors from "../authors.json" with { type: "json" };
import { BLOG_PATH } from "../src/lib/blog-path.ts";
import { frontmatter } from "../src/lib/new-posts.ts";
import { plainTitle } from "../src/lib/title.ts";
import { channelFor, isoDate, slugFromLandingPage, type TrafficRow } from "../src/lib/traffic.ts";

const OUT_FILE = "ga-report.json";

const propertyId = process.env.GA_PROPERTY_ID;
const key = process.env.GA_SERVICE_ACCOUNT_JSON;
if (!propertyId) {
	console.error("Set GA_PROPERTY_ID in .env (see .env.example).");
	process.exit(1);
}
const days = Number(process.argv[2] ?? 90);

const names = new Map(authors.map((a) => [a.slug, a.name]));
const posts = readdirSync("posts")
	.filter((f) => f.endsWith(".md"))
	.map((f) => frontmatter(readFileSync(`posts/${f}`, "utf8")))
	.map((data) => ({
		slug: String(data.slug),
		title: plainTitle(String(data.title ?? "")),
		authors: (Array.isArray(data.authors) ? data.authors.map(String) : []).map((s) => names.get(s) ?? s),
		date: String(data.date ?? "").slice(0, 10),
		topic: String(data.topic ?? ""),
	}));
const known = new Set(posts.map((p) => p.slug));

const client = new BetaAnalyticsDataClient(key ? { credentials: JSON.parse(key) } : {});
const [report] = await client.runReport({
	property: `properties/${propertyId}`,
	dateRanges: [{ startDate: `${days}daysAgo`, endDate: "yesterday" }],
	dimensions: [{ name: "date" }, { name: "landingPage" }, { name: "sessionSource" }, { name: "sessionMedium" }],
	metrics: [
		{ name: "sessions" },
		{ name: "activeUsers" },
		{ name: "engagedSessions" },
		{ name: "userEngagementDuration" },
	],
	dimensionFilter: {
		filter: { fieldName: "landingPage", stringFilter: { matchType: "BEGINS_WITH", value: `${BLOG_PATH}/` } },
	},
	limit: 100_000,
});

const rows: TrafficRow[] = [];
const unknown = new Set<string>();
for (const row of report.rows ?? []) {
	const [date, landingPage, source, medium] = (row.dimensionValues ?? []).map((d) => d.value ?? "");
	const [sessions, users, engaged, duration] = (row.metricValues ?? []).map((m) => Number(m.value ?? 0));
	const slug = slugFromLandingPage(landingPage);
	if (!slug) continue;
	if (!known.has(slug)) unknown.add(slug);
	rows.push({
		date: isoDate(date),
		slug,
		channel: channelFor(source, medium),
		source,
		medium,
		sessions,
		users,
		engagedSessions: engaged,
		engagementSec: Math.round(duration),
	});
}

writeFileSync(OUT_FILE, JSON.stringify({ fetchedAt: new Date().toISOString(), days, posts, rows }, null, "\t"));
const total = rows.reduce((sum, r) => sum + r.sessions, 0);
console.log(`Wrote ${rows.length} rows (${total} sessions over ${days} days) to ${OUT_FILE}.`);
if (unknown.size) console.log(`::warning::Landing pages with no post file: ${[...unknown].join(", ")}`);
