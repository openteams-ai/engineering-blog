import { unified } from "@astrojs/markdown-remark";
import tailwindcss from "@tailwindcss/vite";
import icon from "astro-iconset";
import { defineConfig, fontProviders } from "astro/config";
import { writeFileSync } from "node:fs";
import { BLOG_PATH } from "./src/lib/blog-path.ts";
import { postMoves, redirectsFile } from "./src/lib/old-addresses.ts";
import remarkPostCleanup from "./src/lib/remark-post-cleanup.ts";

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
			hooks: { "astro:build:done": () => writeFileSync("dist/_redirects", redirectsFile(postMoves())) },
		},
		icon({
			// Ship only the Phosphor icons the templates reference.
			include: {
				ph: [
					"bank", "brain", "briefcase", "caret-down-fill", "chart-line-up", "cpu", "dna",
					"envelope-simple", "facebook-logo", "file-py", "github-logo", "globe", "instagram-logo", "lightning",
					"linkedin-logo", "link", "check", "list", "medium-logo", "megaphone", "microphone", "moon",
					"newspaper", "notepad", "pen-nib", "rocket", "rss", "share-network", "shield",
					"sparkle", "sun", "users-three", "x", "x-logo", "youtube-logo",
				],
			},
		}),
	],
	fonts: [
		{ provider: fontProviders.google(), name: "Inter", subsets: ["latin", "latin-ext"], cssVariable: "--font-body", weights: [400, 500, 600, 700, 800], fallbacks: ["sans-serif"] },
		{ provider: fontProviders.google(), name: "Fira Code", cssVariable: "--font-mono", weights: [400, 500], fallbacks: ["monospace"] },
		// Post titles and article text.
		{ provider: fontProviders.google(), name: "IBM Plex Sans", subsets: ["latin", "latin-ext"], cssVariable: "--font-post", weights: ["400 700"], fallbacks: ["sans-serif"] },
		// OG card only.
		{ provider: fontProviders.google(), name: "Sora", cssVariable: "--font-sora", weights: [700], fallbacks: ["sans-serif"] },
		{ provider: fontProviders.google(), name: "IBM Plex Sans", subsets: ["latin", "latin-ext"], cssVariable: "--font-nav", weights: [500], fallbacks: ["sans-serif"] },
	],
});
