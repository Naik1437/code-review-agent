from unittest.mock import patch

import pytest

from app.tools import run_linter_tool
from app.graph import (
    decide_next_step,
    propose_refactor_node,
    validate_refactor_node,
)


# ============================================================
# 1. LINTER TESTS
# ============================================================

def test_linter_detects_syntax_error():
    """Verify that Python syntax errors are detected."""

    bad_code = "def add(a, b)\n    return a + b"

    result = run_linter_tool.invoke({
        "code_string": bad_code
    })

    assert "Syntax error" in result


def test_linter_detects_style_errors():
    """Verify that Flake8 detects formatting problems."""

    bad_code = "def add(a,b):\n    return a+b\n"

    result = run_linter_tool.invoke({
        "code_string": bad_code
    })

    assert "E231" in result or "E225" in result


def test_linter_accepts_clean_code():
    """Verify that valid, clean Python code passes."""

    good_code = "def add(a, b):\n    return a + b\n"

    result = run_linter_tool.invoke({
        "code_string": good_code
    })

    assert result == "No lint errors found."


# ============================================================
# 2. WORKFLOW ROUTING TESTS
# ============================================================

def test_rejection_routes_back_to_refactor():
    """Rejected code should return to the refactoring node."""

    state = {
        "is_approved": False,
        "reviewer_feedback": "Please improve the code"
    }

    assert decide_next_step(state) == "refactor"


def test_approval_ends_workflow():
    """Approved code should end the workflow."""

    state = {
        "is_approved": True,
        "reviewer_feedback": None
    }

    assert decide_next_step(state) == "end"


# ============================================================
# 3. AI REFACTORING TESTS
# ============================================================

def test_refactor_adds_final_newline():
    """AI-generated code should end with a newline."""

    mock_response = type(
        "MockResponse",
        (),
        {"content": "def add(a, b):\n    return a + b"}
    )()

    state = {
        "files": [
            {
                "filename": "sample.py",
                "content": "def add(a,b):\n    return a+b"
            }
        ],
        "lint_errors": "E231,E225",
        "reviewer_feedback": None,
        "history": []
    }

    with patch("app.graph.llm") as mock_llm:
        mock_llm.invoke.return_value = mock_response

        result = propose_refactor_node(state)

    generated_code = result["refactored_files"][0]["content"]

    assert generated_code.endswith("\n")
    assert generated_code.startswith("def add")


def test_refactor_rejects_empty_ai_response():
    """Empty AI responses should not be accepted."""

    mock_response = type(
        "MockResponse",
        (),
        {"content": " "}
    )()

    state = {
        "files": [
            {
                "filename": "sample.py",
                "content": "def add(a, b):\n    return a + b\n"
            }
        ],
        "lint_errors": "",
        "reviewer_feedback": None,
        "history": []
    }

    with patch("app.graph.llm") as mock_llm:
        mock_llm.invoke.return_value = mock_response

        with pytest.raises(ValueError, match="AI returned empty code"):
            propose_refactor_node(state)


# ============================================================
# 4. REFACTORED CODE VALIDATION TESTS
# ============================================================

def test_validate_refactored_code_success():
    """Clean refactored code should pass validation."""

    state = {
        "refactored_files": [
            {
                "filename": "sample.py",
                "content": "def add(a, b):\n    return a + b\n"
            }
        ],
        "history": []
    }

    result = validate_refactor_node(state)

    assert "AI-generated code passed" in result["history"][-1]


def test_validate_refactored_code_failure():
    """Invalid refactored code should fail validation."""

    state = {
        "refactored_files": [
            {
                "filename": "sample.py",
                "content": "def add(a, b)\n    return a + b"
            }
        ],
        "history": []
    }

    with pytest.raises(ValueError, match="failed validation"):
        validate_refactor_node(state)






# ============================================================
# 5. BLACK AND PYLINT INTEGRATION TESTS
# ============================================================

def test_black_detects_formatting_errors():
    """Black should detect incorrectly formatted Python code."""

    bad_code = "x=  10\nprint(x)\n"

    result = run_linter_tool.invoke({
        "code_string": bad_code
    })

    assert "Black findings" in result


def test_pylint_detects_code_quality_issues():
    """Pylint should detect code-quality problems."""

    bad_code = "x= 10\nprint(x)\n"

    result = run_linter_tool.invoke({
        "code_string": bad_code
    })

    assert "Pylint findings" in result


def test_all_linters_accept_clean_code():
    """All three tools should accept clean Python code."""

    good_code = (
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n"
    )

    result = run_linter_tool.invoke({
        "code_string": good_code
    })

    assert result == "No lint errors found."


def test_temporary_file_is_cleaned_up():
    """Temporary Python files should be deleted after linting."""

    from unittest.mock import patch

    with patch("app.tools.os.remove") as mock_remove:
        run_linter_tool.invoke({
            "code_string": "def add(a, b):\n    return a + b\n"
        })

        mock_remove.assert_called_once()