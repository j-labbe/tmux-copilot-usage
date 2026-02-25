Perfect correction - you're right.

For what you want, the source of truth should be GitHub Billing/Copilot usage APIs, not OpenCode local stats.

Because both VS Code Copilot and OpenCode (when using Copilot-backed billing) hit the same GitHub account, your tmux display should reflect combined usage from both.

## What to use

- Use GitHub REST billing endpoints (user or org):
  - `GET /users/{username}/settings/billing/premium_request/usage`
  - `GET /users/{username}/settings/billing/usage/summary`
  - Org equivalents under `/organizations/{org}/settings/billing/...`
- These endpoints are documented and intended for account-level billing usage.
- Copilot metrics endpoints (`/copilot/metrics`) are more activity/engagement oriented, not ideal for credits-remaining style tracking.

## Important reality

- There is not a clean documented endpoint that directly returns `remaining_premium_credits`.
- What you can reliably get:
  - premium request usage by month/day/model/product
  - billable vs discounted quantities/amounts (`grossQuantity`, `discountQuantity`, `netQuantity`)
- So the tmux widget should show:
  - this month premium requests used
  - this month billable premium requests
  - this month Copilot spend
  - optional model breakdown (GPT-5, Claude, etc.)

## Build plan (recommended)

1) Data fetcher script (`bash` or `python`; Python is easier for JSON)

- Resolve identity (`/user`) and mode (user vs org)
- Pull monthly premium usage + summary usage
- Normalize into one cache JSON:
  - `updated_at`
  - `premium_requests_total`
  - `premium_requests_billable`
  - `copilot_spend_usd`
  - `by_model[]`

2) Local cache layer

- Write cache to `~/.cache/copilot-usage/status.json`
- Fetch every 60-120s (not on every tmux repaint)
- Keep last good value + error field for resilience

3) tmux status renderer

- Tiny script reads cache and prints compact text, for example:
  - `Copilot: 182 req | billable 41 | $3.28 | 14:37`

4) tmux plugin wrapper

- TPM-style plugin with settings:
  - `@copilot_usage_token` (or env var)
  - `@copilot_usage_scope` (`user|org|auto`)
  - `@copilot_usage_org`
  - `@copilot_usage_refresh_seconds`
- Hook into `status-right` via `#(script)`

5) Security

- Prefer `GITHUB_TOKEN` env var over storing PAT in tmux.conf
- Required permissions:
  - user scope: fine-grained PAT with user `Plan:read`
  - org scope: org `Administration:read` (or equivalent documented permission)

6) Validation

- Compare API output against GitHub billing UI for same month/day
- Confirm switching between VS Code and OpenCode updates the same counters

## MVP timeline

- Day 1: fetcher + cache + standalone terminal output
- Day 2: tmux plugin + config + docs
- Day 3: polish (error handling, stale-data indicator, model breakdown toggle)
