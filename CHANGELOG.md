# Changelog

## [1.1.0.post1] - 2026-03-11

 ### Changes
This is a maintenance release with no changes to the public API. All updates are internal to the development infrastructure and tooling.

**CI/CD Improvements**   
The GitHub Actions workflows for tests, release, and docs have been overhauled and synced with the latest project template. Integration tests are now correctly excluded from the standard CI test run, and a dedicated tests:ci command was added to run.sh to make this distinction explicit. A missing system dependency step required for Pillow compilation was restored to the test workflow.

**Release Script Overhaul**   
The release script (scripts/release.py) was significantly refactored. It now uses a RollbackState mechanism to safely undo partial changes if the release process fails mid-way, and adds an interactive confirmation mode so each step can be reviewed before execution.

**Developer Tooling**   
The Makefile and run.sh script were synced with the latest generate-project template, bringing in additional development commands and improving consistency. A fix was also applied for Python 3 PATH resolution under Poetry 2.x. The notes/ directory is now excluded from version control via .gitignore.


## [1.1.0] - 2026-01-22

 ### Changes
- 📝 docs: add SyncMultiServerClient documentation
- ✅ test: add comprehensive tests for SyncMultiServerClient
- 🧵 feat: add SyncMultiServerClient for synchronous code


## [1.0.0] - 2025-12-08

 ### Changes
- First Release
