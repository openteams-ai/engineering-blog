// The social brief: four short answers about a post, written by its author,
// that seed its LinkedIn post. One social/<slug>.yml per post.
//
// The questions are what authors (and their AI assistants) see as comments in
// the brief, so they are written for a human reader.
import { basename, extname } from "node:path";
import { parse } from "yaml";
import { frontmatter } from "./new-posts.ts";

export const SOCIAL_DIR = "social";
// Short enough to reject one-liners like "Compares package managers.", long
// enough to pass every example in the fill-social-brief skill.
export const MIN_WORDS = 8;

export const AUDIENCES = [
	"data-scientists",
	"ml-ai-engineers",
	"python-developers",
	"platform-devops-engineers",
	"security-compliance-engineers",
	"oss-maintainers",
	"engineering-leaders",
] as const;

/** The questions, in the order they appear in the file. */
export const QUESTIONS = [
	{ name: "problem", text: "What problem does this article solve? (1-2 sentences)" },
	{ name: "what_it_does", text: "What does the article build, test, compare, or argue? (1-2 sentences)" },
	{ name: "remember_one_thing", text: "If readers remember one thing, what should it be? (1 sentence)" },
	{ name: "audience", text: "Who should read this? Pick one or more:" },
] as const;

export const COMMENT_HEADER = "### Social brief";
// The comment's link already says to answer the questions, so it skips this one.
export const UNANSWERED = "Its 4 questions are unanswered.";
// Likewise for a missing brief: the comment links straight to creating it.
export const MISSING = "The brief is missing.";

/** social/<slug>.yml for a post, by its frontmatter slug, else its file name. */
export function briefPath(postPath: string, markdown: string): string {
	const slug = frontmatter(markdown).slug;
	return `${SOCIAL_DIR}/${slug || basename(postPath, extname(postPath))}.yml`;
}

/** The brief with every answer empty, for the author to fill in. */
export function renderTemplate(postPath: string): string {
	const lines = [
		`# The social brief for ${postPath}. It's used to write the LinkedIn post.`,
		"# Answer each question yourself or with your AI assistant (see Social Brief in",
		"# README.md). The PR can merge once all four are answered.",
	];
	for (const q of QUESTIONS) {
		lines.push("", `# ${q.text}`);
		if (q.name === "audience") lines.push(`# ${AUDIENCES.join(", ")}`);
		// JSON is valid YAML and always quotes, so a colon or leading dash in
		// an answer can't change how the file parses.
		lines.push(`${q.name}: ${q.name === "audience" ? "[]" : '""'}`);
	}
	return lines.join("\n") + "\n";
}

const words = (value: string) => value.split(/\s+/).filter(Boolean).length;

function textProblem(name: string, value: unknown): string | null {
	if (value != null && typeof value !== "string") return `\`${name}\` should be text.`;
	const count = words(value ?? "");
	if (count === 0) return `\`${name}\` is empty.`;
	if (count < MIN_WORDS) {
		return (
			`\`${name}\` is only ${count} word${count === 1 ? "" : "s"}. Say more: at least ${MIN_WORDS} words, ` +
			"with the article's specifics (tools, numbers, what was tested or argued)."
		);
	}
	return null;
}

function audienceProblems(value: unknown): string[] {
	if (!Array.isArray(value) || value.length === 0) {
		return ["`audience` needs at least one group from the list in the brief."];
	}
	return value
		.filter((group) => !(AUDIENCES as readonly unknown[]).includes(group))
		.map((group) => `\`audience\` has \`${group}\`, which isn't one of the groups listed in the brief.`);
}

/** One fix-it message per problem with a brief's text, or `null` when there is no brief. */
export function findProblems(briefText: string | null): string[] {
	if (briefText === null) return [MISSING];
	const data = (parse(briefText) ?? {}) as Record<string, unknown>;
	const isBlank = !QUESTIONS.some((q) => {
		const value = data[q.name];
		return Array.isArray(value) ? value.length > 0 : Boolean(value);
	});
	if (isBlank) return [UNANSWERED];
	return [
		...QUESTIONS.filter((q) => q.name !== "audience").flatMap((q) => textProblem(q.name, data[q.name]) ?? []),
		...audienceProblems(data.audience),
	];
}

type Env = Record<string, string | undefined>;

/** A github.com URL for a repo named in the environment, or "" outside CI. */
function githubUrl(path: string, env: Env, repoVar = "GITHUB_REPOSITORY"): string {
	const repo = env[repoVar] || env.GITHUB_REPOSITORY;
	if (!repo) return "";
	return `${env.GITHUB_SERVER_URL || "https://github.com"}/${repo}/${path}`;
}

/** A URL in the repo the PR comes from, which is a fork for outside PRs. */
function headUrl(path: (branch: string) => string, env: Env): string {
	const branch = env.HEAD_REF || env.GITHUB_HEAD_REF;
	return branch ? githubUrl(path(branch), env, "HEAD_REPO") : "";
}

/** The GitHub web editor for the brief on the PR's branch. */
export const editUrl = (brief: string, env: Env) => headUrl((branch) => `edit/${branch}/${brief}`, env);

/** GitHub's "new file" page on the PR's branch, pre-filled with the template. */
export const createUrl = (post: string, brief: string, env: Env) =>
	headUrl(
		(branch) =>
			`new/${branch}?filename=${encodeURIComponent(brief).replaceAll("%2F", "/")}&value=${encodeURIComponent(renderTemplate(post))}`,
		env,
	);

export interface Result {
	post: string;
	brief: string;
	problems: string[];
}

/** The PR comment: what to fill in while problems remain, thanks once done. */
export function renderComment(results: Result[], env: Env): string {
	const pending = results.filter((r) => r.problems.length > 0);
	if (pending.length === 0) {
		const briefs = results.map((r) => `\`${r.brief}\``).join(", ");
		return `${COMMENT_HEADER} ✅\n\nThanks! ${briefs} is filled in, so this check passes.\n`;
	}

	// A PR comment resolves relative links against the PR's URL, not the repo,
	// so the README link has to be absolute.
	const readme = githubUrl("blob/main/README.md#social-brief", env);
	const guide = readme ? `[Social Brief](${readme})` : "Social Brief";
	const lines = [
		`${COMMENT_HEADER} needed`,
		"",
		"Before this PR can merge, please answer 4 short questions about your post. " +
			"We use them to write its LinkedIn post.",
		"",
	];
	for (const { post, brief, problems } of pending) {
		const [link, action] = problems.includes(MISSING)
			? [createUrl(post, brief, env), `Create \`${brief}\` and answer its questions`]
			: [editUrl(brief, env), `Answer the questions in \`${brief}\``];
		lines.push(link ? `👉 **[${action}](${link})**` : `👉 **${action}**`);
		lines.push(...problems.filter((p) => p !== UNANSWERED && p !== MISSING).map((p) => `- ${p}`));
		lines.push("");
	}
	lines.push(
		"To fill it in, either:",
		"",
		"- **In the browser:** click the link above, answer the questions, and commit.",
		"- **With an AI assistant:** `git pull`, then run `/fill-social-brief " +
			`${pending[0].post}\` (or ask any agent to fill in the brief from the post). ` +
			"Check its answers, then push.",
		"",
		`See ${guide} in the README for what each question means, with examples. ` +
			"This comment updates on every push.",
	);
	return lines.join("\n") + "\n";
}
