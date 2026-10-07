// Create an empty social/<slug>.yml for each post that doesn't have one yet.
// An existing brief is never overwritten, since it may already hold answers.
//
//   node scripts/social/create-brief.ts posts/my-post.md [more posts...]
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { SOCIAL_DIR, briefPath, renderTemplate } from "../../src/lib/social-brief.ts";

for (const post of process.argv.slice(2)) {
	const brief = briefPath(post, readFileSync(post, "utf8"));
	if (existsSync(brief)) {
		console.log(`Keeping existing ${brief}`);
		continue;
	}
	mkdirSync(SOCIAL_DIR, { recursive: true });
	writeFileSync(brief, renderTemplate(post));
	console.log(`Created ${brief}. Answer its questions, then push.`);
}
