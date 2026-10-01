import { defineConfig } from "vitest/config";

// Browser tests against the built site (run `npm run build` first).
export default defineConfig({
	test: {
		environment: "node",
		include: ["e2e/**/*.test.ts"],
		globalSetup: ["e2e/server.ts"],
		// One line per page and check as each finishes, so CI shows progress.
		reporters: ["verbose"],
		testTimeout: 180_000,
		hookTimeout: 180_000,
	},
});
