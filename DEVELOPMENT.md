# Development

<p>
  <a href="https://github.com/openteams-ai/engineering-blog/actions/workflows/ci.yml"><img src="https://github.com/openteams-ai/engineering-blog/actions/workflows/ci.yml/badge.svg?branch=main" alt="CI"></a>
  <a href="https://github.com/openteams-ai/engineering-blog/actions/workflows/deploy.yml"><img src="https://github.com/openteams-ai/engineering-blog/actions/workflows/deploy.yml/badge.svg?branch=main" alt="Deploy"></a>
</p>

For people changing the site's code or settings. Writing a post? You only need the [README](README.md).

## Develop

```bash
npm install
npm run dev          # http://localhost:4321/engineering-blog
npm run build
npm run og           # share cards into dist/ (needed before test:e2e)
npm test             # unit tests
npm run test:e2e     # browser tests against the build
```

## Secrets

| Secret | Used by |
| --- | --- |
| `CLOUDFLARE_API_TOKEN` | `deploy.yml` |
| `SLACK_PR_WEBHOOK` | `notify-pr.yml`: new post PRs |
| `SLACK_PUBLISH_WEBHOOK` | `deploy.yml`: new posts live |
| `SLACK_ACCESS_REQUEST_WEBHOOK` | `grant-write-access.yml`: guest requests |
| `ACCESS_ADMIN_TOKEN` | `grant-write-access.yml`: fine-grained, Administration: write on this repo, Members: read on the org |

## Guest access requests

Guest requests stay open for you to decide, and are posted in the blog's Slack channel. To approve, invite the guest with the Write role under Settings → Collaborators and teams, and remove them after the post merges. Only invite people you'd trust with the repo's secrets: workflows on branches in this repo run with the Cloudflare and Slack credentials.

```bash
# Invite (push = Write)
gh api -X PUT repos/openteams-ai/engineering-blog/collaborators/<username> -f permission=push
# Remove after the post merges
gh api -X DELETE repos/openteams-ai/engineering-blog/collaborators/<username>
```
