# CI failure triage agent

When a GitHub Actions run fails, an agent fetches a **truncated** log, classifies the failure, and comments with a cited line — or returns `unknown`. Infra is **Terraform**. Hard ceiling **$20/month USD**.

Check boxes as you finish them. Do not start Terraform apply until the preprocessor and replay evals work on disk.

**Status (25 Sep 2026):** Week 0 and Week 1 are done — schema, preprocessor (150 lines / 24k cap), pytest + schema tests (12 passing, no AWS/Bedrock), CI runs `uv run pytest` on push/PR. **Next:** Week 2 local agent loop (Bedrock Converse + tools over fixture files). No `terraform apply`.

---

## Product

- [ ] One-sentence demo works: red CI → comment with the right class and a cited log line
- [ ] Duplicate webhook deliveries do not call Bedrock twice (`run_id` idempotency)
- [ ] Invalid model JSON is rejected; the model cannot post comments directly

### In scope (v1)

- [ ] Ingest `workflow_run` completed + failure via webhook
- [ ] Verify `X-Hub-Signature-256`
- [x] Preprocess logs (failed step, last ~150 lines, error/FAIL grep; never the raw MB log)
- [ ] Bedrock **Claude Haiku** agent, max 4 tool rounds, structured JSON result
- [ ] Classify: `flake` | `product_regression` | `infra` | `test_bug` | `unknown`
- [ ] Comment on the SHA/PR with excerpt + recommended action
- [ ] ≥25 golden fixtures in git; PR CI is **replay-only** (no Bedrock)
- [ ] Terraform to **one** AWS account (staging only) via GitHub OIDC
- [ ] Cost controls: token caps, monthly Bedrock counter, AWS Budget at $20

### Out of scope (v1)

Do not build these until the $20 cap has been boring for a month.

- [ ] ~~Auto-fix PRs~~
- [ ] ~~Auto-rerun jobs~~
- [ ] ~~Slack~~
- [ ] ~~GitHub App marketplace listing~~
- [ ] ~~Similar-failure search~~
- [ ] ~~Sonnet / Opus~~
- [ ] ~~Knowledge Bases / OpenSearch~~
- [ ] ~~VPC / NAT Gateway~~
- [ ] ~~Custom domain~~
- [ ] ~~Prod vs staging split~~
- [ ] ~~LLM-as-judge~~
- [ ] ~~Private repo GitHub Actions minutes~~

If a week slips, cut in this order: GitHub App (keep PAT), Sunday live evals, `get_commit_files`, JUnit. **Do not cut** the preprocessor, result schema, or budget counter.

---

## Architecture

```
GitHub workflow_run (failure)
  → API Gateway HTTP API (HMAC)
  → Lambda Python 3.12 (512 MB, 60s)
      → DynamoDB (idempotency, budget counter, audit)
      → S3 (traces, 30-day expiry)
      → Bedrock Converse + toolConfig (eu-west-1, Haiku)
      → GitHub comment (after schema validation)
```

### Tools the model may call

| Tool | Returns | Guard |
|---|---|---|
| `get_workflow_run` | name, SHA, branch, conclusion, jobs | `run_id` from the webhook only |
| `get_failed_job_log` | Preprocessed excerpt | ~6k tokens / 24k chars; failed step only |
| `get_junit_summary` | Failed test names, file, message | Empty + reason if no JUnit artifact |
| `get_commit_files` | Paths changed on the SHA | Path list only; no file bodies in v1 |

There is **no** `post_comment` tool. Lambda posts after validation.

### Result schema (reject if invalid)

- [x] `classification`
- [x] `confidence` (0–1)
- [x] `summary` (≤280 chars)
- [x] `evidence[]`: `source` (`log` \| `junit` \| `commit`) + `excerpt` + `pointer`
- [x] `recommended_action`: `fix_code` \| `fix_test` \| `retry_later` \| `needs_human`
- [x] `cited_log_line` required unless classification is `unknown`

---

## $20 / month envelope

Application **hard-stop** at **$14 estimated Bedrock** in a calendar month. If the counter would exceed $14, Lambda comments `budget paused` and does not call Bedrock.

| Bucket | Cap | Notes |
|---|---:|---|
| Bedrock Haiku (enforced in code) | $14 | ~500 truncated triages, or light use + 20 Sunday evals |
| Lambda, API Gateway, DynamoDB, S3 | $2 | Should be cents |
| CloudWatch (errors only, 7-day retention) | $1 | No full prompt logging |
| Buffer | $3 | One mistake must not blow the month |
| GitHub Actions | $0 | Public repo, standard Linux runners |
| **Total** | **$20** | Planning number, not a hope |

Rough Haiku math after truncation: ~15–20k input + ~800 output ≈ **$0.02–0.03** per failure.

### Controls (must all be true before week 5 webhook)

