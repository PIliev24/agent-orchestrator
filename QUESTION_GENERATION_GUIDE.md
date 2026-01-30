# Educational Question Generation System Guide

A comprehensive guide for setting up and using the Agent Orchestrator to generate educational questions from textbook content using AI.

## Table of Contents

1. [Prerequisites & Setup](#part-1-prerequisites--setup)
2. [Adding Mistral OCR Tool](#part-2-adding-mistral-ocr-tool)
3. [Creating Tools via API](#part-3-creating-tools-via-api)
4. [Creating Agents via API](#part-4-creating-agents-via-api)
5. [Creating Workflows via API](#part-5-creating-workflows-via-api)
6. [Executing Workflows](#part-6-executing-workflows)
7. [Complete Example Walkthrough](#part-7-complete-example-walkthrough)

---

## Part 1: Prerequisites & Setup

### Environment Variables

Create a `.env` file in the project root with the following variables:

```bash
# Database (PostgreSQL with asyncpg driver)
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/agent_orchestrator

# API Authentication
API_KEY=your-secure-api-key-here

# AI Providers (at least one required)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Mistral AI (required for OCR)
MISTRAL_API_KEY=...
```

### PostgreSQL Database Setup

```bash
# Create database
createdb agent_orchestrator

# Or using psql
psql -c "CREATE DATABASE agent_orchestrator;"
```

### Install Dependencies

```bash
# Using uv package manager
uv sync
uv sync --all-extras  # Include dev dependencies

# Install Mistral AI SDK (required for OCR tool)
uv add mistralai
```

### Run Database Migrations

```bash
alembic upgrade head
```

### Start the Server

```bash
uvicorn agent_orchestrator.main:app --reload
```

The API will be available at `http://localhost:8000`. Verify with:

```bash
curl http://localhost:8000/health
```

---

## Part 2: Adding Mistral OCR Tool

The Mistral OCR tool has been added to the codebase. Here's the implementation for reference:

### File: `src/agent_orchestrator/tools/builtin/mistral_ocr.py`

```python
"""Mistral OCR tool for processing documents with AI-powered OCR."""

import base64
import os
from pathlib import Path
from typing import Any, Optional

from agent_orchestrator.tools.base import BaseTool, ToolResult


class MistralOCRTool(BaseTool):
    """Tool for processing documents using Mistral AI's OCR capabilities.

    Supports PDF, DOCX, and image files. Extracts text content and
    returns it as markdown along with any extracted images.
    """

    name = "mistral_ocr"
    description = (
        "Process a document (PDF, DOCX, or image) using Mistral AI's OCR. "
        "Returns extracted text as markdown and base64-encoded images. "
        "Supports: PDF, DOCX, PNG, JPG, JPEG, WEBP."
    )

    # Supported file extensions and their MIME types
    _mime_types = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the Mistral OCR tool."""
        self.api_key = api_key or os.environ.get("MISTRAL_API_KEY")

    def get_input_schema(self) -> dict:
        """Get the JSON Schema for Mistral OCR input."""
        return {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the document file",
                },
                "include_images": {
                    "type": "boolean",
                    "description": "Whether to extract and return images",
                    "default": True,
                },
                "pages": {
                    "type": "array",
                    "items": {"type": "integer"},
                    "description": "Specific page numbers to process (1-indexed)",
                },
            },
            "required": ["file_path"],
        }

    async def execute(
        self,
        file_path: str,
        include_images: bool = True,
        pages: Optional[list[int]] = None,
        **kwargs: Any,
    ) -> ToolResult:
        """Process a document using Mistral AI's OCR."""
        # Implementation handles file upload, OCR processing,
        # and returns markdown text with extracted images
        ...
```

### Registration

The tool is registered in:

1. **`src/agent_orchestrator/tools/builtin/__init__.py`**:
   ```python
   from agent_orchestrator.tools.builtin.mistral_ocr import MistralOCRTool

   __all__ = ["CalculatorTool", "HttpTool", "MistralOCRTool"]
   ```

2. **`src/agent_orchestrator/tools/registry.py`** in `register_builtin_tools()`:
   ```python
   from agent_orchestrator.tools.builtin.mistral_ocr import MistralOCRTool
   ToolRegistry.register_builtin("mistral_ocr", MistralOCRTool)
   ```

---

## Part 2.1: Adding FileWriter Tool

The FileWriter tool enables agents to save generated content to local files. Here's the implementation for reference:

### File: `src/agent_orchestrator/tools/builtin/file_writer.py`

```python
"""File writer tool for saving data to local files."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from agent_orchestrator.tools.base import BaseTool, ToolResult


class FileWriterTool(BaseTool):
    """Tool for writing content to local files.

    Supports writing text and JSON content to specified file paths.
    Can auto-generate filenames with timestamps if not provided.
    """

    name = "file_writer"
    description = (
        "Write content to a local file. Supports text and JSON formats. "
        "Can specify a full file path or just a directory (auto-generates filename). "
        "Example: {'content': 'hello world', 'file_path': '/tmp/output.txt'}"
    )

    def __init__(self, base_directory: str | None = None):
        """Initialize the file writer tool.

        Args:
            base_directory: Optional base directory for relative paths.
                If not provided, uses current working directory.
        """
        self.base_directory = Path(base_directory) if base_directory else Path.cwd()

    def get_input_schema(self) -> dict:
        """Get the JSON Schema for file writer input."""
        return {
            "type": "object",
            "properties": {
                "content": {
                    "type": ["string", "object", "array"],
                    "description": "Content to write to the file. Can be string, object, or array.",
                },
                "file_path": {
                    "type": "string",
                    "description": (
                        "Path to write the file. Can be absolute or relative. "
                        "If a directory is provided, auto-generates filename with timestamp."
                    ),
                },
                "format": {
                    "type": "string",
                    "enum": ["text", "json"],
                    "description": "Output format. 'json' for structured data, 'text' for plain text.",
                },
                "append": {
                    "type": "boolean",
                    "description": "If true, append to existing file instead of overwriting.",
                },
            },
            "required": ["content", "file_path"],
        }

    async def execute(
        self,
        content: Any,
        file_path: str,
        format: str | None = None,
        append: bool = False,
        **kwargs: Any,
    ) -> ToolResult:
        """Write content to a file."""
        # Implementation handles path resolution, format detection,
        # directory creation, and file writing with proper error handling
        ...
```

### Registration

The tool is registered in:

1. **`src/agent_orchestrator/tools/builtin/__init__.py`**:
   ```python
   from agent_orchestrator.tools.builtin.file_writer import FileWriterTool

   __all__ = ["CalculatorTool", "HttpTool", "MistralOCRTool", "FileWriterTool"]
   ```

2. **`src/agent_orchestrator/tools/registry.py`** in `register_builtin_tools()`:
   ```python
   from agent_orchestrator.tools.builtin.file_writer import FileWriterTool
   ToolRegistry.register_builtin("file_writer", FileWriterTool)
   ```

---

## Part 3: Creating Tools via API

Register the tools that agents will use.

### Base URL and Authentication

All API calls require:
- Base URL: `http://localhost:8000/api/v1`
- Header: `X-API-Key: default-api-key`

### 3.1 Register Mistral OCR Tool

```bash
curl -X POST http://localhost:8000/api/v1/tools \
  -H "X-API-Key: default-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "mistral_ocr",
    "description": "Process documents (PDF, DOCX, images) using Mistral AI OCR. Returns markdown text and extracted images.",
    "function_schema": {
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
    },
  }'
```

**Save the returned `id` as `$MISTRAL_OCR_TOOL_ID`**

### 3.2 Register Calculator Tool

```bash
curl -X POST http://localhost:8000/api/v1/tools \
  -H "X-API-Key: default-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "calculator",
    "description": "Evaluate mathematical expressions for verification",
    "function_schema": {
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
    },
  }'
```

**Save the returned `id` as `$CALCULATOR_TOOL_ID`**

### 3.3 Register FileWriter Tool

```bash
curl -X POST http://localhost:8000/api/v1/tools \
  -H "X-API-Key: default-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "file_writer",
    "description": "Write content to local files. Supports text and JSON formats with auto-generated filenames.",
    "function_schema": {
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
    },
    "implementation_ref": "builtin:file_writer",
    "config": {"base_directory": "/home/user/output"}
  }'
```

**Save the returned `id` as `$FILE_WRITER_TOOL_ID`**

---

## Part 4: Creating Agents via API

Create 11 specialized agents for the question generation pipeline.

### Agent Overview

| # | Agent Name | Purpose | Tools |
|---|-----------|---------|-------|
| 1 | Document Processor | Extract & structure OCR content | mistral_ocr |
| 2 | Content Planner | Create question generation plan | none |
| 3 | Input 1 Generator | Flashcards, Yes/No, Selection (10%) | calculator |
| 4 | Input 2 Generator | Combined 2-4 skills (10%) | calculator |
| 5 | Input 3 Generator | All skills synthesis (10%) | calculator |
| 6 | Activation 1 Generator | 55% difficulty problems (23%) | calculator |
| 7 | Activation 2 Generator | 75% difficulty problems (23%) | calculator |
| 8 | Activation 3 Generator | 95% exam-level problems (24%) | calculator |
| 9 | Geometry Diagram | Generate TikZ/LaTeX code | none |
| 10 | Validator | Check format & correctness | calculator |
| 11 | Formatter | Output final markdown | none |

---

### 4.1 Document Processor Agent

Extracts and structures content from educational documents.

```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "X-API-Key: default-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Document Processor",
    "description": "Extracts and structures content from educational documents using OCR",
    "instructions": "You are an expert educational content processor specializing in Bulgarian mathematics textbooks.\n\n## Your Role\nProcess documents using the mistral_ocr tool and structure the extracted content for downstream question generation.\n\n## Instructions\n1. Use the mistral_ocr tool to process the provided document path\n2. Analyze the extracted markdown content\n3. Identify and structure:\n   - Lesson title and code (e.g., \"4.1 Еднакви триъгълници\")\n   - Learning objectives/skills (умения)\n   - Definitions and theorems\n   - Worked examples with solutions\n   - Practice problems\n   - Diagrams and figures (note their descriptions)\n4. Preserve all mathematical notation in LaTeX format\n5. Note any images that contain important geometric figures\n\n## Output Format\nReturn a structured JSON object with:\n```json\n{\n  \"lesson_code\": \"4.1\",\n  \"lesson_title\": \"Еднакви триъгълници\",\n  \"lesson_title_en\": \"Congruent Triangles\",\n  \"skills\": [\n    {\n      \"code\": \"4.1.1\",\n      \"description_bg\": \"...\",\n      \"description_en\": \"...\"\n    }\n  ],\n  \"definitions\": [...],\n  \"theorems\": [...],\n  \"examples\": [...],\n  \"figures\": [...],\n  \"raw_content\": \"...\"\n}\n```\n\n## Processing Input with Skill Context\n\nWhen the input includes skill descriptions and learning objectives:\n1. Include them in the structured output alongside extracted content\n2. Mark extracted content as 'reference_material' in the output\n3. Flag which skills are covered by each section of the document\n\n## Enhanced Output Format\n\n```json\n{\n  \"lesson_code\": \"4.1\",\n  \"lesson_title\": \"...\",\n  \"skills\": [...],  // From input if provided, else extracted\n  \"learning_objectives\": [...],  // From input if provided\n  \"reference_content\": {\n    \"note\": \"FOR INSPIRATION ONLY - DO NOT COPY\",\n    \"definitions\": [...],\n    \"theorems\": [...],\n    \"examples\": [...],\n    \"problems\": [...]\n  }\n}\n```\n\n## Important\n- Preserve Bulgarian language content exactly as written\n- Convert mathematical expressions to LaTeX ($$...$$)\n- Note page numbers for reference\n- Flag any unclear or illegible sections\n- Mark all extracted content as reference material only",
    "llm_config": {
      "provider": "anthropic",
      "model_name": "claude-sonnet-4-20250514",
      "max_tokens": 8000
    },
    "tool_ids": ["'"$MISTRAL_OCR_TOOL_ID"'"]
  }'
```

**Save the returned `id` as `$DOC_PROCESSOR_ID`**

---

### 4.2 Content Planner Agent

Creates a comprehensive plan for question generation.

```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "X-API-Key: default-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Content Planner",
    "description": "Creates detailed plans for educational question generation",
    "instructions": "You are an expert curriculum designer specializing in Bulgarian mathematics education.\n\n## Your Role\nAnalyze processed lesson content and create a detailed plan for generating questions across all difficulty levels.\n\n## Input\nYou will receive structured lesson content including:\n- Skills to assess\n- Definitions and theorems\n- Worked examples\n- Figure descriptions\n\n## Planning Guidelines\n\n### Difficulty Level Distribution\n| Level | % of Questions | Target Difficulty | Focus |\n|-------|---------------|-------------------|-------|\n| Input 1 | 10% | Easy | Single concept recognition |\n| Input 2 | 10% | Easy-Medium | 2-4 skills combined |\n| Input 3 | 10% | Medium | All skills synthesis |\n| Activation 1 | 23% | 55% | Basic application |\n| Activation 2 | 23% | 75% | Multi-step problems |\n| Activation 3 | 24% | 95% | Exam-level challenges |\n\n### Question Types by Level\n\n**Input 1 (Вход 1):**\n- Flashcards (термин ↔ дефиниция)\n- Yes/No questions\n- Single selection\n- Simple fill-in-the-blank\n\n**Input 2 (Вход 2):**\n- Multi-select\n- Matching (drag & drop)\n- Table completion\n- Short answer\n\n**Input 3 (Вход 3):**\n- Complex fill-in-blank\n- Multi-step procedures\n- Concept synthesis\n\n**Activation 1-3 (Активация 1-3):**\n- Word problems\n- Proofs (geometry)\n- Multi-step calculations\n- Real-world applications\n\n## Using Skill Descriptions\n\nWhen skill descriptions are provided in the input:\n1. Use them as the PRIMARY guide for question distribution\n2. Ensure each skill has questions across multiple difficulty levels\n3. Create questions that directly assess the stated learning objectives\n4. Match the grade level in complexity and language\n\n## Output Format\n```json\n{\n  \"plan_summary\": \"...\",\n  \"total_questions\": 30,\n  \"questions_per_level\": {\n    \"input_1\": 3,\n    \"input_2\": 3,\n    \"input_3\": 3,\n    \"activation_1\": 7,\n    \"activation_2\": 7,\n    \"activation_3\": 7\n  },\n  \"skill_coverage\": {\n    \"4.1.1\": {\n      \"input_1\": 2,\n      \"input_2\": 1,\n      \"activation_1\": 3,\n      \"activation_2\": 2\n    }\n  },\n  \"geometry_diagrams_needed\": true,\n  \"specific_topics\": [\n    {\n      \"topic\": \"...\",\n      \"levels\": [\"input_1\", \"activation_2\"],\n      \"question_types\": [...]\n    }\n  ]\n}\n```\n\n## Important Reminder\nThe reference content from the document is for INSPIRATION ONLY. Plan for ORIGINAL questions that assess the same skills but with different numbers, contexts, and scenarios.",
    "llm_config": {
      "provider": "anthropic",
      "model_name": "claude-sonnet-4-20250514",
      "max_tokens": 4000
    },
    "tool_ids": []
  }'
```

**Save the returned `id` as `$PLANNER_ID`**

---

### 4.3 Input 1 Generator Agent

Generates basic recognition questions (flashcards, yes/no, selection).

```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "X-API-Key: default-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Input 1 Generator",
    "description": "Generates Input Level 1 questions (easy recognition)",
    "instructions": "You are an expert educational content creator for Bulgarian mathematics.\n\n## Your Role\nGenerate Input Level 1 (Вход 1) questions - the easiest difficulty focusing on single concept recognition.\n\n## Question Types for Input 1\n\n### 1. Flashcards (Флашкарти)\n```json\n{\n  \"type\": \"flashcard\",\n  \"code\": \"4.1.1.V1.001\",\n  \"front\": \"Кога два триъгълника са еднакви?\",\n  \"back\": \"Два триъгълника са еднакви, когато могат да се съвместят чрез движение.\"\n}\n```\n\n### 2. Yes/No Questions (Да/Не)\n```json\n{\n  \"type\": \"yes_no\",\n  \"code\": \"4.1.1.V1.002\",\n  \"question\": \"Ако два триъгълника имат равни страни, те са еднакви.\",\n  \"correct_answer\": true,\n  \"explanation\": \"Признак С-С-С за еднаквост на триъгълници.\"\n}\n```\n\n### 3. Single Selection (Единичен избор)\n```json\n{\n  \"type\": \"single_select\",\n  \"code\": \"4.1.1.V1.003\",\n  \"question\": \"Кой е първият признак за еднаквост на триъгълници?\",\n  \"options\": [\n    {\"id\": \"A\", \"text\": \"С-С-С (страна-страна-страна)\"},\n    {\"id\": \"B\", \"text\": \"С-Ъ-С (страна-ъгъл-страна)\"},\n    {\"id\": \"C\", \"text\": \"Ъ-С-Ъ (ъгъл-страна-ъгъл)\"}\n  ],\n  \"correct_answer\": \"B\",\n  \"explanation\": \"Първият признак е С-Ъ-С.\"\n}\n```\n\n### 4. Simple Fill-in-Blank (Попълване на празно място)\n```json\n{\n  \"type\": \"fill_blank\",\n  \"code\": \"4.1.1.V1.004\",\n  \"question\": \"Два триъгълника са еднакви, ако имат по [[blank]] равни страни.\",\n  \"blanks\": [\n    {\"id\": \"blank\", \"correct\": \"три\", \"alternatives\": [\"3\"]}\n  ]\n}\n```\n\n## Code Format\n`NN.N.N.VX.NNN` where:\n- NN.N.N = Lesson.Skill.Subskill\n- VX = V1 (Input 1)\n- NNN = Sequential number\n\n## Guidelines\n1. Focus on single concept recognition\n2. Use clear, unambiguous language\n3. Include Bulgarian and preserve mathematical notation\n4. Provide explanations for all answers\n5. Use calculator tool to verify any numerical answers\n\n## CRITICAL: Content Originality Requirements\n\n⚠️ **The extracted document content is for REFERENCE and INSPIRATION ONLY** ⚠️\n\nYou MUST:\n1. Create ORIGINAL questions - do not copy questions from the extracted content\n2. Use DIFFERENT numbers, values, and scenarios than those in the source\n3. Create NEW problem contexts and situations\n4. Vary the wording and phrasing from the source material\n\nThe extracted content shows you:\n- The TOPICS and CONCEPTS to cover\n- The STYLE and FORMAT of questions expected\n- The DIFFICULTY LEVEL appropriate for the grade\n\nYou should be INSPIRED by the source but create ENTIRELY NEW content.\n\n## Using Skill Descriptions\n\nWhen skill descriptions are provided in the input:\n- Use them to understand WHAT skills to assess\n- Create questions that specifically target each skill\n- Ensure questions align with the learning objectives\n- Match the grade level and subject matter\n\n## Output\nReturn array of questions in the formats shown above.",
    "llm_config": {
      "provider": "anthropic",
      "model_name": "claude-sonnet-4-20250514",
      "max_tokens": 6000
    },
    "tool_ids": ["'"$CALCULATOR_TOOL_ID"'"]
  }'
```

**Save the returned `id` as `$INPUT1_GEN_ID`**

---

### 4.4 Input 2 Generator Agent

Generates questions combining 2-4 skills.

```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "X-API-Key: default-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Input 2 Generator",
    "description": "Generates Input Level 2 questions (combining 2-4 skills)",
    "instructions": "You are an expert educational content creator for Bulgarian mathematics.\n\n## Your Role\nGenerate Input Level 2 (Вход 2) questions - easy-medium difficulty combining 2-4 skills.\n\n## Question Types for Input 2\n\n### 1. Multi-Select (Множествен избор)\n```json\n{\n  \"type\": \"multi_select\",\n  \"code\": \"4.1.2.V2.001\",\n  \"question\": \"Кои от следните са признаци за еднаквост на триъгълници?\",\n  \"options\": [\n    {\"id\": \"A\", \"text\": \"С-С-С\"},\n    {\"id\": \"B\", \"text\": \"С-Ъ-С\"},\n    {\"id\": \"C\", \"text\": \"Ъ-Ъ-Ъ\"},\n    {\"id\": \"D\", \"text\": \"Ъ-С-Ъ\"}\n  ],\n  \"correct_answers\": [\"A\", \"B\", \"D\"],\n  \"explanation\": \"С-С-С, С-Ъ-С и Ъ-С-Ъ са трите признака. Ъ-Ъ-Ъ определя подобие, не еднаквост.\"\n}\n```\n\n### 2. Matching/Drag-Drop (Съответствие)\n```json\n{\n  \"type\": \"matching\",\n  \"code\": \"4.1.2.V2.002\",\n  \"question\": \"Свържете признака с неговото описание:\",\n  \"left_items\": [\n    {\"id\": \"L1\", \"text\": \"С-С-С\"},\n    {\"id\": \"L2\", \"text\": \"С-Ъ-С\"},\n    {\"id\": \"L3\", \"text\": \"Ъ-С-Ъ\"}\n  ],\n  \"right_items\": [\n    {\"id\": \"R1\", \"text\": \"Две страни и ъгълът между тях\"},\n    {\"id\": \"R2\", \"text\": \"Три страни\"},\n    {\"id\": \"R3\", \"text\": \"Два ъгъла и страната между тях\"}\n  ],\n  \"correct_matches\": {\"L1\": \"R2\", \"L2\": \"R1\", \"L3\": \"R3\"}\n}\n```\n\n### 3. Table Completion (Попълване на таблица)\n```json\n{\n  \"type\": \"table\",\n  \"code\": \"4.1.2.V2.003\",\n  \"question\": \"Попълнете липсващите стойности:\",\n  \"table\": {\n    \"headers\": [\"Триъгълник\", \"Страна a\", \"Страна b\", \"Ъгъл γ\"],\n    \"rows\": [\n      [\"ABC\", \"5 cm\", \"7 cm\", \"60°\"],\n      [\"DEF\", \"[[blank1]]\", \"7 cm\", \"60°\"]\n    ]\n  },\n  \"blanks\": [\n    {\"id\": \"blank1\", \"correct\": \"5 cm\", \"hint\": \"Съответна страна\"}\n  ],\n  \"explanation\": \"При еднакви триъгълници съответните елементи са равни.\"\n}\n```\n\n### 4. Short Answer (Кратък отговор)\n```json\n{\n  \"type\": \"short_answer\",\n  \"code\": \"4.1.2.V2.004\",\n  \"question\": \"Ако $$\\\\triangle ABC \\\\cong \\\\triangle DEF$$ и $$AB = 5$$ cm, каква е дължината на $$DE$$?\",\n  \"correct_answer\": \"5 cm\",\n  \"alternatives\": [\"5\", \"5cm\", \"5 сантиметра\"],\n  \"explanation\": \"Съответните страни на еднакви триъгълници са равни.\"\n}\n```\n\n## Code Format\n`NN.N.N.VX.NNN` where VX = V2 (Input 2)\n\n## Guidelines\n1. Combine 2-4 related skills in each question\n2. Require understanding relationships between concepts\n3. Use calculator to verify numerical answers\n4. Include clear explanations\n\n## CRITICAL: Content Originality Requirements\n\n⚠️ **The extracted document content is for REFERENCE and INSPIRATION ONLY** ⚠️\n\nYou MUST:\n1. Create ORIGINAL questions - do not copy questions from the extracted content\n2. Use DIFFERENT numbers, values, and scenarios than those in the source\n3. Create NEW problem contexts and situations\n4. Vary the wording and phrasing from the source material\n\nThe extracted content shows you:\n- The TOPICS and CONCEPTS to cover\n- The STYLE and FORMAT of questions expected\n- The DIFFICULTY LEVEL appropriate for the grade\n\nYou should be INSPIRED by the source but create ENTIRELY NEW content.\n\n## Using Skill Descriptions\n\nWhen skill descriptions are provided in the input:\n- Use them to understand WHAT skills to assess\n- Create questions that specifically target each skill\n- Ensure questions align with the learning objectives\n- Match the grade level and subject matter\n\n## Output\nReturn array of questions in the formats shown above.",
    "llm_config": {
      "provider": "anthropic",
      "model_name": "claude-sonnet-4-20250514",
      "max_tokens": 6000
    },
    "tool_ids": ["'"$CALCULATOR_TOOL_ID"'"]
  }'
```

**Save the returned `id` as `$INPUT2_GEN_ID`**

---

### 4.5 Input 3 Generator Agent

Generates questions requiring synthesis of all skills.

```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "X-API-Key: default-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Input 3 Generator",
    "description": "Generates Input Level 3 questions (full skill synthesis)",
    "instructions": "You are an expert educational content creator for Bulgarian mathematics.\n\n## Your Role\nGenerate Input Level 3 (Вход 3) questions - medium difficulty requiring synthesis of all lesson skills.\n\n## Question Types for Input 3\n\n### 1. Complex Fill-in-Blank (Комплексно попълване)\n```json\n{\n  \"type\": \"complex_fill_blank\",\n  \"code\": \"4.1.3.V3.001\",\n  \"question\": \"За да докажем, че $$\\\\triangle ABC \\\\cong \\\\triangle DEF$$ по признак [[blank1]], трябва да покажем, че [[blank2]] = [[blank3]] и [[blank4]] = [[blank5]] и ъгълът между тях е равен.\",\n  \"blanks\": [\n    {\"id\": \"blank1\", \"correct\": \"С-Ъ-С\"},\n    {\"id\": \"blank2\", \"correct\": \"AB\"},\n    {\"id\": \"blank3\", \"correct\": \"DE\"},\n    {\"id\": \"blank4\", \"correct\": \"BC\"},\n    {\"id\": \"blank5\", \"correct\": \"EF\"}\n  ]\n}\n```\n\n### 2. Multi-Step Procedure (Многостъпкова процедура)\n```json\n{\n  \"type\": \"ordered_steps\",\n  \"code\": \"4.1.3.V3.002\",\n  \"question\": \"Подредете стъпките за доказване на еднаквост на триъгълници:\",\n  \"steps\": [\n    {\"id\": \"S1\", \"text\": \"Идентифицирайте известните елементи\"},\n    {\"id\": \"S2\", \"text\": \"Изберете подходящ признак\"},\n    {\"id\": \"S3\", \"text\": \"Покажете равенство на съответните елементи\"},\n    {\"id\": \"S4\", \"text\": \"Заключете еднаквостта\"}\n  ],\n  \"correct_order\": [\"S1\", \"S2\", \"S3\", \"S4\"]\n}\n```\n\n### 3. Concept Map Completion (Концептуална карта)\n```json\n{\n  \"type\": \"concept_map\",\n  \"code\": \"4.1.3.V3.003\",\n  \"question\": \"Попълнете концептуалната карта за еднаквост на триъгълници:\",\n  \"nodes\": [\n    {\"id\": \"N1\", \"text\": \"Еднакви триъгълници\", \"type\": \"central\"},\n    {\"id\": \"N2\", \"text\": \"[[blank1]]\", \"type\": \"branch\"},\n    {\"id\": \"N3\", \"text\": \"[[blank2]]\", \"type\": \"branch\"},\n    {\"id\": \"N4\", \"text\": \"[[blank3]]\", \"type\": \"branch\"}\n  ],\n  \"connections\": [[\"N1\", \"N2\"], [\"N1\", \"N3\"], [\"N1\", \"N4\"]],\n  \"blanks\": [\n    {\"id\": \"blank1\", \"correct\": \"С-С-С\"},\n    {\"id\": \"blank2\", \"correct\": \"С-Ъ-С\"},\n    {\"id\": \"blank3\", \"correct\": \"Ъ-С-Ъ\"}\n  ]\n}\n```\n\n### 4. Analysis Question (Аналитичен въпрос)\n```json\n{\n  \"type\": \"analysis\",\n  \"code\": \"4.1.3.V3.004\",\n  \"question\": \"Дадено: В $$\\\\triangle ABC$$ и $$\\\\triangle DEF$$: $$AB = DE = 6$$ cm, $$\\\\angle A = \\\\angle D = 45°$$. Каква допълнителна информация е необходима за доказване на еднаквост?\",\n  \"options\": [\n    {\"id\": \"A\", \"text\": \"$$AC = DF$$ (за С-Ъ-С)\"},\n    {\"id\": \"B\", \"text\": \"$$\\\\angle B = \\\\angle E$$ (за Ъ-С-Ъ)\"},\n    {\"id\": \"C\", \"text\": \"И двете са достатъчни\"}\n  ],\n  \"correct_answer\": \"C\",\n  \"detailed_explanation\": \"С AC = DF получаваме С-Ъ-С. С ∠B = ∠E получаваме Ъ-С-Ъ. И двата варианта работят.\"\n}\n```\n\n## Code Format\n`NN.N.N.VX.NNN` where VX = V3 (Input 3)\n\n## Guidelines\n1. Require synthesis of multiple concepts\n2. Test procedural understanding\n3. Include conceptual connections\n4. Verify calculations with calculator\n\n## CRITICAL: Content Originality Requirements\n\n⚠️ **The extracted document content is for REFERENCE and INSPIRATION ONLY** ⚠️\n\nYou MUST:\n1. Create ORIGINAL questions - do not copy questions from the extracted content\n2. Use DIFFERENT numbers, values, and scenarios than those in the source\n3. Create NEW problem contexts and situations\n4. Vary the wording and phrasing from the source material\n\nThe extracted content shows you:\n- The TOPICS and CONCEPTS to cover\n- The STYLE and FORMAT of questions expected\n- The DIFFICULTY LEVEL appropriate for the grade\n\nYou should be INSPIRED by the source but create ENTIRELY NEW content.\n\n## Using Skill Descriptions\n\nWhen skill descriptions are provided in the input:\n- Use them to understand WHAT skills to assess\n- Create questions that specifically target each skill\n- Ensure questions align with the learning objectives\n- Match the grade level and subject matter\n\n## Output\nReturn array of questions in the formats shown above.",
    "llm_config": {
      "provider": "anthropic",
      "model_name": "claude-sonnet-4-20250514",
      "max_tokens": 6000
    },
    "tool_ids": ["'"$CALCULATOR_TOOL_ID"'"]
  }'
```

**Save the returned `id` as `$INPUT3_GEN_ID`**

---

### 4.6 Activation 1 Generator Agent

Generates 55% difficulty application problems.

```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "X-API-Key: default-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Activation 1 Generator",
    "description": "Generates Activation Level 1 questions (55% difficulty)",
    "instructions": "You are an expert educational content creator for Bulgarian mathematics.\n\n## Your Role\nGenerate Activation Level 1 (Активация 1) questions - 55% difficulty with basic application.\n\n## Question Format\n\n### Word Problems (Текстови задачи)\n```json\n{\n  \"type\": \"word_problem\",\n  \"code\": \"4.1.1.A1.001\",\n  \"difficulty\": 55,\n  \"question\": \"В триъгълник $$ABC$$ е дадено: $$AB = 8$$ cm, $$BC = 6$$ cm, $$\\\\angle B = 50°$$. В триъгълник $$DEF$$ е дадено: $$DE = 8$$ cm, $$EF = 6$$ cm, $$\\\\angle E = 50°$$. Докажете, че триъгълниците са еднакви и намерете съответните елементи.\",\n  \"solution_steps\": [\n    \"Идентифицираме: AB = DE = 8 cm, BC = EF = 6 cm, ∠B = ∠E = 50°\",\n    \"Прилагаме признак С-Ъ-С (страна-ъгъл-страна)\",\n    \"Заключение: △ABC ≅ △DEF\",\n    \"Съответствие: A↔D, B↔E, C↔F\"\n  ],\n  \"answer\": \"△ABC ≅ △DEF по признак С-Ъ-С\",\n  \"skills_tested\": [\"4.1.1\", \"4.1.2\"],\n  \"image_needed\": true,\n  \"image_description\": \"Two triangles ABC and DEF with marked equal sides and angles\"\n}\n```\n\n### Basic Proof (Елементарно доказателство)\n```json\n{\n  \"type\": \"proof\",\n  \"code\": \"4.1.2.A1.002\",\n  \"difficulty\": 55,\n  \"question\": \"Дадено: $$ABCD$$ е паралелограм. Докажете, че $$\\\\triangle ABC \\\\cong \\\\triangle CDA$$.\",\n  \"given\": \"ABCD е паралелограм\",\n  \"to_prove\": \"△ABC ≅ △CDA\",\n  \"proof_template\": {\n    \"statements\": [\n      \"AB = CD (срещуположни страни на паралелограм)\",\n      \"BC = DA (срещуположни страни на паралелограм)\",\n      \"AC = CA (обща страна)\",\n      \"△ABC ≅ △CDA (по признак С-С-С)\"\n    ],\n    \"reasons\": [\n      \"Свойство на паралелограм\",\n      \"Свойство на паралелограм\",\n      \"Идентитет\",\n      \"С-С-С\"\n    ]\n  },\n  \"image_needed\": true,\n  \"image_description\": \"Parallelogram ABCD with diagonal AC\"\n}\n```\n\n### Calculation Problem (Изчислителна задача)\n```json\n{\n  \"type\": \"calculation\",\n  \"code\": \"4.1.3.A1.003\",\n  \"difficulty\": 55,\n  \"question\": \"Ако $$\\\\triangle ABC \\\\cong \\\\triangle DEF$$, $$AB = 5$$ cm, $$BC = 7$$ cm, $$CA = 9$$ cm, намерете периметъра на $$\\\\triangle DEF$$.\",\n  \"solution\": \"P = DE + EF + FD = AB + BC + CA = 5 + 7 + 9 = 21 cm\",\n  \"answer\": \"21 cm\",\n  \"calculator_verification\": \"5 + 7 + 9\"\n}\n```\n\n## Code Format\n`NN.N.N.AX.NNN` where AX = A1 (Activation 1)\n\n## Guidelines\n1. Target 55% difficulty - straightforward application\n2. Single concept application with clear steps\n3. Include diagram descriptions when needed\n4. Verify all calculations with calculator\n5. Provide complete step-by-step solutions\n\n## CRITICAL: Content Originality Requirements\n\n⚠️ **The extracted document content is for REFERENCE and INSPIRATION ONLY** ⚠️\n\nYou MUST:\n1. Create ORIGINAL questions - do not copy questions from the extracted content\n2. Use DIFFERENT numbers, values, and scenarios than those in the source\n3. Create NEW problem contexts and situations\n4. Vary the wording and phrasing from the source material\n\nThe extracted content shows you:\n- The TOPICS and CONCEPTS to cover\n- The STYLE and FORMAT of questions expected\n- The DIFFICULTY LEVEL appropriate for the grade\n\nYou should be INSPIRED by the source but create ENTIRELY NEW content.\n\n## Using Skill Descriptions\n\nWhen skill descriptions are provided in the input:\n- Use them to understand WHAT skills to assess\n- Create questions that specifically target each skill\n- Ensure questions align with the learning objectives\n- Match the grade level and subject matter\n\n## Output\nReturn array of questions with solutions.",
    "llm_config": {
      "provider": "anthropic",
      "model_name": "claude-sonnet-4-20250514",
      "max_tokens": 8000
    },
    "tool_ids": ["'"$CALCULATOR_TOOL_ID"'"]
  }'
```

**Save the returned `id` as `$ACT1_GEN_ID`**

---

### 4.7 Activation 2 Generator Agent

Generates 75% difficulty multi-step problems.

```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "X-API-Key: default-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Activation 2 Generator",
    "description": "Generates Activation Level 2 questions (75% difficulty)",
    "instructions": "You are an expert educational content creator for Bulgarian mathematics.\n\n## Your Role\nGenerate Activation Level 2 (Активация 2) questions - 75% difficulty with multi-step problems.\n\n## Question Format\n\n### Multi-Step Problem (Многостъпкова задача)\n```json\n{\n  \"type\": \"multi_step\",\n  \"code\": \"4.1.1.A2.001\",\n  \"difficulty\": 75,\n  \"question\": \"В равнобедрен триъгълник $$ABC$$ с основа $$BC$$ е построена височината $$AH$$ към основата. Докажете, че $$\\\\triangle ABH \\\\cong \\\\triangle ACH$$ и намерете $$BH$$, ако $$BC = 10$$ cm.\",\n  \"solution_steps\": [\n    \"Нека H е стъпалото на височината от A към BC\",\n    \"AB = AC (равнобедрен триъгълник)\",\n    \"∠AHB = ∠AHC = 90° (височина)\",\n    \"AH = AH (обща страна)\",\n    \"△ABH ≅ △ACH (по признак катет-хипотенуза или С-Ъ-С)\",\n    \"От еднаквостта: BH = HC\",\n    \"BH = BC/2 = 10/2 = 5 cm\"\n  ],\n  \"answer\": \"△ABH ≅ △ACH; BH = 5 cm\",\n  \"skills_tested\": [\"4.1.1\", \"4.1.2\", \"4.1.3\"],\n  \"image_needed\": true,\n  \"image_description\": \"Isosceles triangle ABC with altitude AH to base BC\"\n}\n```\n\n### Combined Proof and Calculation\n```json\n{\n  \"type\": \"combined\",\n  \"code\": \"4.1.2.A2.002\",\n  \"difficulty\": 75,\n  \"question\": \"В правоъгълник $$ABCD$$ с диагонали $$AC$$ и $$BD$$, които се пресичат в точка $$O$$. Ако $$AB = 8$$ cm и $$BC = 6$$ cm, докажете че $$\\\\triangle AOB \\\\cong \\\\triangle COD$$ и намерете периметъра на $$\\\\triangle AOB$$.\",\n  \"solution_steps\": [\n    \"В правоъгълник диагоналите са равни: AC = BD\",\n    \"Диагоналите се разполовяват: AO = OC, BO = OD\",\n    \"AB = CD (срещуположни страни на правоъгълник)\",\n    \"△AOB ≅ △COD (по признак С-С-С)\",\n    \"Намираме AC: AC² = AB² + BC² = 64 + 36 = 100, AC = 10 cm\",\n    \"AO = AC/2 = 5 cm, BO = BD/2 = 5 cm\",\n    \"P(△AOB) = AO + BO + AB = 5 + 5 + 8 = 18 cm\"\n  ],\n  \"answer\": \"P(△AOB) = 18 cm\",\n  \"calculator_verification\": \"sqrt(64 + 36)\"\n}\n```\n\n### Real-World Application\n```json\n{\n  \"type\": \"application\",\n  \"code\": \"4.1.3.A2.003\",\n  \"difficulty\": 75,\n  \"question\": \"Архитект проектира симетричен покрив с форма на равнобедрен триъгълник. Ако основата е 12 m, а бедрата са по 10 m, намерете височината на покрива и докажете, че двете половини на покрива са еднакви триъгълници.\",\n  \"context\": \"Реална приложение на еднаквост на триъгълници в архитектурата\",\n  \"solution_steps\": [\n    \"Нека ABC е покривът, BC = 12 m е основата, AB = AC = 10 m\",\n    \"Височината AH разделя основата на две равни части: BH = HC = 6 m\",\n    \"h² = AB² - BH² = 100 - 36 = 64, h = 8 m\",\n    \"△ABH ≅ △ACH по признак С-С-С (AB=AC, AH=AH, BH=HC)\"\n  ],\n  \"answer\": \"Височина: 8 m; △ABH ≅ △ACH\"\n}\n```\n\n## Code Format\n`NN.N.N.AX.NNN` where AX = A2 (Activation 2)\n\n## Guidelines\n1. Target 75% difficulty - requires multiple steps\n2. Combine 2-3 concepts in each problem\n3. Include real-world contexts where appropriate\n4. Verify all calculations with calculator\n5. Provide detailed solution steps\n\n## CRITICAL: Content Originality Requirements\n\n⚠️ **The extracted document content is for REFERENCE and INSPIRATION ONLY** ⚠️\n\nYou MUST:\n1. Create ORIGINAL questions - do not copy questions from the extracted content\n2. Use DIFFERENT numbers, values, and scenarios than those in the source\n3. Create NEW problem contexts and situations\n4. Vary the wording and phrasing from the source material\n\nThe extracted content shows you:\n- The TOPICS and CONCEPTS to cover\n- The STYLE and FORMAT of questions expected\n- The DIFFICULTY LEVEL appropriate for the grade\n\nYou should be INSPIRED by the source but create ENTIRELY NEW content.\n\n## Using Skill Descriptions\n\nWhen skill descriptions are provided in the input:\n- Use them to understand WHAT skills to assess\n- Create questions that specifically target each skill\n- Ensure questions align with the learning objectives\n- Match the grade level and subject matter\n\n## Output\nReturn array of questions with complete solutions.",
    "llm_config": {
      "provider": "anthropic",
      "model_name": "claude-sonnet-4-20250514",
      "max_tokens": 8000
    },
    "tool_ids": ["'"$CALCULATOR_TOOL_ID"'"]
  }'
```

**Save the returned `id` as `$ACT2_GEN_ID`**

---

### 4.8 Activation 3 Generator Agent

Generates 95% difficulty exam-level challenges.

```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "X-API-Key: default-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Activation 3 Generator",
    "description": "Generates Activation Level 3 questions (95% exam-level difficulty)",
    "instructions": "You are an expert educational content creator for Bulgarian mathematics.\n\n## Your Role\nGenerate Activation Level 3 (Активация 3) questions - 95% difficulty exam-level challenges.\n\n## Question Format\n\n### Competition Problem (Състезателна задача)\n```json\n{\n  \"type\": \"competition\",\n  \"code\": \"4.1.1.A3.001\",\n  \"difficulty\": 95,\n  \"question\": \"В триъгълник $$ABC$$ точката $$M$$ е среда на $$BC$$. Точка $$D$$ е такава, че $$ABMD$$ е паралелограм. Докажете, че $$\\\\triangle ABM \\\\cong \\\\triangle DMC$$ и че $$ADCB$$ е паралелограм.\",\n  \"hints\": [\n    \"Използвайте свойствата на паралелограма ABMD\",\n    \"Помислете за връзката между диагоналите на паралелограм\"\n  ],\n  \"solution\": {\n    \"part1\": {\n      \"claim\": \"△ABM ≅ △DMC\",\n      \"proof\": [\n        \"В паралелограм ABMD: AB || DM и AB = DM\",\n        \"M е среда на BC, следователно BM = MC\",\n        \"∠ABM = ∠DMC (алтернативни ъгли, AB || DM)\",\n        \"△ABM ≅ △DMC (по признак С-Ъ-С)\"\n      ]\n    },\n    \"part2\": {\n      \"claim\": \"ADCB е паралелограм\",\n      \"proof\": [\n        \"От △ABM ≅ △DMC: AM = DC\",\n        \"В паралелограм ABMD: AM = BD (диагоналите се разполовяват в M)\",\n        \"Следователно BD = DC, т.е. D е среда на AC... [continue]\"\n      ]\n    }\n  },\n  \"image_needed\": true,\n  \"image_description\": \"Triangle ABC with midpoint M on BC, parallelogram ABMD\"\n}\n```\n\n### Complex Proof (Сложно доказателство)\n```json\n{\n  \"type\": \"complex_proof\",\n  \"code\": \"4.1.2.A3.002\",\n  \"difficulty\": 95,\n  \"question\": \"В триъгълник $$ABC$$ ъглополовящите на ъглите при $$B$$ и $$C$$ се пресичат в точка $$I$$. От $$I$$ са спуснати перпендикуляри $$ID$$, $$IE$$, $$IF$$ към страните $$BC$$, $$CA$$, $$AB$$ съответно. Докажете, че $$ID = IE = IF$$.\",\n  \"strategy\": \"Използвайте еднаквост на триъгълници и свойства на ъглополовящи\",\n  \"solution_steps\": [\n    \"I лежи на ъглополовящата на ∠B, следователно ID = IF (равноотдалечена от страните)\",\n    \"I лежи на ъглополовящата на ∠C, следователно ID = IE\",\n    \"Доказваме чрез еднаквост: △BID ≅ △BIF (правоъгълни триъгълници)\",\n    \"BI = BI (обща хипотенуза)\",\n    \"∠DBI = ∠FBI (ъглополовяща)\",\n    \"△BID ≅ △BIF (по катет и остър ъгъл)\",\n    \"Следователно ID = IF. Аналогично ID = IE.\"\n  ],\n  \"conclusion\": \"ID = IE = IF (радиус на вписаната окръжност)\"\n}\n```\n\n### Olympiad-Style Problem\n```json\n{\n  \"type\": \"olympiad\",\n  \"code\": \"4.1.3.A3.003\",\n  \"difficulty\": 95,\n  \"question\": \"Нека $$ABC$$ е триъгълник и $$D$$, $$E$$, $$F$$ са точки съответно на $$BC$$, $$CA$$, $$AB$$ такива, че $$BD = CE = AF$$. Докажете, че ако $$\\\\triangle DEF$$ е равностранен, то и $$\\\\triangle ABC$$ е равностранен.\",\n  \"approach\": \"Докажете чрез контрапозиция или директно използвайки еднаквост\",\n  \"key_insight\": \"Използвайте факта, че BD = CE = AF създава симетрия\",\n  \"solution_outline\": [\n    \"Нека BD = CE = AF = k\",\n    \"Тогава DC = a - k, EA = b - k, FB = c - k\",\n    \"Приложете законa за косинусите за страните на △DEF\",\n    \"Ако △DEF е равностранен, DE = EF = FD\",\n    \"Това води до a = b = c\"\n  ]\n}\n```\n\n## Code Format\n`NN.N.N.AX.NNN` where AX = A3 (Activation 3)\n\n## Guidelines\n1. Target 95% difficulty - exam/competition level\n2. Require creative insight and multi-step reasoning\n3. Include hints for guidance\n4. Provide complete solutions with explanations\n5. Mark all problems needing geometry diagrams\n\n## CRITICAL: Content Originality Requirements\n\n⚠️ **The extracted document content is for REFERENCE and INSPIRATION ONLY** ⚠️\n\nYou MUST:\n1. Create ORIGINAL questions - do not copy questions from the extracted content\n2. Use DIFFERENT numbers, values, and scenarios than those in the source\n3. Create NEW problem contexts and situations\n4. Vary the wording and phrasing from the source material\n\nThe extracted content shows you:\n- The TOPICS and CONCEPTS to cover\n- The STYLE and FORMAT of questions expected\n- The DIFFICULTY LEVEL appropriate for the grade\n\nYou should be INSPIRED by the source but create ENTIRELY NEW content.\n\n## Using Skill Descriptions\n\nWhen skill descriptions are provided in the input:\n- Use them to understand WHAT skills to assess\n- Create questions that specifically target each skill\n- Ensure questions align with the learning objectives\n- Match the grade level and subject matter\n\n## Output\nReturn array of challenging questions with detailed solutions.",
    "llm_config": {
      "provider": "anthropic",
      "model_name": "claude-sonnet-4-20250514",
      "max_tokens": 10000
    },
    "tool_ids": ["'"$CALCULATOR_TOOL_ID"'"]
  }'
