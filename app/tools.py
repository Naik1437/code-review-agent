import os
import subprocess
import tempfile
from langchain_core.tools import tool
import requests
from app.config import GITHUB_TOKEN

@tool
def run_linter_tool(code_string: str) -> str:
    """Writes python code to a temporary file and runs flake8 analysis."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as temp:
        temp.write(code_string)
        temp_path = temp.name

    try:
        result = subprocess.run(
            ["flake8", temp_path],
            capture_output=True,
            text=True,
            timeout=5
        )
        output = result.stdout + result.stderr
        return output if output.strip() else "No lint errors found."
    except Exception as e:
        return f"Lint execution error: {str(e)}"
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

def fetch_github_pr(repo_full_name: str, pull_number: int) -> str:
    """Fetches file contents from a GitHub Pull Request."""
    if not GITHUB_TOKEN:
        return "def add(a, b):\n    return a + b\n"
    url = f"https://api.github.com/repos/{repo_full_name}/pulls/{pull_number}/files"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "vnd.github+json"}
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        files = response.json()
        return files[0].get("patch", "# No patch content found")
    return "print('Error fetching GitHub PR')"

def commit_to_github(repo_full_name: str, branch: str, file_path: str, content: str, commit_message: str):
    """Commits approved refactored code back to GitHub branch."""
    if not GITHUB_TOKEN:
        return True
    url = f"https://api.github.com/repos/{repo_full_name}/contents/{file_path}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "vnd.github+json"}
    get_res = requests.get(url, headers=headers, params={"ref": branch})
    sha = get_res.json().get("sha") if get_res.status_code == 200 else None

    import base64
    encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")
    payload = {"message": commit_message, "content": encoded_content, "branch": branch}
    if sha:
        payload["sha"] = sha
    put_res = requests.put(url, headers=headers, json=payload)
    return put_res.status_code in [200, 201]