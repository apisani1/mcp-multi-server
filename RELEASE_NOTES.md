# mcp-multi-server v1.2.1

Infrastructure-only release. **No library API or runtime behavior changes.**
If you install `mcp-multi-server` with `pip` or `poetry`, this release is
functionally identical to `1.2.0` — you don't need to do anything.

## What changed

### Build & dev environment migrated to UV

The project now uses [UV](https://docs.astral.sh/uv/) for dependency
management and packaging, with [hatchling](https://hatch.pypa.io/) as the
build backend (previously `poetry-core`). The wheel layout
(`src/mcp_multi_server`) and the published distribution name are unchanged.

### For consumers

Nothing to change. The library still installs the same way:

```bash
pip install mcp-multi-server
# or
uv add mcp-multi-server
# or
poetry add mcp-multi-server
```

### For contributors

If you work on the repo locally, the dev workflow has moved off Poetry:

- Replace `poetry install --with dev,test,lint,typing,docs --extras examples`
  with `uv sync --all-groups --all-extras` (or `make install-dev` /
  `make install-all`).
- The lockfile is `uv.lock`; `poetry.lock` is gone.
- `run.sh` and the `Makefile` now call `uv run` / `uv sync`. Existing
  `make` targets (`make test`, `make pre-commit`, `make docs`, `make build`,
  `make release-*`, etc.) continue to work unchanged.

### Infra refresh

`run.sh`, `Makefile`, the GitHub Actions workflows (tests/docs/release),
`.readthedocs.yaml`, and `.vscode/settings.json` were re-synced from the
[`apisani1/generate-project`](https://github.com/apisani1/generate-project)
v2.2.0 UV template, preserving project-specific customizations
(`tests:ci` integration-marker filter, main-branch diff for
`make pre-commit`, system-deps CI step, `--cov=mcp_multi_server`,
`run-*`/`mcp-*` Makefile targets, editor settings).

### Documentation

- `docs/Makefile` Sphinx targets and `docs/index.md` install example
  switched from `poetry` to `uv`.
- `CLAUDE.md` Development Commands and Workflow sections updated for UV.