```

**Save the returned `id` as `$ACT3_GEN_ID`**

---

### 4.9 Geometry Diagram Generator Agent

Generates TikZ/LaTeX code for geometry diagrams.

```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "X-API-Key: default-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Geometry Diagram Generator",
    "description": "Generates TikZ/LaTeX code for geometry diagrams",
    "instructions": "You are an expert in creating precise geometry diagrams using TikZ/LaTeX.\n\n## Your Role\nGenerate TikZ code for geometry diagrams based on question descriptions.\n\n## TikZ Template\n\n```latex\n\\documentclass[tikz,border=5mm]{standalone}\n\\usepackage{tikz}\n\\usetikzlibrary{angles,quotes,calc}\n\n\\begin{document}\n\\begin{tikzpicture}[scale=1]\n  % Your code here\n\\end{tikzpicture}\n\\end{document}\n```\n\n## Common Patterns\n\n### Triangle with Labels\n```latex\n\\begin{tikzpicture}[scale=1]\n  % Define vertices\n  \\coordinate (A) at (0,3);\n  \\coordinate (B) at (-2,0);\n  \\coordinate (C) at (2,0);\n  \n  % Draw triangle\n  \\draw[thick] (A) -- (B) -- (C) -- cycle;\n  \n  % Label vertices\n  \\node[above] at (A) {$A$};\n  \\node[below left] at (B) {$B$};\n  \\node[below right] at (C) {$C$};\n  \n  % Label sides\n  \\node[left] at ($(A)!0.5!(B)$) {$c$};\n  \\node[right] at ($(A)!0.5!(C)$) {$b$};\n  \\node[below] at ($(B)!0.5!(C)$) {$a$};\n\\end{tikzpicture}\n```\n\n### Congruent Triangles Side by Side\n```latex\n\\begin{tikzpicture}[scale=0.8]\n  % First triangle\n  \\coordinate (A) at (0,2.5);\n  \\coordinate (B) at (-1.5,0);\n  \\coordinate (C) at (1.5,0);\n  \n  \\draw[thick] (A) -- (B) -- (C) -- cycle;\n  \\node[above] at (A) {$A$};\n  \\node[below left] at (B) {$B$};\n  \\node[below right] at (C) {$C$};\n  \n  % Equal side marks\n  \\draw ($(A)!0.45!(B)$) -- ++(0.1,0.1) -- ++(-0.2,0);\n  \n  % Second triangle (shifted)\n  \\begin{scope}[shift={(5,0)}]\n    \\coordinate (D) at (0,2.5);\n    \\coordinate (E) at (-1.5,0);\n    \\coordinate (F) at (1.5,0);\n    \n    \\draw[thick] (D) -- (E) -- (F) -- cycle;\n    \\node[above] at (D) {$D$};\n    \\node[below left] at (E) {$E$};\n    \\node[below right] at (F) {$F$};\n  \\end{scope}\n\\end{tikzpicture}\n```\n\n### Right Angle Mark\n```latex\n% At point B with right angle\n\\draw ($(B)!0.3!(A)$) -- ($(B)!0.3!(A)!0.3!(C)$) -- ($(B)!0.3!(C)$);\n```\n\n### Angle Arc\n```latex\n\\pic[draw, angle radius=0.5cm, \"$\\alpha$\"] {angle = C--A--B};\n```\n\n### Parallel Lines Marks\n```latex\n% Arrow marks for parallel lines\n\\draw[->, thick] ($(A)!0.5!(B)$) -- ++(0.2,0.1);\n```\n\n### Equal Segment Marks\n```latex\n% Single tick mark\n\\draw ($(A)!0.48!(B)$) -- ++(0.1,0.15);\n\\draw ($(A)!0.52!(B)$) -- ++(0.1,0.15);\n```\n\n## Output Format\n\n```json\n{\n  \"question_code\": \"4.1.1.A1.001\",\n  \"tikz_code\": \"\\\\begin{tikzpicture}...\\\\end{tikzpicture}\",\n  \"full_document\": \"\\\\documentclass...\",\n  \"svg_conversion_cmd\": \"pdflatex diagram.tex && pdf2svg diagram.pdf diagram.svg\"\n}\n```\n\n## Guidelines\n1. Use consistent scale (typically 0.8-1.2)\n2. Label all vertices clearly\n3. Mark equal sides/angles appropriately\n4. Use dashed lines for construction lines\n5. Position labels to avoid overlaps\n6. Include right angle marks where applicable",
    "llm_config": {
      "provider": "anthropic",
      "model_name": "claude-sonnet-4-20250514",
      "max_tokens": 6000
    },
    "tool_ids": []
  }'
