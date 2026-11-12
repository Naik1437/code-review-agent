from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
from app.graph import app_graph

app = FastAPI(
    title="Autonomous Code Review & Refactoring Agent",
    version="1.0"
)


class WebhookPayload(BaseModel):
    repo_name: Optional[str] = None
    pull_number: Optional[int] = None
    branch: Optional[str] = None
    pr_url: Optional[str] = None
    repository: Optional[dict[str, Any]] = None
    pull_request: Optional[dict[str, Any]] = None


class ReviewPayload(BaseModel):
    approved: bool
    feedback: Optional[str] = None


@app.post("/api/webhooks/github")
async def github_webhook(payload: WebhookPayload):

    repo = payload.repo_name
    pr_num = payload.pull_number
    branch = payload.branch
    pr_url = payload.pr_url

    if payload.repository:
        repo = payload.repository.get("full_name", repo)

    if payload.pull_request:
        pr_num = payload.pull_request.get("number", pr_num)
        pr_url = payload.pull_request.get("html_url", pr_url)
        branch = payload.pull_request.get("head", {}).get("ref", branch)

    if not repo or not pr_num:
        raise HTTPException(400, "Repository and PR number required")

    branch = branch or "main"
    pr_url = pr_url or f"https://github.com/{repo}/pull/{pr_num}"

    thread_id = f"pr-{repo.replace('/', '-')}-{pr_num}"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "pr_url": pr_url,
        "repo_name": repo,
        "pull_number": pr_num,
        "branch": branch,
        "code_contents": "",
        "lint_errors": "",
        "refactored_code": "",
        "is_approved": False,
        "reviewer_feedback": None,
        "history": [],
        "files": [],
        "refactored_files": []
    }

    try:
        app_graph.invoke(initial_state, config=config)
        state = app_graph.get_state(config)

        if not state.next:
            raise RuntimeError("Workflow did not pause for approval")

        return {
            "status": "paused_at_approval_gate",
            "thread_id": thread_id,
            "pr_url": pr_url,
            "history": state.values.get("history", [])
        }

    except Exception as e:
        raise HTTPException(500, str(e))


@app.post("/api/reviews/{thread_id}/approve")
async def review_action(thread_id: str, payload: ReviewPayload):

    config = {"configurable": {"thread_id": thread_id}}

    current_state = app_graph.get_state(config)

    if not current_state.values:
        raise HTTPException(404, "Review thread not found")

    if not current_state.next:
        raise HTTPException(409, "Workflow is not waiting for approval")

    if not payload.approved and not payload.feedback:
        raise HTTPException(400, "Feedback is required when rejecting")

    try:
        app_graph.update_state(
            config,
            {
                "is_approved": payload.approved,
                "reviewer_feedback": payload.feedback
            }
        )

        result = app_graph.invoke(None, config=config)

        new_state = app_graph.get_state(config)

        return {
            "status": (
                "paused_for_reapproval"
                if new_state.next
                else "completed"
            ),
            "thread_id": thread_id,
            "approved": payload.approved,
            "history": (
                new_state.values.get("history", [])
                if new_state.values
                else []
            )
        }

    except Exception as e:
        raise HTTPException(500, str(e))