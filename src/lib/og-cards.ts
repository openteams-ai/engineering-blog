// Share (OG) cards: one for the blog, each post and each author. The build
// lists them in og-manifest.json; `npm run og` (scripts/og.ts) fetches the
// ones the live site already has and renders only the rest, from the
// dev-only pages/og-card route.
import { createHash } from "node:crypto";
import template from "../pages/og-card/[slug].astro?raw";
import { authorsOf } from "./authors";
import { authorRole, bylineNames } from "./byline";
import type { Author } from "./posts";

export interface OgCard {
	key: string;
	title: string;
	byline: string;
	avatar: string | null;
}

interface CardPost {
	slug: string;
	title: string;
	minutes: number;
	authors: Author[];
}

export function ogCards(posts: CardPost[]): OgCard[] {
	return [
		{ key: "home", title: "", byline: "", avatar: null },
		...authorsOf(posts).map(({ author, posts: written }) => ({
			key: `author-${author.slug}`,
			title: author.name,
			byline: `${authorRole(author)} · ${written.length} ${written.length === 1 ? "post" : "posts"}`,
			avatar: author.avatarUrl,
		})),
		...posts.map((p) => ({
			key: p.slug,
			title: p.title,
			byline: p.authors.length ? `${bylineNames(p.authors)} · ${p.minutes} min read` : `${p.minutes} min read`,
			avatar: p.authors[0]?.avatarUrl ?? null,
		})),
	];
}

/**
 * The card's file, named with a fingerprint of everything drawn on it and of
 * the card template. Same content, same file: deploys reuse it. Any change,
 * new file: it gets rendered, and link previews that cache by URL refresh.
 */
export function ogFile(card: OgCard): string {
	const hash = createHash("sha256").update(JSON.stringify([card, template])).digest("hex").slice(0, 8);
	return `/og/og-${card.key}-${hash}.png`;
}
