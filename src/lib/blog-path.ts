/**
 * URL path the blog is served under. Every page and file lives below it,
 * so one route (openteams.com<BLOG_PATH>*) serves the whole site.
 */
export const BLOG_PATH = "/sandbox-4af53e-engineering-blog";

/** Absolute URL path for a page or file inside the blog. */
export const blogUrl = (path = "") => `${BLOG_PATH}${path}`;
