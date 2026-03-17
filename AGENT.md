# Agent Architecture Documentation

## Overview

This document describes the architecture of the LLM agent built for this lab. The agent is a CLI program that connects to an LLM API, uses tools to gather information, and returns structured JSON answers with source references.

## LLM Provider

**Provider:** Qwen Code API (self-hosted)

**Why Qwen Code:**
- 1000 free requests per day — sufficient for development and testing
- Works from Russia without restrictions
- No credit card required
- OpenAI-compatible API with function calling support
- Strong performance on coding and reasoning tasks

**Model:** `qwen3-coder-plus`

**Configuration:**
- API Base: `http://10.93.25.146:8000/v1`
- API Key: Stored in `.env.agent.secret`
- Timeout: 60 seconds per request

## Architecture

### Components

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  CLI Interface  │ ──→ │  Agentic Loop   │ ──→ │  Output Formatter│
│  (arg parsing)  │     │  (tool executor)│     │  (JSON output)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         ↓                       ↓                       ↓
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Settings       │     │  Tool Registry  │     │  Source Extractor│
│  (pydantic)     │     │  (read, list)   │     │  (path parsing)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### Agentic Loop

The agent follows an iterative loop:

1. **Build messages** — System prompt + user question + conversation history
2. **Call LLM** — Send messages with tool definitions
3. **Check response** — Does the LLM want to call tools?
   - **Yes** → Execute tools, append results, go to step 1
   - **No** → Extract final answer, go to step 4
4. **Output JSON** — Return answer, source, and tool_calls

```
┌─────────────────────────────────────────────────────────────────┐
│  1. messages = [system, user_question]                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  2. response = LLM(messages, tools)                             │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │ tool_calls?     │
                    └─────────────────┘
                         │        │
                       yes       no
                         │        │
                         ▼        │
              ┌───────────────────┴──────────────┐
              │                                  │
              ▼                                  ▼
    ┌───────────────────┐              ┌───────────────────┐
    │ 3. Execute tools  │              │ 4. Extract answer │
    │    - read_file    │              │    - source       │
    │    - list_files   │              │    - tool_calls   │
    └───────────────────┘              └───────────────────┘
              │                                  │
              ▼                                  │
    ┌───────────────────┐                        │
    │ Append tool       │                        │
    │ results to        │                        │
    │ messages          │                        │
    └───────────────────┘                        │
              │                                  │
              └──────────────┬───────────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ iteration < 10? │
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
    │ 5. Output JSON    │
    └───────────────────┘
```

### Tools

The agent has **three** tools registered as function-calling schemas:

#### `read_file`

Read the contents of a file from the project repository.

**Parameters:**
- `path` (string): Relative path from project root (e.g., `wiki/git-workflow.md`)

**Returns:** File contents as string, or error message.

**Security:**
- Validates path is within project directory
- Blocks `..` traversal attempts
- Returns error for paths outside project root

#### `list_files`

List files and directories at the given path.

**Parameters:**
- `path` (string): Relative directory path from project root (e.g., `wiki`)

**Returns:** Newline-separated listing, or error message.

**Security:**
- Validates path is within project directory
- Blocks `..` traversal attempts

#### `query_api` (Task 3)

Send an HTTP request to the backend LMS API. Use this to query live data (e.g., item count, completion rates, top learners) or check API behavior (status codes, error responses).

**Parameters:**
- `method` (string): HTTP method — GET, POST, PUT, DELETE, etc.
- `path` (string): API endpoint path (e.g., `/items/`, `/analytics/completion-rate`)
- `body` (string, optional): JSON request body for POST/PUT requests

**Returns:** JSON string with `status_code` and `body` fields.

**Authentication:**
- Uses `LMS_API_KEY` from `.env.docker.secret`
- Sends as `Authorization: Bearer <LMS_API_KEY>` header

**Environment Variables:**
- `AGENT_API_BASE_URL`: Backend base URL (default: `http://localhost:42002`)
- `LMS_API_KEY`: Backend API authentication key

**Example:**
```json
{
  "tool": "query_api",
  "args": {"method": "GET", "path": "/items/"},
  "result": "{\"status_code\": 200, \"body\": \"[]\"}"
}
```

### Path Security

```python
def safe_path(user_path: str) -> Path | None:
    """Validate path is within project root."""
    project_root = get_project_root()
    requested_path = (project_root / user_path).resolve()
    try:
        requested_path.relative_to(project_root)
        return requested_path
    except ValueError:
        return None  # Path is outside project root
```

### System Prompt

The system prompt instructs the LLM to:

1. Use `list_files` to explore the `wiki/` directory
2. Use `read_file` to read relevant wiki pages
3. Find the answer and include the source reference
4. Stop after 10 tool calls maximum

```
You are a documentation assistant for a software engineering lab.

You have access to tools that let you read files and list directories in a project repository.

When asked a question:
1. Use list_files to explore the wiki/ directory to find relevant documentation
2. Use read_file to read the contents of relevant wiki pages
3. Find the answer to the user's question
4. Include the source reference in your final answer (file path + section anchor if applicable)

Maximum 10 tool calls allowed.
```

### Output Format

```json
{
  "answer": "Edit the conflicting file, choose which changes to keep, then stage and commit.",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git-workflow.md\nREADME.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git-workflow.md"},
      "result": "# Git Workflow\n\n## Resolving Merge Conflicts\n..."
    }
  ]
}
```

