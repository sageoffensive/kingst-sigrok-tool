#!/usr/bin/env python3
"""
Generic command execution MCP server for Kali VM
Allows arbitrary shell command execution via MCP
"""

import asyncio
import json
import subprocess
import sys
from typing import Any


def _make_response(id_: Any, result: dict) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "result": result}


def _make_error(id_: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": id_, "error": {"code": code, "message": message}}


def _tool_result(content: str, is_error: bool = False) -> dict:
    return {
        "content": [{"type": "text", "text": content}],
        "isError": is_error,
    }


TOOLS = [
    {
        "name": "run_command",
        "description": "Execute a shell command on the Kali VM",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The shell command to execute",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default: 60)",
                    "default": 60,
                },
            },
            "required": ["command"],
        },
    },
]


def _run(cmd: str, timeout: int = 60) -> tuple[int, str, str]:
    """Run a shell command, return (returncode, stdout, stderr)."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)


def handle_run_command(args: dict) -> str:
    command = args.get("command", "")
    timeout = args.get("timeout", 60)
    
    if not command:
        return "Error: No command specified"
    
    rc, stdout, stderr = _run(command, timeout)
    
    result = f"Command: {command}\n"
    result += f"Exit code: {rc}\n\n"
    
    if stdout:
        result += f"STDOUT:\n{stdout}\n"
    if stderr:
        result += f"STDERR:\n{stderr}\n"
    
    return result


HANDLERS = {
    "run_command": handle_run_command,
}


def handle_request(req: dict) -> dict | None:
    method = req.get("method", "")
    id_ = req.get("id")
    params = req.get("params", {})

    if method == "initialize":
        return _make_response(id_, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "kali-generic-mcp", "version": "1.0.0"},
        })

    if method == "notifications/initialized":
        return None

    if method == "tools/list":
        return _make_response(id_, {"tools": TOOLS})

    if method == "tools/call":
        name = params.get("name", "")
        args = params.get("arguments", {})
        handler = HANDLERS.get(name)
        if not handler:
            return _make_response(id_, _tool_result(f"Unknown tool: {name}", is_error=True))
        try:
            result = handler(args)
            return _make_response(id_, _tool_result(result))
        except Exception as e:
            return _make_response(id_, _tool_result(f"Tool error: {e}", is_error=True))

    if method == "ping":
        return _make_response(id_, {})

    return _make_error(id_, -32601, f"Method not found: {method}")


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as e:
            sys.stdout.write(json.dumps(_make_error(None, -32700, f"Parse error: {e}")) + "\n")
            sys.stdout.flush()
            continue

        response = handle_request(req)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
