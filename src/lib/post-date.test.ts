import { describe, expect, it } from "vitest";
import { postDate } from "./post-date";

describe("postDate", () => {
	it("accepts the Date YAML makes from an unquoted 2026-10-07", () => {
		const date = new Date("2026-10-07");
		expect(postDate.parse(date)).toEqual(date);
	});

	it("reads a quoted YYYY-MM-DD as that day in UTC", () => {
		expect(postDate.parse("2026-10-07").toISOString()).toBe("2026-10-07T00:00:00.000Z");
	});

	it.each([null, undefined, 0, false, 20261007])("rejects %s instead of falling back to 1970", (value) => {
		expect(postDate.safeParse(value).success).toBe(false);
	});

	it.each(["", "garbage", "2026-10-7", "Oct 7 2026", "2026-13-45"])("rejects the text %j", (value) => {
		expect(postDate.safeParse(value).success).toBe(false);
	});
});
