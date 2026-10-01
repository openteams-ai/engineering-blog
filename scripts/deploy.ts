// Deploy dist/ to the Worker and point openteams.com<BLOG_PATH> at it.
// `wrangler deploy` with routes replaces every route on the Worker, so routes
// outside BLOG_PATH are removed.
//
//   node scripts/deploy.ts            production
//   node scripts/deploy.ts pr-12      preview version, routes untouched
import { execFileSync } from "node:child_process";
import { existsSync } from "node:fs";
import { BLOG_PATH } from "../src/lib/blog-path.ts";

const HOST = "openteams.com";

if (!existsSync(`dist${BLOG_PATH}/index.html`)) {
	throw new Error(`dist${BLOG_PATH}/index.html missing: run npm run build first`);
}

const alias = process.argv[2];
const args = alias
	? ["versions", "upload", "--preview-alias", alias]
	: ["deploy", "--route", `${HOST}${BLOG_PATH}`, "--route", `${HOST}${BLOG_PATH}/*`];

execFileSync("npx", ["wrangler", ...args], { stdio: "inherit" });
