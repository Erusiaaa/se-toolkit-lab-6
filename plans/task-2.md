# Task 2: The Documentation Agent — Implementation Plan

## Overview

This task extends the Task 1 agent with an **agentic loop** and **tool calling** capabilities. The agent will:
1. Receive a question from the user
2. Send the question + tool definitions to the LLM
3. If LLM returns tool calls → execute tools, feed results back, repeat
4. If LLM returns final answer → output JSON with answer, source, and tool_calls

## LLM Provider and Model

**Provider:** Qwen Code API (same as Task 1)
**Model:** `qwen3-coder-plus` — supports function/tool calling

## Tool Definitions

### 1. `read_file`

**Purpose:** Read content of a file from the project repository.

**Parameters:**
- `path` (string, required): Relative path from project root (e.g., `wiki/git-workflow.md`)

**Returns:** File contents as string, or error message if file doesn't exist.

**Security:**
- Must resolve path relative to project root
- Block `..` traversal to prevent reading outside project directory
- Use `Path.resolve()` to get canonical path and verify it's within project root

**Schema (OpenAI function calling format):**
```json
{
  "name": "read_file",
  "description": "Read the contents of a file from the project repository.",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "Relative path from project root (e.g., 'wiki/git-workflow.md')"
      }
    },
    "required": ["path"]
  }
}
```

### 2. `list_files`

**Purpose:** List files and directories at a given path.

**Parameters:**
- `path` (string, required): Relative directory path from project root (e.g., `wiki`)

**Returns:** Newline-separated listing of files and directories.

**Security:**
- Must resolve path relative to project root
- Block `..` traversal
- Verify resolved path is within project root

**Schema:**
```json
{
  "name": "list_files",
  "description": "List files and directories at the given path.",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {
        "type": "string",
        "description": "Relative directory path from project root (e.g., 'wiki')"
      }
    },
    "required": ["path"]
  }
}
```

## Agentic Loop Architecture

### Loop Flow

```
┌─────────────────────────────────────────────────────────────────┐
│  1. Build messages list with system prompt + user question     │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. Call LLM with messages + tool definitions                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ Has tool_calls? │
                    └─────────────────┘
                         │        │
                       yes       no
                         │        │
                         ▼        │
              ┌───────────────────┴──────────────┐
              │                                  │
              ▼                                  ▼
    ┌───────────────────┐              ┌───────────────────┐
    │ 3. Execute tools  │              │ 5. Extract answer │
    │    - read_file    │              │    - source       │
    │    - list_files   │              │    - tool_calls   │
    └───────────────────┘              └───────────────────┘
              │                                  │
              ▼                                  │
    ┌───────────────────┐                        │
    │ 4. Append result  │                        │
    │    as tool role   │                        │
    │    to messages    │                        │
    └───────────────────┘                        │
              │                                  │
              └──────────────┬───────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Call count < 10?│
                    └─────────────────┘
                         │        │
                       yes       no
                         │        │
                         ▼        │
              ┌───────────────────┘
              │ (back to step 2)
              │
              ▼
    ┌───────────────────┐
    │ 6. Output JSON    │
    │    to stdout      │
    └───────────────────┘
```

### Message Format

Messages follow OpenAI chat format:

```python
messages = [
    {"role": "system", "content": SYSTEM_PROMPT},
    {"role": "user", "content": question},
    # After tool calls:
    {"role": "assistant", "content": None, "tool_calls": [...]},
    {"role": "tool", "tool_call_id": "...", "content": "..."},
]
```

### System Prompt Strategy

The system prompt should instruct the LLM to:

1. **Use tools to find answers** in the wiki directory
2. **First list files** to discover relevant wiki pages
3. **Then read files** to find the specific answer
4. **Include source reference** (file path + section anchor) in the final answer
5. **Stop after 10 tool calls** maximum

Example system prompt:
```
You are a documentation assistant. You have access to tools that let you read files 
and list directories in a project repository.

When asked a question:
1. Use list_files to explore the wiki/ directory
2. Use read_file to read relevant wiki pages
3. Find the answer and include the source (file path + section anchor)
4. Provide a clear, concise answer

Always include the source of your answer (e.g., wiki/git-workflow.md#resolving-merge-conflicts).
Maximum 10 tool calls allowed.
```

## Path Security Implementation

```python
from pathlib import Path

def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.resolve()

def safe_path(user_path: str) -> Path | None:
    """
    Validate that user-provided path is within project root.
    Returns None if path is unsafe.
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
```

## Error Handling

| Error | Handling |
|-------|----------|
| File not found | Return error message as tool result |
| Path traversal attempt | Return error: "Access denied" |
| LLM returns invalid tool call | Log error, continue loop |
| Timeout (>60s per call) | Exit with error |
| Max 10 tool calls | Stop loop, return partial answer |

## Output Format

```json
{
  "answer": "Edit the conflicting file...",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git-workflow.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "..."
    }
  ]
}
```

## Testing Strategy

### Test 1: Merge Conflict Question
**Question:** "How do you resolve a merge conflict?"
**Expected:**
- `read_file` in tool_calls
- `wiki/git-workflow.md` in source field

### Test 2: List Files Question
**Question:** "What files are in the wiki?"
**Expected:**
- `list_files` in tool_calls

## Dependencies

Same as Task 1:
- `httpx` — HTTP client
- `pydantic-settings` — Settings management

## File Changes

```
project-root/
├── agent.py              # Updated with tools + agentic loop
├── plans/
│   └── task-2.md         # This plan file
├── tests/
│   ├── test_task1_agent.py    # Existing test
│   └── test_task2_agent.py    # New tests for Task 2
└── AGENT.md              # Updated documentation
```

## Acceptance Criteria Checklist

- [ ] `plans/task-2.md` exists with implementation plan
- [ ] `agent.py` defines `read_file` and `list_files` as tool schemas
- [ ] Agentic loop executes tool calls and feeds results back
- [ ] `tool_calls` in output is populated when tools are used
- [ ] `source` field correctly identifies wiki section
- [ ] Tools do not access files outside project directory
- [ ] `AGENT.md` documents tools and agentic loop
- [ ] 2 tool-calling regression tests exist and pass