**Fields:**
- `answer` (string): The final answer from the LLM
- `source` (string): Wiki file path with optional section anchor
- `tool_calls` (array): All tool calls made during the loop

## How to Run

### Prerequisites

1. Set up Qwen Code API on your VM (see `wiki/qwen.md`)
2. Create `.env.agent.secret` with your credentials:
   ```bash
   cp .env.agent.example .env.agent.secret
   # Edit with your API key and VM IP
   ```

### Basic Usage

```bash
uv run agent.py "How do you resolve a merge conflict?"
```

### Expected Output

```json
{
  "answer": "...",
  "source": "wiki/git-workflow.md#resolving-merge-conflicts",
  "tool_calls": [...]
}
```

### Running Tests

```bash
# Run Task 2 tests
pytest tests/test_task2_agent.py -v

# Run all tests
pytest tests/ -v
```

## Environment Variables

| Variable | Source | Description | Example |
|----------|--------|-------------|---------|
| `LLM_API_KEY` | `.env.agent.secret` | Your Qwen Code API key | `your-api-key` |
| `LLM_API_BASE` | `.env.agent.secret` | API base URL | `http://10.93.25.146:8000/v1` |
| `LLM_MODEL` | `.env.agent.secret` | Model name | `qwen3-coder-plus` |
| `LMS_API_KEY` | `.env.docker.secret` | Backend API authentication key for `query_api` | `13` |
| `AGENT_API_BASE_URL` | Environment (optional) | Backend base URL for `query_api` (default: `http://localhost:42002`) | `http://localhost:42002` |

**Important:** The agent reads all configuration from environment variables, not hardcoded values. The autochecker injects different values during evaluation.

## Error Handling

| Error | Behavior |
|-------|----------|
| Missing `.env.agent.secret` | Exit with error message to stderr |
| Missing API key | Exit with error message to stderr |
| Missing `LMS_API_KEY` | Warning printed to stderr, `query_api` will fail |
| Network timeout (>60s) | Exit with timeout error |
| HTTP error (4xx, 5xx) | Print status code and response to stderr |
| Invalid API response | Print parsing error to stderr |
| Path traversal attempt | Return "Access denied" as tool result |
| File not found | Return "File not found" as tool result |
| Max 10 tool calls | Stop loop, return partial answer |
| Backend connection failed | Return error JSON from `query_api` |

## Dependencies

- `httpx` — HTTP client for API calls
- `pydantic-settings` — Environment variable loading and validation
- `pytest` — Testing framework

## File Structure

```
project-root/
├── agent.py              # Main CLI script
├── .env.agent.secret     # LLM credentials (gitignored)
├── .env.agent.example    # Example environment file
├── .env.docker.secret    # Backend API key (gitignored)
├── AGENT.md              # This documentation
├── plans/
│   ├── task-1.md         # Task 1 implementation plan
│   ├── task-2.md         # Task 2 implementation plan
│   └── task-3.md         # Task 3 implementation plan
└── tests/
    ├── test_task1_agent.py  # Task 1 regression test
    ├── test_task2_agent.py  # Task 2 regression tests
    └── test_task3_agent.py  # Task 3 regression tests
```

## Task 3: Lessons Learned

### Adding the `query_api` Tool

The main challenge in Task 3 was integrating a new tool that communicates with an external HTTP API while maintaining the existing agentic loop architecture.

**Key decisions:**

1. **Authentication handling:** The `query_api` tool needs `LMS_API_KEY` from `.env.docker.secret`, which is a different file from the LLM credentials. I extended `AgentSettings` to load both files and added a fallback mechanism using `dotenv`.

2. **Environment variable flexibility:** The agent reads `AGENT_API_BASE_URL` from environment with a sensible default (`http://localhost:42002`). This allows the autochecker to inject different URLs during evaluation.

3. **Tool selection guidance:** The system prompt was updated to clearly distinguish when the LLM should use `query_api` (live data, API behavior) vs `read_file`/`list_files` (wiki, source code). This distinction is crucial for the LLM to choose the right tool.

4. **Error handling:** The `query_api` tool returns structured JSON even on errors (e.g., connection failures, timeouts), so the LLM can reason about API errors and potentially retry or report the issue.

### Benchmark Performance

*To be filled after running `uv run run_eval.py`.*

### Troubleshooting Task 3

| Issue | Solution |
|-------|----------|
| `query_api` returns connection error | Ensure Docker containers are running: `docker-compose ps` |
| Agent uses wrong tool for data questions | Improve system prompt to clarify tool selection |
| API returns 401 Unauthorized | Check `LMS_API_KEY` matches backend configuration |
| Agent times out on multi-step questions | Reduce max iterations or optimize tool descriptions |

## Troubleshooting

> **Tip:** If you encounter issues, check that your VM is running and the Qwen Code API is accessible.

### "Connection refused" error
- Check that your VM is running and accessible
- Verify the IP address and port in `LLM_API_BASE`
- Test connectivity: `curl http://<vm-ip>:<port>/v1/models`

### "Invalid API key" error
- Check that `LLM_API_KEY` matches the key in your VM's `~/qwen-code-oai-proxy/.env`
- Ensure no extra spaces or quotes in the value

### Agent doesn't find the answer
- Check that the wiki directory contains relevant documentation
- The LLM may need more iterations — check stderr for tool call logs

### Tool calls return "Access denied"
- Ensure the path is relative to project root
- Don't use `../` or absolute paths
