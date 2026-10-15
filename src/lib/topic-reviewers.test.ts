import { describe, expect, it } from "vitest";
import { postTopic, reviewers, signupComment } from "./topic-reviewers";

const post = (head: string) => `---\n${head}\n---\n\nBody text.\n`;

describe("postTopic", () => {
	it("reads the topic from the frontmatter", () => {
		expect(postTopic(post("title: T\ntopic: python-tooling"))).toBe("python-tooling");
	});

	it("is undefined for a topic the site doesn't have", () => {
		expect(postTopic(post("title: T\ntopic: cooking"))).toBeUndefined();
	});

	it("is undefined when the post has no topic", () => {
		expect(postTopic(post("title: T"))).toBeUndefined();
	});
});

describe("signupComment", () => {
	const comment = (id: number, login: string, body: string) => ({ id, body, user: { login } });
	const link = (topic: string) => `**[Topic](https://openteams.com/engineering-blog/tag/${topic}/)**`;

	it("finds the issue author's comment that links the topic page", () => {
		const comments = [comment(1, "owner", link("ai-engineering")), comment(2, "owner", link("infrastructure"))];
		expect(signupComment(comments, "owner", "infrastructure")?.id).toBe(2);
	});

	it("ignores a comment by anyone else, even one linking the topic", () => {
		const comments = [comment(1, "someone", link("infrastructure")), comment(2, "owner", link("infrastructure"))];
		expect(signupComment(comments, "owner", "infrastructure")?.id).toBe(2);
	});

	it("doesn't match a topic whose name contains another's", () => {
		const comments = [comment(1, "owner", link("llms-inference"))];
		expect(signupComment(comments, "owner", "ai-engineering")).toBeUndefined();
	});
});

describe("reviewers", () => {
	it("lists each person once and leaves out the PR's author", () => {
		expect(reviewers(["ana", "author", "ben", "ana"], "author")).toEqual(["ana", "ben"]);
	});
});
