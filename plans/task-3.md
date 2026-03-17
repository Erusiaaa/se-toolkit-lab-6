# Task 3: The System Agent — Implementation Plan

## Overview

Add a `query_api` tool to the agent so it can query the deployed backend API and answer:
1. **Static system facts** — framework, ports, status codes (from source code)
2. **Data-dependent queries** — item count, scores, analytics (from live API)

## LLM Provider

**Provider:** Qwen Code API (self-hosted on VM)
**Model:** `qwen3-coder-plus`
**API Base:** `http://10.93.25.146:8000/v1`
**API Key:** Stored in `.env.agent.secret`

## New Tool: `query_api`

### Schema

```json
{
  "type": "function",
  "function": {
    "name": "query_api",
    "description": "Send an HTTP request to the backend LMS API. Use this to query live data (e.g., item count, completion rates) or check API behavior (status codes, errors).",
    "parameters": {
      "type": "object",
      "properties": {
        "method": {
          "type": "string",
          "description": "HTTP method: GET, POST, PUT, DELETE, etc."
        },
        "path": {
          "type": "string",
          "description": "API endpoint path (e.g., '/items/', '/analytics/completion-rate')"
        },
        "body": {
          "type": "string",
          "description": "Optional JSON request body for POST/PUT requests"
        }
      },
      "required": ["method", "path"]
    }
  }
}
```

### Implementation

```python
def tool_query_api(method: str, path: str, body: str | None = None) -> str:
    """
    Call the backend LMS API with authentication.
    
    - Reads LMS_API_KEY from .env.docker.secret
    - Reads AGENT_API_BASE_URL from env (default: http://localhost:42002)
    - Returns JSON string with status_code and body
    """
```

### Authentication

- Use `LMS_API_KEY` from `.env.docker.secret` (NOT the LLM API key!)
- Send as `X-API-Key` header (or check backend docs for exact header name)
- Backend URL: `AGENT_API_BASE_URL` env var, default `http://localhost:42002`

## Environment Variables

Add to `agent.py` settings:

| Variable | Source | Purpose |
|----------|--------|---------|
| `LMS_API_KEY` | `.env.docker.secret` | Backend API authentication |
| `AGENT_API_BASE_URL` | env (optional) | Backend base URL (default: `http://localhost:42002`) |

**Important:** The agent must read these from environment, not hardcode. The autochecker injects different values during evaluation.

## System Prompt Update

Update `SYSTEM_PROMPT` to guide the LLM on **when** to use each tool:

```
You are a documentation and system assistant for a software engineering lab.

You have access to tools that let you:
1. Read files and list directories in the project repository (wiki/, backend/, etc.)
2. Query the live backend API for data and system behavior

Tool selection guide:
- Use `read_file` and `list_files` for:
  - Wiki documentation questions
  - Source code analysis (framework, ports, bug diagnosis)
  - Configuration files (docker-compose.yml, Dockerfile, etc.)

- Use `query_api` for:
  - Data queries (how many items, top learners, completion rates)
  - API behavior questions (status codes, error responses)
  - Live system state

When answering:
1. Identify what kind of question is asked (wiki, source code, or live data)
2. Choose the appropriate tool(s)
3. For bug diagnosis: first query the API to see the error, then read the source code
4. Include source references for wiki/code answers (file path + section anchor)
5. For API queries, report the actual response data

Maximum 10 tool calls allowed.
```

## Implementation Steps

1. **Add environment variable loading**
   - Extend `AgentSettings` to load `LMS_API_KEY` and `AGENT_API_BASE_URL`
   - Handle missing `.env.docker.secret` gracefully

2. **Implement `tool_query_api`**
   - Build URL from `AGENT_API_BASE_URL` + `path`
   - Add auth header with `LMS_API_KEY`
   - Handle HTTP errors (4xx, 5xx) and return structured JSON

3. **Add tool to `TOOLS` list**
   - Include full schema for function calling

4. **Update `execute_tool`**
   - Add handler for `query_api`

5. **Update `SYSTEM_PROMPT`**
   - Guide LLM on tool selection

6. **Update output format**
   - Make `source` optional (system questions may not have wiki source)

7. **Test locally**
   - Run `uv run run_eval.py`
   - Iterate on failures

## Benchmark Strategy

Run `uv run run_eval.py` and track results:

| Question | Expected Tool | Status |
|----------|---------------|--------|
| 0. Protect branch steps | `read_file` | - |
| 1. SSH connection | `read_file` | - |
| 2. Web framework | `read_file` | - |
| 3. API router modules | `list_files` | - |
| 4. Item count | `query_api` | - |
| 5. Status code without auth | `query_api` | - |
| 6. Completion-rate error | `query_api` + `read_file` | - |
| 7. Top-learners crash | `query_api` + `read_file` | - |
| 8. Request lifecycle | `read_file` | - |
| 9. ETL idempotency | `read_file` | - |

## Potential Issues & Mitigations

| Issue | Mitigation |
|-------|------------|
| Backend not running | Start docker-compose first |
| LMS_API_KEY wrong | Check .env.docker.secret matches backend |
| Agent times out | Reduce max iterations or use faster model |
| LLM calls wrong tool | Improve system prompt clarity |
| API returns HTML error | Parse response carefully, return raw content |

## Success Criteria

- [ ] `query_api` tool implemented and authenticated
- [ ] All 10 `run_eval.py` questions pass
- [ ] `AGENT.md` updated (200+ words)
- [ ] 2 new regression tests added
- [ ] Plan updated with benchmark results

## Initial Benchmark Score

*To be filled after first run.*