- [ ] Model is Claude Haiku only (`ALLOW_SONNET` unset in deployed env)
- [ ] Log preprocessor: failed job only; last 150 lines; max 24k characters into the model
- [ ] Agent loop: max 4 tool rounds; `max_tokens` set on Converse
- [ ] Idempotency: one Bedrock session per GitHub `run_id`
- [ ] Live evals: 20 cases, Sunday only, skipped if month-to-date spend > $8
- [ ] PR CI: replay fixtures only — **zero** Bedrock
- [ ] No VPC, no NAT, no OpenSearch, no Knowledge Bases
- [ ] Traces as JSON on S3 (lifecycle 30 days), not CloudWatch Logs
- [ ] Region: `eu-west-1` for Bedrock availability
- [ ] AWS Budget: $10 info, $16 warn, $20 actual (include Marketplace / Anthropic)

---

## Repo layout (target)

```
ci-triage-agent/
  IMPLEMENTATION.md          ← this file
  README.md
  pyproject.toml
  src/ci_triage/             agent, preprocess, tools, budget, GitHub client
  tests/                     pytest: tools, preprocessor, schema, replay
  evals/fixtures/            sanitized logs + expected classification
  evals/cases.yaml
  scripts/triage_local.py    CLI over a saved log
  infra/                     Terraform (flat files, no modules in v1)
    bootstrap/               one-off S3 backend + lock table
    backend.tf
    providers.tf
    variables.tf
    outputs.tf
    lambda.tf
    apigateway.tf
    dynamodb.tf
    s3.tf
    iam.tf
    oidc.tf
    budget.tf
    secrets.tf
  .github/workflows/
    ci.yml                   lint, pytest, replay evals, terraform fmt/validate/plan
    deploy.yml               OIDC → terraform apply on main
    weekly-eval.yml          Sunday live evals (skip if spend high)
```

Python 3.12 for the agent and tests. **HCL** for infra. Do not introduce CDK.

---

## Week 0 — Setup

Do this before writing agent code.

