"""
Regression tests for agent.py (Task 2).

Tests verify that agent.py:
- Runs successfully with documentation questions
- Outputs valid JSON with answer, source, and tool_calls fields
- Uses tools correctly (read_file, list_files)
- Extracts source references from wiki files
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


def validate_output(output: dict, expected_tool: str = None):
    """
    Validate that output has required fields and correct types.

    Args:
        output: The parsed JSON output
        expected_tool: If specified, check that this tool was used
    """
    # Verify required fields exist
    assert "answer" in output, "Missing 'answer' field in output"
    assert "source" in output, "Missing 'source' field in output"
    assert "tool_calls" in output, "Missing 'tool_calls' field in output"

    # Verify types
    assert isinstance(output["answer"], str), "'answer' must be a string"
    assert isinstance(output["source"], str), "'source' must be a string"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be an array"

    # Verify tool_calls structure
    for call in output["tool_calls"]:
        assert "tool" in call, "Each tool_call must have 'tool' field"
        assert "args" in call, "Each tool_call must have 'args' field"
        assert "result" in call, "Each tool_call must have 'result' field"

    # Check expected tool was used
    if expected_tool:
        tools_used = [call["tool"] for call in output["tool_calls"]]
        assert expected_tool in tools_used, (
            f"Expected tool '{expected_tool}' not found in tool_calls. "
            f"Tools used: {tools_used}"
        )


def test_merge_conflict_question():
    """
    Test: "How do you resolve a merge conflict?"

    Expected behavior:
    - Agent uses read_file to read wiki/git-workflow.md
    - Source field contains wiki/git-workflow.md
    - Answer is non-empty
    """
    question = "How do you resolve a merge conflict?"
    print(f"\n=== Test: Merge Conflict Question ===", file=sys.stderr)
    print(f"Question: {question}", file=sys.stderr)

    output = run_agent(question)
    validate_output(output, expected_tool="read_file")

    # Verify source references git-workflow.md
    assert "git-workflow.md" in output["source"], (
        f"Expected 'git-workflow.md' in source, got: {output['source']}"
    )

    # Verify answer is non-empty
    assert len(output["answer"]) > 0, "Answer must be non-empty"

    print(f"✓ Test passed!", file=sys.stderr)
    print(f"  Answer: {output['answer'][:100]}...", file=sys.stderr)
    print(f"  Source: {output['source']}", file=sys.stderr)
    print(f"  Tool calls: {len(output['tool_calls'])}", file=sys.stderr)


def test_list_files_question():
    """
    Test: "What files are in the wiki?"

    Expected behavior:
    - Agent uses list_files to list wiki directory
    - tool_calls contains list_files entry
    - Answer lists some files
    """
    question = "What files are in the wiki?"
    print(f"\n=== Test: List Files Question ===", file=sys.stderr)
    print(f"Question: {question}", file=sys.stderr)

    output = run_agent(question)
    validate_output(output, expected_tool="list_files")

    # Verify answer is non-empty
    assert len(output["answer"]) > 0, "Answer must be non-empty"

    print(f"✓ Test passed!", file=sys.stderr)
    print(f"  Answer: {output['answer'][:100]}...", file=sys.stderr)
    print(f"  Source: {output['source']}", file=sys.stderr)
    print(f"  Tool calls: {len(output['tool_calls'])}", file=sys.stderr)


if __name__ == "__main__":
    # Allow running tests directly
    print("Running Task 2 regression tests...", file=sys.stderr)

    test_merge_conflict_question()
    test_list_files_question()

    print("\n✓ All Task 2 tests passed!", file=sys.stderr)
