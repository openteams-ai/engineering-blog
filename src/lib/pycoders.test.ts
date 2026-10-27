import { describe, expect, it } from "vitest";
import { featuredSlugs, parseIssueList, titleKey } from "./pycoders";

describe("parseIssueList", () => {
	it("reads each issue's number and date", () => {
		const html = `
			<a href="/issues/757" class="fw-normal"><strong>Issue #757:</strong></a>
			<em>(2026-10-20)</em>
			<a href="/issues/756" class="fw-normal"><strong>Issue #756:</strong></a>
			<em>(2026-10-13)</em>`;
		expect(parseIssueList(html)).toEqual([
			{ number: 757, date: "2026-10-20" },
			{ number: 756, date: "2026-10-13" },
		]);
	});
});

describe("titleKey", () => {
	it("matches a title written with an HTML entity and with a plain quote", () => {
		expect(titleKey("OpenTeams&rsquo; Contributions")).toBe(titleKey("OpenTeams' Contributions"));
	});
});

describe("featuredSlugs", () => {
	const posts = [
		{ slug: "pytorch-year-in-review-2026", title: "PyTorch Year in Review: OpenTeams' Contributions in 2026" },
		{ slug: "uv", title: "Benchmarking Python Package Managers" },
	];

	it("finds the posts whose title is in the issue", () => {
		const html = `<a href="https://pycoders.com/link/17274/web">PyTorch Year in Review: OpenTeams&rsquo; Contributions in 2026</a>`;
		expect(featuredSlugs(html, posts)).toEqual(["pytorch-year-in-review-2026"]);
	});

	it("finds nothing when no post is in the issue", () => {
		expect(featuredSlugs("<p>Other Python news</p>", posts)).toEqual([]);
	});
});