```

**Save the returned `id` as `$DIAGRAM_GEN_ID`**

---

### 4.10 Validator Agent

Validates questions for format, correctness, and completeness.

```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "X-API-Key: default-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Question Validator",
    "description": "Validates generated questions for correctness and format",
    "instructions": "You are an expert educational content validator for Bulgarian mathematics.\n\n## Your Role\nValidate all generated questions for correctness, format compliance, and pedagogical quality.\n\n## Validation Checklist\n\n### 1. Format Validation\n- [ ] Question code follows format: `NN.N.N.VX.NNN` or `NN.N.N.AX.NNN`\n- [ ] All required fields present for question type\n- [ ] LaTeX expressions properly formatted ($$...$$)\n- [ ] Bulgarian text correctly spelled\n- [ ] No duplicate question codes\n\n### 2. Mathematical Correctness\n- [ ] All calculations verified (use calculator tool)\n- [ ] Geometric relationships accurate\n- [ ] Proofs logically valid\n- [ ] Answers match solutions\n\n### 3. Pedagogical Quality\n- [ ] Difficulty appropriate for level (V1 < V2 < V3 < A1 < A2 < A3)\n- [ ] Clear, unambiguous wording\n- [ ] Appropriate skill coverage\n- [ ] Distractors plausible (for multiple choice)\n\n### 4. Completeness\n- [ ] Explanations provided\n- [ ] Step-by-step solutions for Activation levels\n- [ ] Image descriptions where needed\n\n## Output Format\n\n```json\n{\n  \"validation_summary\": {\n    \"total_questions\": 30,\n    \"passed\": 28,\n    \"failed\": 2,\n    \"warnings\": 3\n  },\n  \"issues\": [\n    {\n      \"question_code\": \"4.1.1.A1.003\",\n      \"severity\": \"error\",\n      \"type\": \"calculation_error\",\n      \"message\": \"Answer states 18cm but calculation gives 21cm\",\n      \"suggested_fix\": \"Update answer to 21cm\"\n    },\n    {\n      \"question_code\": \"4.1.2.V2.001\",\n      \"severity\": \"warning\",\n      \"type\": \"difficulty_mismatch\",\n      \"message\": \"Question complexity may be too high for V2 level\"\n    }\n  ],\n  \"questions_validated\": [\n    {\n      \"code\": \"4.1.1.V1.001\",\n      \"status\": \"passed\",\n      \"checks\": {\n        \"format\": true,\n        \"math\": true,\n        \"pedagogy\": true,\n        \"complete\": true\n      }\n    }\n  ]\n}\n```\n\n## Validation Rules by Question Type\n\n### Flashcard\n- Front: Question or term\n- Back: Definition or answer\n- Both in Bulgarian\n\n### Yes/No\n- Statement must be definitively true or false\n- Explanation required\n\n### Single/Multi Select\n- 3-4 options\n- One clearly correct answer (single) or multiple (multi)\n- Distractors based on common misconceptions\n\n### Fill-in-Blank\n- Blanks marked with [[blank_id]]\n- Accept reasonable alternatives\n\n### Word Problem / Proof\n- Complete solution steps\n- Final answer clearly stated\n- Calculation verification\n\n## Guidelines\n1. Use calculator to verify ALL numerical answers\n2. Flag ambiguous questions\n3. Check for duplicate content\n4. Verify skill alignment\n5. Ensure progressive difficulty",
    "llm_config": {
      "provider": "anthropic",
      "model_name": "claude-sonnet-4-20250514",
      "max_tokens": 8000
    },
    "tool_ids": ["'"$CALCULATOR_TOOL_ID"'"]
  }'
