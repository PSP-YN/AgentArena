import pytest

from app.agents.bifrost_tool_agent import CalculatorError, execute_tool, safe_calculate


def test_safe_calculator_basic_math():
    assert safe_calculate("19 * 23") == 437
    assert safe_calculate("2 ** 3 + 1") == 9


def test_safe_calculator_rejects_python_calls():
    with pytest.raises(CalculatorError):
        safe_calculate("__import__('os').system('echo unsafe')")


def test_tool_failure_injected_once_then_tool_recovers():
    first, used = execute_tool("calculator", {"expression": "4 + 5"}, "tool_error_once", False)
    second, used_again = execute_tool("calculator", {"expression": "4 + 5"}, "tool_error_once", used)
    assert first.startswith("ToolError:")
    assert used is True
    assert second == "9"
    assert used_again is True


def test_prompt_injection_fixture_is_explicitly_untrusted():
    content, _ = execute_tool("lookup_document", {"doc_id": "demo-policy"}, "misleading_tool_output", False)
    assert "SAFE" in content
    assert "HACKED" in content
    assert "untrusted" in content.casefold()
