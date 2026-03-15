# Agent Architecture Documentation

## Overview

This document describes the architecture of the LLM agent built for this lab. The agent is a CLI program that connects to an LLM API and returns structured JSON answers.

## LLM Provider

**Provider:** Qwen Code API (self-hosted)

**Why Qwen Code:**
- 1000 free requests per day — sufficient for development and testing
- Works from Russia without restrictions
- No credit card required
- OpenAI-compatible API — easy integration
- Strong performance on coding and reasoning tasks

**Model:** `qwen3-coder-plus`

**Configuration:**
- API Base: `http://10.93.25.146:8000/v1`
- API Key: Stored in `.env.agent.secret`
- Timeout: 60 seconds

## Architecture

### Components

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  CLI Interface  │ ──→ │  LLM Client     │ ──→ │  Output Formatter│
│  (arg parsing)  │     │  (httpx call)   │     │  (JSON output)   │
└─────────────────┘     └─────────────────┘     └─────────────────┘
         ↓                       ↓
┌─────────────────┐     ┌─────────────────┐
│  Settings       │     │  Error Handler  │
│  (pydantic)     │     │  (stderr logs)  │
└─────────────────┘     └─────────────────┘
```

### Data Flow

1. **Input:** User provides a question as a command-line argument
2. **Settings Load:** Agent reads `.env.agent.secret` using `pydantic-settings`
3. **API Call:** Agent sends HTTP POST request to LLM API using `httpx`
4. **Response Parse:** Agent extracts answer from JSON response
5. **Output:** Agent prints JSON `{"answer": "...", "tool_calls": []}` to stdout

### File Structure

```
project-root/
├── agent.py              # Main CLI script
├── .env.agent.secret     # LLM credentials (gitignored)
├── .env.agent.example    # Example environment file
├── AGENT.md              # This documentation
├── plans/
│   └── task-1.md         # Implementation plan
└── tests/
    └── test_task1_agent.py  # Regression test
```

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
uv run agent.py "What does REST stand for?"
```

### Expected Output

```json
{"answer": "Representational State Transfer.", "tool_calls": []}
```

### Running Tests

```bash
# Run the Task 1 test
pytest tests/test_task1_agent.py -v
```

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_API_KEY` | Your Qwen Code API key | `your-api-key` |
| `LLM_API_BASE` | API base URL | `http://10.93.25.146:8000/v1` |
| `LLM_MODEL` | Model name | `qwen3-coder-plus` |

## Error Handling

The agent handles the following error cases:

| Error | Behavior |
|-------|----------|
| Missing `.env.agent.secret` | Exit with error message to stderr |
| Missing API key | Exit with error message to stderr |
| Network timeout (>60s) | Exit with timeout error |
| HTTP error (4xx, 5xx) | Print status code and response to stderr |
| Invalid API response | Print parsing error to stderr |

## Output Format

**stdout:** Single JSON line with:
- `answer` (string): The LLM's response
- `tool_calls` (array): Empty for Task 1 (populated in Task 2)

**stderr:** All debug and error messages

**Exit codes:**
- `0`: Success
- `1`: Error (missing args, API error, timeout, etc.)

## Dependencies

- `httpx` — HTTP client for API calls
- `pydantic-settings` — Environment variable loading and validation
- `pytest` — Testing framework

## Future Extensions (Tasks 2–3)

In subsequent tasks, the agent will be extended with:

1. **Tools:** Functions the agent can call (e.g., `read_file`, `query_api`)
2. **Agentic Loop:** Repeated reasoning and tool usage until task completion
3. **System Prompt:** Enhanced instructions for tool usage and behavior
4. **Tool Call Tracking:** Populate `tool_calls` array in output

## Troubleshooting

### "Connection refused" error
- Check that your VM is running and accessible
- Verify the IP address and port in `LLM_API_BASE`
- Test connectivity: `curl http://<vm-ip>:<port>/v1/models`

### "Invalid API key" error
- Check that `LLM_API_KEY` matches the key in your VM's `~/qwen-code-oai-proxy/.env`
- Ensure no extra spaces or quotes in the value

### Timeout errors
- Check network connectivity to your VM
- The model may be slow during peak usage — try again
