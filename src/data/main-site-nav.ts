// Navigation mirrored from the openteams.com header so the engineering blog
// presents the same top bar as the main site. Links are absolute because
// these pages live on the main site, not in this CMS.

import { BLOG_PATH } from "../lib/blog-path";

export const MAIN_SITE_URL = "https://openteams.com";

export interface NavLink {
	label: string;
	url: string;
	icon: string;
	description?: string;
}

export interface NavGroup {
	heading?: string;
	columns: { heading?: string; links: NavLink[] }[];
}

export interface NavMenu {
	label: string;
	groups: NavGroup[];
}

const u = (path: string) => `${MAIN_SITE_URL}${path}`;

export const mainSiteNav: NavMenu[] = [
	{
		label: "Solutions",
		groups: [
			{
				columns: [
					{
						links: [
							{ label: "Our Capabilities", url: u("/capabilities/"), icon: "ph:cpu", description: "Rooted in open source expertise" },
							{ label: "Python Security Remediation", url: u("/python-security-remediation/"), icon: "ph:file-py", description: "Bring accountability to your AI stack." },
						],
					},
					{
						links: [
							{ label: "Nebari", url: u("/nebari/"), icon: "ph:share-network", description: "Build your private Intelligence Hub" },
							{ label: "AI PowerShift", url: u("/ai-powershift/"), icon: "ph:brain", description: "Take control of your AI." },
						],
					},
				],
			},
			{
				heading: "Use Cases",
				columns: [
					{
						heading: "Industry & Science",
						links: [
							{ label: "Biotech", url: u("/the-lung-that-failed-and-what-it-taught-us-about-ai/"), icon: "ph:dna", description: "AI powering life sciences" },
							{ label: "Defense", url: u("/open-source-isnt-the-real-risk-in-national-defense/"), icon: "ph:shield", description: "Secure AI for defense" },
							{ label: "Aerospace", url: u("/what-nasa-did-that-every-tech-leader-should-steal/"), icon: "ph:rocket", description: "AI built for aerospace" },
							{ label: "Energy", url: u("/they-didnt-want-a-vendor-they-wanted-ownership/"), icon: "ph:lightning", description: "Optimizing energy with AI" },
						],
					},
					{
						heading: "Strategy & Intelligence",
						links: [
							{ label: "Artificial Intelligence", url: u("/the-democratization-of-ai-has-already-happened/"), icon: "ph:sparkle", description: "Real-world AI in action" },
							{ label: "Strategic Intelligence", url: u("/how-a-fast-growing-ai-company-rebuilt-from-the-stack-up/"), icon: "ph:newspaper", description: "Intelligence for strategic decisions" },
							{ label: "Advertising", url: u("/ai-logo-detection-ad-analytics/"), icon: "ph:megaphone", description: "AI-driven campaign performance" },
							{ label: "Investment Management", url: u("/inside-a-1t-firms-fight-to-build-real-ai-infrastructure/"), icon: "ph:chart-line-up", description: "Smarter data-driven decisions" },
						],
					},
				],
			},
		],
	},
	{
		label: "Resources",
		groups: [
			{
				heading: "Resources",
				columns: [
					{
						links: [
							{ label: "OpenTeams Blog", url: u("/blog/"), icon: "ph:newspaper" },
							{ label: "Engineering Blog", url: BLOG_PATH, icon: "ph:pen-nib" },
							{ label: "Case Studies", url: u("/case-studies/"), icon: "ph:notepad" },
						],
					},
				],
			},
		],
	},
	{
		label: "Company",
		groups: [
			{
				heading: "Company",
				columns: [
					{
						links: [
							{ label: "About Us", url: u("/about-us/"), icon: "ph:users-three" },
							{ label: "Press Room", url: u("/press/"), icon: "ph:microphone" },
							{ label: "Careers", url: u("/careers/"), icon: "ph:briefcase" },
						],
					},
				],
			},
		],
	},
];
