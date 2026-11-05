import { describe, expect, it } from "vitest";
import { blogSlug, featuredSlugs, openteamsLinks, parseIssueList, titleKey } from "./pycoders";

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

describe("openteamsLinks", () => {
	it("finds the article PyCoder's credits to openteams.com, whatever its title", () => {
		const html = `
			<span><a href="https://pycoders.com/link/17338/web" style="color: #AAA" target="_blank">Polars 2.0: Streaming by Default and Stricter Types</a></span><br>
			<span><a href="https://pycoders.com/link/17338/web" target="_blank">OPENTEAMS.COM</a> • Shared by Khuyen Tran</span>
			<span><a href="https://pycoders.com/link/17346/web">GOOGLEBLOG.COM</a> • Shared by anonymous</span>`;
		expect(openteamsLinks(html)).toEqual(["https://pycoders.com/link/17338/web"]);
	});
});

describe("blogSlug", () => {
	it("reads the slug of an engineering-blog post", () => {
		expect(blogSlug("https://openteams.com/engineering-blog/polars-2-whats-new/")).toBe("polars-2-whats-new");
	});

	it("ignores other openteams.com pages", () => {
		expect(blogSlug("https://openteams.com/blog/some-news/")).toBeUndefined();
	});
});
