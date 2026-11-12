# Autonomous Code Review & Refactoring Agent with LangGraph

An AI-powered autonomous code review and refactoring system built using Python, LangGraph, FastAPI, Groq LLM and GitHub REST API integration.

The application automatically fetches Python files from GitHub Pull Requests, performs syntax and lint analysis, generates AI-powered refactoring suggestions, validates the proposed changes, and pauses for Human-in-the-Loop (HITL) approval before committing approved changes to GitHub.

## Key Features

- **Autonomous Agent Workflow:** Uses LangGraph to coordinate multiple code review and refactoring stages.
- **GitHub Integration:** Fetches Pull Request details and modified Python files using GitHub REST APIs.
- **Automated Code Analysis:** Uses AST parsing and Flake8 to identify syntax and style issues.
- **AI-Powered Refactoring:** Uses Groq LLM to generate improved Python code while preserving original functionality.
- **Human-in-the-Loop Approval:** Pauses execution before committing changes.
- **Reviewer Feedback Loop:** Rejected proposals are sent back to the AI refactoring stage with reviewer feedback.
- **Persistent State Management:** Uses SQLite checkpointing to preserve workflow state.
- **Automated Validation:** Rechecks AI-generated code before presenting it for approval.
- **FastAPI REST API:** Provides webhook and approval endpoints.
- **Docker Deployment:** Supports containerized execution using Docker Compose.
- **Automated Testing:** Includes pytest tests for linting, refactoring and workflow routing.

## Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python 3.11 |
| Agent Framework | LangGraph |
| LLM Integration | Groq API |
| LLM Client | LangChain OpenAI-compatible client |
| Backend Framework | FastAPI |
| GitHub Integration | GitHub REST API |
| Syntax Validation | Python AST |
| Code Linting | Flake8 |
| State Persistence | SQLite |
| Testing Framework | Pytest |
| Containerization | Docker |
| API Documentation | OpenAPI / Swagger UI |

## Project Architecture

```text
code-review-agent/
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── graph.py
│   ├── main.py
│   └── tools.py
│
├── tests/
│   └── test_agent.py
│
├── data/
│   └── workflow_checkpoint.db
│
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── openapi.json
├── requirements.txt
├── README.md
└── conftest.py
```

The SQLite database is generated automatically when the application starts.

## System Workflow

The application follows a stateful agent workflow implemented using LangGraph.

1. **Fetch Pull Request:** Retrieves Pull Request details and modified Python files from GitHub.
2. **Lint Analysis:** Executes Python syntax checks and Flake8 analysis.
3. **AI Refactoring:** Sends the original code and lint findings to the Groq LLM.
4. **Refactor Validation:** Validates the generated code using the linter.
5. **Human Approval:** Interrupts execution before applying changes.
6. **Feedback Processing:** If rejected, reviewer feedback is passed back to the refactoring node.
7. **Reapproval:** Generates and validates another proposal before pausing again.
8. **Apply Changes:** If approved, commits the refactored files to the GitHub source branch.

### Workflow Architecture

```text
       GitHub Pull Request
                |
                v
         Fetch PR Node
                |
                v
          Lint Code Node
                |
                v
       AI Refactoring Node
                |
                v
       Validate Code Node
                |
                v
       Human Approval Gate
                |
          +-----+-----+
          |           |
       Reject       Approve
          |           |
          v           v
      Feedback     Apply Changes
          |           |
          v           v
      Refactor     GitHub Commit
          |
          v
      Validate
          |
          v
   Approval Gate
```

## Installation and Local Setup

### 1. Clone the Repository

```bash
git clone https://github.com/Naik1437/code-review-agent.git
cd code-review-agent
```

### 2. Create a Virtual Environment

Windows PowerShell:

```powershell
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root using `.env.example` as a reference.

```env
GITHUB_TOKEN=your_github_token
GROQ_API_KEY=your_groq_api_key
OPENAI_API_KEY=
```

**GitHub Token:** Configure repository permissions for reading Pull Requests and reading/writing repository contents.

**Groq API Key:** Configure a valid Groq API key for AI-powered refactoring.

The project uses Groq's OpenAI-compatible API endpoint through the LangChain client.

Never commit `.env` or expose API keys publicly.

### 5. Start the Application

```powershell
uvicorn app.main:app --reload
```

The application runs at:

```text
http://localhost:8000
```

## API Endpoints

### 1. GitHub Webhook

**POST** `/api/webhooks/github`

Receives GitHub Pull Request information and starts the autonomous review workflow.

Example request:

```json
{
  "repo_name": "Naik1437/code-review-agent",
  "pull_number": 1,
  "branch": "test-review"
}
```

### 2. Human Approval / Rejection

**POST** `/api/reviews/{thread_id}/approve`

Accepts human approval or rejection and optional reviewer feedback.

Example rejection request:

```json
{
  "approved": false,
  "feedback": "Please improve code readability and add proper type hints."
}
```

Example approval request:

```json
{
  "approved": true,
  "feedback": "Approved. The refactored code meets the requirements."
}
```

## API Documentation

FastAPI automatically generates interactive API documentation.

**Swagger UI:**

```text
http://localhost:8000/docs
```

**OpenAPI JSON:**

```text
http://localhost:8000/openapi.json
```

The exported API specification is available in `openapi.json`.

## Docker Deployment

Make sure Docker Desktop is installed and running.

### Build and Start

```powershell
docker compose up -d --build
```

### Check Container Status

```powershell
docker compose ps
```

### View Application Logs

```powershell
docker compose logs -f
```

### Stop the Application

```powershell
docker compose down
```

The application is accessible at:

```text
http://localhost:8000/docs
```

The Docker Compose configuration mounts the local `data` directory for persistent SQLite checkpoint storage.

## Automated Testing

Run the test suite:

```powershell
pytest -v
```

The current test suite contains 9 tests covering:

| Test Category | Description |
|---|---|
| Syntax Detection | Detects invalid Python syntax |
| Style Validation | Identifies Flake8 formatting issues |
| Clean Code Validation | Accepts properly formatted Python code |
| Rejection Routing | Verifies rejection routing decisions |
| Approval Routing | Verifies approval routing decisions |
| AI Refactoring | Checks generated code formatting |
| Empty Response Handling | Rejects empty AI responses |
| Successful Validation | Accepts valid refactored code |
| Failed Validation | Rejects invalid refactored code |

**Latest test result: 9 passed.**

## Demonstrated Workflow Scenarios

The following scenarios were successfully executed during project testing:

**Scenario 1: Pull Request Review**
- Submitted a GitHub PR review request.
- Retrieved modified Python files.
- Executed lint analysis.
- Generated AI refactoring.
- Paused at the human approval gate.

**Scenario 2: Human Rejection**
- Rejected the initial proposal.
- Submitted reviewer feedback.
- Regenerated the refactored code.
- Paused for reapproval.

**Scenario 3: Human Approval**
- Approved the generated proposal.
- Applied the changes.
- Successfully committed the updated Python file to the GitHub source branch.

## Future Enhancements

- GitHub webhook signature verification.
- Support for additional programming languages.
- Enhanced retry and error-handling mechanisms.
- Full integration testing of checkpoint recovery and workflow routing.
- Improved sandbox isolation and resource limits.
- Support for additional LLM providers.
- More advanced code quality and security analysis.

## Author

Developed as a practical project demonstrating autonomous AI agents, LangGraph orchestration, LLM integration, GitHub API automation, FastAPI development and Human-in-the-Loop workflows.