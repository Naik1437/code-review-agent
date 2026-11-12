import sqlite3
from pathlib import Path
from typing import Any, List, Optional, TypedDict

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_openai import ChatOpenAI

from app.config import GROQ_API_KEY
from app.tools import (
    run_linter_tool,
    fetch_github_pr_files,
    commit_to_github,
)


# ============================================================
# 1. REVIEW STATE
# ============================================================

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


# ============================================================
# 2. GROQ LLM CONFIGURATION
# ============================================================

llm = (
    ChatOpenAI(
        model="openai/gpt-oss-20b",
        temperature=0,
        api_key=GROQ_API_KEY,
        base_url="https://api.groq.com/openai/v1",
    )
    if GROQ_API_KEY
    else None
)


# ============================================================
# 3. FETCH PULL REQUEST NODE
# ============================================================

def fetch_pr_node(state: ReviewState):
    """Fetch modified Python files from GitHub."""

    repo_name = state.get("repo_name")
    pull_number = state.get("pull_number")

    if not repo_name or not pull_number:
        raise ValueError(
            "Repository name and pull request number are required."
        )

    files = fetch_github_pr_files(
        repo_name,
        pull_number,
    )

    if not files:
        raise ValueError("No Python files found in the pull request.")

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


# ============================================================
# 4. LINT CODE NODE
# ============================================================

def lint_code_node(state: ReviewState):
    """Execute Flake8 checks on fetched Python files."""

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
            "Executed syntax and Flake8 checks."
        ],
    }


# ============================================================
# 5. PROPOSE REFACTOR NODE
# ============================================================

def propose_refactor_node(state: ReviewState):
    """Generate improved Python code using Groq."""

    if llm is None:
        raise RuntimeError(
            "GROQ_API_KEY is missing. "
            "Configure it before running AI refactoring."
        )

    files = state.get("files", [])

    if not files:
        raise ValueError("No Python files available for refactoring.")

    refactored_files = []

    for item in files:

        prompt = f"""
You are an expert Python software engineer.

Review and refactor the following Python source code.

Requirements:

1. Fix all syntax errors.
2. Fix Flake8 style errors.
3. Follow Python best practices.
4. Preserve the original program's functionality.
5. Incorporate the reviewer's feedback.
6. Do not invent missing functionality.
7. Return ONLY the complete Python source code.
8. Do not include Markdown code fences.
9. Do not include explanations.
10. Ensure the file ends with a newline character.

Filename:
{item['filename']}

Original source code:
{item['content']}

Lint findings:
{state.get('lint_errors', '')}

Reviewer feedback:
{state.get('reviewer_feedback') or 'No additional feedback.'}
"""

        response = llm.invoke(prompt)

        if not isinstance(response.content, str):
            raise ValueError(
                "The AI model returned an unexpected response format."
            )

        code = response.content.strip()

        # Remove Markdown code fences if the model returns them.
        if code.startswith("```"):

            lines = code.split("\n", 1)

            if len(lines) > 1:
                code = lines[1]

            code = code.rsplit("```", 1)[0].strip()

        # Check for empty response before adding newline.
        if not code.strip():
            raise ValueError(
                f"AI returned empty code for {item['filename']}."
            )

        # FIX: Ensure the generated Python file ends with a newline.
        code = code.rstrip() + "\n"

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
            "Generated AI refactoring proposals using Groq."
        ],
    }


# ============================================================
# 6. VALIDATE REFACTORED CODE NODE
# ============================================================

def validate_refactor_node(state: ReviewState):
    """Validate AI-generated code using the linter."""

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
            "Refactored code failed validation:\n"
            + "\n\n".join(errors)
        )

    return {
        "history": state.get("history", []) + [
            "AI-generated code passed syntax and Flake8 validation."
        ]
    }


# ============================================================
# 7. APPLY CHANGES NODE
# ============================================================

def apply_changes_node(state: ReviewState):
    """Commit changes to GitHub only after human approval."""

    if not state.get("is_approved", False):

        return {
            "history": state.get("history", []) + [
                "Changes rejected. Reviewer feedback will be processed."
            ]
        }

    repo = state["repo_name"]
    branch = state["branch"]

    refactored_files = state.get("refactored_files", [])

    if not refactored_files:
        raise ValueError("No refactored files available to commit.")

    for item in refactored_files:

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


# ============================================================
# 8. CONDITIONAL ROUTING
# ============================================================

def decide_next_step(state: ReviewState):
    """Route rejected changes back to refactoring."""

    if state.get("is_approved", False):
        return "end"

    return "refactor"


# ============================================================
# 9. SQLITE PERSISTENT CHECKPOINTING
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_DIR = BASE_DIR / "data"
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_PATH = DATABASE_DIR / "workflow_checkpoint.db"
conn = sqlite3.connect(
    str(DATABASE_PATH),
    check_same_thread=False,
)

memory = SqliteSaver(conn)

memory.setup()


# ============================================================
# 10. BUILD LANGGRAPH WORKFLOW
# ============================================================

workflow = StateGraph(ReviewState)

# Register nodes.
workflow.add_node("fetch_pr_node", fetch_pr_node)
workflow.add_node("lint_code_node", lint_code_node)
workflow.add_node("propose_refactor_node", propose_refactor_node)
workflow.add_node("validate_refactor_node", validate_refactor_node)
workflow.add_node("apply_changes_node", apply_changes_node)

# Define entry point.
workflow.set_entry_point("fetch_pr_node")

# Define normal workflow transitions.
workflow.add_edge("fetch_pr_node", "lint_code_node")

workflow.add_edge("lint_code_node", "propose_refactor_node")

workflow.add_edge("propose_refactor_node", "validate_refactor_node")

workflow.add_edge("validate_refactor_node", "apply_changes_node")

# Define approval/rejection routing.
workflow.add_conditional_edges(
    "apply_changes_node",
    decide_next_step,
    {
        "refactor": "propose_refactor_node",
        "end": END,
    },
)

# Compile graph with persistent memory and human approval gate.
app_graph = workflow.compile(
    checkpointer=memory,
    interrupt_before=["apply_changes_node"],
)