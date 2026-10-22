import { describe, expect, it } from "vitest";
import { channelFor, isoDate, slugFromLandingPage } from "./traffic";

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
