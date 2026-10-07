import { getCollection, type CollectionEntry } from "astro:content";
import authors from "../../authors.json";
import { blogUrl } from "./blog-path";
import { TOPIC_LABELS, type Topic } from "../data/topics";
import { readingTimeMinutes } from "./reading-time";
import { plainTitle, titleParts, type TitlePart } from "./title";

/** Where to find an author elsewhere, each an absolute address. All optional. */
export interface AuthorLinks {
	github?: string;
	linkedin?: string;
	x?: string;
	bluesky?: string;
	website?: string;
}

export interface Author {
	slug: string;
	name: string;
	bio: string;
	avatarUrl: string | null;
	links?: AuthorLinks;
}

export interface Post {
	slug: string;
	/** Title without backticks, for plain-text uses. */
	title: string;
	/** Title split into text and code parts, for rendering. */
	titleParts: TitlePart[];
	excerpt: string;
	authors: Author[];
	topic: { slug: Topic; label: string };
	date: Date;
	/** When the post last changed: its `updated` date if it has one, else the day it came out. */
	changed: Date;
	minutes: number;
	entry: CollectionEntry<"posts">;
}

// A photo kept in the blog (public/authors/) is listed by its path there;
// one hosted elsewhere by its full address.
const authorBySlug = new Map(
	(authors as Author[]).map((a) => [a.slug, { ...a, avatarUrl: a.avatarUrl?.startsWith("/") ? blogUrl(a.avatarUrl) : a.avatarUrl }]),
);

function toPost(entry: CollectionEntry<"posts">): Post {
	return {
		slug: entry.id,
		title: plainTitle(entry.data.title),
		titleParts: titleParts(entry.data.title),
		excerpt: entry.data.meta_description,
		authors: entry.data.authors.flatMap((s) => authorBySlug.get(s) ?? []),
		topic: { slug: entry.data.topic, label: TOPIC_LABELS[entry.data.topic] },
		date: entry.data.date,
		changed: entry.data.updated ?? entry.data.date,
		minutes: readingTimeMinutes(entry.body ?? ""),
		entry,
	};
}

/** All engineering posts, newest first. */
export async function getPosts(): Promise<Post[]> {
	const entries = await getCollection("posts");
	return entries.map(toPost).sort((a, b) => b.date.getTime() - a.date.getTime());
}

/** Topics that have at least one post, in label order. */
export function topicsOf(posts: Post[]): { slug: string; label: string; count: number }[] {
	const counts = new Map<Topic, number>();
	for (const p of posts) counts.set(p.topic.slug, (counts.get(p.topic.slug) ?? 0) + 1);
	return [...counts]
		.map(([slug, count]) => ({ slug, label: TOPIC_LABELS[slug], count }))
		.sort((a, b) => a.label.localeCompare(b.label));
}

export { authorsOf } from "./authors";
