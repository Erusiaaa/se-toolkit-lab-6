"""
Regression tests for agent.py (Task 3) - System Agent.

Tests verify that agent.py:
- Runs successfully with system questions
- Outputs valid JSON with answer and tool_calls fields
- Uses query_api tool for data-dependent questions
- Uses read_file for source code analysis questions
"""

import json
import subprocess
import sys
from pathlib import Path


def run_agent(question: str) -> dict:
    """
    Run agent.py with a question and return the parsed JSON output.

    Args:
        question: The question to ask the agent

    Returns:
        Parsed JSON output as dict

    Raises:
        AssertionError: If agent fails or output is invalid
    """
    project_root = Path(__file__).parent.parent
    agent_path = project_root / "agent.py"

    result = subprocess.run(
        [sys.executable, "-m", "uv", "run", str(agent_path), question],
        capture_output=True,
        text=True,
        timeout=300,  # Give extra time for multiple LLM calls
    )

    # Print stderr for debugging
    if result.stderr:
        print(f"stderr: {result.stderr}", file=sys.stderr)

    # Check exit code
    assert result.returncode == 0, f"agent.py failed with exit code {result.returncode}"

    # Parse stdout as JSON
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"stdout is not valid JSON: {e}\nstdout: {result.stdout}")

    return output


def validate_output(output: dict, expected_tools: list[str] | None = None):
    """
    Validate that output has required fields and correct types.

    Args:
        output: The parsed JSON output
        expected_tools: If specified, check that these tools were used
    """
    # Verify required fields exist
    assert "answer" in output, "Missing 'answer' field in output"
    assert "tool_calls" in output, "Missing 'tool_calls' field in output"

    # Verify types
    assert isinstance(output["answer"], str), "'answer' must be a string"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be an array"

    # Verify tool_calls structure
    for call in output["tool_calls"]:
        assert "tool" in call, "Each tool_call must have 'tool' field"
        assert "args" in call, "Each tool_call must have 'args' field"
        assert "result" in call, "Each tool_call must have 'result' field"

    # Check expected tools were used
    if expected_tools:
        tools_used = [call["tool"] for call in output["tool_calls"]]
        for expected_tool in expected_tools:
            assert expected_tool in tools_used, (
                f"Expected tool '{expected_tool}' not found in tool_calls. "
                f"Tools used: {tools_used}"
            )


def test_item_count_question():
    """
    Test: "How many items are in the database?"

    Expected behavior:
    - Agent uses query_api to GET /items/
    - Answer contains a number (could be 0 or more)
    - tool_calls contains query_api entry
    """
    question = "How many items are in the database?"
    print(f"\n=== Test: Item Count Question ===", file=sys.stderr)
    print(f"Question: {question}", file=sys.stderr)

    output = run_agent(question)
    validate_output(output, expected_tools=["query_api"])

    # Verify answer is non-empty and contains some indication of quantity
    assert len(output["answer"]) > 0, "Answer must be non-empty"
    
    # Check that answer mentions items or count
    answer_lower = output["answer"].lower()
    assert "item" in answer_lower or "0" in answer_lower or "empty" in answer_lower, (
        f"Answer should mention items or count: {output['answer']}"
    )

    print(f"✓ Test passed!", file=sys.stderr)
    print(f"  Answer: {output['answer'][:150]}...", file=sys.stderr)
    print(f"  Tool calls: {len(output['tool_calls'])}", file=sys.stderr)


def test_framework_question():
    """
    Test: "What Python web framework does the backend use?"

    Expected behavior:
    - Agent uses read_file to read source code (e.g., backend/app/main.py)
    - Answer mentions FastAPI
    - tool_calls contains read_file entry
    """
    question = "What Python web framework does the backend use? Read the source code to find out."
    print(f"\n=== Test: Framework Question ===", file=sys.stderr)
    print(f"Question: {question}", file=sys.stderr)

    output = run_agent(question)
    validate_output(output, expected_tools=["read_file"])

    # Verify answer mentions FastAPI
    answer_lower = output["answer"].lower()
    assert "fastapi" in answer_lower, (
        f"Answer should mention FastAPI: {output['answer']}"
    )

    print(f"✓ Test passed!", file=sys.stderr)
    print(f"  Answer: {output['answer'][:150]}...", file=sys.stderr)
    print(f"  Source: {output.get('source', 'N/A')}", file=sys.stderr)
    print(f"  Tool calls: {len(output['tool_calls'])}", file=sys.stderr)


if __name__ == "__main__":
    # Allow running tests directly
    print("Running Task 3 regression tests...", file=sys.stderr)

    test_item_count_question()
    test_framework_question()

    print("\n✓ All Task 3 tests passed!", file=sys.stderr)
