# AGENTS.md

## Project Mission
Build a public-facing podcast summarizer MVP that is simple, secure, and production-minded.

## Product Scope (MVP)
- Input:
  - Upload audio file (`.mp3`, `.m4a`, `.wav`) is required.
  - Podcast URL input is optional (nice-to-have).
- Output per job:
  - Full transcript.
  - Structured summary with sections:
    - Executive summary
    - Key takeaways
    - Timeline
    - Quotes
- Persistence:
  - Store each run as a job with a unique job ID.
  - Job artifacts must be retrievable by ID.

## Required Stack
- Backend: Python + FastAPI.
- UI: Choose the fastest path and keep it minimal:
  - Preferred for speed: minimal HTML page served by FastAPI.
  - Acceptable alternative: Streamlit frontend.

## Engineering Rules
- Security:
  - Never hardcode API keys, tokens, or secrets.
  - Use environment variables for all secrets and sensitive configuration.
  - Add a `.env.example` with placeholder variable names only.
- Code quality:
  - Keep modules small and focused.
  - Use type hints where reasonable (request/response models, service boundaries, core logic).
  - Avoid premature abstraction; optimize for readability and maintainability.
- Validation and errors:
  - Validate file type and basic input constraints at API boundary.
  - Return clear, structured error responses.
- Persistence:
  - Persist job metadata, transcript, and summary in a deterministic structure.
  - Use stable, collision-resistant IDs (for example, UUID4).

## Suggested Architecture
- `app/main.py`: FastAPI app entrypoint and route registration.
- `app/api/`: request handlers (upload, summarize, job status/result retrieval).
- `app/services/`: transcription, summarization, and orchestration logic.
- `app/models/`: typed schemas (Pydantic models/dataclasses).
- `app/storage/`: persistence layer for job artifacts.
- `tests/`: unit tests for core logic and basic API tests.

## Testing Requirements
- Add basic tests for core logic, at minimum:
  - Summary structure generation.
  - Job persistence/retrieval by ID.
  - Input validation for allowed file formats.
- Include at least one API-level test for core endpoint flow.

## Developer Workflow Requirements
Before finalizing any task, always run formatting and tests (if tools are available in environment):
- Formatting (pick project-standard tool):
  - `ruff format .` (or `black .` if Black is used)
- Lint (recommended):
  - `ruff check .`
- Tests:
  - `pytest`

If a required tool is unavailable, note that explicitly in task handoff.

## Deliverables Checklist
- [ ] FastAPI backend for upload + processing + retrieval by job ID.
- [ ] Minimal UI (FastAPI-served HTML or Streamlit), whichever is faster.
- [ ] Persistent job results containing transcript + structured summary.
- [ ] Clear `README.md` with local setup and run instructions.
- [ ] README includes a sample run command.
- [ ] Basic automated tests for core logic.

## README Minimum Content
- Project overview and MVP capabilities.
- Setup steps:
  - Python version
  - virtual environment creation
  - dependency installation
  - environment variable setup
- Run instructions for backend (and UI, if separate).
- Sample run command (for example, `curl` upload request).
- Test command(s).

## Non-Goals (for MVP)
- Complex auth/roles.
- Multi-tenant scaling features.
- Advanced analytics dashboards.
- Over-optimized infrastructure.

## Definition of Done (MVP Task)
A task is done when:
1. Feature works end-to-end for at least one supported audio format.
2. Output includes transcript and all required structured summary sections.
3. Result is persisted and retrievable via job ID.
4. Formatting and tests have been run (or tool unavailability clearly documented).
5. README updates are included when behavior/setup changes.
