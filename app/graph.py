import sqlite3
from typing import Any, List, Optional, TypedDict

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_openai import ChatOpenAI

from app.tools import (
    run_linter_tool,
    fetch_github_pr_files,
    commit_to_github,
)
from app.config import OPENAI_API_KEY


class ReviewState(TypedDict):
    pr_url: str
    repo_name: str
    pull_number: int
    branch: str
    code_contents: str
    lint_errors: str
    refactored_code: str
    is_approved: bool
    reviewer_feedback: Optional[str]
    history: List[str]
    files: List[dict[str, Any]]
    refactored_files: List[dict[str, str]]


# Configure the AI model.
llm = (
    ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=OPENAI_API_KEY,
    )
    if OPENAI_API_KEY
    else None
)


def fetch_pr_node(state: ReviewState):
    """Fetch all changed Python files from the GitHub pull request."""

    if not state.get("repo_name") or not state.get("pull_number"):
        raise ValueError("Repository name and pull request number are required.")

    files = fetch_github_pr_files(
        state["repo_name"],
        state["pull_number"],
    )

    code_contents = "\n\n".join(
        f"# FILE: {item['filename']}\n{item['content']}"
        for item in files
    )

    history = state.get("history", []) + [
        f"Fetched {len(files)} Python file(s) from GitHub."
    ]

    return {
        "files": files,
        "code_contents": code_contents,
        "history": history,
    }


def lint_code_node(state: ReviewState):
    """Run Flake8 on every fetched Python file."""

    results = []

    for item in state.get("files", []):
        result = run_linter_tool.invoke({
            "code_string": item["content"]
        })

        results.append(
            f"File: {item['filename']}\n{result}"
        )

    lint_errors = "\n\n".join(results)

    return {
        "lint_errors": lint_errors,
        "history": state.get("history", []) + [
            "Executed syntax and Flake8 checks on fetched files."
        ],
    }


def propose_refactor_node(state: ReviewState):
    """Generate improved code using the configured AI model."""

    if llm is None:
        raise RuntimeError(
            "OPENAI_API_KEY is missing. Configure it before running AI refactoring."
        )

    files = state.get("files", [])
    refactored_files = []

    for item in files:
        prompt = f"""
You are an expert Python code reviewer.

Improve the following Python source code.

Requirements:
1. Fix syntax errors and Flake8 issues.
2. Follow Python best practices.
3. Preserve the original program's functionality.
4. Incorporate the reviewer's feedback.
5. Do not invent missing functionality.
6. Return ONLY the complete Python source code.
7. Do not return Markdown code fences or explanations.

Filename:
{item['filename']}

Original code:
{item['content']}

Lint findings:
{state.get('lint_errors', '')}

Reviewer feedback:
{state.get('reviewer_feedback') or 'No additional feedback.'}
"""

        response = llm.invoke(prompt)
        code = response.content.strip()

        if code.startswith("```"):
            code = code.split("\n", 1)[-1]
            code = code.rsplit("```", 1)[0].strip()

        refactored_files.append({
            "filename": item["filename"],
            "content": code,
        })

    combined_code = "\n\n".join(
        f"# FILE: {item['filename']}\n{item['content']}"
        for item in refactored_files
    )

    return {
        "refactored_files": refactored_files,
        "refactored_code": combined_code,
        "history": state.get("history", []) + [
            "Generated AI refactoring proposals."
        ],
    }


def validate_refactor_node(state: ReviewState):
    """Re-run syntax and lint checks on AI-generated code."""

    errors = []

    for item in state.get("refactored_files", []):
        result = run_linter_tool.invoke({
            "code_string": item["content"]
        })

        if result != "No lint errors found.":
            errors.append(
                f"File: {item['filename']}\n{result}"
            )

    if errors:
        raise ValueError(
            "Refactored code did not pass validation:\n"
            + "\n\n".join(errors)
        )

    return {
        "history": state.get("history", []) + [
            "AI-generated code passed syntax and Flake8 validation."
        ]
    }


def apply_changes_node(state: ReviewState):
    """Commit changes only after human approval."""

    if not state.get("is_approved", False):
        return {
            "history": state.get("history", []) + [
                "Changes rejected. Reviewer feedback will be processed."
            ]
        }

    repo = state["repo_name"]
    branch = state["branch"]

    for item in state.get("refactored_files", []):
        success = commit_to_github(
            repo_full_name=repo,
            branch=branch,
            file_path=item["filename"],
            content=item["content"],
            commit_message=(
                f"Autonomous Agent: Refactor {item['filename']}"
            ),
        )

        if not success:
            raise RuntimeError(
                f"GitHub commit failed for {item['filename']}."
            )

    return {
        "history": state.get("history", []) + [
            "Approved changes successfully committed to GitHub."
        ]
    }


def decide_next_step(state: ReviewState):
    """Choose the next step based on human approval."""

    if state.get("is_approved", False):
        return "end"

    return "refactor"


# Persistent SQLite checkpoint storage.
conn = sqlite3.connect(
    "workflow_checkpoint.db",
    check_same_thread=False,
)

memory = SqliteSaver(conn)
memory.setup()


# Construct the LangGraph workflow.
workflow = StateGraph(ReviewState)

workflow.add_node("fetch_pr_node", fetch_pr_node)
workflow.add_node("lint_code_node", lint_code_node)
workflow.add_node("propose_refactor_node", propose_refactor_node)
workflow.add_node("validate_refactor_node", validate_refactor_node)
workflow.add_node("apply_changes_node", apply_changes_node)

workflow.set_entry_point("fetch_pr_node")

workflow.add_edge("fetch_pr_node", "lint_code_node")
workflow.add_edge("lint_code_node", "propose_refactor_node")
workflow.add_edge("propose_refactor_node", "validate_refactor_node")
workflow.add_edge("validate_refactor_node", "apply_changes_node")

workflow.add_conditional_edges(
    "apply_changes_node",
    decide_next_step,
    {
        "refactor": "propose_refactor_node",
        "end": END,
    },
)

app_graph = workflow.compile(
    checkpointer=memory,
    interrupt_before=["apply_changes_node"],
)