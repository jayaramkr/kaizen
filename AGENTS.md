# What is Evolve?
Evolve (`altk-evolve`; older surfaces say "Kaizen" or "tips") is a Python library and service that lets AI agents improve from their own history. Agent trajectories are mined for **guidelines** — reusable lessons — which are stored and served back to future agents working on similar tasks.

## Key Concepts
- **Trajectory**: a recorded agent run — the messages, tool calls and results of one task.
- **Guideline**: an actionable lesson generated from a trajectory, with a `content`, `rationale`, `trigger` and `category` (`strategy` | `recovery` | `optimization`).
- **Entity**: anything stored in the backend — guidelines, policies, user facts.
- **Namespace**: an isolated store of entities.
- **Conflict resolution**: LLM-based merging of duplicate or contradictory entities on write.
- **Consistency analysis**: resampling each step of a trajectory several times and scoring how much the model's choices vary, so guidelines can focus on the steps where it wavered.
- **Hook seam**: plugin points at every entity read/write and every LLM call, used for PII redaction, secrets detection and legal hold.
- **Retention**: policy-driven ageing and deletion of stored entities.

## Architecture Flow
1. An agent completes a task; its trajectory is captured by an observability platform (Arize Phoenix or Langfuse), or submitted directly through the MCP `save_trajectory` tool.
2. `evolve sync phoenix`, or `save_trajectory`, processes the trajectory. Depending on `EVOLVE_GUIDELINES_MODE` it runs the **standard** pipeline, the **consistency** pipeline, or both.
3. Generated guidelines are written as entities, with conflict resolution applied.
4. Future agents query the MCP server for relevant guidelines before starting work.

Every entity read/write and every LLM call along the way passes through the hook seam, and stored entities age out under retention policies.

## Project Directory Tree (some files omitted)
```text
.
├── altk_evolve (Primary source root — the installable package)
│   ├── auto (Opt-in auto-instrumentation of openai/litellm/smolagents/openai-agents)
│   ├── backend (Storage backends: filesystem (default), milvus, postgres/pgvector)
│   ├── cli (Typer CLI: namespaces, entities, sync, skills, viz, hooks, retention)
│   ├── config (Settings read from EVOLVE_-prefixed environment variables)
│   ├── db (SQLite used for namespace metadata by every backend)
│   ├── frontend
│   │   ├── api (FastAPI routes for the UI and the scoped memory API)
│   │   ├── client (EvolveClient — the native Python client wrapping a backend)
│   │   ├── mcp (FastMCP server — 47 tools; also serves the REST API and the UI)
│   │   ├── services (Request-scoped client injection shared by REST and MCP)
│   │   └── ui (React/TypeScript dashboard)
│   ├── hooks (Engine-agnostic hook seam, plus PII/secrets/legal-hold plugins)
│   ├── llm (Every piece of code that prompts an LLM)
│   │   ├── guidelines (Standard + consistency pipelines, segmentation, clustering, retrieval)
│   │   ├── conflict_resolution
│   │   └── fact_extraction
│   ├── retention (Policies, engine, scheduler and store for data retention)
│   ├── schema (Pydantic models used throughout)
│   ├── sync (Phoenix span ingestion)
│   ├── utils
│   └── viz (Standalone entity/trajectory browser)
├── docs (MkDocs site source, published to GitHub Pages)
├── includes (Single-source snippets shared by the docs site and README)
├── examples (Runnable examples: hooks, retention, PII benchmark, low-code tracing)
├── plugin-source (SOURCE OF TRUTH for the evolve-lite platform plugins)
├── platform-integrations (GENERATED from plugin-source — do not edit by hand)
├── sandbox (Docker images for running Claude Code / Codex in isolation)
├── scripts (Repo maintenance: trajectory extraction, README sync)
├── demo (Files used by the Claude Code demo)
├── experiments (One-off experiment scripts)
├── explorations (Tangential research — avoid unless explicitly asked)
├── tests
│   ├── unit (Fast, no network — the default suite)
│   ├── e2e (Needs services and credentials)
│   ├── llm (Makes real LLM calls)
│   └── platform_integrations (Exercises the generated plugins)
└── .env.example (Environment variable template)
```

