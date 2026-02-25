#!/usr/bin/env python3

import argparse
import fcntl
import os
import pathlib
import subprocess
import sys
import time


def parse_args():
    parser = argparse.ArgumentParser(
        description="Background updater for Copilot usage cache"
    )
    parser.add_argument("--scope", choices=["auto", "user", "org"], default="auto")
    parser.add_argument("--org", default="")
    parser.add_argument("--token", default=os.environ.get("GITHUB_TOKEN", ""))
    parser.add_argument(
        "--cache-file",
        default=os.path.expanduser("~/.cache/copilot-usage/status.json"),
    )
    parser.add_argument("--refresh-seconds", type=int, default=90)
    parser.add_argument("--python", default=sys.executable)
    return parser.parse_args()


def main():
    args = parse_args()
    cache_path = pathlib.Path(args.cache_file).expanduser()
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = cache_path.parent / "updater.lock"

    with lock_path.open("w", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 0

        fetcher = pathlib.Path(__file__).with_name("fetch_usage.py")

        while True:
            cmd = [
                args.python,
                str(fetcher),
                "--scope",
                args.scope,
                "--cache-file",
                str(cache_path),
            ]
            if args.org:
                cmd.extend(["--org", args.org])
            if args.token:
                cmd.extend(["--token", args.token])

            subprocess.run(
                cmd, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            time.sleep(max(30, args.refresh_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
