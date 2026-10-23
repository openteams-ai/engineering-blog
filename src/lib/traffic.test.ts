import { describe, expect, it } from "vitest";
import { channelFor, dailyVisits, isoDate, median, shouldAlert, slugFromLandingPage } from "./traffic";

describe("channelFor", () => {
	it.each([
		["LinkedIn", "Social", "LinkedIn (company)"],
		["LinkediN", "Sociaal", "LinkedIn (company)"],
		["linkedin.com", "referral", "LinkedIn (personal)"],
		["lnkd.in", "referral", "LinkedIn (personal)"],
		["tldrai", "(not set)", "TLDR"],
		["news.ycombinator.com", "referral", "Hacker News"],
		["X", "Social", "X"],
		["twitter", "social", "X"],
		["hs_email", "email", "Email"],
		["softwaretestingweekly", "email", "Newsletters"],
		["chatgpt.com", "ai-assistant", "AI assistants"],
		["perplexity.ai", "referral", "AI assistants"],
		["t.co", "referral", "X"],
		["reddit.com", "referral", "Reddit"],
		["teams.public.onecdn.static.microsoft", "referral", "Chat"],
		["google", "organic", "Search"],
		["search.brave.com", "referral", "Search"],
		["(direct)", "(none)", "Direct / unknown"],
		["m.facebook.com", "referral", "Other"],
	])("sends %s / %s to %s", (source, medium, channel) => {
		expect(channelFor(source, medium)).toBe(channel);
	});
});

describe("slugFromLandingPage", () => {
	it("gives the slug of a post page", () => {
		expect(slugFromLandingPage("/engineering-blog/my-post/")).toBe("my-post");
	});

	it("ignores the query string", () => {
		expect(slugFromLandingPage("/engineering-blog/my-post/?ref=x")).toBe("my-post");
	});

	it("skips the blog home, tag and author pages", () => {
		expect(slugFromLandingPage("/engineering-blog/")).toBeNull();
		expect(slugFromLandingPage("/engineering-blog/tag/python/")).toBeNull();
		expect(slugFromLandingPage("/engineering-blog/author/khuyen-tran/")).toBeNull();
	});

	it("skips files and pages outside the blog", () => {
		expect(slugFromLandingPage("/engineering-blog/rss.xml")).toBeNull();
		expect(slugFromLandingPage("/pricing/")).toBeNull();
	});
});

describe("isoDate", () => {
	it("turns a GA4 date into an ISO date", () => {
		expect(isoDate("20261021")).toBe("2026-10-21");
	});
});

describe("dailyVisits", () => {
	it("sums each day's post visits, oldest day first", () => {
		expect(
			dailyVisits([
				{ date: "20261021", landingPage: "/engineering-blog/polars/", sessions: 3 },
				{ date: "20261020", landingPage: "/engineering-blog/uv/", sessions: 5 },
				{ date: "20261021", landingPage: "/engineering-blog/uv/?utm_source=x", sessions: 4 },
			]),
		).toEqual([
			{ date: "20261020", visits: 5 },
			{ date: "20261021", visits: 7 },
		]);
	});

	it("leaves out pages that aren't posts", () => {
		expect(dailyVisits([{ date: "20261021", landingPage: "/engineering-blog/", sessions: 9 }])).toEqual([]);
	});
});

describe("median", () => {
	it("gives the middle value of an odd count", () => {
		expect(median([40, 5, 150])).toBe(40);
	});

	it("averages the two middle values of an even count", () => {
		expect(median([30, 10, 40, 20])).toBe(25);
	});

	it("is 0 with no values", () => {
		expect(median([])).toBe(0);
	});
});

describe("shouldAlert", () => {
	const days = (...visits: number[]) => visits.map((v) => ({ visits: v }));

	it("alerts on the first day over the threshold", () => {
		expect(shouldAlert(days(40, 39, 148), 100)).toBe(true);
	});

	it("stays quiet on the second day of the same spike", () => {
		expect(shouldAlert(days(39, 148, 155), 100)).toBe(false);
	});

	it("alerts again when the spike keeps climbing", () => {
		expect(shouldAlert(days(39, 150, 240), 100)).toBe(true);
	});

	it("compares with the highest earlier day of the spike", () => {
		expect(shouldAlert(days(39, 200, 120, 250), 100)).toBe(false);
	});

	it("alerts on a new spike after a quiet day", () => {
		expect(shouldAlert(days(150, 40, 130), 100)).toBe(true);
	});

	it("stays quiet under the threshold", () => {
		expect(shouldAlert(days(39, 90), 100)).toBe(false);
	});
});