- [x] AWS account ready; you can sign in (IAM Identity Center SSO user, not root)
- [x] Enable **Claude Haiku** on Bedrock in `eu-west-1` (access is not automatic)
- [x] Confirm with a tiny Converse ping (< $0.001) — `eu.anthropic.claude-haiku-4-5-20251001-v1:0` returned `pong`
- [x] Create AWS Budget: $10 / $16 / $20, email to you, include Marketplace/Anthropic
- [x] Create a **public** GitHub repo for this project (Actions minutes stay $0) — [`PaulieWalnuts147/ci-triage-agent`](https://github.com/PaulieWalnuts147/ci-triage-agent)
- [x] Copy this file to the repo root if it is not already there
- [x] Python 3.12 installed — uv pin `.python-version`; `uv run python --version` is 3.12.12 (Homebrew `python3` may still be 3.14; ignore it in this repo)
- [x] Terraform CLI installed — `terraform version` is v1.16.3 (no `infra/` skeleton until Week 3)
- [x] AWS CLI installed and configured for the account (`aws configure sso`, profile `davidnsso`)
- [ ] Decide fixture-repo name (e.g. `ci-triage-fixtures`) — can wait until week 5
- [x] Agree: no Lambda-in-VPC experiments (NAT is how POCs become $50)

---

## Week 1 — Domain (no AWS in tests)

- [x] `pyproject.toml` + package `ci_triage`
- [x] Pydantic result schema and classification enum (`src/ci_triage/schema.py`)
- [x] Log preprocessor with hard character cap (`src/ci_triage/preprocess.py`)
- [x] Pytest: synthetic **flake** log (`tests/fixtures/flake.log`)
- [x] Pytest: synthetic **pytest assertion** failure (`tests/fixtures/pytest_assert.log`)
- [x] Pytest: synthetic **npm 503 / registry** infra failure (`tests/fixtures/npm_503.log`)
- [x] Pytest: synthetic **OOM / runner killed** infra failure (`tests/fixtures/oom.log`)
- [x] Preprocessor tests prove the cap cannot be exceeded (`over_char_cap.log`)
- [x] `pytest` is green with **no** AWS and **no** Bedrock calls (12 tests; also `tests/test_schema.py`)

**Done when:** preprocessor never exceeds the char cap; tests do not call AWS.

---

## Week 2 — Local agent loop

- [ ] Bedrock Converse client with `toolConfig`
- [ ] Tool implementations over **fixture files** (fake GitHub)
- [ ] CLI: `python -m ci_triage path/to/log` (or `scripts/triage_local.py`)
- [ ] Output always validates against the Pydantic schema
- [ ] Traces written to local JSON
- [ ] Max 4 tool rounds enforced in code
- [ ] Save ~10 manual traces for later eval labelling

**Done when:** the CLI prints valid JSON for fixture logs.

---

## Week 3 — Evals in CI (still no apply)

- [ ] `evals/cases.yaml` with **25** labelled fixtures
- [ ] Replay runner: canned model events, no Bedrock
- [ ] GitHub Action `ci.yml`: lint, pytest, replay evals
- [ ] PR fails if replay score drops
- [ ] README (or this file) shows replay score, e.g. 25/25
- [ ] `infra/` skeleton: `versions.tf`, `providers.tf`, `variables.tf`
- [ ] `terraform fmt -check` and `terraform validate` in `ci.yml` (no apply)
- [ ] Optional: `tflint` on PRs

**Done when:** a PR that breaks a golden case goes red; CI never calls Bedrock.

---

## Week 4 — Terraform on AWS

Bootstrap state **once**, by hand or via `infra/bootstrap`. This is a few cents/month (S3 + tiny DynamoDB). Do not use local state on `main`.

- [ ] Bootstrap: S3 state bucket (versioned, encryption, no public access)
- [ ] Bootstrap: DynamoDB table for state locking
- [ ] Remote backend configured in `infra/backend.tf`
- [ ] GitHub OIDC provider + IAM role (`oidc.tf`) — **no long-lived AWS keys in GitHub**
- [ ] HTTP API Gateway
- [ ] Lambda (Python 3.12, 512 MB, 60s timeout) from a built zip or container image **without** a NAT/VPC
- [ ] DynamoDB table: idempotency / audit / budget counter
- [ ] S3 traces bucket + 30-day lifecycle
- [ ] SSM (or Secrets Manager) for webhook secret + GitHub PAT
- [ ] IAM least privilege: Lambda can Converse Haiku, read/write its DDB/S3, read SSM, call nothing else
- [ ] `aws_budgets_budget` (or confirm the console budget from week 0)
- [ ] Outputs: API URL, Lambda name, bucket, table
- [ ] `deploy.yml`: on `main`, OIDC → `terraform plan` → `terraform apply`
- [ ] `ci.yml`: on PRs, `terraform plan` (no apply) and post/store the plan
- [ ] Health/ping route on the API
- [ ] Confirm month-to-date AWS spend is still ≈ $0–1

**Done when:** Actions can apply from `main`, you can curl the health route, and there is no NAT Gateway in the plan.

---

## Week 5 — Wire GitHub

- [ ] Fixture repo with planted failing workflows (assertion, flake-ish timeout, fake 503)
- [ ] Webhook (or `workflow_run` via GitHub App / repo hook) pointing at the API
- [ ] HMAC verification live
- [ ] Fine-grained PAT in SSM (contents/actions read, PR/commit comment write)
- [ ] Idempotency on `run_id`
- [ ] Budget counter increments by estimated token cost
- [ ] Over-budget path posts `budget paused` and skips Bedrock
- [ ] Comment posted on the failing SHA/PR
- [ ] Duplicate delivery test: second webhook does not bill twice
- [ ] End-to-end: push a bad test → red run → correct class + cited line

**Done when:** the planted assertion failure is classified `product_regression` or `test_bug` with a real excerpt, not a hallucinated stack frame.

---

## Week 6 — Demo and cost proof

- [ ] README: what it is, architecture, example comment, how to run locally
- [ ] README: eval score and link to a redacted S3/trace example (or committed sample trace)
- [ ] Weekly eval workflow: Sunday, 20 live Haiku cases, skip if spend > $8
- [ ] Kill-switch documented: IAM deny on `bedrock:InvokeModel` / Converse
- [ ] Screenshot or export of the $20 AWS Budget
- [ ] 3-minute recording of the fixture-repo demo
- [ ] Calendar-month projection ≤ $20 at expected volume
- [ ] Optional: replace PAT with a GitHub App private key in SSM

**Done when:** a stranger can understand the repo from the README, and you would not be afraid to leave the stack up for a month.

---

## Week 0 command scratchpad

```bash
uv run python --version    # 3.12.x (not Homebrew python3)
terraform version          # 1.9+
aws sts get-caller-identity --profile davidnsso

# Working ping (eu-west-1 needs the EU inference profile, not the bare model id):
aws bedrock-runtime converse \
  --profile davidnsso \
  --region eu-west-1 \
  --model-id eu.anthropic.claude-haiku-4-5-20251001-v1:0 \
  --messages '[{"role":"user","content":[{"text":"Reply with the single word pong."}]}]' \
  --inference-config '{"maxTokens":8}'
```

Model IDs change; keep using the Haiku **EU inference profile** in `eu-west-1`. Keep `maxTokens` tiny for the ping.

---

## Definition of done (v1)

- [ ] Public repo with Terraform, Python agent, replay evals in CI, OIDC apply on main
- [ ] Fixture failure produces a correct, evidenced comment
- [ ] Budget counter + AWS Budget both in place
- [ ] No NAT, no OpenSearch, no prompt logging to CloudWatch
- [ ] You can pause Bedrock with one IAM change
