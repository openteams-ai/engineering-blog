import { unified } from "@astrojs/markdown-remark";
import tailwindcss from "@tailwindcss/vite";
import icon from "astro-iconset";
import { defineConfig } from "astro/config";
import { writeFileSync } from "node:fs";
import { BLOG_PATH, pageUrl } from "./src/lib/blog-path.ts";
import { fonts } from "./src/lib/fonts.ts";
import { postMoves, redirectsFile } from "./src/lib/old-addresses.ts";
import remarkPostCleanup from "./src/lib/remark-post-cleanup.ts";

// Topics that were renamed keep their old tag page address.
const topicMoves = [{ from: `${BLOG_PATH}/tag/practices`, to: pageUrl("/tag/code-quality") }];

export default defineConfig({
	site: "https://openteams.com",
	output: "static",
	trailingSlash: "ignore",
	// Pages, assets and public files are all written under dist<BLOG_PATH>/.
	base: BLOG_PATH,
	outDir: `./dist${BLOG_PATH}`,
	devToolbar: { enabled: false },
	vite: { plugins: [tailwindcss()] },
	markdown: {
		// Straight quotes, matching the current blog.
		processor: unified({ remarkPlugins: [remarkPostCleanup], smartypants: false }),
		syntaxHighlight: { type: "shiki", excludeLangs: ["mermaid"] },
		shikiConfig: { theme: "catppuccin-mocha" },
	},
	integrations: [
		{
			// Old addresses of posts that moved here redirect to them. Cloudflare
			// reads the rules from the root of what is deployed (dist/), one
			// level above the blog's own folder.
			name: "old-addresses",
			hooks: { "astro:build:done": () => writeFileSync("dist/_redirects", redirectsFile([...postMoves(), ...topicMoves])) },
		},
		icon({
			// Ship only the Phosphor icons the templates reference.
			include: {
				ph: [
					"bank", "brain", "briefcase", "caret-down-fill", "chart-line-up", "cpu", "dna",
					"envelope-simple", "facebook-logo", "file-code", "github-logo", "globe", "instagram-logo", "lightning",
					"linkedin-logo", "link", "check", "list", "medium-logo", "megaphone", "microphone", "moon",
					"newspaper", "notepad", "pen-nib", "rocket", "rss", "share-network", "shield",
					"sparkle", "sun", "users-three", "x", "x-logo", "youtube-logo",
				],
			},
		}),
	],
	fonts,
});
