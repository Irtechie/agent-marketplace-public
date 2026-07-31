# Agent Marketplace Public

Public, reusable agent skills.

Each skill is a self-contained folder under `skills/`. Copy an individual
folder into a skill directory supported by your agent host; you do not need to
install the whole marketplace.

## Available Skills

| Skill | Purpose |
|---|---|
| [`interactive-workflow-workbench`](skills/interactive-workflow-workbench/) | Build evidence-grounded, interactive HTML workflow and architecture workbenches. |
| [`pr-review-workbench`](skills/pr-review-workbench/) | Turn a repository PR inbox into a terse, visual, minimum-evidence review workbench. |

Machine-readable discovery metadata lives in `catalog/skills.json`. A listed
SHA256 pins the complete normalized skill package.

## Trust

Review a skill before installing it. Marketplace inclusion means the published
files passed this repository's checks; it is not permission to bypass your
agent host's security, approval, or execution boundaries.

## License

Apache-2.0. See `LICENSE`.