## First Time Setup
```bash
uv sync && source .venv/bin/activate
cp .env.example .env    # settings are defined in altk_evolve/config/
pre-commit install
```
Governance features and non-default backends are optional extras. Install what you need, or everything:
```bash
uv sync --extra hooks --extra pii-regex     # e.g. to work on the hook seam
uv sync --all-extras                         # everything, incl. milvus/pgvector/tracing
```
Without the relevant extra, some unit tests skip rather than fail — so a green run with extras missing is not the full picture.

## Development Guidelines
- This project is managed by `uv`, not `python` or `pip`. Run every Python command through `uv`, and add dependencies in `pyproject.toml`.
- **Do not edit `platform-integrations/` directly.** It is rendered from `plugin-source/`, and CI fails if the two differ byte-for-byte. Edit `plugin-source/`, then re-render with `uv run python plugin-source/build_plugins.py render` (and confirm with `... check`, which is what CI runs).
- **Do not edit the "Latest from Evolve" block in `README.md`.** Edit `includes/latest-updates.md` and run `uv run python scripts/sync_latest_updates.py` (its `check` mode is what CI runs).
- **Dispatch hooks from the backend layer, never from a frontend.** A new entity read/write path needs the matching `dispatch_*` call in `altk_evolve/backend/`, and a new LLM call site needs `dispatch_llm_pre_call(..., purpose=...)`. There is no central wrapper, so a missed call site is a bypass of the PII boundary.
- **Governance defaults fail closed.** A hook plugin that errors halts the operation, and configured plugins with no engine installed raise at startup. Do not downgrade either to a warning.
- Settings use `pydantic_settings` with `extra="ignore"`, so a renamed or removed setting is dropped silently. When retiring a setting, add a validator that warns.
- Non-Python files that must ship (YAML configs, Jinja2 prompts) need declaring in **both** `pyproject.toml` package-data and `MANIFEST.in`.
- LLM prompts are Jinja2 templates in a `prompts/` directory beside the calling code.
- `explorations/` is experimental and excluded from packaging and the default test run.

## Testing Instructions
- Run pytest verbosely (`-v`) so failures carry context.
- Run one file or test: `uv run pytest tests/unit/test_client.py -v` or `uv run pytest tests/unit/test_client.py::test_name -v`.
- Markers are `unit`, `e2e`, `llm` and `platform_integrations`. **The default run excludes `llm` and `e2e`** (see `addopts` in `pyproject.toml`), because those need credentials or running services.
- Select by marker: `uv run pytest -m unit`, or `uv run pytest -m "e2e or unit"`.
- Mock `completion` at the module that imports it, and mock `_get_sentence_transformer` rather than `SentenceTransformer` directly.
- MCP tests create a unique database file per test to avoid SQLite locking.

## Available Interfaces
- **MCP server** (`uv run evolve-mcp`): 47 tools across guideline retrieval (`get_guidelines`, `get_relevant_guidelines`, `get_entities`…), entity management, `save_trajectory`, user facts, and retention policies, rules, schedules and jobs. The same process serves the REST API and the UI under `/ui`.
- **CLI** (`uv run evolve --help`): subcommands `namespaces`, `entities`, `sync`, `skills`, `viz`, `hooks` and `retention`. `evolve hooks init` scaffolds a hooks config.
- **Python client**: `EvolveClient()` for programmatic access, including `client.retention(namespace_id)`.
- **Docs**: `uv run --group docs mkdocs serve` to preview; the published site is built from `main` automatically.

## Coding Standards
- Use Ruff for linting and formatting (configured in `pyproject.toml`), and mypy for types: `uv run ruff check .`, `uv run ruff format .`, `uv run mypy altk_evolve`.
- Always run `uv run ruff format .` and `git add -u` before committing, to avoid pre-commit stash conflicts with ruff's auto-fixes.
- Write commit messages in the Conventional Commits format expected by `python-semantic-release`. PRs are squash-merged, so the **PR title** becomes the commit subject that determines the version bump:
  - `feat(scope): description` — new feature, minor version bump
  - `fix(scope): description` — bug fix, patch version bump
  - `perf(scope): description` — performance improvement, patch version bump
  - `test(scope):`, `chore(scope):`, `docs(scope):`, etc. — no version bump
  - Breaking changes: append `!` after the type/scope (e.g. `feat!:`) or add `BREAKING CHANGE:` in the footer. A changed **default** that alters output for existing deployments deserves one even if no signature changes.
- All new features need tests — unit, plus e2e where applicable.
