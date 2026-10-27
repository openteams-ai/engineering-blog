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
//
// PyCoder's Weekly sends readers without UTM tags, so they arrive as Direct.
// For posts it featured, the Direct visits above the post's usual level on
// the issue day and the day after are credited to it as an estimate.
import { writeFileSync } from "node:fs";
import { BetaAnalyticsDataClient } from "@google-analytics/data";
import { BLOG_PATH } from "../src/lib/blog-path.ts";
import { channelFor, creditNewsletterDirect, isoDate, slugFromLandingPage, type TrafficRow } from "../src/lib/traffic.ts";
import { readPosts } from "./posts.ts";
import { pycodersFeatures, pycodersSource } from "./pycoders-features.ts";

const OUT_FILE = "ga-report.json";

const propertyId = process.env.GA_PROPERTY_ID;
const key = process.env.GA_SERVICE_ACCOUNT_JSON;
if (!propertyId) {
	console.error("Set GA_PROPERTY_ID in .env (see .env.example).");
	process.exit(1);
}
const days = Number(process.argv[2] ?? 90);

const posts = readPosts();
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

// One row per day, post, source and medium: GA4 gives a row per landing page
// variant (a query string makes another), which would split a post's Direct.
const merged = new Map<string, TrafficRow>();
const unknown = new Set<string>();
for (const row of report.rows ?? []) {
	const [date, landingPage, source, medium] = (row.dimensionValues ?? []).map((d) => d.value ?? "");
	const [sessions, users, engaged, duration] = (row.metricValues ?? []).map((m) => Number(m.value ?? 0));
	const slug = slugFromLandingPage(landingPage);
	if (!slug) continue;
	if (!known.has(slug)) unknown.add(slug);
	const key = [date, slug, source, medium].join("|");
	const entry = merged.get(key) ?? {
		date: isoDate(date),
		slug,
		channel: channelFor(source, medium),
		source,
		medium,
		sessions: 0,
		users: 0,
		engagedSessions: 0,
		engagementSec: 0,
	};
	entry.sessions += sessions;
	entry.users += users;
	entry.engagedSessions += engaged;
	entry.engagementSec += Math.round(duration);
	merged.set(key, entry);
}

const since = new Date(Date.now() - days * 864e5).toISOString().slice(0, 10);
const features = await pycodersFeatures(posts, since);
const rows = creditNewsletterDirect(
	[...merged.values()],
	features.map((f) => ({ slug: f.slug, date: f.date, source: pycodersSource(f.number) })),
);
const credited = rows.filter((r) => r.medium === "estimated from direct").reduce((sum, r) => sum + r.sessions, 0);
console.log(`PyCoder's Weekly featured ${features.length} post(s); credited ${credited} Direct visits to it.`);

writeFileSync(OUT_FILE, JSON.stringify({ fetchedAt: new Date().toISOString(), days, posts, rows }, null, "\t"));
const total = rows.reduce((sum, r) => sum + r.sessions, 0);
console.log(`Wrote ${rows.length} rows (${total} sessions over ${days} days) to ${OUT_FILE}.`);
if (unknown.size) console.log(`::warning::Landing pages with no post file: ${[...unknown].join(", ")}`);
