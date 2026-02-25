#!/usr/bin/env python3

import argparse
import datetime as dt
import json
import os
import pathlib
import sys
import urllib.error
import urllib.parse
import urllib.request


API_BASE = "https://api.github.com"
API_VERSION = "2022-11-28"


def api_get(path, token, params=None):
    url = API_BASE + path
    if params:
        query = urllib.parse.urlencode(params)
        url = f"{url}?{query}"

    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", API_VERSION)
    req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            payload = response.read().decode("utf-8")
            return json.loads(payload)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {exc.code} on {path}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error calling {path}: {exc}") from exc


def flatten_quantity_rows(node, rows):
    if isinstance(node, dict):
        lower_keys = {k.lower(): k for k in node.keys()}
        has_quantity = any(
            k in lower_keys
            for k in (
                "grossquantity",
                "discountquantity",
                "netquantity",
                "totalquantity",
            )
        )
        if has_quantity:
            rows.append(node)

        for value in node.values():
            flatten_quantity_rows(value, rows)
    elif isinstance(node, list):
        for item in node:
            flatten_quantity_rows(item, rows)


def get_number(record, *keys):
    lowered = {k.lower(): v for k, v in record.items()}
    for key in keys:
        if key.lower() in lowered:
            value = lowered[key.lower()]
            if isinstance(value, (int, float)):
                return float(value)
            try:
                return float(str(value))
            except ValueError:
                return 0.0
    return 0.0


def parse_premium_usage(data):
    rows = []
    flatten_quantity_rows(data, rows)

    total = 0.0
    billable = 0.0
    by_model = {}

    for row in rows:
        gross = get_number(row, "grossQuantity", "totalQuantity")
        net = get_number(row, "netQuantity")
        discount = get_number(row, "discountQuantity")

        if gross == 0.0 and net == 0.0 and discount > 0:
            gross = net + discount
        if net == 0.0 and gross > 0.0 and discount > 0:
            net = max(0.0, gross - discount)

        total += gross
        billable += net

        model = (
            row.get("model")
            or row.get("modelName")
            or row.get("sku")
            or row.get("name")
            or "unknown"
        )
        model_key = str(model)
        if model_key not in by_model:
            by_model[model_key] = {"model": model_key, "total": 0.0, "billable": 0.0}
        by_model[model_key]["total"] += gross
        by_model[model_key]["billable"] += net

    model_rows = sorted(by_model.values(), key=lambda item: item["total"], reverse=True)
    return int(round(total)), int(round(billable)), model_rows


def extract_spend_usd(node):
    if isinstance(node, dict):
        lowered = {str(k).lower(): v for k, v in node.items()}

        direct_candidates = (
            "copilot_spend_usd",
            "copilotspendusd",
            "total_amount_usd",
            "totalamountusd",
            "net_amount_usd",
            "netamountusd",
            "amount_usd",
            "amountusd",
        )
        for key in direct_candidates:
            if key in lowered and isinstance(lowered[key], (int, float, str)):
                try:
                    return float(lowered[key])
                except ValueError:
                    pass

        amount_sum = 0.0
        has_amount = False
        for key, value in node.items():
            key_l = str(key).lower()
            if ("amount" in key_l or key_l.endswith("usd")) and isinstance(
                value, (int, float, str)
            ):
                try:
                    amount_sum += float(value)
                    has_amount = True
                except ValueError:
                    pass
            else:
                nested = extract_spend_usd(value)
                if nested is not None:
                    amount_sum += nested
                    has_amount = True

        if has_amount:
            return amount_sum

    if isinstance(node, list):
        total = 0.0
        has_any = False
        for item in node:
            nested = extract_spend_usd(item)
            if nested is not None:
                total += nested
                has_any = True
        if has_any:
            return total

    return None


def call_usage_endpoint(path_template, token, year, month):
    params = {"year": year, "month": month}
    try:
        return api_get(path_template, token, params=params)
    except RuntimeError:
        return api_get(path_template, token, params=None)


def load_cache(cache_path):
    if not cache_path.exists():
        return None
    try:
        return json.loads(cache_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def write_cache(cache_path, payload):
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = cache_path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp_path.replace(cache_path)


def build_parser():
    parser = argparse.ArgumentParser(description="Fetch GitHub Copilot billing usage")
    parser.add_argument("--scope", choices=["auto", "user", "org"], default="auto")
    parser.add_argument("--org", default="")
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    parser.add_argument(
        "--cache-file",
        default=os.path.expanduser("~/.cache/copilot-usage/status.json"),
    )
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()

    if not args.token:
        parser.error("missing token; set GITHUB_TOKEN or pass --token")

    cache_path = pathlib.Path(os.path.expanduser(args.cache_file))
    previous = load_cache(cache_path)
    now = dt.datetime.now(dt.timezone.utc)
    year = now.year
    month = now.month

    try:
        user = api_get("/user", args.token)
        username = user.get("login")
        if not username:
            raise RuntimeError("Could not resolve username from /user")

        scope = args.scope
        if scope == "auto":
            scope = "org" if args.org else "user"

        if scope == "org":
            if not args.org:
                raise RuntimeError("Org scope requires --org")
            prefix = f"/organizations/{args.org}/settings/billing"
            scope_name = args.org
        else:
            prefix = f"/users/{username}/settings/billing"
            scope_name = username

        premium_data = call_usage_endpoint(
            f"{prefix}/premium_request/usage", args.token, year, month
        )
        summary_data = call_usage_endpoint(
            f"{prefix}/usage/summary", args.token, year, month
        )

        total, billable, by_model = parse_premium_usage(premium_data)
        spend = extract_spend_usd(summary_data)
        if spend is None:
            spend = 0.0

        payload = {
            "updated_at": now.isoformat(),
            "scope": scope,
            "scope_name": scope_name,
            "premium_requests_total": total,
            "premium_requests_billable": billable,
            "copilot_spend_usd": round(float(spend), 4),
            "by_model": by_model,
            "error": None,
        }
        write_cache(cache_path, payload)
        print(json.dumps(payload))
        return 0
    except Exception as exc:
        if previous:
            previous["error"] = {
                "message": str(exc),
                "at": now.isoformat(),
            }
            write_cache(cache_path, previous)
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
