import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";
import { z } from "astro/zod";
import { existsSync } from "node:fs";
import authors from "../authors.json";
import { TOPICS } from "./data/topics";

const AUTHOR_SLUGS = authors.map((a) => a.slug) as [string, ...string[]];

// One markdown file per post. The frontmatter `slug` becomes the entry id.
const posts = defineCollection({
	loader: glob({ pattern: "*.md", base: "./posts" }),
	schema: z.object({
		title: z.string(),
		slug: z.string(),
		// Slugs from authors.json; the first is the main author.
		authors: z.array(z.enum(AUTHOR_SLUGS)).min(1),
		meta_description: z.string().default(""),
		date: z.coerce.date(),
		// One of the topics in src/data/topics.ts; the post is listed under it.
		topic: z.enum(TOPICS),
		// Set when a published post is edited in a way readers should know about.
		updated: z.coerce.date().optional(),
	}).superRefine((post, ctx) => {
		// `astro dev` skips this so a draft can be previewed before its art exists.
		if (import.meta.env.DEV || existsSync(`src/components/art/${post.slug}.astro`)) return;
		ctx.addIssue({
			code: "custom",
			path: ["slug"],
			message: `no thumbnail: add src/components/art/${post.slug}.astro (run /draw-card-art)`,
		});
	}),
});

export const collections = { posts };
