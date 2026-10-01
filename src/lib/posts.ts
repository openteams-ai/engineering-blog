import { getCollection, type CollectionEntry } from "astro:content";
import authors from "../data/authors.json";
import { POST_TOPICS, TOPIC_LABELS } from "../data/topics";
import { readingTimeMinutes } from "./reading-time";

export interface Author {
	slug: string;
	name: string;
	bio: string;
	avatarUrl: string | null;
}

export interface Post {
	slug: string;
	title: string;
	excerpt: string;
	authors: Author[];
	topic: { slug: string; label: string } | null;
	date: Date;
	minutes: number;
	entry: CollectionEntry<"posts">;
}

const authorBySlug = new Map((authors as Author[]).map((a) => [a.slug, a]));

function toPost(entry: CollectionEntry<"posts">): Post {
	const topicSlug = POST_TOPICS[entry.id];
	return {
		slug: entry.id,
		title: entry.data.title,
		excerpt: entry.data.meta_description,
		authors: entry.data.authors.flatMap((s) => authorBySlug.get(s) ?? []),
		topic: topicSlug ? { slug: topicSlug, label: TOPIC_LABELS[topicSlug] ?? topicSlug } : null,
		date: entry.data.date,
		minutes: readingTimeMinutes(entry.body ?? ""),
		entry,
	};
}

/** All engineering posts, newest first. */
export async function getPosts(): Promise<Post[]> {
	const entries = await getCollection("posts", (e) => e.data.categories.includes("Engineering"));
	return entries.map(toPost).sort((a, b) => b.date.getTime() - a.date.getTime());
}

/** Topics that have at least one post, in label order. */
export function topicsOf(posts: Post[]): { slug: string; label: string; count: number }[] {
	const counts = new Map<string, number>();
	for (const p of posts) if (p.topic) counts.set(p.topic.slug, (counts.get(p.topic.slug) ?? 0) + 1);
	return [...counts]
		.map(([slug, count]) => ({ slug, label: TOPIC_LABELS[slug] ?? slug, count }))
		.sort((a, b) => a.label.localeCompare(b.label));
}
