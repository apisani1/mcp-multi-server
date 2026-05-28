#!/usr/bin/env python3
"""
Detect the installed/declared MCP Python SDK version in the target repo.

Resolution order:
  1. pyproject.toml (PEP 621 [project.dependencies] or Poetry [tool.poetry.dependencies])
  2. uv.lock (TOML, package == "mcp")
  3. poetry.lock (TOML, package == "mcp")
  4. pip-style requirements*.txt

Print the resolved version to stdout. Exit 0 if found, exit 2 if not.
Use --repo to target a specific directory; default is CWD.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

try:
    import tomllib  # py3.11+
except ImportError:  # pragma: no cover
    import tomli as tomllib  # type: ignore


VERSION_RE = re.compile(r"(\d+\.\d+(?:\.\d+)?(?:[a-zA-Z0-9.+-]*)?)")


def from_pyproject(p: Path) -> str | None:
    if not p.exists():
        return None
    data = tomllib.loads(p.read_text())
    project_deps = data.get("project", {}).get("dependencies", []) or []
    for dep in project_deps:
        if isinstance(dep, str) and dep.lower().startswith("mcp"):
            m = VERSION_RE.search(dep)
            if m:
                return m.group(1)
    poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {}) or {}
    mcp_spec = poetry_deps.get("mcp")
    if isinstance(mcp_spec, str):
        m = VERSION_RE.search(mcp_spec)
        if m:
            return m.group(1)
    if isinstance(mcp_spec, dict):
        ver = mcp_spec.get("version", "")
        m = VERSION_RE.search(ver)
        if m:
            return m.group(1)
    return None


def from_uv_lock(p: Path) -> str | None:
    if not p.exists():
        return None
    data = tomllib.loads(p.read_text())
    for pkg in data.get("package", []) or []:
        if pkg.get("name") == "mcp":
            ver = pkg.get("version")
            if ver:
                return ver
    return None


def from_poetry_lock(p: Path) -> str | None:
    if not p.exists():
        return None
    data = tomllib.loads(p.read_text())
    for pkg in data.get("package", []) or []:
        if pkg.get("name") == "mcp":
            ver = pkg.get("version")
            if ver:
                return ver
    return None


def from_requirements(repo: Path) -> str | None:
    for req in repo.glob("requirements*.txt"):
        for line in req.read_text().splitlines():
            line = line.strip()
            if line.lower().startswith("mcp"):
                m = VERSION_RE.search(line)
                if m:
                    return m.group(1)
    return None


def detect(repo: Path) -> str | None:
    for fn in (
        lambda: from_pyproject(repo / "pyproject.toml"),
        lambda: from_uv_lock(repo / "uv.lock"),
        lambda: from_poetry_lock(repo / "poetry.lock"),
        lambda: from_requirements(repo),
    ):
        v = fn()
        if v:
            return v
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=".", help="Repo root (default: CWD)")
    args = ap.parse_args()
    repo = Path(args.repo).resolve()
    version = detect(repo)
    if version is None:
        print(
            f"error: could not detect mcp version in {repo} "
            "(checked pyproject.toml, uv.lock, poetry.lock, requirements*.txt)",
            file=sys.stderr,
        )
        return 2
    print(version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