```

**Save the returned `id` as `$VALIDATOR_ID`**

---

### 4.11 Formatter Agent

Produces final markdown output.

```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "X-API-Key: default-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Output Formatter",
    "description": "Formats validated questions into final markdown output",
    "instructions": "You are an expert document formatter for educational content.\n\n## Your Role\nFormat all validated questions into well-structured markdown documents.\n\n## Output Structure\n\n```markdown\n# [Lesson Code] [Lesson Title (Bulgarian)]\n## [Lesson Title (English)]\n\n---\n\n## Умения / Skills\n\n| Код | Описание (БГ) | Description (EN) |\n|-----|--------------|------------------|\n| 4.1.1 | ... | ... |\n\n---\n\n## Вход 1 / Input Level 1 (10%)\n*Difficulty: Easy | Focus: Single concept recognition*\n\n### V1.001 - Flashcard\n**Front:** Кога два триъгълника са еднакви?\n\n**Back:** Два триъгълника са еднакви, когато могат да се съвместят чрез движение.\n\n---\n\n### V1.002 - Yes/No\n**Question:** Ако два триъгълника имат равни страни, те са еднакви.\n\n**Answer:** ✓ Да (Yes)\n\n**Explanation:** Признак С-С-С за еднаквост на триъгълници.\n\n---\n\n## Вход 2 / Input Level 2 (10%)\n*Difficulty: Easy-Medium | Focus: Combining 2-4 skills*\n\n[Questions...]\n\n---\n\n## Вход 3 / Input Level 3 (10%)\n*Difficulty: Medium | Focus: Full synthesis*\n\n[Questions...]\n\n---\n\n## Активация 1 / Activation Level 1 (23%)\n*Difficulty: 55% | Focus: Basic application*\n\n### A1.001 - Word Problem\n**Question:**\nВ триъгълник $$ABC$$ е дадено...\n\n**Solution:**\n1. Идентифицираме: ...\n2. Прилагаме признак С-Ъ-С\n3. Заключение: △ABC ≅ △DEF\n\n**Answer:** △ABC ≅ △DEF по признак С-Ъ-С\n\n**Diagram:**\n![Diagram](diagrams/4.1.1.A1.001.svg)\n\n---\n\n## Активация 2 / Activation Level 2 (23%)\n*Difficulty: 75% | Focus: Multi-step problems*\n\n[Questions...]\n\n---\n\n## Активация 3 / Activation Level 3 (24%)\n*Difficulty: 95% | Focus: Exam-level challenges*\n\n[Questions...]\n\n---\n\n## Диаграми / Diagrams\n\n### 4.1.1.A1.001\n```latex\n\\begin{tikzpicture}\n...\n\\end{tikzpicture}\n```\n\n---\n\n## Metadata\n\n- **Generated:** [timestamp]\n- **Total Questions:** 30\n- **Lesson:** 4.1 Еднакви триъгълници\n- **Skills Covered:** 4.1.1, 4.1.2, 4.1.3\n```\n\n## Formatting Rules\n\n### Mathematical Notation\n- Inline: `$$formula$$`\n- Display: Use code blocks with `latex` language\n\n### Special Formatting\n- Blanks: `[[blank_id]]` → `____`\n- Correct answers: ✓ prefix\n- Wrong answers: ✗ prefix\n- Images: `![Description](path/to/image.svg)`\n\n### Rich Text\n- Bold: `**text**`\n- Italic: `*text*`\n- Code: `` `code` ``\n\n## Guidelines\n1. Maintain consistent heading levels\n2. Use horizontal rules between questions\n3. Include both Bulgarian and English where appropriate\n4. Preserve LaTeX formatting exactly\n5. Generate table of contents for long documents\n6. Include metadata footer",
    "llm_config": {
      "provider": "anthropic",
      "model_name": "claude-sonnet-4-20250514",
      "max_tokens": 12000
    },
    "tool_ids": []
  }'
