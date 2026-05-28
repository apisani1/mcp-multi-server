#!/usr/bin/env python3
"""
Detect which of the four MCP-migration specialist subagents are installed.

Looks in:
  - <repo>/.claude/agents/<name>.md   (project-scoped)
  - ~/.claude/agents/<name>.md        (user-scoped)

Specialists checked:
  - transport-auditor
  - oauth-auditor
  - conformance-checker
  - fastmcp-reviewer

Emits a JSON object to stdout:
  {
    "transport-auditor": {"present": true,  "path": "/abs/path/to/agent.md", "scope": "project"},
    "oauth-auditor":     {"present": false, "path": null,                    "scope": null},
    ...
  }

Exit 0 always (presence info is informational; absence is not an error).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

SPECIALISTS = [
    "transport-auditor",
    "oauth-auditor",
    "conformance-checker",
    "fastmcp-reviewer",
]


def find(name: str, repo: Path) -> tuple[bool, str | None, str | None]:
    project = repo / ".claude" / "agents" / f"{name}.md"
    if project.exists():
        return True, str(project), "project"
    user = Path(os.path.expanduser("~")) / ".claude" / "agents" / f"{name}.md"
    if user.exists():
        return True, str(user), "user"
    return False, None, None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="Repo root (default: CWD)")
    args = ap.parse_args()
    repo = Path(args.repo).resolve()

    result: dict[str, dict] = {}
    for name in SPECIALISTS:
        present, path, scope = find(name, repo)
        result[name] = {"present": present, "path": path, "scope": scope}

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
