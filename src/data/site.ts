import { pageUrl } from "../lib/blog-path";
import { MAIN_SITE_URL } from "./main-site-nav";

export const SITE_TITLE = "OpenTeams";
/** How every page title ends, the same as on the main site. */
export const TITLE_ENDING = "OpenTeams | AI you own";
/** The main site's Google Analytics property, so blog visits are counted with it. */
export const ANALYTICS_ID = "G-P5T85K8QL2";
/**
 * The Engineering newsletter's HubSpot form ("Engineering blog signup") and
 * its subscription type. These IDs are public: any embed of the form shows
 * them. Signups land in HubSpot under Marketing, Forms.
 */
export const ENGINEERING_SIGNUP = {
	portalId: "48576056",
	formGuid: "4bb33d04-d180-414b-b548-71fe35117817",
	subscriptionTypeId: 4097849099,
};
/**
 * The clock dates are printed on. It is the one the main site used, so a
 * post keeps the date it had there wherever the site is built.
 */
export const DATE_ZONE = "America/Los_Angeles";
export const SITE_TAGLINE = "Building the Infrastructure for a Distributed AI Economy";

const u = (path: string) => `${MAIN_SITE_URL}${path}`;

export const footerColumns = [
	{
		heading: "Products",
		links: [
			{ label: "AI/ML Products", url: u("/ai-ml-products/") },
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
			{ label: "Engineering Blog", url: pageUrl() },
			{ label: "Case Studies", url: u("/case-studies/") },
			{ label: "Contact", url: u("/contact-us/") },
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
