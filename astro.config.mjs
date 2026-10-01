import { unified } from "@astrojs/markdown-remark";
import tailwindcss from "@tailwindcss/vite";
import icon from "astro-iconset";
import { defineConfig, fontProviders } from "astro/config";
import { BLOG_PATH } from "./src/lib/blog-path.ts";
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
		icon({
			// Ship only the Phosphor icons the templates reference.
			include: {
				ph: [
					"brain", "briefcase", "caret-down-fill", "chart-line-up", "cpu", "dna",
					"facebook-logo", "file-py", "github-logo", "instagram-logo", "lightning",
					"linkedin-logo", "list", "medium-logo", "megaphone", "microphone", "moon",
					"newspaper", "notepad", "pen-nib", "rocket", "rss", "share-network", "shield",
					"sparkle", "sun", "users-three", "x", "x-logo", "youtube-logo",
				],
			},
		}),
	],
	fonts: [
		{ provider: fontProviders.google(), name: "Inter", cssVariable: "--font-body", weights: [400, 500, 600, 700, 800], fallbacks: ["sans-serif"] },
		{ provider: fontProviders.google(), name: "Fira Code", cssVariable: "--font-mono", weights: [400, 500], fallbacks: ["monospace"] },
		// OG card only.
		{ provider: fontProviders.google(), name: "Sora", cssVariable: "--font-sora", weights: [700], fallbacks: ["sans-serif"] },
		{ provider: fontProviders.google(), name: "IBM Plex Sans", cssVariable: "--font-nav", weights: [500], fallbacks: ["sans-serif"] },
	],
});
