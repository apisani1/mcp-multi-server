---
description: Sync a generated repo's dev-environment files with a released generate-project template, preserving customizations
argument-hint: "[version|latest, e.g. 2.1.0 or v2.1.0]"
---

# Update Dev Environment

Sync the infrastructure / development-environment files in the **current repository** with a
released version of the cookiecutter template from
[`apisani1/generate-project`](https://github.com/apisani1/generate-project), preserving all
project-specific customizations.

The optional argument selects which released version to sync against:
- `2.1.0` or `v2.1.0` — that exact release tag
- `latest` or omitted — the latest **stable** release (pre-releases excluded)

`$ARGUMENTS` holds the requested version (may be empty).

---

## Step 0 — Detect the package manager

Read `pyproject.toml` in the current repo and decide which template applies:

- `build-backend = "hatchling.build"` (or a `[tool.uv]` table / a `uv.lock` file) → **uv** →
  `template = uv-template`
- `build-backend = "poetry.core.masonry.api"` (or a `[tool.poetry]` table / a `poetry.lock`
  file) → **poetry** → `template = poetry-template`

If the signals are ambiguous or conflicting, **stop and ask the user** which manager to sync
against before continuing.

## Step 1 — Detect project values

From the current repo's `pyproject.toml`, extract the values used to substitute the cookiecutter
template variables:

- `project_name` = `[project].name`
- `package_name` = read from the build configuration — **do not** assume it is `project_name`
  with hyphens replaced by underscores:
  - uv: the directory in `[tool.hatch.build.targets.wheel].packages`, with the leading `src/`
    stripped (e.g. `["src/foo_bar"]` → `foo_bar`)
  - poetry: the `include` value in `[tool.poetry].packages`
    (e.g. `[{ include = "foo_bar", from = "src" }]` → `foo_bar`)
  - Fallback if neither is set: the single directory under `src/`
- `python_min_version` = `[project].requires-python` with any leading `>=`, `^`, or `~=` stripped

## Step 2 — Resolve the version ref

Determine the git ref to fetch from:

1. Normalize the argument: trim whitespace and strip a leading `v`.
2. If it is empty or `latest`, resolve the **latest stable release**:
   ```bash
   gh release view --repo apisani1/generate-project --json tagName -q .tagName
   ```
   GitHub's "latest" already excludes drafts and pre-releases. If `gh` is unavailable, fall
   back to listing tags and picking the highest stable one:
   ```bash
   git ls-remote --tags https://github.com/apisani1/generate-project \
     | sed 's:.*/::; s:\^{}::' | sort -u
   ```
   Drop any tag whose version segment matches `rc`, `b`, `beta`, `a`, `alpha`, or `post`,
   version-sort the remainder, and take the highest.
3. Otherwise the ref is `v<version>` (re-add the `v` prefix). Verify the tag exists:
   ```bash
   gh api repos/apisani1/generate-project/git/ref/tags/v<version>
   ```
   (or `git ls-remote --tags https://github.com/apisani1/generate-project v<version>`).
   If it does not exist, **stop and report** the available recent tags.

**Report the resolved ref to the user** before fetching anything.

## Step 3 — Fetch each template file from GitHub

The template files live inside a directory literally named `{{cookiecutter.project_name}}` in
the source repo, so its braces must be percent-encoded (`{{` → `%7B%7B`, `}}` → `%7D%7D`) in the
raw URL. For a given `<file>`:

```
https://raw.githubusercontent.com/apisani1/generate-project/<ref>/src/generate_project/templates/<template>/%7B%7Bcookiecutter.project_name%7D%7D/<file>
```

Fetch with `curl -fsSL "<url>"` (or `gh api`). If a file returns 404, it is not part of this
template — skip it. After fetching, substitute the cookiecutter variables in the file content
with the detected project values before merging:
`{{ cookiecutter.project_name }}` → `project_name`, `{{ cookiecutter.package_name }}` →
`package_name`, `{{ cookiecutter.python_min_version }}` → `python_min_version`.

## Step 4 — Update each file

Process the files below **sequentially**. For each file:
1. Fetch the template file (Step 3) and substitute the cookiecutter variables
2. Read the current file in the repo (if it exists)
3. Apply the merge strategy described below
4. Write the result

---

### Merge Strategies

**Full Replace** — used when a file contains no expected project-specific content. Overwrite the
current file entirely with the substituted template.

**Diff-and-Merge** — used for files that commonly contain project-specific additions. The process is:
1. Identify what is in the *current file* but **not** in the template (these are project-specific additions)
2. Identify what is in the *template* but **not** in the current file (these are template improvements to bring in)
3. Update the file by applying template improvements while keeping every project-specific addition in place

**Preserve-First** — used for files that are primarily project-specific documentation. The template
provides structure only; the current content takes precedence and is never reduced.

---

### `.github/workflows/delete_workflow_runs.yml`
**Strategy:** Full Replace

---

### `.github/workflows/docs.yml`
**Strategy:** Diff-and-Merge
Typical project-specific additions to preserve:
- Any "Install system dependencies" steps added for native library compilation (e.g. image processing, database, or crypto libraries)

---

### `.github/workflows/tests.yml`
**Strategy:** Diff-and-Merge

Typical project-specific additions to preserve:
- Any "Install system dependencies" steps added for native library compilation (e.g. image processing, database, or crypto libraries)
- Custom `run.sh` command names in the pytest step that differ from the template's default
- Extra exit code handling clauses (e.g. `|| [ $? -eq 5 ]` to allow "no tests collected")
- Additional environment variables or secrets used only in this project

---

### `.github/workflows/release.yml`
**Strategy:** Diff-and-Merge

Typical project-specific additions to preserve:
- Release type detection logic that classifies version strings (stable, pre-release, post, draft) — often an `if/elif` block setting `is_latest`, `release_type`, or similar variables
- TestPyPI package installation verification steps (install from TestPyPI and verify import works)
- ReadTheDocs retry/polling logic
- Any extra job steps that validate or notify on release

---

### `.github/workflows/update_rtd.yml`
**Strategy:** Full Replace (after variable substitution — `project_name` appears as the RTD project slug in API call paths)

---

### `.github/dependabot.yml`
**Strategy:** Create-If-Missing, otherwise Diff-and-Merge

Ships a `github-actions` entry that keeps the SHA-pinned actions current (minor/patch updates are
batched into one PR; major updates arrive as separate PRs). If the project has no
`.github/dependabot.yml`, create it from the template. If it exists, keep every `updates` entry the
project already has (e.g. `uv`, `pip`, `npm` ecosystems) and only add or update the
`github-actions` entry. Never remove an existing entry. The file has no cookiecutter variables, so
there is nothing to substitute.

---

### `.readthedocs.yaml`
**Strategy:** Full Replace

---

### `.gitignore`
**Strategy:** Diff-and-Merge

Start from the template version and append any entries present in the current file that are absent from the template. These represent project-specific ignores (local tooling artifacts, extra cache directories, data files, etc.). Do not remove any entries that exist in the current file.

---

### `.vscode/settings.json`
**Strategy:** Diff-and-Merge

This is JSON, so merge at the **key** level. Start from the template and overlay the current
file: keep every key the user has added or changed that the template does not provide or sets
differently (e.g. local interpreter paths, extra `"[language]"` blocks, personal editor toggles).
Never drop a key that exists in the current file. Bring in template keys that are new.

---

### `scripts/update_versions.py`
**Strategy:** Full Replace

---

### `scripts/release.py`
**Strategy:** Full Replace (all project-specific configuration is read at runtime from `pyproject.toml`, not hardcoded in the script)

Sync this together with `.gitignore`: the script saves its rollback state to
`.before_last_release.json` and then runs `git add .`, so the project's `.gitignore` must contain
that entry or the state file gets committed. The template `.gitignore` has it; if the Diff-and-Merge
of `.gitignore` somehow leaves it out, add it.

---

### `scripts/install_claude_skills.py`
**Strategy:** Full Replace (no project-specific content; all configuration is read at runtime)

---

### `Makefile`
**Strategy:** Diff-and-Merge

Typical project-specific additions to preserve:
- Any `run-*` targets for running example scripts or application entry points
- Any targets for project-specific tooling (e.g. MCP inspector, config generators, notebook runners)
- Any extra `test-*` variants using custom pytest markers
- Any targets referencing project-specific modules or scripts

Insert preserved custom targets in a clearly separated block before the `help` target.

**Exception — the `run` and `worktree-*` targets.** `run`, `worktree-setup`, `worktree-archive`
and `worktree-delete` are template-owned and must be taken from the template verbatim. If the
project has customized any of them, do not preserve it in place: move the command into the
matching escape-hatch file (`scripts/run.sh`, or `scripts/worktree-<phase>.sh`), which the
template-owned functions prefer over their built-in defaults. Report this migration in the
summary.

---

### `run.sh`
**Strategy:** Diff-and-Merge

Typical project-specific sections to preserve:
- Any shims or PATH fixes at the top of the script (e.g. Python version resolution for specific tool compatibility)
- Project-specific source paths in `get:python:files` and related helpers
- Extra `--extras <name>` flags in install commands
- Custom pytest markers in test commands (e.g. `-m "not integration"` to exclude integration tests)
- The `--cov=<package_name>` argument in coverage commands
- Any project-specific run commands (`run:*`, `mcp-*`, etc.) not present in the template
- Any Jupyter kernel setup functions

**Exception — the `run` and `worktree:*` functions.** Take the template's `run`, `worktree:hook`,
`worktree:setup`, `worktree:archive`, `worktree:delete` and `get:venv:home` functions verbatim.
`run` dispatches to `scripts/run.sh` → console script → `examples/main.py`; each `worktree:*`
phase ends by calling `scripts/worktree-<phase>.sh`. If the project has customized any of them,
move the command into the matching escape-hatch file instead of preserving the customization, and
report the migration in the summary.

**Poetry projects:** the template now exports `POETRY_VIRTUALENVS_IN_PROJECT=true` near the top of
`run.sh`. Take it. Without it Poetry uses its global cache, and the copied-`.venv` handling in
`venv` plus `worktree:archive`'s cleanup silently do nothing. Warn that the next install creates a
fresh in-project `.venv`, superseding any cached environment.

---

### `supacode.json`
**Strategy:** Create-If-Missing, otherwise leave alone

Only relevant to Supacode users; the template ships it when generated with `--supacode`. If the
project has no `supacode.json` and the user wants the worktree lifecycle wired up, create it with
exactly the three lifecycle keys:

```json
{
  "archiveScript" : "./run.sh worktree:archive",
  "deleteScript" : "./run.sh worktree:delete",
  "setupScript" : "./run.sh worktree:setup"
}
```

Never overwrite an existing one. Supacode rewrites this file itself when repository settings
change in its UI, so any other keys it contains (`runScript`, `scripts`, `openActionID`, ...) are
the user's own configuration — leave them untouched.

---

### `CLAUDE.md`
**Strategy:** Preserve-First

The template provides a generic structure. The current file likely contains hand-written
project-specific documentation (architecture overviews, design patterns, component descriptions,
routing logic, etc.) that must never be reduced.

Apply this approach:
- Keep all sections from the current file that do not appear in the template
- For sections that exist in both (e.g. "Development Commands"), update to the template version only if the current version is a strict subset of the template (i.e. the template adds useful commands but the current version has no customizations)
- Never remove existing content from `CLAUDE.md`

---

## Step 5 — Post-Update

After all files have been updated, run:

```bash
make pre-commit
```

This formats and lints only the changed files. Report any issues that arise.

## Step 6 — Summary

Report the package manager detected, the package name and Python version used, and the resolved
release ref synced from. Then list which files were changed and briefly note what was updated vs.
what was preserved in each.
