// Tell Slack about posts that just went live. Run after the production deploy
// with the post files the push added. Edits to live posts aren't announced.
//
//   node scripts/notify-published.ts posts/my-post.md ...
//
// Without SLACK_PUBLISH_WEBHOOK it prints what it would send. A failed send
// is a warning, not an error: the post is already live.
import { readFileSync } from "node:fs";
import authors from "../authors.json" with { type: "json" };
import { announcement } from "../src/lib/new-posts.ts";

const webhook = process.env.SLACK_PUBLISH_WEBHOOK;

for (const file of process.argv.slice(2)) {
	const body = announcement(readFileSync(file, "utf8"), authors);
	if (!webhook) {
		console.log(`Would announce: ${JSON.stringify(body)}`);
		continue;
	}
	try {
		const res = await fetch(webhook, {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(body),
			signal: AbortSignal.timeout(30_000),
		});
		console.log(res.ok ? `Announced: ${body.post_url}` : `::warning::Slack answered ${res.status} for ${file}`);
	} catch (err) {
		console.log(`::warning::Could not reach Slack for ${file}: ${err}`);
	}
}
