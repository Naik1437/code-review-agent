import ast
import base64
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Any

import requests
from langchain_core.tools import tool

from app.config import GITHUB_TOKEN


GITHUB_API = "https://api.github.com"

HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28"
}

if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"


def _check_github_response(response: requests.Response) -> None:
    """Raise a useful error when GitHub returns an unsuccessful response."""
    if not response.ok:
        raise RuntimeError(
            f"GitHub API error {response.status_code}: {response.text[:500]}"
        )


def fetch_github_pr_files(
    repo_full_name: str,
    pull_number: int
) -> list[dict[str, Any]]:
    """Fetch complete contents of Python files changed in a pull request."""

    if not GITHUB_TOKEN:
        raise RuntimeError("GITHUB_TOKEN is missing from .env.")

    # Get Pull Request details to obtain the correct head commit SHA.
    pr_url = f"{GITHUB_API}/repos/{repo_full_name}/pulls/{pull_number}"

    pr_response = requests.get(
        pr_url,
        headers=HEADERS,
        timeout=20
    )
    _check_github_response(pr_response)

    head_sha = pr_response.json()["head"]["sha"]

    # Get changed files.
    files_url = f"{GITHUB_API}/repos/{repo_full_name}/pulls/{pull_number}/files"

    files_response = requests.get(
        files_url,
        headers=HEADERS,
        timeout=20
    )
    _check_github_response(files_response)

    python_files = []

    for file_info in files_response.json():
        filename = file_info.get("filename", "")

        if not filename.endswith(".py"):
            continue

        if file_info.get("status") == "removed":
            continue

        content_url = (
            f"{GITHUB_API}/repos/{repo_full_name}/contents/{filename}"
        )

        content_response = requests.get(
            content_url,
            headers=HEADERS,
            params={"ref": head_sha},
            timeout=20
        )
        _check_github_response(content_response)

        data = content_response.json()

        if data.get("encoding") != "base64":
            raise RuntimeError(
                f"Unexpected encoding for {filename}"
            )

        source = base64.b64decode(
            data["content"]
        ).decode("utf-8")

        python_files.append({
            "filename": filename,
            "content": source,
            "status": file_info.get("status")
        })

    if not python_files:
        raise RuntimeError(
            "No Python source files were found in this pull request."
        )

    return python_files

def fetch_github_pr(
    repo_full_name: str,
    pull_number: int
) -> str:
    """Fetch the first changed Python file for graph compatibility."""

    files = fetch_github_pr_files(repo_full_name, pull_number)

    return files[0]["content"]


@tool
def run_linter_tool(code_string: str) -> str:
    """Validate Python syntax and run Flake8, Black and Pylint."""

    if not code_string.strip():
        return "Lint error: Empty Python source code."

    try:
        ast.parse(code_string)
    except SyntaxError as error:
        return (
            f"Syntax error at line {error.lineno}: "
            f"{error.msg}"
        )

    temp_path = None

    try:
        # Create a temporary Python file.
        with tempfile.NamedTemporaryFile(
            mode="w",
            suffix=".py",
            encoding="utf-8",
            delete=False
        ) as temp:
            temp.write(code_string)
            temp_path = temp.name

        # Run all three validation tools.
        commands = {
            "Flake8": [
                sys.executable, "-m", "flake8", temp_path
            ],
            "Black": [
                sys.executable, "-m", "black",
                "--check", "--diff", temp_path
            ],
            "Pylint": [
                sys.executable, "-m", "pylint",
                "--score=n",
                "--reports=n",
                "--disable=C0114,C0116",
                temp_path
            ]
        }

        results = []

        for tool_name, command in commands.items():

            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=20,
                check=False
            )

            output = (
                result.stdout + result.stderr
            ).strip()

            if result.returncode != 0:
                results.append(
                    f"{tool_name} findings:\n"
                    f"{output or 'Validation failed.'}"
                )

        if results:
            return "\n\n".join(results)

        return "No lint errors found."

    except subprocess.TimeoutExpired:
        return "Lint execution error: Validation timed out."

    except OSError as error:
        return f"Lint execution error: {error}"

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
def commit_to_github(
    repo_full_name: str,
    branch: str,
    file_path: str,
    content: str,
    commit_message: str
) -> bool:
    """Commit approved Python code to the specified GitHub branch."""

    if not GITHUB_TOKEN:
        raise RuntimeError("GITHUB_TOKEN is missing. Cannot commit changes.")

    if not file_path or file_path.startswith("/"):
        raise ValueError("Invalid GitHub file path.")

    if ".." in file_path.split("/"):
        raise ValueError("Invalid GitHub file path.")

    url = (
        f"{GITHUB_API}/repos/{repo_full_name}"
        f"/contents/{file_path}"
    )

    get_response = requests.get(
        url,
        headers=HEADERS,
        params={"ref": branch},
        timeout=20
    )

    if get_response.status_code == 200:
        sha = get_response.json()["sha"]
    elif get_response.status_code == 404:
        sha = None
    else:
        _check_github_response(get_response)
        sha = None

    encoded_content = base64.b64encode(
        content.encode("utf-8")
    ).decode("utf-8")

    payload = {
        "message": commit_message,
        "content": encoded_content,
        "branch": branch
    }

    if sha:
        payload["sha"] = sha

    put_response = requests.put(
        url,
        headers=HEADERS,
        json=payload,
        timeout=30
    )

    _check_github_response(put_response)

    return put_response.status_code in (200, 201)