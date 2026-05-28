#!/usr/bin/env python3
"""
Create a new timestamped migration-report run directory and update the `latest` pointer.

Output: prints the new directory path (absolute) to stdout.

Usage:
  new_run_dir.py --repo <path> [--mode <mode>]

`--repo` is required and must be an absolute path to the target repository root. The
script does not fall back to CWD because Bash CWD often resets between tool calls in
agent contexts, which silently scatters run dirs under the wrong root. Fail loudly
instead.

The `latest` pointer is a plain text file (not a symlink), for Windows compatibility.
Pointer write is atomic: tempfile + rename.

Do NOT call this for `execute` mode — execute operates in place on the directory that
`latest` currently points to.
"""
from __future__ import annotations

import argparse
import os
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True, help="Absolute path to repo root (required)")
    ap.add_argument("--mode", default="audit", help="Mode label (for logging only)")
    args = ap.parse_args()

    if args.mode == "execute":
        print(
            "error: do not create a new run dir for `execute` mode; "
            "operate in place on `latest`.",
            file=sys.stderr,
        )
        return 2

    repo = Path(args.repo).resolve()
    if not (repo / "pyproject.toml").exists() and not (repo / ".git").exists():
        print(
            f"error: --repo {repo} does not look like a project root "
            "(no pyproject.toml or .git found). Pass an absolute repo path.",
            file=sys.stderr,
        )
        return 2
    reports = repo / ".claude" / "migration-reports"
    reports.mkdir(parents=True, exist_ok=True)

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H-%M-%SZ")
    run_dir = reports / ts
    run_dir.mkdir(exist_ok=False)

    pointer = reports / "latest"
    fd, tmp_path = tempfile.mkstemp(dir=str(reports), prefix=".latest.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(ts + "\n")
        os.replace(tmp_path, pointer)
    except Exception:
        try:
            os.unlink(tmp_path)
        except FileNotFoundError:
            pass
        raise

    print(str(run_dir))
    return 0


if __name__ == "__main__":
    sys.exit(main())
