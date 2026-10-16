// Who reviews a new post: the people who put a 👍 on its topic's comment in
// the sign-up issue. The GitHub calls live in scripts/request-reviewers.ts.
import { TOPICS, type Topic } from "../data/topics.ts";
import { frontmatter } from "./new-posts.ts";

export interface IssueComment {
	id: number;
	body: string;
	user: { login: string };
}

/** The post's topic, or undefined when it's missing or not one the site knows. */
export function postTopic(markdown: string): Topic | undefined {
	const topic = frontmatter(markdown).topic;
	return TOPICS.find((t) => t === topic);
}

/**
 * The topic's sign-up comment: one by the issue's author that links the topic
 * page. Comments by anyone else are ignored, so they can't add reviewers.
 */
export function signupComment(
	comments: IssueComment[],
	issueAuthor: string,
	topic: Topic,
): IssueComment | undefined {
	return comments.find((c) => c.user.login === issueAuthor && c.body.includes(`/tag/${topic}/`));
}

/** Everyone who signed up, once each, minus the PR's author (who can't review their own PR). */
export function reviewers(voters: string[], prAuthor: string): string[] {
	return [...new Set(voters)].filter((login) => login !== prAuthor);
}
