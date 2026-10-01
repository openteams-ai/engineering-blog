import { BLOG_PATH } from "../lib/blog-path";
import { MAIN_SITE_URL } from "./main-site-nav";

export const SITE_TITLE = "OpenTeams";
export const SITE_TAGLINE = "Building the Infrastructure for a Distributed AI Economy";

const u = (path: string) => `${MAIN_SITE_URL}${path}`;

export const footerColumns = [
	{
		heading: "Products",
		links: [
			{ label: "AI/ML Products", url: u("/ai-ml-products/") },
			{ label: "AI Readiness", url: u("/ai-readiness-assessment/") },
			{ label: "Open SaaS", url: u("/open-saas/") },
			{ label: "Capabilities", url: u("/capabilities/") },
		],
	},
	{
		heading: "Company",
		links: [
			{ label: "About Us", url: u("/about-us/") },
			{ label: "Careers", url: u("/careers/") },
			{ label: "Press", url: u("/press/") },
			{ label: "Communities", url: u("/openteams-communities/") },
		],
	},
	{
		heading: "Resources",
		links: [
			{ label: "Blog", url: u("/blog/") },
			{ label: "Engineering Blog", url: BLOG_PATH },
			{ label: "Case Studies", url: u("/case-studies/") },
			{ label: "Contact", url: u("/contact/") },
		],
	},
];

export const socialLinks = [
	{ label: "LinkedIn", icon: "ph:linkedin-logo", url: "https://www.linkedin.com/company/openteams" },
	{ label: "Instagram", icon: "ph:instagram-logo", url: "https://www.instagram.com/openteams/" },
	{ label: "YouTube", icon: "ph:youtube-logo", url: "https://www.youtube.com/@openteams" },
	{ label: "Medium", icon: "ph:medium-logo", url: "https://medium.com/openteams" },
	{ label: "X", icon: "ph:x-logo", url: "https://x.com/openteamsinc" },
	{ label: "Facebook", icon: "ph:facebook-logo", url: "https://www.facebook.com/openteamsinc/" },
	{ label: "GitHub", icon: "ph:github-logo", url: "https://github.com/openteams-ai" },
];
