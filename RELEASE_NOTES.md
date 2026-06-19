# mcp-multi-server v1.2.2

Infrastructure-only release. **No library API or runtime behavior changes.**
If you install `mcp-multi-server` with `pip` or `uv`, this release is
functionally identical to `1.2.1`.

## What changed

### Bug fixes

- **CI: pip install name corrected** — the TestPyPI smoke-test step in `release.yml`
  was calling `pip install mcp_multi_server` (underscore), which would fail to resolve
  the package on PyPI. Fixed to `mcp-multi-server`.

- **Coverage path fix** — `run.sh tests:cov` was passing `--cov=mcp_multi_server`
  instead of `--cov=src/mcp_multi_server`, causing coverage to report against the wrong
  path. Fixed.

- **`scripts/release.py` mypy fix** — `read_release_doc` early-exit branches now
  explicitly return `None` rather than forwarding the return value of
  `confirm_release_doc_fallback`, resolving type errors reported by mypy.

### Internal improvements

- **ReadTheDocs CI workflow** now syncs available versions before activating the new
  tag, then triggers explicit builds for both the tagged version and `latest`. The step
  has a proper `id` for outcome-based reporting in the Release Summary, and uses
  `::warning::` annotations and `exit 1` for correct CI failure signaling.

- **`make release-*` / `make rollback` accept extra args** via a new `ARGS ?=` Makefile
  variable (forwarded as `$(ARGS)` to `run.sh`, which in turn passes `"$@"` through to
  `scripts/release.py`). Example: `make release-micro ARGS=--dry-run`.

- Synced dev environment with `apisani1/generate-project` v2.3.0 (`.gitignore`
  `.claude/*` pattern, `regenerate_asset_manifest()` stub in `scripts/release.py`).
