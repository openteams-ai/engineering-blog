import { describe, expect, it } from "vitest";
import { parse } from "yaml";
import { MISSING, UNANSWERED, briefPath, createUrl, findProblems, renderComment, renderTemplate } from "./social-brief";

const POST = "posts/my-post.md";
const LONG = "Compares four package managers on install time with numbers from real projects.";
const brief = (fields: Record<string, unknown>) =>
	Object.entries(fields)
		.map(([k, v]) => `${k}: ${JSON.stringify(v)}`)
		.join("\n");
const answered = { problem: LONG, what_it_does: LONG, remember_one_thing: LONG, audience: ["data-scientists"] };
const CI = { GITHUB_REPOSITORY: "org/blog", HEAD_REPO: "fork/blog", HEAD_REF: "my-branch" };

describe("briefPath", () => {
	it("uses the frontmatter slug", () => {
		expect(briefPath(POST, "---\nslug: other-name\n---\n")).toBe("social/other-name.yml");
	});

	it("falls back to the file name", () => {
		expect(briefPath(POST, "No frontmatter.")).toBe("social/my-post.yml");
	});
});

describe("findProblems", () => {
	it("passes a fully answered brief", () => {
		expect(findProblems(brief(answered))).toEqual([]);
	});

	it("reports a missing brief", () => {
		expect(findProblems(null)).toEqual([MISSING]);
	});

	it("reports the untouched template as one problem", () => {
		expect(findProblems(renderTemplate(POST))).toEqual([UNANSWERED]);
	});

	it("accepts exactly the minimum number of words", () => {
		expect(findProblems(brief({ ...answered, problem: "one two three four five six seven eight" }))).toEqual([]);
	});

	it("rejects one word under the minimum, with the count", () => {
		const [problem] = findProblems(brief({ ...answered, problem: "one two three four five six seven" }));
		expect(problem).toMatch(/^`problem` is only 7 words\./);
	});

	it("says singular for one word, and empty for none", () => {
		expect(findProblems(brief({ ...answered, problem: "Short.", what_it_does: "" }))).toEqual([
			expect.stringMatching(/^`problem` is only 1 word\./),
			"`what_it_does` is empty.",
		]);
	});

	it("needs at least one audience", () => {
		expect(findProblems(brief({ ...answered, audience: [] }))).toEqual([
			"`audience` needs at least one group from the list in the brief.",
		]);
	});

	it("names an audience that isn't in the list", () => {
		expect(findProblems(brief({ ...answered, audience: ["data-scientists", "marketers"] }))).toEqual([
			"`audience` has `marketers`, which isn't one of the groups listed in the brief.",
		]);
	});
});

describe("renderTemplate", () => {
	it("parses to every field empty", () => {
		expect(parse(renderTemplate(POST))).toEqual({ problem: "", what_it_does: "", remember_one_thing: "", audience: [] });
	});
});

describe("renderComment", () => {
	it("thanks the author once every brief passes", () => {
		expect(renderComment([{ post: POST, brief: "social/my-post.yml", problems: [] }], CI)).toContain("Thanks!");
	});

	it("links a missing brief to a pre-filled new file on the PR's repo and branch", () => {
		const comment = renderComment([{ post: POST, brief: "social/my-post.yml", problems: [MISSING] }], CI);
		expect(comment).toContain("https://github.com/fork/blog/new/my-branch?filename=social/my-post.yml&value=");
		expect(comment).toContain("[Social Brief](https://github.com/org/blog/blob/main/README.md#social-brief)");
	});

	it("lists specific problems under the edit link", () => {
		const comment = renderComment([{ post: POST, brief: "social/my-post.yml", problems: ["`problem` is empty."] }], CI);
		expect(comment).toContain("https://github.com/fork/blog/edit/my-branch/social/my-post.yml");
		expect(comment).toContain("- `problem` is empty.");
	});

	it("has no links outside CI", () => {
		expect(createUrl(POST, "social/my-post.yml", {})).toBe("");
	});
});