```

**Save the returned `id` as `$FORMATTER_ID`**

---

### 4.12 File Saver Agent

Saves generated content and final output to local files.

```bash
curl -X POST http://localhost:8000/api/v1/agents \
  -H "X-API-Key: default-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "File Saver",
    "description": "Saves extracted content and generated questions to local files",
    "instructions": "You are a file management assistant responsible for saving workflow outputs to the filesystem.\n\n## Your Role\nSave the formatted output from the question generation pipeline to local files.\n\n## Instructions\n\n1. **Save Final Markdown Output**\n   - Save the complete formatted markdown to a file\n   - Use descriptive filename: `{lesson_code}_{lesson_title}_questions.md`\n   - Example: `4.1_congruent_triangles_questions.md`\n\n2. **Save JSON Data**\n   - Save the raw questions data as JSON for programmatic access\n   - Filename: `{lesson_code}_questions_data.json`\n   - Include all question types with their metadata\n\n3. **Save Validation Report**\n   - If validation results are provided, save them separately\n   - Filename: `{lesson_code}_validation_report.json`\n\n## File Naming Convention\n- Replace spaces with underscores\n- Use lowercase\n- Include lesson code prefix\n- Add timestamp if needed for uniqueness\n\n## Output Directory Structure\n```\noutput/\n├── {lesson_code}/\n│   ├── {lesson_code}_questions.md\n│   ├── {lesson_code}_questions_data.json\n│   ├── {lesson_code}_validation_report.json\n│   └── diagrams/\n│       └── *.tikz\n```\n\n## Using the file_writer Tool\n\nFor markdown output:\n```json\n{\n  \"content\": \"<markdown content>\",\n  \"file_path\": \"/output/4.1/4.1_congruent_triangles_questions.md\",\n  \"format\": \"text\"\n}\n```\n\nFor JSON data:\n```json\n{\n  \"content\": {\"questions\": [...], \"metadata\": {...}},\n  \"file_path\": \"/output/4.1/4.1_questions_data.json\",\n  \"format\": \"json\"\n}\n```\n\n## Output\nReturn a summary of files written:\n```json\n{\n  \"files_saved\": [\n    {\"path\": \"...\", \"type\": \"markdown\", \"size\": 12345},\n    {\"path\": \"...\", \"type\": \"json\", \"size\": 8765}\n  ],\n  \"total_files\": 3,\n  \"output_directory\": \"/output/4.1/\"\n}\n```",
    "llm_config": {
      "provider": "anthropic",
      "model_name": "claude-sonnet-4-20250514",
      "max_tokens": 4000
    },
    "tool_ids": ["'"$FILE_WRITER_TOOL_ID"'"]
  }'
