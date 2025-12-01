#!/usr/bin/env python3
"""
Python script to generate MCP server configuration.
"""

import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import (
    Any,
    Dict,
    Optional,
)


def find_poetry_command() -> str:
    """Find the poetry executable in the system PATH or common locations.

    Returns:
        str: Absolute path to poetry executable

    Raises:
        RuntimeError: If poetry cannot be found
    """
    # First, try to find poetry in PATH
    poetry_path = shutil.which("poetry")
    if poetry_path is not None:
        return poetry_path

    # Fallback: check common installation locations
    common_locations = [
        Path.home() / ".local" / "bin" / "poetry",
        Path.home() / ".poetry" / "bin" / "poetry",
    ]

    for location in common_locations:
        if location.exists() and location.is_file():
            return str(location.resolve())

    raise RuntimeError(
        "Poetry executable not found in PATH or common locations. "
        "Please ensure Poetry is installed and available. "
        "Searched locations: PATH, ~/.local/bin/poetry, ~/.poetry/bin/poetry"
    )


def find_project_directory() -> str:
    """Find the project root directory.

    Uses the location of this script file to determine the project root.
    Assumes this script is in the 'scripts/' subdirectory of the project.

    Returns:
        str: Absolute path to project root directory
    """
    # This file is at: <project_root>/scripts/mcp_config.py
    # So parent.parent gives us the project root
    script_path = Path(__file__).resolve()
    project_root = script_path.parent.parent
    return str(project_root)


def extract_server_name(filepath: Path) -> Optional[str]:
    """Extract server name from FastMCP() pattern in the file."""
    try:
        content = filepath.read_text(encoding="utf-8")
        pattern = r'FastMCP\(["\']([^"\']*)["\']'
        match = re.search(pattern, content)
        if match:
            return match.group(1)
        return None
    except Exception as e:
        print(f"Error reading file {filepath}: {e}")
        return None


def create_or_update_config(server_name: str, filename: str, config_file: Path) -> bool:
    try:
        # Create default config if file doesn't exist
        if not config_file.exists():
            default_config: Dict[str, Any] = {"mcpServers": {}}
            config_file.write_text(json.dumps(default_config, indent=2))

        # Load existing config
        config_data = json.loads(config_file.read_text(encoding="utf-8"))

        # Ensure mcpServers exists
        if "mcpServers" not in config_data:
            config_data["mcpServers"] = {}

        # Convert filename to module name (remove .py extension and convert path separators to dots)
        module_name = filename.replace(".py", "").replace("/", ".").replace("\\", ".")

        # Get absolute paths for portability
        poetry_cmd = find_poetry_command()
        project_dir = find_project_directory()

        # Add server configuration using module calling approach
        config_data["mcpServers"][server_name] = {
            "command": poetry_cmd,
            "args": [
                "run",
                "--directory",
                project_dir,
                "python3",
                "-m",
                f"{module_name}",
            ],
        }

        # Write updated config using a temporary file for atomic operation
        with tempfile.NamedTemporaryFile(mode="w", dir=config_file.parent, delete=False) as tmp:
            json.dump(config_data, tmp, indent=2)
            tmp_path = Path(tmp.name)

        # Atomically replace the original file
        tmp_path.replace(config_file)

        return True
    except Exception as e:
        print(f"Error updating config file {config_file}: {e}")
        return False


def main(default_config_file: str = "mcp_servers.json") -> None:
    if len(sys.argv) < 2:
        print("Usage: python3 mcp_config.py <filename> [config_file]")
        print("  filename:    Python file containing the FastMCP server")
        print(f"  config_file: JSON config file to update (default: {default_config_file})")
        sys.exit(1)

    filename = sys.argv[1]
    config_file_name = sys.argv[2] if len(sys.argv) > 2 else default_config_file

    src_path = Path(filename)
    if not src_path.exists():
        print(f"Error: File {src_path} not found")
        sys.exit(1)

    server_name = extract_server_name(src_path)
    if not server_name:
        print(f'Error: Could not find FastMCP("<servername>") pattern in {filename}')
        sys.exit(1)

    config_file = Path(config_file_name)
    try:
        if create_or_update_config(server_name, filename, config_file):
            print(f"Added MCP server configuration for '{server_name}' using '{filename}' to {config_file}")
        else:
            sys.exit(1)
    except RuntimeError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
