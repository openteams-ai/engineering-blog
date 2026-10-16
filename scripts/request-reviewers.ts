// Request reviews on a post PR from the people signed up for each new post's
// topic in the sign-up issue. Edits to published posts don't get any.
//
//   GH_TOKEN=... node scripts/request-reviewers.ts 42
//
// Outside GitHub Actions it prints who it would request. The post files are
// read from the PR's head through the API, as data: nothing from the PR runs.
import { postTopic, reviewers, signupComment, type IssueComment } from "../src/lib/topic-reviewers.ts";

const SIGNUP_ISSUE = 55;
const API = "https://api.github.com";
const repo = process.env.GITHUB_REPOSITORY ?? "openteams-ai/engineering-blog";
const pr = process.argv[2];
const dryRun = !process.env.GITHUB_ACTIONS;

async function github(path: string, init: RequestInit = {}): Promise<Response> {
	const res = await fetch(`${API}${path}`, {
		...init,
		headers: {
			Accept: "application/vnd.github+json",
			Authorization: `Bearer ${process.env.GH_TOKEN}`,
			...init.headers,
		},
		signal: AbortSignal.timeout(30_000),
	});
	if (!res.ok && res.status !== 422) throw new Error(`GitHub answered ${res.status} for ${path}`);
	return res;
}

/** Every item of a list endpoint, page by page. */
async function all<T>(path: string): Promise<T[]> {
	const items: T[] = [];
	for (let page = 1; ; page++) {
		const sep = path.includes("?") ? "&" : "?";
		const batch: T[] = await (await github(`${path}${sep}per_page=100&page=${page}`)).json();
		items.push(...batch);
		if (batch.length < 100) return items;
	}
}

const pull = await (await github(`/repos/${repo}/pulls/${pr}`)).json();
const files = await all<{ filename: string; status: string }>(`/repos/${repo}/pulls/${pr}/files`);
const added = files
	.filter((f) => f.status === "added" && /^posts\/[^/]+\.md$/.test(f.filename))
	.map((f) => f.filename);
if (added.length === 0) {
	console.log("No new posts.");
	process.exit(0);
}

const issue = await (await github(`/repos/${repo}/issues/${SIGNUP_ISSUE}`)).json();
const comments = await all<IssueComment>(`/repos/${repo}/issues/${SIGNUP_ISSUE}/comments`);

const voters: string[] = [];
for (const file of added) {
	const markdown = await (
		await github(`/repos/${pull.head.repo.full_name}/contents/${file}?ref=${pull.head.sha}`, {
			headers: { Accept: "application/vnd.github.raw" },
		})
	).text();
	const topic = postTopic(markdown);
	const comment = topic && signupComment(comments, issue.user.login, topic);
	if (!comment) {
		console.log(`::warning::No sign-up comment for ${file} (topic: ${topic ?? "none"})`);
		continue;
	}
	const reactions = await all<{ user: { login: string } }>(
		`/repos/${repo}/issues/comments/${comment.id}/reactions?content=%2B1`,
	);
	const logins = reactions.map((r) => r.user.login);
	console.log(`${file} (${topic}): ${logins.join(", ") || "nobody"}`);
	voters.push(...logins);
}

// One request per person: GitHub rejects the whole list if any one login
// can't review, such as someone without access to the repo.
for (const login of reviewers(voters, pull.user.login)) {
	if (dryRun) {
		console.log(`Would request ${login}`);
		continue;
	}
	const res = await github(`/repos/${repo}/pulls/${pr}/requested_reviewers`, {
		method: "POST",
		body: JSON.stringify({ reviewers: [login] }),
	});
	console.log(res.ok ? `Requested ${login}` : `::warning::Could not request ${login}`);
}
