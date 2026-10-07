import { describe, expect, it } from "vitest";
import { announcement, frontmatter } from "./new-posts";

const AUTHORS = [
	{ slug: "khuyen-tran", name: "Khuyen Tran" },
	{ slug: "anuj-kumar-singh", name: "Anuj Kumar Singh" },
];

const post = (head: string) => `---\n${head}\n---\n\nBody text.\n`;

describe("announcement", () => {
	it("gives the title, live address and author name", () => {
		const md = post("title: My Post\nslug: my-post\nauthors:\n  - khuyen-tran");
		expect(announcement(md, AUTHORS)).toEqual({
			post_title: "My Post",
			post_url: "https://openteams.com/engineering-blog/my-post/",
			author: "Khuyen Tran",
		});
	});

	it("drops the backticks that mark code in a title", () => {
		const md = post("title: Your Agent Ignored `AGENTS.md`\nslug: x");
		expect(announcement(md, AUTHORS).post_title).toBe("Your Agent Ignored AGENTS.md");
	});

	it("joins several authors and keeps the slug of one not in the list", () => {
		const md = post("title: T\nslug: t\nauthors: [anuj-kumar-singh, guest-writer]");
		expect(announcement(md, AUTHORS).author).toBe("Anuj Kumar Singh, guest-writer");
	});

	it("leaves the author empty when the post lists none", () => {
		expect(announcement(post("title: T\nslug: t"), AUTHORS).author).toBe("");
	});
});

describe("frontmatter", () => {
	it("is empty for a file without a frontmatter block", () => {
		expect(frontmatter("# Just a heading\n")).toEqual({});
	});
});
