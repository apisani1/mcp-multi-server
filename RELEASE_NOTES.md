## MCP Multi-Server v1.2.5

A security-hardening release. The `mcp_multi_server` library API is unchanged; the fixes cover the bundled example code and raise minimum dependency versions.

### Security
- Example servers restrict file reads to `MCP_EXAMPLES_FILES_ROOT` (default: current working directory).
- Example media handler only fetches `http(s)` resource links.
- The inventory database unpickler now uses an allow-list and rejects unexpected types with `UnpicklingError`.
- Vulnerable locked dependencies refreshed.

### Upgrade notes
- Minimum `mcp` is now **1.30.0** (was 1.27.1).
- The `examples` extra now requires `pillow>=12.3.0,<14.0.0`.
- If your example servers read files outside the working directory, set `MCP_EXAMPLES_FILES_ROOT`.

### Improvements to the example chat clients
- Text-file contents from embedded blobs are passed to the LLM.
- OpenAI API errors, prompt/resource retrieval errors and failed tool results are reported without ending the session.
- Denied file access is logged as one line instead of a traceback.

**Full changelog**: https://github.com/apisani1/mcp-multi-server/compare/v1.2.4...v1.2.5
