"""
Tool schemas for the <plugin-name> plugin — what the LLM sees.

Each constant is a JSON-Schema-style tool definition passed to
ctx.register_tool(schema=...) in __init__.py.

Rules:
- "name" must EXACTLY match the handler function name in tools.py
- "description" is what the LLM reads — be specific, include the return shape
- "parameters": every param needs "type" and "description"; list required ones in "required"
- Optional params with defaults: mention the default in the description, omit from "required"
"""

# ── Ping ──────────────────────────────────────────────────────────────────────

PING = {
    "name": "<plugin>_ping",
    "description": (
        "Check connectivity and authentication to <PLUGIN>. "
        "Call this first to verify credentials are working before using other <plugin>_* tools. "
        "Returns: {\"status\": \"ok\", ...} or {\"error\": \"...\"}."
    ),
    "parameters": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

# ── Add more tools below ───────────────────────────────────────────────────────
# Copy the pattern:
#
# SOME_TOOL = {
#     "name": "<plugin>_some_tool",
#     "description": (
#         "What this tool does in one or two sentences. "
#         "Include any important caveats (e.g. pagination, case-sensitivity). "
#         "Returns: {\"items\": [...], \"total\": N} or {\"error\": \"...\"}."
#     ),
#     "parameters": {
#         "type": "object",
#         "properties": {
#             "required_param": {
#                 "type": "string",
#                 "description": "What this param is. No default.",
#             },
#             "optional_param": {
#                 "type": "integer",
#                 "description": "Max results to return (default 20).",
#             },
#         },
#         "required": ["required_param"],
#     },
# }
