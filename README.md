# CI failure triage agent

When a GitHub Actions run fails, this agent takes a **truncated** log, classifies the failure, and comments with a cited line — or returns `unknown`.

v1 is a single AWS account in `eu-west-1` (Bedrock Claude Haiku, Lambda, no VPC). Hard ceiling **$20/month**.

This repo is in **Week 0 setup**. The agent is not deployed yet.

See [IMPLEMENTATION.md](IMPLEMENTATION.md) for the plan, cost envelope, and week-by-week checklist.
