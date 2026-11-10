import { describe, expect, it } from "vitest";
import { authorList, monthName, postsInMonth, preheader, previousMonth, renderIssue, titleHtml } from "./newsletter";

const post = (title: string) => ({
	url: "https://openteams.com/engineering-blog/x/",
	title,
	summary: "A summary.",
	authors: ["Ada Lovelace"],
	image: "https://openteams.com/engineering-blog/og/art-x-1.png",
});

describe("months", () => {
	it("names a month", () => {
		expect(monthName("2026-11")).toBe("November 2026");
	});

	it("steps back a month, across a year", () => {
		expect(previousMonth("2026-11")).toBe("2026-10");
		expect(previousMonth("2027-01")).toBe("2026-12");
	});
});

describe("postsInMonth", () => {
	it("keeps the month's posts, oldest first", () => {
		const posts = [{ date: "2026-10-30T09:00:00-04:00" }, { date: "2026-09-30" }, { date: "2026-10-12" }];
		expect(postsInMonth(posts, "2026-10")).toEqual([{ date: "2026-10-12" }, { date: "2026-10-30T09:00:00-04:00" }]);
	});
});

describe("titleHtml", () => {
	it("sets code in the code font and escapes the rest", () => {
		const html = titleHtml("Your `pip install` & <you>");
		expect(html).toContain(">pip install</span>");
		expect(html).toContain(" &amp; &lt;you&gt;");
	});
});

describe("authorList", () => {
	it("joins names the way the byline does", () => {
		expect(authorList(["A"])).toBe("A");
		expect(authorList(["A", "B"])).toBe("A and B");
		expect(authorList(["A", "B", "C"])).toBe("A, B and C");
	});
});

describe("preheader", () => {
	it("lists the titles without backticks", () => {
		expect(preheader([post("Use `uv`"), post("Polars 2.0")])).toBe("Use uv · Polars 2.0");
	});

	it("cuts a long list to fit", () => {
		expect(preheader([post("x".repeat(200))], 20)).toHaveLength(20);
	});
});

describe("renderIssue", () => {
	const template = [
		"<title>[[month]]</title><p>[[month_upper]]</p><i>[[preheader]]</i>",
		"\t<!-- POST -->",
		'<td style="background:[[background]]"><a href="[[url]]">[[title_html]]</a>[[summary]] By [[authors]] <img src="[[image]]" alt="[[image_alt]]"></td>',
		"\t<!-- /POST -->",
		"<footer>{{ unsubscribe_link }}</footer>",
	].join("\n");

	it("repeats the post block per post, taking turns on the background", () => {
		const html = renderIssue(template, "2026-11", [post("One"), post("Two"), post("Three")]);
		expect(html.match(/<td /g)).toHaveLength(3);
		expect([...html.matchAll(/background:(#\w+)/g)].map((m) => m[1])).toEqual(["#EDF1FF", "#FFF3F0", "#EDF1FF"]);
	});

	it("fills the month and leaves HubSpot's own tags alone", () => {
		const html = renderIssue(template, "2026-11", [post("One")]);
		expect(html).toContain("<title>November 2026</title><p>NOVEMBER 2026</p>");
		expect(html).toContain("{{ unsubscribe_link }}");
		expect(html).not.toContain("[[");
	});
});
