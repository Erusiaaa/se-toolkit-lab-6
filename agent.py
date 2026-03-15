#!/usr/bin/env python3
"""
Agent CLI - Calls an LLM with tool calling capabilities.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON object with 'answer', 'source', and 'tool_calls' fields to stdout.
    All debug output goes to stderr.
"""

import json
import sys
from pathlib import Path
from typing import Any

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """Settings loaded from .env.agent.secret."""

    model_config = SettingsConfigDict(
        env_file=".env.agent.secret",
        env_file_encoding="utf-8",
    )

    llm_api_key: str
    llm_api_base: str
    llm_model: str = "qwen3-coder-plus"


def load_settings() -> AgentSettings:
    """Load and validate agent settings from environment file."""
    env_file = Path(".env.agent.secret")
    if not env_file.exists():
        print("Error: .env.agent.secret file not found", file=sys.stderr)
        print(
            "Create it by copying .env.agent.example and filling in your LLM credentials",
            file=sys.stderr,
        )
        sys.exit(1)

    try:
        settings = AgentSettings()
        return settings
    except Exception as e:
        print(f"Error loading settings: {e}", file=sys.stderr)
        sys.exit(1)


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.resolve()


def safe_path(user_path: str) -> Path | None:
    """
    Validate that user-provided path is within project root.
    Returns None if path is unsafe (outside project directory).
    """
    project_root = get_project_root()
    # Resolve the user path relative to project root
    requested_path = (project_root / user_path).resolve()
    # Check if resolved path is within project root
    try:
        requested_path.relative_to(project_root)
        return requested_path
    except ValueError:
        return None  # Path is outside project root


def tool_read_file(path: str) -> str:
    """
    Read the contents of a file from the project repository.

    Args:
        path: Relative path from project root (e.g., 'wiki/git-workflow.md')

    Returns:
        File contents as string, or error message if file doesn't exist or is unsafe.
    """
    safe = safe_path(path)
    if safe is None:
        return "Error: Access denied - path is outside project directory"

    if not safe.exists():
        return f"Error: File not found: {path}"

    if not safe.is_file():
        return f"Error: Not a file: {path}"

    try:
        return safe.read_text(encoding="utf-8")
    except Exception as e:
        return f"Error reading file: {e}"


def tool_list_files(path: str) -> str:
    """
    List files and directories at the given path.

    Args:
        path: Relative directory path from project root (e.g., 'wiki')

    Returns:
        Newline-separated listing of files and directories, or error message.
    """
    safe = safe_path(path)
    if safe is None:
        return "Error: Access denied - path is outside project directory"

    if not safe.exists():
        return f"Error: Directory not found: {path}"

    if not safe.is_dir():
        return f"Error: Not a directory: {path}"

    try:
        entries = sorted(safe.iterdir())
        names = [entry.name for entry in entries]
        return "\n".join(names)
    except Exception as e:
        return f"Error listing directory: {e}"


# Tool definitions for LLM function calling
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read the contents of a file from the project repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root (e.g., 'wiki/git-workflow.md')",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files and directories at the given path.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root (e.g., 'wiki')",
                    }
                },
                "required": ["path"],
            },
        },
    },
]

# System prompt for the documentation agent
SYSTEM_PROMPT = """You are a documentation assistant for a software engineering lab.

You have access to tools that let you read files and list directories in a project repository.

When asked a question:
1. Use list_files to explore the wiki/ directory to find relevant documentation
2. Use read_file to read the contents of relevant wiki pages
3. Find the answer to the user's question
4. Include the source reference in your final answer (file path + section anchor if applicable)

For example, if you find the answer in wiki/git-workflow.md under the "Resolving Merge Conflicts" section,
the source should be: wiki/git-workflow.md#resolving-merge-conflicts

Maximum 10 tool calls allowed. After that, provide the best answer you have found so far.
"""


def execute_tool(tool_name: str, args: dict[str, Any]) -> str:
    """
    Execute a tool call and return the result.

    Args:
        tool_name: Name of the tool to execute
        args: Arguments for the tool

    Returns:
        Tool result as string
    """
    if tool_name == "read_file":
        path = args.get("path", "")
        print(f"  Executing read_file({path!r})", file=sys.stderr)
        return tool_read_file(path)

    elif tool_name == "list_files":
        path = args.get("path", "")
        print(f"  Executing list_files({path!r})", file=sys.stderr)
        return tool_list_files(path)

    else:
        return f"Error: Unknown tool: {tool_name}"


