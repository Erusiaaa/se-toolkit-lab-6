#!/usr/bin/env python3
"""
Agent CLI - Calls an LLM to answer user questions.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON object with 'answer' and 'tool_calls' fields to stdout.
    All debug output goes to stderr.
"""

import json
import sys
from pathlib import Path

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


def call_llm(question: str, settings: AgentSettings) -> str:
    """
    Call the LLM API with the user's question.

    Args:
        question: The user's question
        settings: Agent settings with API credentials

    Returns:
        The LLM's answer as a string

    Raises:
        SystemExit: On API errors or timeouts
    """
    url = f"{settings.llm_api_base}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.llm_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": settings.llm_model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": question},
        ],
    }

    print(f"Calling LLM at {url}...", file=sys.stderr)

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            # Extract the answer from the response
            answer = data["choices"][0]["message"]["content"]
            return answer

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
    except (KeyError, IndexError) as e:
        print(f"Error: Unexpected API response format: {e}", file=sys.stderr)
        print(f"Response: {data if 'data' in locals() else 'N/A'}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main entry point for the agent CLI."""
    # Parse command-line arguments
    if len(sys.argv) != 2:
        print("Usage: uv run agent.py \"Your question here\"", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    # Load settings
    settings = load_settings()

    # Call the LLM
    answer = call_llm(question, settings)

    # Format and output the result
    result = {
        "answer": answer,
        "tool_calls": [],
    }

    # Output JSON to stdout (single line)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
