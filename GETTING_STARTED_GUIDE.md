# Getting Started: Agent Orchestration for Question Generation

A step-by-step guide to using the Agent Orchestrator frontend to create and execute the Educational Question Generation workflow.

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Step 1: Start the Backend](#step-1-start-the-backend)
4. [Step 2: Start the Frontend](#step-2-start-the-frontend)
5. [Step 3: Register Tools](#step-3-register-tools)
6. [Step 4: Create Agents](#step-4-create-agents)
7. [Step 5: Create the Workflow](#step-5-create-the-workflow)
8. [Step 6: Execute the Workflow](#step-6-execute-the-workflow)
9. [Step 7: Review Results](#step-7-review-results)
10. [Troubleshooting](#troubleshooting)

---

## Overview

This guide walks you through using the Agent Orchestrator to automatically generate educational questions from textbook content. The system uses:

- **OCR Processing**: Extract text from PDF/image documents using Mistral AI
- **AI Agents**: Specialized agents for planning, generating, validating, and formatting questions
- **Parallel Processing**: Generate questions at different difficulty levels simultaneously
- **File Output**: Save results to local files for further use

### What You'll Build

```
Document (PDF) → OCR → Planning → Question Generation → Validation → Formatted Output → Saved Files
                                        ↓
                    ┌───────────────────┼───────────────────┐
                    ↓                   ↓                   ↓
              Input Level 1-3    Activation Level 1-3   Geometry Diagrams
```

---

## Prerequisites

Before starting, ensure you have:

### Required API Keys

Set these in your backend `.env` file:

```bash
# Required
MISTRAL_API_KEY=your-mistral-api-key    # For OCR processing
ANTHROPIC_API_KEY=your-anthropic-key    # For Claude agents

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/agent_orchestrator

# API Authentication
API_KEY=default-api-key
```

### Required Software

- PostgreSQL database running
- Python 3.12+ with uv package manager
- Bun (for frontend)
- A PDF textbook or educational document to process

---

## Step 1: Start the Backend

1. **Navigate to the backend directory:**
   ```bash
   cd /home/petariliev/Programming/agent-orchestrator
   ```

2. **Install dependencies:**
   ```bash
   uv sync --all-extras
   ```

3. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

4. **Start the server:**
   ```bash
   uvicorn agent_orchestrator.main:app --reload
   ```

5. **Verify the server is running:**
   ```bash
   curl http://localhost:8000/health
   ```

   Expected response: `{"status": "healthy"}`

---

## Step 2: Start the Frontend

1. **Navigate to the frontend directory:**
   ```bash
   cd agent-orchestrator-ui
   ```

2. **Install dependencies:**
   ```bash
   bun install
   ```

3. **Configure environment:**
   Create `.env.local`:
   ```bash
   VITE_API_URL=http://localhost:8000/api/v1
   VITE_API_KEY=default-api-key
   ```

4. **Start the development server:**
   ```bash
   bun run dev
   ```

5. **Open the frontend:**
   Navigate to `http://localhost:5173` in your browser.

---

## Step 3: Register Tools

Navigate to **Tools** in the sidebar and create the following tools:

### 3.1 Mistral OCR Tool

Click **"New Tool"** and fill in:

| Field | Value |
|-------|-------|
| Name | `mistral_ocr` |
| Description | Process documents (PDF, DOCX, images) using Mistral AI OCR. Returns markdown text and extracted images. |

**Function Schema** (paste in JSON editor):
```json
{
  "name": "mistral_ocr",
  "description": "Process a document using Mistral AI OCR",
  "parameters": {
    "type": "object",
    "properties": {
      "file_path": {
        "type": "string",
        "description": "Path to the document file (PDF, DOCX, PNG, JPG, JPEG, WEBP)"
      },
      "include_images": {
        "type": "boolean",
        "description": "Whether to extract and return images (default: true)"
      },
      "pages": {
        "type": "array",
        "items": {"type": "integer"},
        "description": "Specific page numbers to process (1-indexed)"
      }
    },
    "required": ["file_path"]
  }
}
```

**Save and note the Tool ID.**

### 3.2 Calculator Tool

Click **"New Tool"** and fill in:

| Field | Value |
|-------|-------|
| Name | `calculator` |
| Description | Evaluate mathematical expressions for verification |

**Function Schema:**
```json
{
  "name": "calculator",
  "description": "Evaluate a mathematical expression",
  "parameters": {
    "type": "object",
    "properties": {
      "expression": {
        "type": "string",
        "description": "Mathematical expression to evaluate (e.g., \"(2 + 3) * 4\")"
      }
    },
    "required": ["expression"]
  }
}
```

**Save and note the Tool ID.**

### 3.3 File Writer Tool

Click **"New Tool"** and fill in:

| Field | Value |
|-------|-------|
| Name | `file_writer` |
| Description | Write content to local files. Supports text and JSON formats. |

**Function Schema:**
```json
{
  "name": "file_writer",
  "description": "Write content to a local file",
  "parameters": {
    "type": "object",
    "properties": {
      "content": {
        "type": ["string", "object", "array"],
        "description": "Content to write (string, object, or array)"
      },
      "file_path": {
        "type": "string",
        "description": "Path to write the file (directory or full path)"
      },
      "format": {
        "type": "string",
        "enum": ["text", "json"],
        "description": "Output format (auto-detected if not specified)"
      },
      "append": {
        "type": "boolean",
        "description": "Append to existing file instead of overwriting"
      }
    },
    "required": ["content", "file_path"]
  }
}
```

**Config** (optional):
```json
{
  "base_directory": "/home/user/output"
}
```

**Save and note the Tool ID.**

---

## Step 4: Create Agents

Navigate to **Agents** in the sidebar and create the following agents:

### Quick Reference: Agent Creation Settings

For all agents, use these LLM settings unless otherwise specified:

| Setting | Value |
|---------|-------|
| Provider | `anthropic` |
| Model Name | `claude-sonnet-4-20250514` |
| Max Tokens | See individual agent |

### 4.1 Document Processor Agent

| Field | Value |
|-------|-------|
| Name | Document Processor |
| Description | Extracts and structures content from educational documents using OCR |
| Max Tokens | 8000 |
| Tools | Select `mistral_ocr` |

**Instructions:** (Copy the full instructions from QUESTION_GENERATION_GUIDE.md Section 4.1)

The key responsibilities:
- Process documents using the mistral_ocr tool
- Extract lesson title, code, skills, definitions, theorems, examples
- Preserve Bulgarian language and LaTeX notation
- Mark extracted content as "reference material"

**Save and note the Agent ID.**

### 4.2 Content Planner Agent

| Field | Value |
|-------|-------|
| Name | Content Planner |
| Description | Creates detailed plans for educational question generation |
| Max Tokens | 4000 |
| Tools | None |

**Instructions:** (Copy from QUESTION_GENERATION_GUIDE.md Section 4.2)

Key responsibilities:
- Analyze processed content and create question distribution plan
- Define questions per difficulty level (Input 1-3, Activation 1-3)
- Map skills to questions
- Consider geometry diagram needs

**Save and note the Agent ID.**

### 4.3 - 4.8 Question Generator Agents

Create 6 generator agents with the following configurations:

| Agent | Name | Max Tokens | Focus |
|-------|------|------------|-------|
| 4.3 | Input 1 Generator | 6000 | Flashcards, Yes/No, Single Select |
| 4.4 | Input 2 Generator | 6000 | Multi-select, Matching, Tables |
| 4.5 | Input 3 Generator | 6000 | Complex synthesis questions |
| 4.6 | Activation 1 Generator | 8000 | 55% difficulty problems |
| 4.7 | Activation 2 Generator | 8000 | 75% difficulty problems |
| 4.8 | Activation 3 Generator | 10000 | 95% exam-level problems |

**All generators should:**
- Have the `calculator` tool attached
- Include the CRITICAL originality instructions (create original content, NOT copy)
- Include skill description handling instructions

**Save all Agent IDs.**

### 4.9 Geometry Diagram Generator

| Field | Value |
|-------|-------|
| Name | Geometry Diagram Generator |
| Description | Generates TikZ/LaTeX code for geometry diagrams |
| Max Tokens | 6000 |
| Tools | None |

**Save and note the Agent ID.**

### 4.10 Question Validator

| Field | Value |
|-------|-------|
| Name | Question Validator |
| Description | Validates generated questions for correctness and format |
| Max Tokens | 8000 |
| Tools | Select `calculator` |

**Save and note the Agent ID.**

### 4.11 Output Formatter

| Field | Value |
|-------|-------|
| Name | Output Formatter |
| Description | Formats validated questions into final markdown output |
| Max Tokens | 12000 |
| Tools | None |

**Save and note the Agent ID.**

### 4.12 File Saver

| Field | Value |
|-------|-------|
| Name | File Saver |
| Description | Saves extracted content and generated questions to local files |
| Max Tokens | 4000 |
| Tools | Select `file_writer` |

**Save and note the Agent ID.**

---

## Step 5: Create the Workflow

Navigate to **Workflows** in the sidebar and click **"New Workflow"**.

### Basic Information

| Field | Value |
|-------|-------|
| Name | Educational Question Generation Pipeline |
| Description | Complete pipeline for generating educational questions from textbook content |
| Is Template | Yes (checked) |

### State Schema

Paste this JSON in the state schema editor:

```json
{
  "type": "object",
  "properties": {
    "document_path": {"type": "string"},
    "lesson_code": {"type": "string"},
    "lesson_title": {"type": "string"},
    "lesson_title_en": {"type": "string"},
    "skills": {"type": "array"},
    "learning_objectives": {"type": "array"},
    "grade_level": {"type": "integer"},
    "subject": {"type": "string"},
    "additional_context": {"type": "string"},
    "processed_content": {"type": "object"},
    "generation_plan": {"type": "object"},
    "questions": {
      "type": "object",
      "properties": {
        "input_1": {"type": "array"},
        "input_2": {"type": "array"},
        "input_3": {"type": "array"},
        "activation_1": {"type": "array"},
        "activation_2": {"type": "array"},
        "activation_3": {"type": "array"}
      }
    },
    "diagrams_needed": {"type": "boolean"},
    "diagrams": {"type": "array"},
    "validation_results": {"type": "object"},
    "final_markdown": {"type": "string"},
    "output_files": {"type": "object"}
  },
  "required": ["document_path"]
}
```

### Add Workflow Nodes

Add nodes in this order (use the visual workflow builder if available):

| Node ID | Type | Agent | Description |
|---------|------|-------|-------------|
| `doc_processor` | Agent | Document Processor | Extracts content from document |
| `planner` | Agent | Content Planner | Creates generation plan |
| `parallel_generators` | Parallel | - | Fan-out to generators |
| `gen_v1` | Agent | Input 1 Generator | Generates Input Level 1 |
| `gen_v2` | Agent | Input 2 Generator | Generates Input Level 2 |
| `gen_v3` | Agent | Input 3 Generator | Generates Input Level 3 |
| `gen_a1` | Agent | Activation 1 Generator | Generates Activation 1 |
| `gen_a2` | Agent | Activation 2 Generator | Generates Activation 2 |
| `gen_a3` | Agent | Activation 3 Generator | Generates Activation 3 |
| `join_questions` | Join | - | Aggregates all questions |
| `diagram_router` | Router | - | Checks if diagrams needed |
| `diagram_generator` | Agent | Geometry Diagram Generator | Creates TikZ diagrams |
| `validator` | Agent | Question Validator | Validates questions |
| `formatter` | Agent | Output Formatter | Creates final markdown |
| `save_output` | Agent | File Saver | Saves files |

### Add Workflow Edges

Connect the nodes:

```
__start__ → doc_processor → planner → parallel_generators
parallel_generators → gen_v1, gen_v2, gen_v3, gen_a1, gen_a2, gen_a3
gen_v1, gen_v2, gen_v3, gen_a1, gen_a2, gen_a3 → join_questions
join_questions → diagram_router
diagram_router → diagram_generator (conditional: diagrams_needed)
diagram_router → validator (default)
diagram_generator → validator
validator → formatter → save_output → __end__
```

**Save the Workflow and note the Workflow ID.**

---

## Step 6: Execute the Workflow

Navigate to **Executions** → **New Execution**.

### 6.1 Select Workflow

Choose "Educational Question Generation Pipeline" from the dropdown.

### 6.2 Fill in Execution Input

The Skill Context Form will appear. Fill in:

#### Required Fields

| Field | Example Value |
|-------|---------------|
| Document Path | `/home/user/textbooks/math_7_chapter4.pdf` |

#### Optional Fields (Recommended)

| Field | Example Value |
|-------|---------------|
| Lesson Code | `4.1` |
| Lesson Title (Bulgarian) | `Еднакви триъгълници` |
| Lesson Title (English) | `Congruent Triangles` |
| Grade Level | `7` |
| Subject | `mathematics` |

#### Skills (Click "Add Skill" for each)

| Code | Description (Bulgarian) | Description (English) |
|------|------------------------|----------------------|
| 4.1.1 | Определяне на еднакви триъгълници | Identifying congruent triangles |
| 4.1.2 | Прилагане на признаци за еднаквост | Applying congruence criteria |
| 4.1.3 | Доказване на еднаквост на триъгълници | Proving triangle congruence |

#### Learning Objectives (Click "Add Objective" for each)

- Understand the concept of triangle congruence
- Apply the three congruence criteria (SSS, SAS, ASA)
- Construct proofs using congruence relationships

#### Additional Context

```
Focus on geometric proofs and real-world applications. Students have prior knowledge of basic triangle properties and angle relationships.
```

### 6.3 Execute

Click **"Execute Workflow"**.

### 6.4 Monitor Progress

The Execution Progress component will show:
- Real-time node status (pending → running → completed)
- Progress bar
- Live SSE event stream

**Typical execution flow:**
1. `doc_processor` - Processing document (may take 1-2 minutes for large PDFs)
2. `planner` - Creating question plan
3. `gen_v1` through `gen_a3` - Running in parallel
4. `join_questions` - Aggregating results
5. `diagram_router` - Checking for diagram needs
6. `diagram_generator` - Creating TikZ diagrams (if needed)
7. `validator` - Validating all questions
8. `formatter` - Creating final markdown
9. `save_output` - Saving files

### 6.5 Cancel if Needed

Click **"Cancel Execution"** if you need to stop the process.

---

## Step 7: Review Results

### 7.1 View Execution Details

Navigate to **Executions** and click on your completed execution.

You'll see:
- **Status**: COMPLETED (or FAILED with error details)
- **Execution Steps**: Each node's input/output
- **Final Output**: The complete results

### 7.2 Access Output Files

The File Saver agent saves files to your configured output directory:

```
output/
├── {lesson_code}/
│   ├── {lesson_code}_questions.md        # Final formatted questions
│   ├── {lesson_code}_questions_data.json # Raw question data (for programmatic use)
│   ├── {lesson_code}_validation_report.json # Validation results
│   └── diagrams/
│       └── *.tikz                        # TikZ diagram code files
```

### 7.3 Review Generated Questions

Open the markdown file to see:

```markdown
# 4.1 Еднакви триъгълници
## Congruent Triangles

## Умения / Skills
| Код | Описание (БГ) | Description (EN) |
|-----|--------------|------------------|
| 4.1.1 | Определяне на еднакви триъгълници | Identifying congruent triangles |
...

## Вход 1 / Input Level 1 (10%)
### V1.001 - Flashcard
**Front:** Кога два триъгълника са еднакви?
**Back:** Два триъгълника са еднакви, когато...

## Активация 3 / Activation Level 3 (24%)
### A3.001 - Competition Problem
**Question:** В триъгълник $$ABC$$...

## Metadata
- **Generated:** 2024-01-15T14:30:00Z
- **Total Questions:** 30
- **Validation:** Passed (30/30)
```

### 7.4 Use the JSON Data

For integration with other systems, use the JSON file:

```json
{
  "lesson_code": "4.1",
  "questions": {
    "input_1": [...],
    "input_2": [...],
    "activation_3": [...]
  },
  "validation_results": {
    "total": 30,
    "passed": 30,
    "failed": 0
  }
}
```

---

## Troubleshooting

### Common Issues

#### 1. "Tool not found: builtin:mistral_ocr"

**Cause:** The MistralOCRTool is not registered in the backend.

**Solution:**
1. Ensure `mistral_ocr.py` exists in `src/agent_orchestrator/tools/builtin/`
2. Check that it's exported in `__init__.py`
3. Verify it's registered in `registry.py`
4. Restart the backend server

#### 2. "MISTRAL_API_KEY not configured"

**Cause:** Missing or invalid Mistral API key.

**Solution:**
1. Get an API key from https://console.mistral.ai/
2. Add to your `.env` file: `MISTRAL_API_KEY=your-key`
3. Restart the backend server

#### 3. Execution Timeout

**Cause:** Large documents or slow API responses.

**Solution:**
- Process specific pages only: Use the `pages` parameter in OCR
- Use streaming execution to monitor progress
- Check API rate limits

#### 4. Empty or Poor OCR Results

**Cause:** Low-quality document scans.

**Solution:**
- Use high-resolution PDF scans (300+ DPI)
- Try processing pages individually
- Check if the document is text-based or image-based

#### 5. Validation Failures

**Cause:** Generated questions don't meet format requirements.

**Solution:**
- Review the validation report for specific errors
- Check agent instructions for format requirements
- Regenerate specific question types if needed

#### 6. Questions Copied from Source

**Cause:** Generator agents not following originality instructions.

**Solution:**
- Ensure all generator agents have the "CRITICAL: Content Originality Requirements" section
- Verify the instructions emphasize "INSPIRATION ONLY"
- Review generated questions against source material

### Debug Mode

Enable debug logging in the backend:

```bash
export LOG_LEVEL=DEBUG
uvicorn agent_orchestrator.main:app --reload
```

### API Verification

Test individual components via API:

```bash
# Test OCR tool directly
curl -X POST http://localhost:8000/api/v1/tools/execute \
  -H "X-API-Key: default-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "tool_id": "YOUR_MISTRAL_OCR_TOOL_ID",
    "input": {"file_path": "/path/to/test.pdf"}
  }'

# Test a single agent
curl -X POST http://localhost:8000/api/v1/agents/{agent_id}/invoke \
  -H "X-API-Key: default-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "input": "Test input message"
  }'
```

---

## Next Steps

Once you've successfully executed the workflow:

1. **Iterate on Agent Instructions**: Refine prompts based on output quality
2. **Add More Subjects**: Create workflows for physics, chemistry, etc.
3. **Customize Question Types**: Add new question formats to generators
4. **Integrate with LMS**: Use the JSON output to import into learning platforms
5. **Build Assessment Pipelines**: Create workflows for generating full exams

---

## Quick Reference: IDs to Track

Keep a record of all created IDs:

| Resource | Name | ID |
|----------|------|-----|
| Tool | mistral_ocr | |
| Tool | calculator | |
| Tool | file_writer | |
| Agent | Document Processor | |
| Agent | Content Planner | |
| Agent | Input 1 Generator | |
| Agent | Input 2 Generator | |
| Agent | Input 3 Generator | |
| Agent | Activation 1 Generator | |
| Agent | Activation 2 Generator | |
| Agent | Activation 3 Generator | |
| Agent | Geometry Diagram Generator | |
| Agent | Question Validator | |
| Agent | Output Formatter | |
| Agent | File Saver | |
| Workflow | Question Generation Pipeline | |

---

## Support

- **Backend Issues**: Check server logs and API responses
- **Frontend Issues**: Check browser console for errors
- **Workflow Issues**: Review individual node outputs in execution details
- **Agent Issues**: Test agents individually before full workflow execution