def call_llm(
    messages: list[dict[str, Any]],
    settings: AgentSettings,
    use_tools: bool = True,
) -> dict[str, Any]:
    """
    Call the LLM API with messages and optional tool definitions.

    Args:
        messages: List of message dicts for the chat
        settings: Agent settings with API credentials
        use_tools: Whether to include tool definitions in the request

    Returns:
        Parsed JSON response from the API
    """
    url = f"{settings.llm_api_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }

    payload: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": messages,
    }

    if use_tools:
        payload["tools"] = TOOLS

    print(f"Calling LLM at {url}...", file=sys.stderr)

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

    except httpx.TimeoutException:
        print("Error: Request timed out after 60 seconds", file=sys.stderr)
        sys.exit(1)
    except httpx.HTTPStatusError as e:
        print(f"Error: API returned status code {e.response.status_code}", file=sys.stderr)
        print(f"Response: {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except httpx.RequestError as e:
        print(f"Error: Failed to connect to LLM API: {e}", file=sys.stderr)
        sys.exit(1)


def run_agentic_loop(question: str, settings: AgentSettings) -> dict[str, Any]:
    """
    Run the agentic loop: call LLM, execute tools, repeat until final answer.

    Args:
        question: User's question
        settings: Agent settings

    Returns:
        Result dict with answer, source, and tool_calls
    """
    # Initialize messages with system prompt and user question
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    # Track all tool calls for the output
    tool_calls_log: list[dict[str, Any]] = []

    # Maximum iterations
    max_iterations = 10

    for iteration in range(max_iterations):
        print(f"\n--- Iteration {iteration + 1}/{max_iterations} ---", file=sys.stderr)

        # Call LLM
        response_data = call_llm(messages, settings, use_tools=True)

        # Extract the assistant message
        choice = response_data["choices"][0]
        message = choice["message"]

        # Check for tool calls
        tool_calls = message.get("tool_calls")

        if not tool_calls:
            # No tool calls - LLM provided final answer
            print("LLM provided final answer (no tool calls)", file=sys.stderr)
            answer = message.get("content", "")

            # Try to extract source from the answer
            source = extract_source_from_answer(answer, tool_calls_log)

            return {
                "answer": answer,
                "source": source,
                "tool_calls": tool_calls_log,
            }

        # Process tool calls
        print(f"LLM requested {len(tool_calls)} tool call(s)", file=sys.stderr)

        # Add assistant message with tool calls to messages
        messages.append(message)

        # Execute each tool call
        for tool_call in tool_calls:
            tool_id = tool_call["id"]
            function = tool_call["function"]
            tool_name = function["name"]

            # Parse arguments
            try:
                args = json.loads(function["arguments"])
            except json.JSONDecodeError:
                args = {}

            # Log the tool call
            tool_call_entry = {
                "tool": tool_name,
                "args": args,
                "result": None,  # Will be set after execution
            }
            tool_calls_log.append(tool_call_entry)

            # Execute the tool
            result = execute_tool(tool_name, args)
            tool_call_entry["result"] = result

            # Add tool result to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_id,
                "content": result,
            })

            print(f"  Result: {result[:100]}...", file=sys.stderr)

    # Max iterations reached
    print("\nMax iterations reached", file=sys.stderr)

    # Try to provide whatever answer we have
    if tool_calls_log:
        # Summarize what we found
        answer = "I reached the maximum number of tool calls (10). Based on my research:"
        # Try to extract some useful info from the last tool result
        last_result = tool_calls_log[-1].get("result", "")
        if last_result:
            answer += f"\n\nLast found: {last_result[:500]}"
        source = extract_source_from_answer(answer, tool_calls_log)
    else:
        answer = "Unable to find an answer within the tool call limit."
        source = ""

    return {
        "answer": answer,
        "source": source,
        "tool_calls": tool_calls_log,
    }


def extract_source_from_answer(answer: str, tool_calls_log: list[dict[str, Any]]) -> str:
    """
    Try to extract or infer the source from the answer and tool calls.

    Args:
        answer: The LLM's answer
        tool_calls_log: List of tool calls made

    Returns:
        Source string (file path with optional section anchor)
    """
    # Look for wiki file references in the answer
    import re

    # Pattern to match wiki/*.md references
    pattern = r"(wiki/[\w-]+\.md(?:#[\w-]+)?)"
    matches = re.findall(pattern, answer, re.IGNORECASE)

    if matches:
        return matches[0]

    # If no explicit source in answer, use the last read_file path
    for call in reversed(tool_calls_log):
        if call["tool"] == "read_file":
            path = call["args"].get("path", "")
            if path.startswith("wiki/"):
                return path

    return ""


def main() -> None:
    """Main entry point for the agent CLI."""
    # Parse command-line arguments
    if len(sys.argv) != 2:
        print("Usage: uv run agent.py \"Your question here\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    # Load settings
    settings = load_settings()

    # Run the agentic loop
    result = run_agentic_loop(question, settings)

    # Output JSON to stdout (single line)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
