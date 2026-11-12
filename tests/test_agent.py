from app.tools import run_linter_tool

def test_linter_isolation():
    # Test with invalid python syntax/lint error
    bad_code = "print('hello'   # syntax error / missing paren"
    result = run_linter_tool.invoke({"code_string": bad_code})
    assert isinstance(result, str)
    assert len(result) > 0