// Fail unless every given post has a fully answered social/<slug>.yml.
//
// Runs as the `social-brief` check on pull requests that add a post. Inside
// GitHub Actions each problem is also an error annotation on the brief file,
// and --comment writes the body of the PR comment that asks the author to
// fill the brief in.
//
//   node scripts/social/check-brief.ts posts/my-post.md [more posts...]
//   node scripts/social/check-brief.ts --comment comment.md posts/my-post.md
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { parseArgs } from "node:util";
import { MISSING, briefPath, createUrl, editUrl, findProblems, renderComment, type Result } from "../../src/lib/social-brief.ts";

const { values, positionals } = parseArgs({ options: { comment: { type: "string" } }, allowPositionals: true });
const env = process.env;

const results: Result[] = positionals.map((post) => {
	const brief = briefPath(post, readFileSync(post, "utf8"));
	return { post, brief, problems: findProblems(existsSync(brief) ? readFileSync(brief, "utf8") : null) };
});

for (const { post, brief, problems } of results) {
	if (problems.length === 0) {
		console.log(`✅ ${brief}`);
		continue;
	}
	const link = problems.includes(MISSING) ? createUrl(post, brief, env) : editUrl(brief, env);
	for (const problem of problems) {
		const message = `${brief}: ${problem}` + (link ? ` Fix it here: ${link}` : "");
		console.log(`❌ ${message}`);
		if (env.GITHUB_ACTIONS === "true") console.log(`::error file=${brief}::${message}`);
	}
}

if (values.comment && results.length > 0) writeFileSync(values.comment, renderComment(results, env));
process.exitCode = results.some((r) => r.problems.length > 0) ? 1 : 0;
