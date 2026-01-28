# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LangGraph-based AI Agent Orchestrator with multi-provider support (OpenAI, Anthropic, Google). Provides a REST API for creating agents, registering tools, defining workflows as DAGs, and executing them with state persistence.

## Commands

```bash
# Install dependencies (uses uv package manager)
uv sync
uv sync --all-extras  # Include dev dependencies

# Run the server
uvicorn agent_orchestrator.main:app --reload
# Or: python -m agent_orchestrator.main

# Database migrations
alembic upgrade head           # Apply all migrations
alembic revision -m "message"  # Create new migration

# Testing
pytest                         # Run all tests
pytest tests/path/test_file.py::test_name  # Single test
pytest --cov=src/agent_orchestrator        # With coverage

# Code quality
ruff check src/                # Lint
ruff format src/               # Format
mypy src/                      # Type check (strict mode)
```

## Architecture

### Service-Oriented Design

```
FastAPI API (/api/v1/*)
       │
       ▼
   Services (agent_service, workflow_service, execution_service, tool_service)
       │
       ├─────────────────┐
       ▼                 ▼
   SQLAlchemy ORM   WorkflowCompiler
   (PostgreSQL)     (LangGraph StateGraph)
       │                 │
       └────────┬────────┘
                ▼
        AI Providers (OpenAI, Anthropic, Google)
```

### Key Flow: Workflow Execution

1. `POST /api/v1/executions` receives workflow_id + input
2. `ExecutionService` loads workflow from DB (nodes, edges, agents, tools)
3. `WorkflowCompiler.compile()` converts DB models → LangGraph `StateGraph`
4. Graph executes with checkpointing (resumable via thread_id)
5. Returns execution record with output

### Node Types (WorkflowNode)

- **AGENT**: Executes an LLM agent with bound tools
- **ROUTER**: Conditional branching based on state evaluation
- **PARALLEL**: Fan-out to multiple concurrent nodes
- **JOIN**: Fan-in/aggregation of parallel results
- **SUBGRAPH**: Nested workflow execution

### Database Models

All models use `UUIDMixin` (UUID PKs) and `TimestampMixin` (created_at, updated_at).

- `Agent` → `AgentTool` → `Tool` (many-to-many)
- `Workflow` → `WorkflowNode`, `WorkflowEdge` (one-to-many)
- `Execution` → `ExecutionStep` (one-to-many)

## Key Patterns

### Adding a New AI Provider

1. Create `src/agent_orchestrator/providers/newprovider.py` extending `BaseProvider`
2. Implement `create_model()`, optionally `create_model_with_tools()` and `create_model_with_structured_output()`
3. Register in `ProviderFactory._providers` dict in `factory.py`

### Adding a Built-in Tool

1. Create class in `src/agent_orchestrator/tools/builtin/` extending `BaseTool`
2. Implement `get_input_schema()` and `execute()` methods
3. Add to `register_builtin_tools()` in `registry.py`

### API Authentication

All endpoints require `X-API-Key` header. Validated via `api_key_dependency` in `dependencies.py`.

## Configuration

Environment variables loaded via pydantic-settings (`config.py`). Copy `.env.example` to `.env`.

Required:
- `DATABASE_URL` - PostgreSQL connection (asyncpg driver)
- `API_KEY` - API authentication key
- At least one of: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`

## Code Conventions

- **Async-first**: All DB operations and HTTP handlers use asyncio
- **Type-strict**: mypy in strict mode, Python 3.12+
- **Line length**: 100 characters (ruff)
- **Import order**: Enforced by ruff (stdlib, third-party, local)