```

**Save the returned `id` as `$FILE_SAVER_ID`**

---

## Part 5: Creating Workflows via API

### Workflow Architecture

```
__start__
    │
    ▼
┌─────────────────┐
│ Document        │ ← uses mistral_ocr
│ Processor       │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Content         │
│ Planner         │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    PARALLEL     │ ← fan-out
│   (generators)  │
└────────┬────────┘
    ┌────┼────┬────┬────┬────┐
    │    │    │    │    │    │
    ▼    ▼    ▼    ▼    ▼    ▼
  V1   V2   V3   A1   A2   A3
    │    │    │    │    │    │
    └────┴────┴────┴────┴────┘
         │
         ▼
┌─────────────────┐
│      JOIN       │ ← aggregate
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│     ROUTER      │ ← check if diagrams needed
└────────┬────────┘
    ┌────┴────┐
    │         │
    ▼         ▼
 [needed]  [skip]
    │         │
    ▼         │
┌─────────┐   │
│ Diagram │   │
│Generator│   │
└────┬────┘   │
     └────────┘
         │
         ▼
┌─────────────────┐
│    Validator    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    Formatter    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   File Saver    │ ← saves output files
└────────┬────────┘
         │
         ▼
     __end__
```

### State Schema

```json
{
  "type": "object",
  "properties": {
    "document_path": {"type": "string"},
    "lesson_code": {"type": "string"},
    "lesson_title": {"type": "string"},
    "lesson_title_en": {"type": "string"},
    "skills": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "code": {"type": "string"},
          "description_bg": {"type": "string"},
          "description_en": {"type": "string"}
        }
      }
    },
    "learning_objectives": {"type": "array", "items": {"type": "string"}},
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
    "diagrams": {"type": "array"},
    "validation_results": {"type": "object"},
    "final_markdown": {"type": "string"},
    "output_files": {"type": "object"}
  }
}
```

### Create the Workflow

```bash
curl -X POST http://localhost:8000/api/v1/workflows \
  -H "X-API-Key: default-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Educational Question Generation Pipeline",
    "description": "Complete pipeline for generating educational questions from textbook content",
    "is_template": true,
    "state_schema": {
      "type": "object",
      "properties": {
        "document_path": {"type": "string", "description": "Path to the source document"},
        "lesson_code": {"type": "string", "description": "Lesson code (e.g., 4.1)"},
        "processed_content": {"type": "object", "description": "Structured content from OCR"},
        "generation_plan": {"type": "object", "description": "Question generation plan"},
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
        "final_markdown": {"type": "string"}
      },
      "required": ["document_path"]
    },
    "nodes": [
      {
        "node_id": "doc_processor",
        "node_type": "agent",
        "agent_id": "'"$DOC_PROCESSOR_ID"'",
        "config": {
          "input_mapping": {"file_path": "$.document_path"},
          "output_key": "processed_content"
        }
      },
      {
        "node_id": "planner",
        "node_type": "agent",
        "agent_id": "'"$PLANNER_ID"'",
        "config": {
          "input_mapping": {"content": "$.processed_content"},
          "output_key": "generation_plan"
        }
      },
      {
        "node_id": "parallel_generators",
        "node_type": "parallel",
        "parallel_nodes": ["gen_v1", "gen_v2", "gen_v3", "gen_a1", "gen_a2", "gen_a3"],
        "config": {
          "fan_out_key": "generation_plan"
        }
      },
      {
        "node_id": "gen_v1",
        "node_type": "agent",
        "agent_id": "'"$INPUT1_GEN_ID"'",
        "config": {
          "input_mapping": {
            "content": "$.processed_content",
            "plan": "$.generation_plan"
          },
          "output_key": "questions.input_1"
        }
      },
      {
        "node_id": "gen_v2",
        "node_type": "agent",
        "agent_id": "'"$INPUT2_GEN_ID"'",
        "config": {
          "input_mapping": {
            "content": "$.processed_content",
            "plan": "$.generation_plan"
          },
          "output_key": "questions.input_2"
        }
      },
      {
        "node_id": "gen_v3",
        "node_type": "agent",
        "agent_id": "'"$INPUT3_GEN_ID"'",
        "config": {
          "input_mapping": {
            "content": "$.processed_content",
            "plan": "$.generation_plan"
          },
          "output_key": "questions.input_3"
        }
      },
      {
        "node_id": "gen_a1",
        "node_type": "agent",
        "agent_id": "'"$ACT1_GEN_ID"'",
        "config": {
          "input_mapping": {
            "content": "$.processed_content",
            "plan": "$.generation_plan"
          },
          "output_key": "questions.activation_1"
        }
      },
      {
        "node_id": "gen_a2",
        "node_type": "agent",
        "agent_id": "'"$ACT2_GEN_ID"'",
        "config": {
          "input_mapping": {
            "content": "$.processed_content",
            "plan": "$.generation_plan"
          },
          "output_key": "questions.activation_2"
        }
      },
      {
        "node_id": "gen_a3",
        "node_type": "agent",
        "agent_id": "'"$ACT3_GEN_ID"'",
        "config": {
          "input_mapping": {
            "content": "$.processed_content",
            "plan": "$.generation_plan"
          },
          "output_key": "questions.activation_3"
        }
      },
      {
        "node_id": "join_questions",
        "node_type": "join",
        "config": {
          "aggregation_key": "questions",
          "wait_for": ["gen_v1", "gen_v2", "gen_v3", "gen_a1", "gen_a2", "gen_a3"]
        }
      },
      {
        "node_id": "diagram_router",
        "node_type": "router",
        "router_config": {
          "routes": [
            {
              "condition": "any(q.get('image_needed', False) for level in state.get('questions', {}).values() for q in (level if isinstance(level, list) else []))",
              "target": "diagram_generator"
            }
          ],
          "default": "validator"
        }
      },
      {
        "node_id": "diagram_generator",
        "node_type": "agent",
        "agent_id": "'"$DIAGRAM_GEN_ID"'",
        "config": {
          "input_mapping": {"questions": "$.questions"},
          "output_key": "diagrams"
        }
      },
      {
        "node_id": "validator",
        "node_type": "agent",
        "agent_id": "'"$VALIDATOR_ID"'",
        "config": {
          "input_mapping": {
            "questions": "$.questions",
            "diagrams": "$.diagrams"
          },
          "output_key": "validation_results"
        }
      },
      {
        "node_id": "formatter",
        "node_type": "agent",
        "agent_id": "'"$FORMATTER_ID"'",
        "config": {
          "input_mapping": {
            "processed_content": "$.processed_content",
            "questions": "$.questions",
            "diagrams": "$.diagrams",
            "validation_results": "$.validation_results"
          },
          "output_key": "final_markdown"
        }
      },
      {
        "node_id": "save_output",
        "node_type": "agent",
        "agent_id": "'"$FILE_SAVER_ID"'",
        "config": {
          "input_mapping": {
            "lesson_code": "$.lesson_code",
            "lesson_title": "$.processed_content.lesson_title_en",
            "final_markdown": "$.final_markdown",
            "questions": "$.questions",
            "validation_results": "$.validation_results",
            "diagrams": "$.diagrams"
          },
          "output_key": "output_files"
        }
      }
    ],
    "edges": [
      {"source_node": "__start__", "target_node": "doc_processor"},
      {"source_node": "doc_processor", "target_node": "planner"},
      {"source_node": "planner", "target_node": "parallel_generators"},
      {"source_node": "parallel_generators", "target_node": "gen_v1"},
      {"source_node": "parallel_generators", "target_node": "gen_v2"},
      {"source_node": "parallel_generators", "target_node": "gen_v3"},
      {"source_node": "parallel_generators", "target_node": "gen_a1"},
      {"source_node": "parallel_generators", "target_node": "gen_a2"},
      {"source_node": "parallel_generators", "target_node": "gen_a3"},
      {"source_node": "gen_v1", "target_node": "join_questions"},
      {"source_node": "gen_v2", "target_node": "join_questions"},
      {"source_node": "gen_v3", "target_node": "join_questions"},
      {"source_node": "gen_a1", "target_node": "join_questions"},
      {"source_node": "gen_a2", "target_node": "join_questions"},
      {"source_node": "gen_a3", "target_node": "join_questions"},
      {"source_node": "join_questions", "target_node": "diagram_router"},
      {"source_node": "diagram_router", "target_node": "diagram_generator", "condition": "diagrams_needed"},
      {"source_node": "diagram_router", "target_node": "validator"},
      {"source_node": "diagram_generator", "target_node": "validator"},
      {"source_node": "validator", "target_node": "formatter"},
      {"source_node": "formatter", "target_node": "save_output"},
      {"source_node": "save_output", "target_node": "__end__"}
    ]
  }'
