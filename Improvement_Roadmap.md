# End‑to‑End App Development Agent – Improvement Roadmap

## Overview
The current repository contains the core scaffolding for an **AI‑driven software engineer**.  It already implements:
- A basic **project planner** (`app/agents/planner.py`) that uses Ollama/Qwen‑2.5 to generate a development plan.
- A **self‑repair** module (`app/testing/self_repair.py`) that can parse errors and attempt fixes.
- Basic project generation utilities.

The roadmap you supplied defines **12 high‑level capabilities** ranging from natural‑language understanding to deployment automation.  To move from the present prototype to a production‑grade agent we should tackle the work in **phased increments**, each delivering a complete, testable feature set.

---

## Phase 1 – Core Engine (Requirements → Project Generation)
| Goal | Current Status | Actions |
|------|----------------|---------|
| **Natural‑Language Understanding** | Minimal (planner only) | - Refactor the planner to separate *intent extraction* from *plan generation*.<br>- Add a small **NLU** helper that parses the user prompt into a structured JSON schema (purpose, target users, features, tech preferences). |
| **AI Project Planner** | Implemented (static prompt) | - Convert the static `SYSTEM_PROMPT` into a **template** that can be populated with extracted intent.
- Store the generated plan in `DEVELOPMENT_PLAN.md` inside the generated project.
- Add unit tests for the planner (mock Ollama responses). |
| **Architecture Designer** | Not present | - Introduce a new agent `architecture_designer.py` that consumes the JSON intent and the development plan to produce:
  - Component diagram (Mermaid flowchart) saved as `ARCHITECTURE.md`.
  - Database schema (SQLAlchemy models) if a DB is required.
- Use `mermaid` code blocks for visualisation. |
| **Project Generator** | Basic (file copies) | - Expand `project_generator.py` to scaffold **React + Vite** frontend and **FastAPI** backend based on the chosen stack.
- Use Jinja2 templates for files (`package.json`, `vite.config.ts`, `main.py`, Dockerfiles, etc.). |
| **Self‑Repair** | Implemented, needs validation | - Write integration tests that deliberately introduce syntax errors and verify the repair loop fixes them.
- Add a configurable retry limit and detailed repair logs (`repair.log`). |

### Deliverables
- `app/agents/nlu_extractor.py`
- Updated `planner.py` using the new intent schema.
- `app/agents/architecture_designer.py`
- Enhanced `project_generator.py` with Jinja2 templates.
- Test suite under `tests/` covering all Phase 1 modules.

---

## Phase 2 – Full Stack Development
| Goal | Current Status | Actions |
|------|----------------|---------|
| **Frontend Development Agent** | In progress (React scaffolding) | - Complete component library generation (pages, navigation, forms).
- Add ESLint + Prettier config.
- Generate a small demo UI (Task list). |
| **Backend Development Agent** | Basic FastAPI stub | - Implement CRUD endpoints based on the API spec from Phase 1.
- Add authentication (JWT) and role‑based access.
- Integrate **PostgreSQL** (SQLAlchemy) with migrations (Alembic). |
| **Database Integration** | Planned | - Auto‑generate migration scripts from the schema produced by the Architecture Designer.
- Provide optional **SQLite** fallback for quick local runs. |
| **Frontend/Backend Integration** | Not implemented | - Generate API client code for the frontend (Axios wrapper) using the OpenAPI spec produced by the backend.
- Verify end‑to‑end type safety with TypeScript. |

### Deliverables
- `app/generators/react_frontend_templates/` (Jinja2 files).
- `app/generators/fastapi_backend_templates/`.
- `openapi.json` produced during generation.
- Updated CI workflow (`tests/integration_test.py`).

---

## Phase 3 – Quality Assurance
| Goal | Current Status | Actions |
|------|----------------|---------|
| **Automated Testing Agent** | Planned | - Add a test‑generation module that creates **pytest** tests for each backend route and **Vitest** tests for React components.
- Run linting (`ruff`, `eslint`) and type checks (`mypy`, `tsc`). |
| **Self‑Repair Agent (extended)** | Implemented | - Extend to handle failing tests: parse traceback, locate source file, apply quick fixes, and re‑run.
- Record a repair summary in `REPAIR_REPORT.md`. |

### Deliverables
- `app/testing/test_generator.py`
- CI script (`run_all_checks.sh`).

---

## Phase 4 – Delivery & Deployment
| Goal | Current Status | Actions |
|------|----------------|---------|
| **GitHub Integration** | Planned | - Use the GitHub REST API (via `gh` CLI or `requests`) to create a repo, push the generated project, and open a PR for the initial commit.
- Add optional branch strategy (dev/main). |
| **Documentation Agent** | Planned | - Auto‑generate `README.md`, API docs (`redoc`), and usage guides.
- Include a **Getting Started** section with Docker commands. |
| **Deployment Agent** | Planned | - Produce `Dockerfile` and `docker-compose.yml` for local dev.
- Add optional Vercel deployment script (`vercel.json`). |

### Deliverables
- `deployment/` folder with Docker configs.
- `github_integration.py` module.
- `docs/` generated files.

---

## Phase 5 – Product Experience
| Goal | Current Status | Actions |
|------|----------------|---------|
| **Project Management Dashboard** | Planned | - Build a minimal web UI (React) that shows the generation log, test results, and provides a *Download* button for the final zip.
- Persist state in a local SQLite DB (`dashboard.db`). |
| **Multi‑Project Management** | Planned | - Store each generated project under `generated_projects/<project_name>` with metadata (`metadata.json`). |

### Deliverables
- `dashboard/` React app.
- Backend API to serve project metadata.

---

## Technical Stack (as you recommended)
- **LLM**: local Ollama `qwen2.5:7b` (can swap to larger later).
- **Orchestration**: LangGraph (to chain agents, handle retries, and maintain state).
- **Backend**: FastAPI + SQLAlchemy + Alembic + PostgreSQL (fallback SQLite).
- **Frontend**: React + Vite + TypeScript.
- **Testing**: pytest + Vitest.
- **Version Control**: Git + GitHub API.
- **Deployment**: Docker + Vercel (optional).
- **Quality**: Ruff, ESLint, mypy, tsc.

---

## Next Immediate Steps (You can approve any of these)
1. **Create the NLU extractor** and modify the planner to use it.
2. **Add Jinja2 templating** for the project generator.
3. **Write unit tests** for the planner and generator.
4. Generate the first **ARCHITECTURE.md** (Mermaid diagram) from a sample prompt.

Once these are in place we will have a solid foundation to start Phase 2.

---

*Feel free to pick a specific phase or task to prioritize, or let me know if you need more detail on any component.*

