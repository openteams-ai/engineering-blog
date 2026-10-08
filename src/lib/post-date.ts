// A post's `date` and `updated` frontmatter. YAML turns an unquoted
// 2026-10-07 into a Date; a quoted one stays a string. Anything else fails
// the build: z.coerce.date() alone turns an empty field, a number or `false`
// into 1970-01-01, and reads "2026-10-7" in local time, a day early in UTC.
import { z } from "astro/zod";

const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/;

export const postDate = z
	.union([z.date(), z.string().regex(ISO_DAY)], { error: "must be a date written as YYYY-MM-DD" })
	.pipe(z.coerce.date({ error: "must be a real calendar date, written as YYYY-MM-DD" }));
