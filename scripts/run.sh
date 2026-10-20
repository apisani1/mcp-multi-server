#!/usr/bin/env bash
# Per-repo escape hatch for `make run` / `./run.sh run`: run any Python module.
# Usage: make run ARGS="examples.client.chat_client [module args...]"
set -euo pipefail

if [ $# -eq 0 ]; then
    echo "Usage: make run ARGS=\"<module.path> [args...]\""
    echo ""
    echo "Examples:"
    echo "  make run ARGS=\"examples.client.chat_client\""
    echo "  make run ARGS=\"examples.servers.tool_server\""
    echo "  make run ARGS=\"mcp_multi_server.client\""
    echo ""
    echo "Or use convenience targets: make run-chat, make run-tool-server, ..."
    exit 1
fi

exec uv run python3 -m "$@"
