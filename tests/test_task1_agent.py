"""
Regression tests for agent.py (Task 1).

Tests verify that agent.py:
- Runs successfully with a question argument
- Outputs valid JSON to stdout
- Contains required 'answer' and 'tool_calls' fields
"""

import json
import subprocess
import sys
from pathlib import Path


def test_agent_outputs_valid_json():
    """
    Test that agent.py outputs valid JSON with required fields.

    This test:
    1. Runs agent.py as a subprocess with a test question
    2. Parses stdout as JSON
    3. Verifies 'answer' field exists and is a non-empty string
    4. Verifies 'tool_calls' field exists and is an array
    """
    # Path to agent.py (same directory as this test file's parent)
    project_root = Path(__file__).parent.parent
    agent_path = project_root / "agent.py"

    # Test question
    test_question = "What is 2 + 2?"

    # Run agent.py as subprocess
    result = subprocess.run(
        [sys.executable, "-m", "uv", "run", str(agent_path), test_question],
        capture_output=True,
        text=True,
        timeout=120,  # Give extra time for network request
    )

    # Print stderr for debugging (won't affect test result)
    if result.stderr:
        print(f"stderr: {result.stderr}", file=sys.stderr)

    # Check exit code
    assert result.returncode == 0, f"agent.py failed with exit code {result.returncode}"

    # Parse stdout as JSON
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"stdout is not valid JSON: {e}\nstdout: {result.stdout}")

    # Verify 'answer' field exists and is non-empty
    assert "answer" in output, "Missing 'answer' field in output"
    assert isinstance(output["answer"], str), "'answer' must be a string"
    assert len(output["answer"]) > 0, "'answer' must be non-empty"

    # Verify 'tool_calls' field exists and is an array
    assert "tool_calls" in output, "Missing 'tool_calls' field in output"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be an array"

    print(f"✓ Test passed! Answer: {output['answer']}", file=sys.stderr)


if __name__ == "__main__":
    # Allow running this test directly
    test_agent_outputs_valid_json()
    print("All tests passed!")
