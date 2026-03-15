# Task 1: Call an LLM from Code — Implementation Plan

## LLM Provider and Model

**Provider:** Qwen Code API (self-hosted on VM)

**Reasons for choosing Qwen Code:**
- 1000 free requests per day — sufficient for development and testing
- Works from Russia without restrictions
- No credit card required
- OpenAI-compatible API — easy to integrate using standard libraries
- Strong model performance for coding tasks

**Model:** `qwen3-coder-plus` (recommended default)

**Configuration:**
- API Base URL: `http://10.93.25.146:8000/v1` (VM IP with Qwen Code API proxy)
- API Key: Stored in `.env.agent.secret` (not hardcoded)
- Model name: Read from environment variable `LLM_MODEL`

## Agent Architecture

### Components

1. **Environment Loader**
   - Reads `.env.agent.secret` file
   - Extracts `LLM_API_KEY`, `LLM_API_BASE`, `LLM_MODEL`
   - Uses `python-dotenv` library for loading

2. **Command-Line Interface**
   - Single CLI argument: the user's question
   - Uses `sys.argv` for argument parsing
   - Validates input (exits with error if no question provided)

3. **LLM Client**
   - Uses `httpx` or `requests` library for HTTP calls
   - Sends POST request to `{LLM_API_BASE}/chat/completions`
   - Headers: `Authorization: Bearer {LLM_API_KEY}`, `Content-Type: application/json`
   - Request body: OpenAI-compatible format with model and messages

4. **Response Parser**
   - Parses JSON response from LLM
   - Extracts the `content` field from the first choice
   - Formats output as required JSON structure

5. **Output Formatter**
   - Outputs single JSON line to stdout: `{"answer": "...", "tool_calls": []}`
   - All debug/logging output goes to stderr
   - Exit code 0 on success, non-zero on error

### Data Flow

```
User Input (CLI arg) 
    → Read .env.agent.secret 
    → Build HTTP request 
    → Call LLM API 
    → Parse JSON response 
    → Format output 
    → Print JSON to stdout
```

## Error Handling

- **Missing environment file:** Exit with clear error message to stderr
- **Missing API key:** Exit with error
- **Network errors:** Catch exceptions, print to stderr, exit with code 1
- **API errors (4xx, 5xx):** Print error details to stderr, exit with code 1
- **Timeout:** Set 60-second timeout for API request

## Testing Strategy

**Single regression test:**
- Run `agent.py` as subprocess with a test question
- Parse stdout as JSON
- Verify:
  - `answer` field exists and is a non-empty string
  - `tool_calls` field exists and is an array
- Test file location: `tests/test_task1_agent.py`

## File Structure

```
project-root/
├── agent.py              # Main CLI script
├── .env.agent.secret     # LLM credentials (gitignored)
├── plans/
│   └── task-1.md         # This plan file
├── tests/
│   └── test_task1_agent.py  # Regression test
└── AGENT.md              # Documentation (to be updated)
```

## Dependencies

- `httpx` or `requests` — for HTTP requests to LLM API
- `python-dotenv` — for loading environment variables
- `pytest` — for running tests (already in project)

## Acceptance Criteria Checklist

- [ ] `plans/task-1.md` exists with implementation plan
- [ ] `agent.py` exists in project root
- [ ] `uv run agent.py "..."` outputs valid JSON with `answer` and `tool_calls`
- [ ] API key stored in `.env.agent.secret` (not hardcoded)
- [ ] `AGENT.md` documents the solution architecture
- [ ] 1 regression test exists and passes
