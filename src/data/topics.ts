// The topics a post can pick in its frontmatter `topic` field, with the
// label its badge shows.
export const TOPIC_LABELS = {
	"llms-inference": "LLMs & Inference",
	"ai-engineering": "AI Engineering",
	"python-tooling": "Python Tooling",
	practices: "Practices",
	infrastructure: "Infrastructure",
} as const;

export type Topic = keyof typeof TOPIC_LABELS;

export const TOPICS = Object.keys(TOPIC_LABELS) as [Topic, ...Topic[]];
