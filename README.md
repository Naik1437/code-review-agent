# Autonomous Code Review & Refactoring Agent with LangGraph

An autonomous AI agent built using Python, FastAPI, LangGraph, and GitHub API integrations to review incoming Pull Requests, execute sandboxed linter analysis, generate AI refactoring proposals, and enforce Human-in-the-Loop (HITL) approval gates before committing changes.

## Features
- **LangGraph Stateful Pipeline**: Manages the complete PR review lifecycle across fetch, lint, refactor, and commit nodes.
- **Persistent Checkpoints**: Utilizes SQLite (`workflow_checkpoint.db`) to checkpoint threads and support state rollbacks and human feedback loops.
- **Custom Sandbox Linter Tool**: Automatically runs `flake8` analysis on code strings inside temporary secure files.
- **FastAPI Webhooks & Approvals**: Exposes webhook endpoints for PR ingestion and approval/feedback REST routes.

## Installation & Local Setup

1. **Clone the repository and set up a virtual environment:**
   ```bash
   python -m venv venv
   # On Windows:
   venv\Scripts\activate
Testing autonomous code review agent.
