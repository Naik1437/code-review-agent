from app.tools import run_linter_tool
from app.graph import decide_next_step


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

  

def test_rejection_routes_back_to_refactor():
    state = {
        "is_approved": False,
        "reviewer_feedback": "Please improve the code"
    }

    assert decide_next_step(state) == "refactor"


def test_approval_ends_workflow():
    state = {
        "is_approved": True,
        "reviewer_feedback": None
    }

    assert decide_next_step(state) == "end"