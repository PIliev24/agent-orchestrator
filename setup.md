Setup


  Implementation Summary

  56 Python files created across these modules:

  Core Structure

  - config.py - Settings with pydantic-settings
  - main.py - FastAPI application entry point

  Database Layer

  - database/models/ - SQLAlchemy models for Agent, Tool, Workflow, WorkflowNode, WorkflowEdge, Execution, ExecutionStep
  - database/engine.py - Async SQLAlchemy engine
  - database/session.py - Session dependency

  API Layer

  - api/routes/ - RESTful endpoints for agents, tools, workflows, executions, health
  - api/dependencies.py - Database session and API key auth
  - api/exception_handlers.py - Custom error handling

  Services Layer

  - services/agent_service.py - Agent CRUD
  - services/tool_service.py - Tool CRUD
  - services/workflow_service.py - Workflow CRUD with validation
  - services/execution_service.py - Workflow execution with streaming

  LangGraph Workflow Engine

  - workflows/compiler.py - JSON → StateGraph compilation
  - workflows/state.py - Workflow state management
  - workflows/checkpointer.py - PostgreSQL persistence
  - workflows/nodes/ - Agent, router, parallel, join node implementations

  AI Providers

  - providers/openai.py, anthropic.py, google.py - LangChain integrations
  - providers/factory.py - Provider factory with temperature locked to 0

  Tools

  - tools/registry.py - Tool registry
  - tools/builtin/calculator.py, http_tool.py - Built-in tools

  Migration Setup

  - alembic.ini, alembic/env.py - Async Alembic configuration

  Next Steps

  1. Start PostgreSQL: docker run -d --name pg-orchestrator -e POSTGRES_DB=agent_orchestrator -e POSTGRES_PASSWORD=postgres -p 5432:5432 postgres:16
  2. Run migrations: alembic revision --autogenerate -m "Initial migration" && alembic upgrade head
  3. Start server: uvicorn agent_orchestrator.main:app --reload
  4. Test the API at http://localhost:8000/docs

  # Start PostgreSQL
  docker run -d --name pg-orchestrator \
    -e POSTGRES_DB=agent_orchestrator \
    -e POSTGRES_PASSWORD=postgres \
    -p 5432:5432 \
    postgres:16

  # Run migrations
  cd /home/petariliev/Programming/agent-orchestrator
  alembic revision --autogenerate -m "Initial migration"
  alembic upgrade head

  # Start server
  uvicorn agent_orchestrator.main:app --reload

  Test Endpoints

  1. Health Check

  curl http://localhost:8000/api/v1/health

  2. Create a Tool

  curl -X POST http://localhost:8000/api/v1/tools \
    -H "Content-Type: application/json" \
    -H "X-API-Key: default-api-key" \
    -d '{
      "name": "calculator",
      "description": "Evaluate mathematical expressions",
      "function_schema": {
        "name": "calculator",
        "description": "Evaluate a math expression",
        "parameters": {
          "type": "object",
          "properties": {
            "expression": {"type": "string"}
          },
          "required": ["expression"]
        }
      },
    }'

  3. Create an Agent

  curl -X POST http://localhost:8000/api/v1/agents \
    -H "Content-Type: application/json" \
    -H "X-API-Key: default-api-key" \
    -d '{
      "name": "Math Assistant",
      "description": "Helps with math questions",
      "instructions": "You are a helpful math assistant. Answer math questions clearly and concisely.",
      "llm_config": {
        "provider": "openai",
        "model_name": "gpt-4o-mini"
      }
    }'

  4. List Agents

  curl http://localhost:8000/api/v1/agents \
    -H "X-API-Key: default-api-key"

  5. Create a Simple Workflow

  Replace <AGENT_ID> with the UUID from step 3:
  curl -X POST http://localhost:8000/api/v1/workflows \
    -H "Content-Type: application/json" \
    -H "X-API-Key: default-api-key" \
    -d '{
      "name": "Simple QA Workflow",
      "description": "Single agent Q&A",
      "nodes": [
        {
          "node_id": "qa_agent",
          "node_type": "agent",
          "agent_id": "<AGENT_ID>"
        }
      ],
      "edges": [
        {"source_node": "__start__", "target_node": "qa_agent"},
        {"source_node": "qa_agent", "target_node": "__end__"}
      ]
    }'

  6. List Workflows

  curl http://localhost:8000/api/v1/workflows \
    -H "X-API-Key: default-api-key"

  7. Execute Workflow

  Replace <WORKFLOW_ID> with the UUID from step 5:
  curl -X POST http://localhost:8000/api/v1/executions \
    -H "Content-Type: application/json" \
    -H "X-API-Key: default-api-key" \
    -d '{
      "workflow_id": "<WORKFLOW_ID>",
      "input": {
        "query": "What is 25 * 4?"
      }
    }'

  8. Get Execution Status (lightweight, for polling)

  Replace <EXECUTION_ID>:
  curl http://localhost:8000/api/v1/executions/<EXECUTION_ID>/status \
    -H "X-API-Key: default-api-key"

  9. Get Full Execution Details

  Replace <EXECUTION_ID>:
  curl http://localhost:8000/api/v1/executions/<EXECUTION_ID> \
    -H "X-API-Key: default-api-key"

  10. List Executions

  curl http://localhost:8000/api/v1/executions \
    -H "X-API-Key: default-api-key"

  11. Execute Workflow with Streaming (SSE)

  For real-time progress updates, use the streaming endpoint:
  curl -N -X POST http://localhost:8000/api/v1/executions/stream \
    -H "Content-Type: application/json" \
    -H "X-API-Key: default-api-key" \
    -d '{
      "workflow_id": "<WORKFLOW_ID>",
      "input": {"query": "Explain the Pythagorean theorem"}
    }'

  12. Cancel a Running Execution

  Replace <EXECUTION_ID>:
  curl -X POST http://localhost:8000/api/v1/executions/<EXECUTION_ID>/cancel \
    -H "X-API-Key: default-api-key"

  ---
  Multi-Agent Workflow Example

  Create a second agent and a workflow with conditional routing:

  # Create a validator agent
  curl -X POST http://localhost:8000/api/v1/agents \
    -H "Content-Type: application/json" \
    -H "X-API-Key: default-api-key" \
    -d '{
      "name": "Answer Validator",
      "instructions": "You validate answers. Respond with JSON: {\"valid\": true/false, \"feedback\": \"...\"}",
      "llm_config": {
        "provider": "openai",
        "model_name": "gpt-4o-mini"
      }
    }'

  # Create workflow with two agents
  curl -X POST http://localhost:8000/api/v1/workflows \
    -H "Content-Type: application/json" \
    -H "X-API-Key: default-api-key" \
    -d '{
      "name": "QA with Validation",
      "nodes": [
        {"node_id": "generator", "node_type": "agent", "agent_id": "<GENERATOR_AGENT_ID>"},
        {"node_id": "validator", "node_type": "agent", "agent_id": "<VALIDATOR_AGENT_ID>"}
      ],
      "edges": [
        {"source_node": "__start__", "target_node": "generator"},
        {"source_node": "generator", "target_node": "validator"},
        {"source_node": "validator", "target_node": "__end__"}
      ]
    }'

  ---
  OpenAPI Docs

  For interactive testing, open: http://localhost:8000/docs