```

**Save the returned `id` as `$WORKFLOW_ID`**

---

## Part 6: Executing Workflows

### Enhanced Input Schema with Skill Context

When executing workflows, you can provide comprehensive skill and lesson context to guide question generation. This enables more targeted and curriculum-aligned content.

#### Full Input Structure

```json
{
  "document_path": "/path/to/textbook.pdf",
  "lesson_code": "4.1",
  "lesson_title": "Еднакви триъгълници",
  "lesson_title_en": "Congruent Triangles",
  "skills": [
    {
      "code": "4.1.1",
      "description_bg": "Определяне на еднакви триъгълници",
      "description_en": "Identifying congruent triangles"
    },
    {
      "code": "4.1.2",
      "description_bg": "Прилагане на признаци за еднаквост",
      "description_en": "Applying congruence criteria"
    },
    {
      "code": "4.1.3",
      "description_bg": "Доказване на еднаквост на триъгълници",
      "description_en": "Proving triangle congruence"
    }
  ],
  "learning_objectives": [
    "Understand the concept of triangle congruence",
    "Apply the three congruence criteria (SSS, SAS, ASA)",
    "Construct proofs using congruence relationships"
  ],
  "grade_level": 7,
  "subject": "mathematics",
  "additional_context": "Focus on geometric proofs and real-world applications. Students have prior knowledge of basic triangle properties."
}
```

#### Input Field Descriptions

| Field | Required | Description |
|-------|----------|-------------|
| `document_path` | Yes | Path to the source document (PDF, DOCX, or images) |
| `lesson_code` | No | Lesson identifier (e.g., "4.1") |
| `lesson_title` | No | Bulgarian lesson title |
| `lesson_title_en` | No | English lesson title |
| `skills` | No | Array of skill definitions with codes and descriptions |
| `learning_objectives` | No | Array of learning objectives for the lesson |
| `grade_level` | No | Target grade level (1-12) |
| `subject` | No | Subject area (e.g., "mathematics", "physics") |
| `additional_context` | No | Additional guidance for content generation |

**Note:** When skills are provided via input, they take precedence over skills extracted from the document. The document content serves as **reference material for inspiration only** - questions must be original.

### 6.1 Execute with Document Path

```bash
curl -X POST http://localhost:8000/api/v1/executions \
  -H "X-API-Key: default-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "'"$WORKFLOW_ID"'",
    "input": {
      "document_path": "/path/to/textbook/chapter4.pdf",
      "lesson_code": "4.1"
    }
  }'
