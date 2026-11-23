// Days a post was shared on LinkedIn. LinkedIn's mobile app drops the
// referrer, so readers who tap the link there show up as Direct. On the share
// day and the day after, ga-report.ts moves a post's Direct visits above its
// usual level to "LinkedIn (estimated)". Add a line when you share a post
// without a UTM-tagged link.
export const SOCIAL_SHARES: { slug: string; date: string }[] = [
	{ slug: "unlimited-ocr-2-long-pdf-tables", date: "2026-11-10" },
];
