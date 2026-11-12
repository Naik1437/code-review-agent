# Autonomous Code Review & Refactoring Agent with LangGraph

An AI-powered autonomous code review and refactoring system built using Python, LangGraph, FastAPI, and GitHub API integration.

The application automatically fetches Python files from GitHub Pull Requests, performs lint analysis, generates AI-based refactoring suggestions, validates the proposed changes, and pauses for Human-in-the-Loop (HITL) approval before committing changes to GitHub.

## Features

- **LangGraph Stateful Workflow:** Orchestrates the code review lifecycle through fetch, lint, refactor, validation, and apply nodes.
- **GitHub API Integration:** Fetches Pull Request details and modified Python files.
- **Custom Linter Tool:** Uses Flake8 to detect Python syntax and style issues.
- **AI-Powered Refactoring:** Uses an LLM to generate improved code suggestions.
- **Human-in-the-Loop Approval:** Requires human approval before applying changes.
- **Reviewer Feedback:** Supports rejection and refactoring based on reviewer feedback.
- **Persistent Checkpointing:** Uses SQLite to preserve workflow state.
- **FastAPI REST API:** Provides webhook and review approval endpoints.
- **Docker Support:** Includes Dockerfile and Docker Compose for containerized deployment.
- **Automated Testing:** Uses pytest to validate linter behavior and approval routing.

## Technology Stack

| Component | Technology |
|---|---|
| Programming Language | Python 3.11 |
| Agent Framework | LangGraph |
| LLM Integration | LangChain OpenAI |
| Backend API | FastAPI |
| GitHub Integration | GitHub REST API |
| Code Analysis | Flake8 |
| State Persistence | SQLite |
| Testing | Pytest |
| Containerization | Docker |
| API Documentation | OpenAPI / Swagger UI |

## Project Structure

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
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── openapi.json
├── requirements.txt
├── README.md
└── conftest.py
```

## System Workflow

1. **Fetch Pull Request:** Retrieves Pull Request information and modified Python files from GitHub.
2. **Lint Analysis:** Runs Flake8 to identify syntax and code-style issues.
3. **AI Refactoring:** Generates improved code suggestions using the configured language model.
4. **Refactor Validation:** Checks the generated code using the linter.
5. **Human Approval:** Pauses execution before applying changes.
6. **Feedback Loop:** If rejected, reviewer feedback is passed back to the refactoring stage.
7. **Apply Changes:** If approved, the agent commits the refactored files to GitHub.

## Installation and Local Setup

### 1. Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd code-review-agent
```

### 2. Create a Virtual Environment

Windows:

```powershell
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root.

```env
GITHUB_TOKEN=your_github_token
OPENAI_API_KEY=your_openai_api_key
```

Configure a GitHub token with the required repository permissions for reading Pull Requests and writing repository contents.

A valid OpenAI API key with API access and available billing or credits is required for the configured AI refactoring stage.

**Security:** Never commit `.env` or expose API keys publicly.

### 5. Start the Application

```powershell
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

## API Endpoints

### 1. GitHub Webhook

**POST** `/api/webhooks/github`

Receives GitHub Pull Request information and starts the review workflow.

### 2. Review Approval

**POST** `/api/reviews/{thread_id}/approve`

Accepts reviewer approval or rejection and optional feedback.

Example request:

```json
{
  "approved": false,
  "feedback": "Please improve the code readability."
}
```

For approval:

```json
{
  "approved": true,
  "feedback": null
}
```

## API Documentation

FastAPI automatically generates interactive API documentation.

Swagger UI:

```text
http://localhost:8000/docs
```

OpenAPI specification:

```text
http://localhost:8000/openapi.json
```

The exported specification is available in `openapi.json`.

## Docker Deployment

Make sure Docker Desktop is installed and running.

### Build the Docker Image

```powershell
docker compose build
```

### Start the Container

```powershell
docker compose up -d
```

### Check Running Containers

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

After starting the container, access:

```text
http://localhost:8000/docs
```

## Running Tests

Execute the automated test suite:

```powershell
pytest -v
```

The current test suite covers:

- Python syntax error detection.
- Flake8 style error detection.
- Acceptance of clean Python code.
- Rejection routing to the refactoring stage.
- Approval routing to workflow completion.

## Future Improvements

- GitHub webhook signature verification.
- Support for additional programming languages.
- Improved retry and error-handling mechanisms.
- More comprehensive integration and API tests.
- Enhanced code security and sandbox isolation.
- Support for additional LLM providers.

## Author

Developed as a practical project demonstrating autonomous AI agents, LangGraph orchestration, GitHub API integration, FastAPI development, and Human-in-the-Loop workflows.