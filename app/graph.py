import sqlite3
from typing import List, TypedDict, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langchain_openai import ChatOpenAI
from app.tools import run_linter_tool, fetch_github_pr, commit_to_github
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

try:
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0, openai_api_key=OPENAI_API_KEY)
except Exception:
    llm = None

def fetch_pr_node(state: ReviewState):
    repo = state.get("repo_name", "test/repo")
    pr_num = state.get("pull_number", 1)
    code = fetch_github_pr(repo, pr_num)
    history = state.get("history", []) + ["Fetched PR code from GitHub."]
    return {"code_contents": code, "history": history}

def lint_code_node(state: ReviewState):
    code = state.get("code_contents", "")
    lint_result = run_linter_tool.invoke({"code_string": code})
    history = state.get("history", []) + ["Executed sandbox linter check."]
    return {"lint_errors": lint_result, "history": history}

def propose_refactor_node(state: ReviewState):
    code = state.get("code_contents", "")
    errors = state.get("lint_errors", "")
    feedback = state.get("reviewer_feedback", "")
    
    if llm is None:
        refactored = code + f"\n# Feedback applied: {feedback}" if feedback else code
    else:
        prompt = f"Fix all lint errors and incorporate feedback while keeping original logic. Original Code:\n{code}\nErrors:\n{errors}\nFeedback:\n{feedback}\nReturn ONLY valid Python code."
        response = llm.invoke(prompt)
        refactored = response.content.replace("```python", "").replace("```", "").strip()
        
    history = state.get("history", []) + ["Generated refactored code proposal."]
    return {"refactored_code": refactored, "history": history}

def apply_changes_node(state: ReviewState):
    if state.get("is_approved", False):
        repo = state.get("repo_name", "test/repo")
        branch = state.get("branch", "main")
        code = state.get("refactored_code", "")
        commit_to_github(repo, branch, "main.py", code, "Autonomous Agent: Apply refactored code fixes")
        history = state.get("history", []) + ["Approved! Changes committed back to GitHub."]
        return {"history": history}
    history = state.get("history", []) + ["Changes rejected with feedback. Re-routing to refactor."]
    return {"history": history}

def decide_next_step(state: ReviewState):
    if state.get("is_approved", False):
        return "end"
    return "refactor"

conn = sqlite3.connect("workflow_checkpoint.db", check_same_thread=False)
memory = SqliteSaver(conn)

workflow = StateGraph(ReviewState)
workflow.add_node("fetch_pr_node", fetch_pr_node)
workflow.add_node("lint_code_node", lint_code_node)
workflow.add_node("propose_refactor_node", propose_refactor_node)
workflow.add_node("apply_changes_node", apply_changes_node)

workflow.set_entry_point("fetch_pr_node")
workflow.add_edge("fetch_pr_node", "lint_code_node")
workflow.add_edge("lint_code_node", "propose_refactor_node")
workflow.add_edge("propose_refactor_node", "apply_changes_node")

# Conditional edge for feedback loop: if rejected, go back to propose_refactor_node; if approved, go to END
workflow.add_conditional_edges(
    "apply_changes_node",
    decide_next_step,
    {
        "refactor": "propose_refactor_node",
        "end": END
    }
)

app_graph = workflow.compile(
    checkpointer=memory,
    interrupt_before=["apply_changes_node"]
)