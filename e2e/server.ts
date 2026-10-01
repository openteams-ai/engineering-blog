// Serves dist/ like Cloudflare static assets: a path maps to a file, a
// directory to its index.html, anything else is a 404.
import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize } from "node:path";

const TYPES: Record<string, string> = {
	".html": "text/html; charset=utf-8",
	".js": "text/javascript",
	".css": "text/css",
	".json": "application/json",
	".xml": "application/rss+xml",
	".svg": "image/svg+xml",
	".png": "image/png",
	".webp": "image/webp",
	".avif": "image/avif",
	".jpg": "image/jpeg",
	".woff2": "font/woff2",
};

export const PORT = 4399;

export default function setup() {
	// E2E_ORIGIN points the tests at a deployed copy instead.
	if (process.env.E2E_ORIGIN) return;
	const root = normalize(join(process.cwd(), "dist"));
	const server = createServer((req, res) => {
		const path = decodeURIComponent(new URL(req.url ?? "/", "http://x").pathname);
		let file = normalize(join(root, path));
		if (!file.startsWith(root)) return res.writeHead(403).end();
		if (existsSync(file) && statSync(file).isDirectory()) file = join(file, "index.html");
		if (!existsSync(file)) return res.writeHead(404).end("not found");
		res.writeHead(200, { "content-type": TYPES[extname(file)] ?? "application/octet-stream" });
		createReadStream(file).pipe(res);
	});
	server.listen(PORT);
	return () => new Promise<void>((done) => server.close(() => done()));
}
