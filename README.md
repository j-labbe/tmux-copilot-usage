# copilot-usage

tmux plugin that shows GitHub Copilot billing usage (combined across VS Code Copilot and OpenCode when both bill the same GitHub account).

## What it shows

- Premium requests this month
- Billable premium requests this month
- Copilot spend in USD this month
- Last refresh time
- Optional top model breakdown

## Requirements

- `python3`
- A GitHub token in `GITHUB_TOKEN` (recommended) or tmux option
- Token permissions:
  - User scope: `Plan:read`
  - Org scope: org billing/admin read equivalent permission

## Install (TPM)

In `.tmux.conf`:

```tmux
set -g @plugin 'yourname/copilot-usage'

# optional settings
set -g @copilot_usage_scope 'auto'      # auto|user|org
set -g @copilot_usage_org ''            # required when scope=org
set -g @copilot_usage_refresh_seconds '90'
set -g @copilot_usage_show_model 'off'  # on|off
set -g @copilot_usage_auto_append 'on'  # on|off
set -g @copilot_usage_monthly_limit '500' # monthly request target
set -g @copilot_usage_bar_width '10'
set -g @copilot_usage_percent_metric 'total' # total|billable
```

Then reload tmux and install plugins with TPM.

## Status segment format

The plugin renders:

`Copilot: 182 req | billable 41 | $3.28 | 8% [#---------] | 14:37`

Color thresholds for the percentage bar:

- Green: usage < 75%
- Orange: usage >= 75% and < 90%
- Red: usage >= 90%

Note: percentage defaults to `total / @copilot_usage_monthly_limit`. You can switch to `billable` with `@copilot_usage_percent_metric`.

If refresh fails, the last known value is kept and `| stale` is appended.

## Security

- Prefer exporting `GITHUB_TOKEN` in your shell startup instead of placing a token in tmux config.
- If you must use tmux option, set:

```tmux
set -g @copilot_usage_token 'ghp_...'
```

## Local scripts

- `bin/fetch_usage.py`: fetches API data and updates cache
- `bin/updater.py`: background fetch loop with lock file
- `bin/render_status.py`: reads cache and prints tmux segment

Manual test:

```bash
GITHUB_TOKEN=... python3 bin/fetch_usage.py --scope user
python3 bin/render_status.py
```
