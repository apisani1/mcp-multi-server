# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MCP Multi-Server is a Python library for managing connections to multiple Model Context Protocol (MCP) servers. It provides a unified interface for capability discovery (tools, resources, prompts) and intelligent routing across distributed MCP servers.

## Architecture

### Core Components

**`src/mcp_multi_server/client.py`** - The `MultiServerClient` class is the heart of the library:
- Manages connections to multiple MCP servers via `sessions: Dict[str, ClientSession]`
- Tracks capabilities per server via `capabilities: Dict[str, ServerCapabilities]`
- Maintains routing maps: `tool_to_server` and `prompt_to_server` for name-based routing
- Uses `AsyncExitStack` internally for managing multiple concurrent async contexts

**`src/mcp_multi_server/config.py`** - Pydantic models for JSON configuration:
- `ServerConfig`: command + args for spawning a server
- `MCPServersConfig`: dict of named server configurations

**`src/mcp_multi_server/types.py`** - `ServerCapabilities` model tracking what each server provides

**`src/mcp_multi_server/utils.py`** - Utility functions including:
- `mcp_tools_to_openai_format()` - convert MCP tools to OpenAI function calling format
- `format_namespace_uri()` / `parse_namespace_uri()` - namespace handling for resource routing
- `extract_template_variables()` / `substitute_template_variables()` - URI template processing

### Key Design Patterns

**Intelligent Routing:**
- Tools & Prompts: Name-based lookup stored during `connect_all()`
- Resources: Namespace-based parsing using `server:uri` format (colon separator distinguishes from protocol schemes like `://`)
- Collision handling: Last server wins with warning logs

**Error Handling:**
- Tool calls return `CallToolResult` with `isError=True` for routing errors
- Resources/Prompts raise `McpError` exceptions (aligns with MCP SDK behavior)
- Server connection failures log warnings but don't prevent other servers from connecting

**Metadata Injection:**
- All aggregated capabilities include `meta["serverName"]` for traceability
- Resources additionally get namespaced URIs for routing

## Development Commands

This project uses a combination of Poetry for dependency management and a custom `run.sh` script for development tasks. All commands can be executed via either the Makefile (which delegates to `run.sh`) or directly via `run.sh`.

### Environment Setup
```bash
make venv                 # Create and activate local virtual environment
make install              # Install core dependencies
make install-lint         # Install linting dependencies
make install-test         # Install testing dependencies
make install-docs         # Install documentation dependencies
make install-dev          # Install all development dependencies (dev, test, lint, typing and docs dependency groups)
./run.sh install:all      # CI alternative: install all dependencies without interaction
```

### Code Quality
```bash
make format               # Format code with black and isort
make format-diff          # Run formatters on changed files
make lint                 # Run mypy, flake8, and pylint
make lint-diff            # Run all linters on changed files
make check                # Run format + lint + tests on all files(local development)
make pre-commit           # Format and lint only on changed files
./run.sh check:ci         # CI version (format only checks, no file modifications)

```

### Testing
```bash
make test                 # Run all tests
make test-cov             # Run tests with coverage
make coverage             # Generate coverage report
make test-verbose         # Run tests with verbose output
./run.sh tests:pattern "test_name"  # Run only tests matching pattern
```

### Documentation
```bash
make docs-api             # Generate API documentation automatically
make docs                 # Build Sphinx documentation
make docs-live            # Start live documentation server with auto-reload
make docs-clean           # Clean and rebuild documentation
```

### Package Building
```bash
make build                # Build package with Poetry
make validate-build       # Validate package builds correctly
make clean                # Clean build artifacts
```
