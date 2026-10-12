import { describe, expect, it } from "vitest";
import { ogCards, ogFile } from "./og-cards";

const alice = { slug: "alice", name: "Alice Smith", bio: "Engineer at Example. Writes.", avatarUrl: "https://example.com/a.png" };
const bob = { slug: "bob", name: "Bob Jones", bio: "", avatarUrl: null };
const posts = [
	{ slug: "first", title: "First Post", minutes: 4, authors: [alice] },
	{ slug: "second", title: "Second Post", minutes: 7, authors: [alice, bob] },
];

describe("ogCards", () => {
	it("makes the home card, one card per post and one per author", () => {
		expect(ogCards(posts).map((c) => c.key)).toEqual(["home", "author-alice", "author-bob", "first", "second"]);
	});

	it("gives an author card their role and post count", () => {
		const cards = ogCards(posts);
		expect(cards.find((c) => c.key === "author-alice")).toEqual({
			key: "author-alice",
			title: "Alice Smith",
			byline: "Engineer at Example · 2 posts",
			avatar: "https://example.com/a.png",
		});
		expect(cards.find((c) => c.key === "author-bob")?.byline).toBe("OpenTeams · 1 post");
	});

	it("names every author of a post on its card", () => {
		expect(ogCards(posts).find((c) => c.key === "second")?.byline).toBe("Alice Smith & Bob Jones · 7 min read");
	});
});

describe("ogFile", () => {
	const card = { key: "first", title: "First Post", byline: "Alice Smith · 4 min read", avatar: null };

	it("names the file after the card and a fingerprint of its content", () => {
		expect(ogFile(card)).toMatch(/^\/og\/og-first-[0-9a-f]{8}\.png$/);
	});

	it("keeps the same name while the content is the same", () => {
		expect(ogFile({ ...card })).toBe(ogFile(card));
	});

	it("changes the name when anything on the card changes", () => {
		expect(ogFile({ ...card, title: "First Post, Revised" })).not.toBe(ogFile(card));
		expect(ogFile({ ...card, byline: "Alice Smith · 5 min read" })).not.toBe(ogFile(card));
		expect(ogFile({ ...card, avatar: "https://example.com/new.png" })).not.toBe(ogFile(card));
	});
});