```

### 6.2 Stream Execution Progress (Real-time)

```bash
curl -N -X POST http://localhost:8000/api/v1/executions/stream \
  -H "X-API-Key: default-api-key" \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "workflow_id": "'"$WORKFLOW_ID"'",
    "input": {
      "document_path": "/path/to/textbook/chapter4.pdf",
      "lesson_code": "4.1"
    }
  }'
```

Events received:
- `node_start`: When a node begins execution
- `node_complete`: When a node finishes
- `execution_complete`: When the entire workflow completes
- `error`: If an error occurs

### 6.3 Check Execution Status

```bash
# Get full execution details
curl -X GET "http://localhost:8000/api/v1/executions/$EXECUTION_ID" \
  -H "X-API-Key: default-api-key"

# Get lightweight status (for polling)
curl -X GET "http://localhost:8000/api/v1/executions/$EXECUTION_ID/status" \
  -H "X-API-Key: default-api-key"
```

### 6.4 Cancel Running Execution

```bash
curl -X POST "http://localhost:8000/api/v1/executions/$EXECUTION_ID/cancel" \
  -H "X-API-Key: default-api-key"
```

### 6.5 List Executions

```bash
# List all executions
curl -X GET "http://localhost:8000/api/v1/executions" \
  -H "X-API-Key: default-api-key"

# Filter by workflow
curl -X GET "http://localhost:8000/api/v1/executions?workflow_id=$WORKFLOW_ID" \
  -H "X-API-Key: default-api-key"

# Filter by status
curl -X GET "http://localhost:8000/api/v1/executions?status=COMPLETED" \
  -H "X-API-Key: default-api-key"
```

---

## Part 7: Complete Example Walkthrough

### Step 1: Prepare Your Environment

```bash
# Set environment variables
export API_KEY="default-api-key"
export BASE_URL="http://localhost:8000/api/v1"

# Verify server is running
curl "$BASE_URL/../health"
```

### Step 2: Register Tools

```bash
# Register Mistral OCR tool
MISTRAL_TOOL=$(curl -s -X POST "$BASE_URL/tools" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "mistral_ocr",
    "description": "Process documents using Mistral AI OCR",
    "function_schema": {
      "name": "mistral_ocr",
      "description": "Process a document using Mistral AI OCR",
      "parameters": {
        "type": "object",
        "properties": {
          "file_path": {"type": "string", "description": "Path to document"}
        },
        "required": ["file_path"]
      }
    },
  }')

MISTRAL_OCR_TOOL_ID=$(echo $MISTRAL_TOOL | jq -r '.id')
echo "Mistral OCR Tool ID: $MISTRAL_OCR_TOOL_ID"

# Register Calculator tool
CALC_TOOL=$(curl -s -X POST "$BASE_URL/tools" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "calculator",
    "description": "Evaluate mathematical expressions",
    "function_schema": {
      "name": "calculator",
      "description": "Evaluate a mathematical expression",
      "parameters": {
        "type": "object",
        "properties": {
          "expression": {"type": "string", "description": "Expression to evaluate"}
        },
        "required": ["expression"]
      }
    },
  }')

CALCULATOR_TOOL_ID=$(echo $CALC_TOOL | jq -r '.id')
echo "Calculator Tool ID: $CALCULATOR_TOOL_ID"
```

### Step 3: Create Agents

Create all 11 agents using the curl commands from Part 4. Save all returned IDs.

### Step 4: Create Workflow

Create the workflow using the curl command from Part 5.

### Step 5: Execute the Pipeline

```bash
# Path to your textbook PDF
DOCUMENT_PATH="/home/user/textbooks/math_7_grade/chapter4_triangles.pdf"

# Execute the workflow
EXECUTION=$(curl -s -X POST "$BASE_URL/executions" \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "'"$WORKFLOW_ID"'",
    "input": {
      "document_path": "'"$DOCUMENT_PATH"'",
      "lesson_code": "4.1"
    }
  }')

EXECUTION_ID=$(echo $EXECUTION | jq -r '.id')
echo "Execution ID: $EXECUTION_ID"
```

### Step 6: Monitor Progress

```bash
# Poll for status
while true; do
  STATUS=$(curl -s -X GET "$BASE_URL/executions/$EXECUTION_ID/status" \
    -H "X-API-Key: $API_KEY")

  CURRENT_STATUS=$(echo $STATUS | jq -r '.status')
  CURRENT_NODE=$(echo $STATUS | jq -r '.current_node')

  echo "Status: $CURRENT_STATUS | Node: $CURRENT_NODE"

  if [ "$CURRENT_STATUS" = "COMPLETED" ] || [ "$CURRENT_STATUS" = "FAILED" ]; then
    break
  fi

  sleep 5
done
```

### Step 7: Retrieve Results

```bash
# Get full execution results
RESULT=$(curl -s -X GET "$BASE_URL/executions/$EXECUTION_ID" \
  -H "X-API-Key: $API_KEY")

# Extract final markdown
MARKDOWN=$(echo $RESULT | jq -r '.output_data.final_markdown')

# Save to file
echo "$MARKDOWN" > "questions_4.1_output.md"
echo "Output saved to questions_4.1_output.md"
```

### Expected Output

The final markdown file will contain:

```markdown
# 4.1 Еднакви триъгълници
## Congruent Triangles

---

## Умения / Skills

| Код | Описание (БГ) | Description (EN) |
|-----|--------------|------------------|
| 4.1.1 | Определяне на еднакви триъгълници | Identifying congruent triangles |
| 4.1.2 | Прилагане на признаци за еднаквост | Applying congruence criteria |
| 4.1.3 | Доказване на еднаквост | Proving triangle congruence |

---

## Вход 1 / Input Level 1 (10%)

### V1.001 - Flashcard
**Front:** Кога два триъгълника са еднакви?
**Back:** Два триъгълника са еднакви, когато могат да се съвместят чрез движение.

[... more questions ...]

---

## Активация 3 / Activation Level 3 (24%)

### A3.001 - Competition Problem
**Question:** В триъгълник $$ABC$$ точката $$M$$ е среда на $$BC$$...

[... complex solutions ...]

---

## Metadata

- **Generated:** 2024-01-15T14:30:00Z
- **Total Questions:** 30
- **Validation:** Passed (30/30)
```

---

## Troubleshooting

### Common Issues

1. **MISTRAL_API_KEY not configured**
   - Ensure the environment variable is set
   - Restart the server after setting

2. **Tool not found: builtin:mistral_ocr**
   - Ensure the tool is registered in `registry.py`
   - Restart the server to reload tools

3. **Execution timeout**
   - Large documents may take longer
   - Use streaming endpoint to monitor progress

4. **OCR quality issues**
   - Ensure documents are high quality scans
   - Try processing specific pages only

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
uvicorn agent_orchestrator.main:app --reload
```

---

## Appendix: Question Format Reference

### Question Types Summary

| Type | Level | Fields |
|------|-------|--------|
| flashcard | V1 | front, back |
| yes_no | V1 | question, correct_answer, explanation |
| single_select | V1, V2 | question, options, correct_answer |
| multi_select | V2 | question, options, correct_answers |
| fill_blank | V1, V2, V3 | question, blanks |
| matching | V2 | left_items, right_items, correct_matches |
| table | V2, V3 | headers, rows, blanks |
| ordered_steps | V3 | steps, correct_order |
| word_problem | A1, A2, A3 | question, solution_steps, answer |
| proof | A1, A2, A3 | given, to_prove, proof_template |
| calculation | A1, A2 | question, solution, answer |
| competition | A3 | question, hints, solution |

### Code Format

```
NN.N.N.XX.NNN
│  │ │ │  └── Sequential number (001-999)
│  │ │ └───── Level (V1, V2, V3, A1, A2, A3)
│  │ └─────── Subskill number
│  └───────── Skill number
└──────────── Lesson number
```

Example: `4.1.2.A2.003` = Lesson 4.1, Skill 2, Activation Level 2, Question 3

---

## License

This guide is part of the Agent Orchestrator project.
