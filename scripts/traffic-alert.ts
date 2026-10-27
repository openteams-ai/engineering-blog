// Tell Slack when yesterday's blog visits went over a threshold, and how that
// compares with a typical day. Run daily after the traffic dashboard's refresh.
//
//   node --env-file-if-exists=.env scripts/traffic-alert.ts
//
// Counts visits the way the traffic dashboard does: sessions that started on
// a post (see ga-report.ts for GA_PROPERTY_ID and GA_SERVICE_ACCOUNT_JSON).
// TRAFFIC_ALERT_THRESHOLD sets the bar (default 100). Without
// SLACK_TRAFFIC_WEBHOOK it prints what it would send.
//
// A spike that lasts several days posts once, on its first day, and again
// only if a later day beats it by 1.5x.
import { BetaAnalyticsDataClient } from "@google-analytics/data";
import { BLOG_PATH } from "../src/lib/blog-path.ts";
import { dailyVisits, isoDate, median, shouldAlert } from "../src/lib/traffic.ts";

const DASHBOARD_URL = "https://claude.ai/artifact/5PKQDQH9bv8HH1wcKu8rje";
// "A typical day" is the median of this many days before yesterday.
const TYPICAL_DAYS = 28;

const propertyId = process.env.GA_PROPERTY_ID;
const key = process.env.GA_SERVICE_ACCOUNT_JSON;
const webhook = process.env.SLACK_TRAFFIC_WEBHOOK;
const threshold = Number(process.env.TRAFFIC_ALERT_THRESHOLD || 100);
if (!propertyId) {
	console.error("Set GA_PROPERTY_ID in .env (see .env.example).");
	process.exit(1);
}

// "yesterday" is in the GA property's time zone, so dates come from GA too
// rather than from this machine's clock.
const client = new BetaAnalyticsDataClient(key ? { credentials: JSON.parse(key) } : {});
const [report] = await client.runReport({
	property: `properties/${propertyId}`,
	dateRanges: [{ startDate: `${TYPICAL_DAYS + 1}daysAgo`, endDate: "yesterday" }],
	dimensions: [{ name: "date" }, { name: "landingPage" }],
	metrics: [{ name: "sessions" }],
	dimensionFilter: {
		filter: { fieldName: "landingPage", stringFilter: { matchType: "BEGINS_WITH", value: `${BLOG_PATH}/` } },
	},
	limit: 100_000,
});

const days = dailyVisits(
	(report.rows ?? []).map((row) => ({
		date: row.dimensionValues?.[0]?.value ?? "",
		landingPage: row.dimensionValues?.[1]?.value ?? "",
		sessions: Number(row.metricValues?.[0]?.value ?? 0),
	})),
);
const latest = days.at(-1);
if (!latest) {
	console.log("No post visits in GA for the last days.");
	process.exit(0);
}
// Days before the blog moved have no visits and no rows, so they don't drag
// the typical day down.
const normal = Math.round(median(days.slice(0, -1).map((d) => d.visits)));
const date = new Date(`${isoDate(latest.date)}T00:00:00Z`).toLocaleDateString("en-US", {
	weekday: "short",
	month: "short",
	day: "numeric",
	timeZone: "UTC",
});
console.log(`${date}: ${latest.visits} visits (typical day ${normal}, threshold ${threshold}).`);
if (!shouldAlert(days, threshold)) {
	if (latest.visits > threshold) console.log("Same spike as the day before, and not a new high. No alert.");
	process.exit(0);
}

const timesNormal = normal ? String(Math.round(latest.visits / normal)) : "many";
const body = {
	text: `Great day for the engineering blog! We had ${latest.visits} visits on ${date}, about ${timesNormal}x a typical day.\nMore on the dashboard: ${DASHBOARD_URL}`,
	date,
	visits: String(latest.visits),
	threshold: String(threshold),
	normal: String(normal),
	times_normal: timesNormal,
	dashboard_url: DASHBOARD_URL,
};
if (!webhook) {
	console.log(`Would send:\n${body.text}`);
	process.exit(0);
}
const res = await fetch(webhook, {
	method: "POST",
	headers: { "Content-Type": "application/json" },
	body: JSON.stringify(body),
	signal: AbortSignal.timeout(30_000),
});
if (!res.ok) {
	console.error(`Slack answered ${res.status}.`);
	process.exit(1);
}
console.log("Sent the alert to Slack.");
