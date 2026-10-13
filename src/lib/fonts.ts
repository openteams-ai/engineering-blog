// The site's web fonts, for astro.config.mjs.
import { fontProviders } from "astro/config";

// Astro downloads only the latin subset unless told otherwise, and letters
// such as the "ł" in Michał are in latin-ext. A page downloads a subset only
// when it shows one of its letters.
const subsets = ["latin", "latin-ext"];

export const fonts = [
	{ provider: fontProviders.google(), name: "Inter", subsets, cssVariable: "--font-body", weights: [400, 500, 600, 700, 800], fallbacks: ["sans-serif"] },
	{ provider: fontProviders.google(), name: "Fira Code", subsets, cssVariable: "--font-mono", weights: [400, 500], fallbacks: ["monospace"] },
	// Post titles and article text.
	{ provider: fontProviders.google(), name: "IBM Plex Sans", subsets, cssVariable: "--font-post", weights: ["400 700"], fallbacks: ["sans-serif"] },
	// OG card only.
	{ provider: fontProviders.google(), name: "Sora", subsets, cssVariable: "--font-sora", weights: [700], fallbacks: ["sans-serif"] },
	{ provider: fontProviders.google(), name: "IBM Plex Sans", subsets, cssVariable: "--font-nav", weights: [500], fallbacks: ["sans-serif"] },
];
