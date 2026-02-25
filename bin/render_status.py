#!/usr/bin/env python3

import argparse
import datetime as dt
import json
import os
import pathlib


def parse_args():
    parser = argparse.ArgumentParser(description="Render Copilot usage for tmux")
    parser.add_argument(
        "--cache-file",
        default=os.path.expanduser("~/.cache/copilot-usage/status.json"),
    )
    parser.add_argument("--show-model", action="store_true")
    parser.add_argument("--show-billable", action="store_true")
    parser.add_argument("--monthly-limit", type=int, default=0)
    parser.add_argument("--bar-width", type=int, default=10)
    parser.add_argument(
        "--percent-metric",
        choices=["total", "billable"],
        default="total",
    )
    return parser.parse_args()


def short_time(ts):
    try:
        parsed = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return "--:--"
    local = parsed.astimezone()
    return local.strftime("%H:%M")


def main():
    args = parse_args()
    cache_path = pathlib.Path(args.cache_file).expanduser()

    if not cache_path.exists():
        print("Copilot: n/a")
        return 0

    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        print("Copilot: n/a")
        return 0

    total = int(data.get("premium_requests_total", 0))
    billable = int(data.get("premium_requests_billable", 0))
    spend = float(data.get("copilot_spend_usd", 0.0))
    updated = short_time(str(data.get("updated_at", "")))
    error = data.get("error")

    text = f"Copilot: {total} req | ${spend:.2f}"
    if args.show_billable:
        text += f" | billable {billable}"

    if args.monthly_limit > 0:
        usage_value = total if args.percent_metric == "total" else billable
        pct = min(999, int(round((usage_value / args.monthly_limit) * 100)))
        bar_width = max(5, args.bar_width)
        filled = min(bar_width, int(round((min(pct, 100) / 100) * bar_width)))
        bar = ("█" * filled) + ("░" * (bar_width - filled))

        if pct >= 90:
            color = "red"
        elif pct >= 75:
            color = "colour208"
        else:
            color = "green"

        text += f" | #[fg={color}]{pct}% [{bar}]#[default]"

    text += f" | {updated}"

    if args.show_model:
        by_model = data.get("by_model") or []
        if by_model:
            top = by_model[0]
            model = str(top.get("model", "?")).strip() or "?"
            text += f" | {model}:{int(round(float(top.get('total', 0))))}"

    if error:
        text += " | stale"

    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
