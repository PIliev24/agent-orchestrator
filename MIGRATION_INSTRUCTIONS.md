# Migration Instructions: Go API AI Workflows → Agent Orchestrator

This document provides comprehensive instructions for recreating and improving all AI content generation workflows from the Go API (`quizgpt-api`) using the `agent-orchestrator`.

---

## Table of Contents

1. [Overview of Current Go API Capabilities](#1-overview-of-current-go-api-capabilities)
2. [Mapping to Agent-Orchestrator Concepts](#2-mapping-to-agent-orchestrator-concepts)
3. [Custom Tools to Build](#3-custom-tools-to-build)
4. [Agent Definitions](#4-agent-definitions)
5. [Workflow 1: Document Processing Pipeline](#5-workflow-1-document-processing-pipeline)
6. [Workflow 2: Simple Question Generation](#6-workflow-2-simple-question-generation)
7. [Workflow 3: Question Generation Wizard](#7-workflow-3-question-generation-wizard-multi-phase)
8. [Workflow 4: Combined End-to-End Pipeline](#8-workflow-4-combined-end-to-end-pipeline)
9. [Integration with Go API (HTTP Tool Callbacks)](#9-integration-with-go-api-http-tool-callbacks)
10. [Improvements Over the Go Implementation](#10-improvements-over-the-go-implementation)

---

## 1. Overview of Current Go API Capabilities

The Go API (`quizgpt-api`) implements three AI-driven content generation systems for the EtoKak educational platform. All produce Bulgarian-language educational content in BlockNote format.

### 1.1 Document Processing Pipeline

**Location:** `api/agents/orchestrator/extraction_pipeline.go`, `api/service/document_processing_handlers.go`

A 3-step sequential pipeline that extracts practice problems from uploaded documents (PDF, DOCX):

```
Step 1: Instruction Preparation Chain
  ├─ Document Analysis (identify structure, content type, topics)
  └─ Instruction Generation (teacher persona, focus areas, difficulty guidance)

Step 2: Content Extraction
  ├─ Build extraction instructions from lesson context + generated instructions
  ├─ Split large documents into 30KB chunks
  ├─ Extract problems from each chunk via LLM
  └─ Deduplicate results

Step 3: Verification
  ├─ Verify extracted problems against lesson skills
  └─ Filter out problems with error-level issues
```

**Agents involved:**
- `InstructionPreparationChain` — 2-step chain (analyze document → generate instructions)
- `DocumentExtractionAgent` — extracts problems from OCR content
- `ExtractionVerificationAgent` — validates extracted problems

### 1.2 Simple Question Generation

**Location:** `api/agents/question_agent.go`, `api/service/agent.go`

Single-shot question generation. Takes a description and count, generates questions directly via LLM with combined instructions (base + format + Bulgarian standards + pedagogical principles).

### 1.3 Question Generation Wizard (Multi-Phase)

**Location:** `api/service/question_wizard_handlers.go`, `api/agents/levelset_question_agent.go`

A multi-phase workflow with user interaction:

```
Phase 1: PLANNING
  ├─ Fetch lesson skills, level sets, existing question counts
  ├─ Calculate target counts per level set
  ├─ Fetch reference content (extraction.md) from Google Drive
  └─ Run Planner Agent to determine question type distribution

Phase 2: USER CONFIRMATION
  └─ User reviews plan, adjusts targets, confirms

Phase 3: PARALLEL GENERATION
  ├─ 3 concurrent worker goroutines
  ├─ Each worker runs LevelSetQuestionAgent for assigned level sets
  ├─ Parse and validate BlockNote responses
  └─ Aggregate results
```

**Agents involved:**
- `QuestionPlannerAgent` — calculates optimal question counts and type distribution
- `LevelSetQuestionAgent` — generates questions for a specific level set
- `InstructionGeneratorAgent` — creates grade/subject-specific instructions

### 1.4 Shared Infrastructure

**AI Providers:** OpenAI (`gpt-5`), Anthropic (`claude-sonnet-4-5`), Google (`gemini-2.5-flash`)

**Question Types:** Selection, Multiselect, FreeInput, FillBlanks, Flashcard, Reorder, Connection, Tablefiller

**Pedagogical Framework:** 6-stage matrix (Input 1-3, Activation 1-3) with Bloom's taxonomy progression

---

## 2. Mapping to Agent-Orchestrator Concepts

| Go API Concept | Agent-Orchestrator Equivalent |
|---|---|
| `agents.QuestionAgent` | Agent (with instructions + output_schema) |
| `agents.LevelSetQuestionAgent` | Agent (with level-set-specific instructions) |
| `agents.InstructionPreparationChain` | Subgraph workflow (2-node chain) |
| `agents.ExtractionVerificationAgent` | Agent node with structured output |
| `agents.DocumentExtractionAgent` | Agent node with `mistral_ocr` tool |
| `orchestrator.ContentExtractionPipeline` | Workflow (3 sequential agent nodes) |
| Wizard 3-worker goroutine pool | Parallel node (fan-out to N level-set agents) |
| Wizard planning phase | Agent node (planner) |
| Background channels (`backgroundChan`) | Execution service (async via SSE streaming) |
| In-memory wizard session | Checkpointed workflow state (PostgreSQL) |
| LLM provider selection | Agent `llm_config.provider` field |
| `api.ParseQuestionItem` / BlockNote format | Agent `output_schema` (JSON Schema) |
| `instructions.QuestionFormatInstructions` | Agent `instructions` field |
| Go retry logic (3 retries) | Agent node tool loop (MAX_TOOL_ITERATIONS=10) |
| `GenerateJSON()` helper | `create_model_with_structured_output()` |

### Key Architecture Differences

1. **Go API:** Procedural pipeline with manual goroutine orchestration, in-memory session state
2. **Agent-Orchestrator:** Declarative graph-based workflows with automatic state management, checkpointing, and parallel execution via LangGraph

---

## 3. Custom Tools to Build

The agent-orchestrator has 4 built-in tools (`calculator`, `file_writer`, `http_request`, `mistral_ocr`). The following custom tools must be created for the migration.

### 3.1 Go API Callback Tool

Calls back to the Go API to fetch lesson context, save results, etc.

```json
{
  "name": "go_api_callback",
  "description": "Make authenticated requests to the Go API for lesson data, saving results, etc.",
  "function_schema": {
    "name": "go_api_callback",
    "description": "Call the Go API with authentication",
    "parameters": {
      "type": "object",
      "properties": {
        "endpoint": {
          "type": "string",
          "description": "API endpoint path, e.g. /api/lessons/{id}"
        },
        "method": {
          "type": "string",
          "enum": ["GET", "POST", "PUT", "DELETE"],
          "default": "GET"
        },
        "body": {
          "type": "object",
          "description": "Request body for POST/PUT"
        }
      },
      "required": ["endpoint"]
    }
  },
  "implementation_ref": "builtin:http",
  "config": {
    "base_url": "https://api.etokak.com",
    "default_headers": {
      "Authorization": "Bearer ${GO_API_TOKEN}",
      "Content-Type": "application/json"
    }
  }
}
```

> **Implementation note:** This wraps the built-in `http_request` tool with a fixed `base_url` and auth headers. Create a custom tool class extending `BaseTool` that prepends the base URL and injects auth headers.

### 3.2 Google Drive Tool

Fetches reference content (extraction.md) and uploads results.

```json
{
  "name": "google_drive",
  "description": "Read and write files to Google Drive for lesson reference content",
  "function_schema": {
    "name": "google_drive",
    "description": "Interact with Google Drive",
    "parameters": {
      "type": "object",
      "properties": {
        "action": {
          "type": "string",
          "enum": ["read", "write", "list"]
        },
        "folder_path": {
          "type": "string",
          "description": "Drive folder path, e.g. courses/{name}/lessons/{name}/"
        },
        "file_name": {
          "type": "string"
        },
        "content": {
          "type": "string",
          "description": "Content to write (for write action)"
        }
      },
      "required": ["action"]
    }
  },
  "implementation_ref": "custom:google_drive"
}
```

> **Implementation note:** Create a custom tool class that uses the Google Drive API with a service account. Store credentials in the tool's `config`.

### 3.3 BlockNote Validator Tool

Validates generated questions against the BlockNote schema and question type rules.

```json
{
  "name": "blocknote_validator",
  "description": "Validate BlockNote question data structure and detect question type",
  "function_schema": {
    "name": "blocknote_validator",
    "description": "Validate a BlockNote question array",
    "parameters": {
      "type": "object",
      "properties": {
        "block_note_data": {
          "type": "array",
          "description": "The BlockNote blocks array to validate"
        }
      },
      "required": ["block_note_data"]
    }
  },
  "implementation_ref": "custom:blocknote_validator"
}
```

> **Implementation note:** Port the validation logic from `api/agents/question_agent.go:ValidateBlockNoteQuestion()` and `api/pkg/questions/` to Python. This tool checks that the first block has `content[0].type = "questionType"`, validates the type is in the allowed set, and returns `{valid: bool, detected_type: string, errors: string[]}`.

### 3.4 Document Chunker Tool

Splits large documents into 30KB chunks with intelligent boundary detection.

```json
{
  "name": "document_chunker",
  "description": "Split large OCR content into chunks for processing",
  "function_schema": {
    "name": "document_chunker",
    "description": "Split document content into processable chunks",
    "parameters": {
      "type": "object",
      "properties": {
        "content": {
          "type": "string",
          "description": "Full document content with [PAGE N] markers"
        },
        "max_chunk_size": {
          "type": "integer",
          "default": 30000,
          "description": "Maximum characters per chunk"
        }
      },
      "required": ["content"]
    }
  },
  "implementation_ref": "custom:document_chunker"
}
```

> **Implementation note:** Port the chunking logic from `api/service/document_processing_handlers.go` (lines 1114-1154). Split at `\n---\n` → `\n# File:` → `\n\n` → `\n` → hard limit.

---

## 4. Agent Definitions

### 4.1 Document Analyzer Agent

Analyzes document structure before extraction.

```json
{
  "name": "document_analyzer",
  "description": "Analyzes OCR document structure, content type, and characteristics",
  "instructions": "You are a document structure analyzer. Analyze educational documents and identify their structure.\n\nAnalyze the provided document content and return a JSON object with:\n- contentType: \"textbook\", \"worksheet\", \"exam\", \"mixed\", or \"unknown\"\n- structurePatterns: Array of patterns found (e.g., \"numbered_problems\", \"lettered_subproblems\", \"sections_with_headers\")\n- topicIndicators: Array of topic indicators (e.g., \"algebra\", \"geometry\", \"fractions\")\n- pageCount: Number of pages based on [PAGE N] markers\n- hasFigures: Whether figures/diagrams are referenced\n- hasSolutions: Whether solutions or answers are included",
  "llm_config": {
    "provider": "anthropic",
    "model_name": "claude-sonnet-4-5-20250514",
    "max_tokens": 2000
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "contentType": {"type": "string", "enum": ["textbook", "worksheet", "exam", "mixed", "unknown"]},
      "structurePatterns": {"type": "array", "items": {"type": "string"}},
      "topicIndicators": {"type": "array", "items": {"type": "string"}},
      "pageCount": {"type": "integer"},
      "hasFigures": {"type": "boolean"},
      "hasSolutions": {"type": "boolean"}
    },
    "required": ["contentType", "structurePatterns", "topicIndicators", "pageCount", "hasFigures", "hasSolutions"]
  },
  "tool_ids": []
}
```

### 4.2 Instruction Generator Agent

Generates tailored extraction instructions based on lesson context and document analysis.

```json
{
  "name": "instruction_generator",
  "description": "Generates tailored extraction instructions based on lesson context and document analysis",
  "instructions": "You are an expert educational content specialist. Generate precise extraction instructions that help identify relevant practice problems for students.\n\nGiven lesson context, skill details, related lessons (for exclusion), and document analysis results, generate extraction instructions as a JSON object with:\n- teacherPersona: Brief description of the ideal teacher persona for this grade/subject\n- focusAreas: Array of specific areas to focus on when extracting problems\n- skillMappings: Object mapping general problem types to specific skill codes\n- difficultyGuidance: Guidance on how to assess difficulty for this grade level\n- exclusionCriteria: Array of specific things to exclude\n- customRules: Array of special rules based on document type and structure\n- contentPatterns: Array of patterns to look for based on the document structure",
  "llm_config": {
    "provider": "anthropic",
    "model_name": "claude-sonnet-4-5-20250514",
    "max_tokens": 4000
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "teacherPersona": {"type": "string"},
      "focusAreas": {"type": "array", "items": {"type": "string"}},
      "skillMappings": {"type": "object"},
      "difficultyGuidance": {"type": "string"},
      "exclusionCriteria": {"type": "array", "items": {"type": "string"}},
      "customRules": {"type": "array", "items": {"type": "string"}},
      "contentPatterns": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["teacherPersona", "focusAreas", "difficultyGuidance", "exclusionCriteria"]
  },
  "tool_ids": []
}
```

### 4.3 Document Extraction Agent

Extracts practice problems from OCR-processed documents. This is the core extraction agent that uses the full instruction set from `instructions/document_extraction.go`.

```json
{
  "name": "document_extractor",
  "description": "Extracts practice problems from OCR-processed educational documents",
  "instructions": "<SEE FULL PROMPT BELOW>",
  "llm_config": {
    "provider": "anthropic",
    "model_name": "claude-sonnet-4-5-20250514",
    "max_tokens": 8000
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "exampleProblems": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "id": {"type": "string"},
            "statement": {"type": "string"},
            "difficulty": {"type": "string", "enum": ["easy", "medium", "hard"]},
            "figureId": {"type": "string"},
            "pageIndex": {"type": "integer"},
            "suggestedStage": {"type": "string"},
            "suggestedQuestionType": {"type": "string"},
            "targetLevelSetCode": {"type": "string"}
          },
          "required": ["id", "statement", "difficulty", "pageIndex"]
        }
      },
      "isGeometry": {"type": "boolean"},
      "geometryElements": {"type": "array"}
    },
    "required": ["exampleProblems", "isGeometry"]
  },
  "tool_ids": ["<mistral_ocr_tool_id>", "<document_chunker_tool_id>"]
}
```

**Full instructions prompt** (combine dynamically based on lesson context):

```
You are an expert educational content extractor specializing in {subject_name} for {grade_name} level students.

ETO KAK PEDAGOGICAL MATRIX KNOWLEDGE:

The ETO KAK system uses a structured 6-stage progression matrix for skill mastery:

┌─────────────────────────────────────────────────────────────────────────────────┐
│ STAGE        │ BLOOM'S LEVEL   │ TARGET % │ MIN TASKS │ FOCUS                   │
├─────────────────────────────────────────────────────────────────────────────────┤
│ Input 1      │ Remember        │ 34%      │ 15        │ Recognition, recall     │
│ Input 2      │ Understand      │ 55%      │ 15        │ Comprehension, explain  │
│ Input 3      │ Apply           │ 75%      │ 15        │ Use in new situations   │
│ Activation 1 │ Apply           │ 75%      │ 35        │ Problem-solving         │
│ Activation 2 │ Analyze         │ 89%      │ 35        │ Break down, compare     │
│ Activation 3 │ Evaluate        │ 95%      │ 35        │ Judge, justify, create  │
└─────────────────────────────────────────────────────────────────────────────────┘

LEVEL SET CODE FORMAT:
Codes follow the pattern NN.N.N.N where:
- First digits: Skill/topic identifier
- Second digit: Stage within skill progression
- Third digit: Difficulty variant
- Fourth digit: Version/variant number

TARGET LESSON CONTEXT:
- Lesson: {lesson_name}
- Description: {lesson_description}
- Course: {course_name}
- Subject: {subject_name}
- Grade: {grade_name}

LESSON STAGES AND REQUIREMENTS:
{stages_list}

LESSON LEVEL SETS:
{level_sets_list}

ASSOCIATED SKILLS:
{skills_list}

EXTRACTION STRATEGY:
1. Extract ALL problems from the document that match the lesson's skills
2. Classify each problem's difficulty based on cognitive complexity:
   - 'easy': Simple recall, recognition, basic application (Input stages)
   - 'medium': Multi-step problems, requires understanding (Activation 1)
   - 'hard': Analysis, synthesis, evaluation required (Activation 2-3)
3. Look for problems in sections like 'Упражнения', 'Задачи', 'Примери', 'Въпроси'
4. Include numbered exercises
5. Include worked examples that can be converted to practice problems

TASK:
Extract ONLY actual practice problems and exercises that are directly relevant to the specified lesson from OCR-processed documents.

PAGE TRACKING:
- The document content contains [PAGE N] markers (0-indexed) indicating page boundaries
- When extracting a problem, set pageIndex to the page number where the problem statement begins

CRITICAL FILTERING RULES:
1. ONLY extract problems that match the TARGET LESSON'S name, description, skills and level sets
2. DO NOT extract problems from other lessons, chapters, or topics
3. SKIP any content that teaches different skills than those listed
4. SKIP prerequisite/review problems unless they explicitly match the lesson's skills
5. Cross-reference each problem against the lesson's skills and level sets before including it
6. If a problem doesn't clearly relate to the listed skills, DO NOT include it

WHAT TO EXTRACT:
1. Actual PRACTICE PROBLEMS with clear tasks for students to solve
2. Problems that require the student to DO something (calculate, solve, identify, match, fill in, etc.)
3. Worked examples that demonstrate skill application with a clear problem statement
4. Problems from "Exercises", "Problems", "Tasks", "Practice" sections

DO NOT EXTRACT:
1. Introductory text explaining concepts
2. Definitions, theorems, or formulas presented as teaching content
3. "Consider this...", "For example...", or "Notice that..." illustrations
4. Overview sections, table of contents, objectives lists
5. Historical context, background information, or motivational text

FIGURE ASSOCIATION:
- When a problem references or requires a figure/diagram, set the figureId field
- The figureId should describe the figure location, e.g., "page3-fig1"

GEOMETRY DETECTION:
Set isGeometry to true if the lesson primarily involves geometric shapes, spatial relationships, geometric constructions, or coordinate geometry.
```

### 4.4 Extraction Verification Agent

Validates extracted problems against lesson context.

```json
{
  "name": "extraction_verifier",
  "description": "Verifies extracted problems match the intended lesson context",
  "instructions": "You are an expert educational content verifier. Verify that extracted problems match the intended lesson context.\n\nFor each extracted problem, verify:\n1. Does it match the lesson's topic and skills?\n2. Is the difficulty assessment appropriate for the grade level?\n3. Is it a valid practice problem (not just explanatory text)?\n\nReturn verification results with isValid (true if >70% valid), confidence (0.0-1.0), issues array (each with problemId, issueType, description, severity), and suggestions array.",
  "llm_config": {
    "provider": "anthropic",
    "model_name": "claude-sonnet-4-5-20250514",
    "max_tokens": 4000
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "isValid": {"type": "boolean"},
      "confidence": {"type": "number", "minimum": 0, "maximum": 1},
      "issues": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "problemId": {"type": "string"},
            "issueType": {"type": "string", "enum": ["off_topic", "wrong_skill", "difficulty_mismatch", "not_a_problem", "incomplete"]},
            "description": {"type": "string"},
            "severity": {"type": "string", "enum": ["warning", "error"]}
          }
        }
      },
      "suggestions": {"type": "array", "items": {"type": "string"}}
    },
    "required": ["isValid", "confidence", "issues", "suggestions"]
  },
  "tool_ids": []
}
```

### 4.5 Question Planner Agent

Plans question generation: counts, type distribution, strategy.

```json
{
  "name": "question_planner",
  "description": "Plans optimal question counts and type distribution per level set",
  "instructions": "<FULL PROMPT BELOW>",
  "llm_config": {
    "provider": "anthropic",
    "model_name": "claude-sonnet-4-5-20250514",
    "max_tokens": 4000
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "status": {"type": "string"},
      "plan": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "levelSetId": {"type": "string"},
            "levelSetCode": {"type": "string"},
            "levelSetName": {"type": "string"},
            "activationLevel": {"type": "string"},
            "existingCount": {"type": "integer"},
            "targetCount": {"type": "integer"},
            "toGenerate": {"type": "integer"},
            "questionTypeDistribution": {"type": "object"},
            "reasoning": {"type": "string"}
          }
        }
      },
      "summary": {"type": "string"}
    },
    "required": ["status", "plan"]
  },
  "tool_ids": ["<go_api_callback_tool_id>"]
}
```

**Full instructions prompt:**

```
You are an educational content planning specialist for the EtoKak platform. Your task is to analyze a lesson's skill matrix and determine optimal question counts for each level set based on pedagogical principles.

## Question Count Rules (CRITICAL)

### Input Phases (activation levels: input_1, input_2, input_3)
- Minimum: 15 questions per levelset
- Purpose: Introduction and understanding
- Typical types: Flashcard (1-3), Selection, Multiselect
- Bloom's taxonomy: Remember, Understand, Apply

### Activation Phases (activation levels: activation_1, activation_2)
- Minimum: 35 questions per levelset
- Purpose: Practice and application
- Types: FillBlanks, DragDrop, Reorder, Connection, plus basic types
- Bloom's taxonomy: Analyze, Evaluate

### Activation 3 (activation level: activation_3)
- Minimum: 35 questions per levelset
- MUST include FreeInput questions for exam-level assessment
- Purpose: NVO/exam-level mastery
- Bloom's taxonomy: Create

## Question Type Distribution Guidelines

### Input 1 (introduction)
- 10-20% Flashcards (2-3)
- 40-50% Selection (6-8)
- 30-40% Multiselect (5-6)

### Input 2-3 (expansion/generalization)
- 30-40% Selection
- 20-30% Multiselect
- 20-30% FillBlanks
- 10-20% Connection/Reorder

### Activation 1 (primary activation)
- 20-30% Selection/Multiselect
- 30-40% FillBlanks
- 20-30% DragDrop/Reorder
- 10-20% Connection

### Activation 2 (secondary activation)
- 15-25% Selection/Multiselect
- 30-40% FillBlanks
- 20-30% Connection/Reorder
- 10-20% Tablefiller

### Activation 3 (mastery/exam level)
- 20-30% FreeInput (REQUIRED)
- 20-30% FillBlanks
- 20-30% Connection/Reorder

## Level Set Code Format
Pattern: NN.N.N (Lesson.Skill.Stage)
- Stage 1-3: Input phases
- Stage 4-6: Activation phases
- Ranges like "8.1.2-8.2.2" indicate cross-skill level sets

## Important Considerations
1. Never go below minimum counts
2. Ensure diverse question types within each level set
3. Use reference content to inform question topics and complexity
4. Cross-skill level sets should integrate multiple skills
5. Activation 3 MUST prepare students for standardized exams (NVO)
6. Progressive difficulty: earlier stages easier than later
```

### 4.6 Level Set Question Generator Agent

Generates questions for a specific level set. Create one agent definition per activation level, or dynamically build instructions.

```json
{
  "name": "levelset_question_generator",
  "description": "Generates educational questions for a specific level set in BlockNote format",
  "instructions": "<SEE FULL PROMPT BELOW>",
  "llm_config": {
    "provider": "anthropic",
    "model_name": "claude-sonnet-4-5-20250514",
    "max_tokens": 16000
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "status": {"type": "string", "enum": ["completed", "error"]},
      "questions": {
        "type": "array",
        "items": {
          "type": "object",
          "properties": {
            "id": {"type": "string"},
            "levelSetCode": {"type": "string"},
            "levelSetOk": {"type": "boolean"},
            "status": {"type": "string"},
            "statusNotes": {"type": "string"},
            "ok": {"type": "boolean"},
            "blockNoteData": {"type": "array"},
            "isTheory": {"type": "boolean"},
            "questionType": {"type": "string"}
          },
          "required": ["id", "levelSetCode", "blockNoteData", "questionType"]
        }
      },
      "error": {"type": "string"}
    },
    "required": ["status", "questions"]
  },
  "tool_ids": ["<calculator_tool_id>", "<blocknote_validator_tool_id>"]
}
```

**Full instructions prompt** (combined from `BaseIntroduction` + `QuestionFormatInstructions` + `BulgarianFormattingStandards` + `PedagogicalPrinciples`):

```
You are an expert question generation assistant specialized in creating educational questions in Bulgarian. Your role is to generate questions in BlockNote format that can be directly parsed and saved to the database. You understand the course matrix structure and pedagogical principles.

# CRITICAL BLOCKNOTE FORMAT REQUIREMENTS:

Every question MUST be formatted as a BlockNote array. The FIRST block is CRITICAL and must have this exact structure:

{
  "id": "unique-id-here",
  "type": "paragraph",
  "props": null,
  "content": [
    {
      "type": "questionType",
      "text": "",
      "styles": null,
      "props": {
        "questionType": "Selection"
      }
    }
  ],
  "children": null
}

Valid questionType values: "Selection", "Multiselect", "FreeInput", "FillBlanks", "Flashcard", "Reorder", "Connection", "Tablefiller"

After the questionType block, include blocks with proper labels:
- "Question: " (bold) followed by the question text
- "Possible answers:" (bold) for selection/multiselect, followed by "A) ", "B) ", etc.
- "Answer: " (bold) followed by the answer
- "Solution: " (bold) followed by the solution explanation

# QUESTION TYPES SUPPORTED:

## 1. SELECTION (single choice)
Content: { question: {type, title, text, content}, options: [{type, content}], optionsRenderType }
Answer: { index: 0 }

## 2. MULTISELECT
Content: Same as selection
Answer: { indexes: [0, 2] }

## 3. FREEINPUT
Content: { question: {...}, inputs: [{type: "input", placeholder}], inputType, possibleAnswers, separator }
Answer: { inputs: ["answer1", "answer2"] }

## 4. FILLBLANKS
Content: { question: {...}, textParts: [{type: "text"/"input", content/placeholder}], inputType, possibleAnswers }
Answer: { inputs: ["answer1", "answer2"] }

## 5. FLASHCARD
Content: { question: {type, content}, answer: {type, content} }
Answer: {}

## 6. REORDER
Content: { question: {type, content}, items: [{type, content}] }
Answer: { order: [0, 1, 2] }

## 7. CONNECTION
Content: { question: {type, content}, leftItems: [{type, content}], rightItems: [{type, content}] }
Answer: { connections: [{left: 0, right: 1}] }

## 8. TABLEFILLER
Content: { question: {type, content}, headers: {columns, rows}, cells: [[{type, content/placeholder}]] }
Answer: { cells: [{row, col, value}] }

# BULGARIAN FORMATTING STANDARDS:

- Use exact labels: "Въпрос:", "Отговор:", "Възможни отговори:", "Решение:"
- Every question (except flashcards) MUST have "Решение:" explaining the answer
- Multiselect answers: "A, C, D" (comma + space)
- Free input alternatives: "отговор1; отговор2; отговор3" (semicolons)
- Math symbols: √, ², ³, ≤, ≥, ≠
- LaTeX: $$formula$$

# PEDAGOGICAL PRINCIPLES:

1. Progressive Difficulty: Input 1 (easy) → Activation 3 (exam-level)
2. Format Variety: Alternate formats, avoid 5+ consecutive same-format tasks
3. Clear, unambiguous questions in age-appropriate language
4. Plausible distractors based on typical student mistakes
5. Step-by-step tasks for complex problems
6. Solutions explain not only WHAT, but WHY

# COURSE STRUCTURE:
Course → Chapter → Lesson → Skills → LevelSets → Questions

## Activation Levels:
- Input 1: Remember/Understand (34%), min 15 tasks - Flashcards, Selection, Yes/No
- Input 2: Apply (55%), min 15 tasks - combines micro-skills
- Input 3: Apply (75%), min 15 tasks - integrates all micro-skills
- Activation 1: Analyze (75%), min 35 tasks - multi-step, real-world
- Activation 2: Evaluate (89%), min 35 tasks - complex synthesis
- Activation 3: Create (95%), min 35 tasks - NVO/exam level, MUST include FreeInput

## Level Set Generation Context
(Injected dynamically per execution - see state.input)

You are generating questions for:
- Level Set Code: {levelSetCode}
- Activation Level: {activationLevel}
- Questions to Generate: {toGenerate}
- Lesson: {lessonName}
- Subject: {subjectName}
- Grade: {gradeName}

### Reference Content
{referenceContent}

### Question Type Distribution
{typeDistribution}
```

### 4.7 Simple Question Generator Agent

For the direct question generation flow (no wizard).

```json
{
  "name": "simple_question_generator",
  "description": "Generates questions directly from a description (no wizard flow)",
  "instructions": "<Same base instructions as 4.6, without level-set-specific context. The user provides a free-form description and desired count.>",
  "llm_config": {
    "provider": "anthropic",
    "model_name": "claude-sonnet-4-5-20250514",
    "max_tokens": 16000
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "status": {"type": "string"},
      "questions": {"type": "array"},
      "error": {"type": "string"}
    },
    "required": ["status", "questions"]
  },
  "tool_ids": ["<calculator_tool_id>", "<blocknote_validator_tool_id>"]
}
```

---

## 5. Workflow 1: Document Processing Pipeline

Replaces: `api/agents/orchestrator/extraction_pipeline.go` + `api/service/document_processing_handlers.go`

### 5.1 State Schema

```json
{
  "type": "object",
  "properties": {
    "document_path": {"type": "string", "description": "Path to uploaded document"},
    "lesson_id": {"type": "string", "description": "UUID of the lesson"},
    "lesson_context": {
      "type": "object",
      "description": "Lesson name, description, skills, level sets, course, subject, grade"
    },
    "user_instructions": {"type": "string", "description": "Optional user-provided extraction guidance"},
    "document_content": {"type": "string", "description": "OCR-extracted text with [PAGE N] markers"},
    "document_analysis": {
      "type": "object",
      "description": "Content type, structure patterns, topic indicators"
    },
    "extraction_instructions": {
      "type": "object",
      "description": "Generated teacher persona, focus areas, exclusion criteria"
    },
    "extracted_content": {
      "type": "object",
      "description": "Extracted problems with IDs, statements, difficulty, page indices"
    },
    "verification_result": {
      "type": "object",
      "description": "Verification results: isValid, confidence, issues, suggestions"
    },
    "filtered_content": {
      "type": "object",
      "description": "Problems after removing error-level issues"
    }
  },
  "required": ["document_path", "lesson_id"]
}
```

### 5.2 Workflow Definition

```json
{
  "name": "Document Processing Pipeline",
  "description": "Extracts practice problems from uploaded educational documents using OCR, AI analysis, and verification",
  "is_template": true,
  "state_schema": "<state schema above>",
  "nodes": [
    {
      "node_id": "ocr_processor",
      "node_type": "AGENT",
      "agent_id": "<document_extractor_agent_id>",
      "config": {
        "description": "Process document with Mistral OCR to extract text"
      }
    },
    {
      "node_id": "document_analyzer",
      "node_type": "AGENT",
      "agent_id": "<document_analyzer_agent_id>",
      "config": {
        "description": "Analyze document structure and characteristics"
      }
    },
    {
      "node_id": "instruction_generator",
      "node_type": "AGENT",
      "agent_id": "<instruction_generator_agent_id>",
      "config": {
        "description": "Generate tailored extraction instructions"
      }
    },
    {
      "node_id": "content_extractor",
      "node_type": "AGENT",
      "agent_id": "<document_extractor_agent_id>",
      "config": {
        "description": "Extract problems from document using generated instructions"
      }
    },
    {
      "node_id": "verifier",
      "node_type": "AGENT",
      "agent_id": "<extraction_verifier_agent_id>",
      "config": {
        "description": "Verify extracted problems match lesson context"
      }
    }
  ],
  "edges": [
    {"source_node": "__start__", "target_node": "ocr_processor"},
    {"source_node": "ocr_processor", "target_node": "document_analyzer"},
    {"source_node": "document_analyzer", "target_node": "instruction_generator"},
    {"source_node": "instruction_generator", "target_node": "content_extractor"},
    {"source_node": "content_extractor", "target_node": "verifier"},
    {"source_node": "verifier", "target_node": "__end__"}
  ]
}
```

### 5.3 Graph Visualization

```
[START]
   │
   ▼
[ocr_processor] ── Uses: mistral_ocr tool
   │
   ▼
[document_analyzer] ── Analyzes structure, detects content type
   │
   ▼
[instruction_generator] ── Generates teacher persona, focus areas, exclusion criteria
   │
   ▼
[content_extractor] ── Extracts problems using combined instructions + document_chunker tool
   │
   ▼
[verifier] ── Validates problems against lesson skills, filters errors
   │
   ▼
[END] ── Output: filtered_content with verified problems
```

### 5.4 Execution

```bash
# Start execution
curl -X POST http://localhost:8000/api/v1/executions \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "<document_processing_workflow_id>",
    "input": {
      "document_path": "/uploads/textbook_chapter4.pdf",
      "lesson_id": "uuid-of-lesson",
      "lesson_context": {
        "lesson_name": "Еднакви триъгълници",
        "lesson_description": "...",
        "course_name": "Математика 7 клас",
        "subject_name": "Математика",
        "grade_name": "7 клас",
        "skills": [
          {"skill_name": "Признаци за еднаквост", "skill_code": "7.1", "category": "geometry"}
        ],
        "level_sets": [
          {"level_set_name": "Input 1", "level_set_code": "7.1.1", "activation_level": "Input", "target_percentage": 34, "minimum_tasks": 15}
        ]
      }
    }
  }'

# Stream execution events
curl -N http://localhost:8000/api/v1/executions/<execution_id>/stream \
  -H "X-API-Key: $API_KEY"
```

---

## 6. Workflow 2: Simple Question Generation

Replaces: `api/agents/question_agent.go` + direct generation in `api/service/agent.go`

### 6.1 State Schema

```json
{
  "type": "object",
  "properties": {
    "description": {"type": "string", "description": "Free-form description of what to generate"},
    "count": {"type": "integer", "description": "Number of questions to generate"},
    "lesson_context": {"type": "object", "description": "Optional lesson/course context"},
    "questions": {
      "type": "array",
      "description": "Generated questions in BlockNote format"
    }
  },
  "required": ["description", "count"]
}
```

### 6.2 Workflow Definition

```json
{
  "name": "Simple Question Generation",
  "description": "Directly generates questions from a description without wizard flow",
  "is_template": true,
  "state_schema": "<state schema above>",
  "nodes": [
    {
      "node_id": "generator",
      "node_type": "AGENT",
      "agent_id": "<simple_question_generator_agent_id>"
    }
  ],
  "edges": [
    {"source_node": "__start__", "target_node": "generator"},
    {"source_node": "generator", "target_node": "__end__"}
  ]
}
```

This is the simplest workflow — a single agent node.

---

## 7. Workflow 3: Question Generation Wizard (Multi-Phase)

Replaces: `api/service/question_wizard_handlers.go` + `api/agents/levelset_question_agent.go`

This is the most complex workflow, leveraging parallel execution, routing, checkpointing, and subgraphs.

### 7.1 State Schema

```json
{
  "type": "object",
  "properties": {
    "lesson_id": {"type": "string"},
    "course_id": {"type": "string"},
    "selected_level_set_ids": {
      "type": "array",
      "items": {"type": "string"},
      "description": "UUIDs of level sets to generate for"
    },
    "lesson_context": {
      "type": "object",
      "description": "Full lesson context with skills, level sets, grade, subject"
    },
    "reference_content": {
      "type": "string",
      "description": "extraction.md content from Google Drive"
    },
    "existing_counts": {
      "type": "object",
      "description": "Map of levelSetId -> existing question count"
    },
    "plan": {
      "type": "array",
      "description": "Planned generation targets per level set"
    },
    "plan_confirmed": {
      "type": "boolean",
      "description": "Whether user confirmed the plan (set via checkpoint resume)"
    },
    "level_set_results": {
      "type": "object",
      "description": "Map of levelSetId -> generated questions"
    },
    "all_questions": {
      "type": "array",
      "description": "Combined questions from all level sets"
    },
    "phase": {
      "type": "string",
      "enum": ["planning", "awaiting_confirmation", "generating", "completed", "failed"]
    }
  },
  "required": ["lesson_id", "course_id", "selected_level_set_ids"]
}
```

### 7.2 Workflow Definition

```json
{
  "name": "Question Generation Wizard",
  "description": "Multi-phase question generation with planning, user confirmation, and parallel generation",
  "is_template": true,
  "state_schema": "<state schema above>",
  "nodes": [
    {
      "node_id": "fetch_context",
      "node_type": "AGENT",
      "agent_id": "<context_fetcher_agent_id>",
      "config": {
        "description": "Fetch lesson context, existing counts, reference content from Go API and Google Drive"
      }
    },
    {
      "node_id": "planner",
      "node_type": "AGENT",
      "agent_id": "<question_planner_agent_id>"
    },
    {
      "node_id": "confirmation_gate",
      "node_type": "ROUTER",
      "router_config": {
        "routes": [
          {
            "condition": "state.get('plan_confirmed', False) == True",
            "target": "parallel_generators"
          }
        ],
        "default": "__end__"
      }
    },
    {
      "node_id": "parallel_generators",
      "node_type": "PARALLEL",
      "parallel_nodes": [],
      "config": {
        "fan_out_key": "plan",
        "description": "Fan-out to one generator per level set in the plan"
      }
    },
    {
      "node_id": "levelset_generator",
      "node_type": "AGENT",
      "agent_id": "<levelset_question_generator_agent_id>"
    },
    {
      "node_id": "join_results",
      "node_type": "JOIN",
      "config": {
        "aggregation_strategy": "merge",
        "output_key": "level_set_results"
      }
    },
    {
      "node_id": "validator",
      "node_type": "AGENT",
      "agent_id": "<blocknote_validation_agent_id>",
      "config": {
        "description": "Validate all generated questions"
      }
    }
  ],
  "edges": [
    {"source_node": "__start__", "target_node": "fetch_context"},
    {"source_node": "fetch_context", "target_node": "planner"},
    {"source_node": "planner", "target_node": "confirmation_gate"},
    {"source_node": "confirmation_gate", "target_node": "parallel_generators", "condition": "state.get('plan_confirmed', False) == True"},
    {"source_node": "confirmation_gate", "target_node": "__end__", "condition": "default"},
    {"source_node": "parallel_generators", "target_node": "levelset_generator"},
    {"source_node": "levelset_generator", "target_node": "join_results"},
    {"source_node": "join_results", "target_node": "validator"},
    {"source_node": "validator", "target_node": "__end__"}
  ]
}
```

### 7.3 Graph Visualization

```
[START]
   │
   ▼
[fetch_context] ── Uses: go_api_callback + google_drive tools
   │                 Fetches lesson skills, level sets, existing counts, extraction.md
   ▼
[planner] ── Calculates target counts, question type distribution per level set
   │
   ▼
[confirmation_gate] ── ROUTER
   │
   ├─── plan_confirmed == True ───┐
   │                               ▼
   │                      [parallel_generators] ── PARALLEL fan-out on plan[]
   │                               │
   │                    ┌──────────┼──────────┐
   │                    ▼          ▼          ▼
   │              [gen_ls_1]  [gen_ls_2]  [gen_ls_N]  ── Each generates questions
   │                    │          │          │           for one level set
   │                    └──────────┼──────────┘
   │                               ▼
   │                      [join_results] ── Merge all generated questions
   │                               │
   │                               ▼
   │                        [validator] ── Validate BlockNote format
   │                               │
   │                               ▼
   └─── plan_confirmed != True ──► [END]
                                   │
                                   ▼
                                 [END]
```

### 7.4 Multi-Phase Execution with Checkpointing

The wizard workflow uses checkpointing to implement the confirmation gate:

**Phase 1: Planning**

```bash
# Start execution — runs through fetch_context → planner → confirmation_gate → __end__
# (plan_confirmed is not set, so confirmation_gate routes to __end__)
curl -X POST http://localhost:8000/api/v1/executions \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "workflow_id": "<wizard_workflow_id>",
    "input": {
      "lesson_id": "...",
      "course_id": "...",
      "selected_level_set_ids": ["ls-1", "ls-2", "ls-3"]
    }
  }'

# Response includes thread_id and output_data with the plan
# {
#   "thread_id": "abc123",
#   "output_data": {
#     "plan": [...],
#     "phase": "awaiting_confirmation"
#   }
# }
```

**Phase 2: User reviews plan, optionally edits targets**

The Go API presents the plan to the user. User confirms.

**Phase 3: Resume with confirmation**

```bash
# Resume execution on the same thread with plan_confirmed = true
curl -X POST http://localhost:8000/api/v1/executions \
  -H "X-API-Key: $API_KEY" \
  -d '{
    "workflow_id": "<wizard_workflow_id>",
    "thread_id": "abc123",
    "input": {
      "plan_confirmed": true,
      "plan": [<possibly modified plan>]
    }
  }'

# This resumes from the confirmation_gate checkpoint
# plan_confirmed is now true → routes to parallel_generators
# Parallel generation runs, results are joined and validated
```

### 7.5 Key Improvement: Parallel Execution

The Go API uses a fixed pool of 3 goroutines processing level sets from a channel. The orchestrator uses LangGraph's `Send` API for true data-parallel fan-out:

- Each level set in the plan becomes a separate `Send` target
- All level sets execute concurrently (not limited to 3 workers)
- The join node aggregates results automatically
- Failures in one level set don't block others

---

## 8. Workflow 4: Combined End-to-End Pipeline

A combined workflow that chains document processing into question generation, using subgraphs.

### 8.1 Workflow Definition

```json
{
  "name": "End-to-End Document to Questions Pipeline",
  "description": "Processes a document, extracts problems, plans question generation, and generates questions — all in one workflow",
  "is_template": true,
  "nodes": [
    {
      "node_id": "document_processing",
      "node_type": "SUBGRAPH",
      "subgraph_workflow_id": "<document_processing_workflow_id>",
      "config": {
        "description": "Run full document processing pipeline as subgraph"
      }
    },
    {
      "node_id": "planner",
      "node_type": "AGENT",
      "agent_id": "<question_planner_agent_id>",
      "config": {
        "description": "Plan question generation based on extracted problems and level sets"
      }
    },
    {
      "node_id": "parallel_generators",
      "node_type": "PARALLEL",
      "config": {
        "fan_out_key": "plan"
      }
    },
    {
      "node_id": "levelset_generator",
      "node_type": "AGENT",
      "agent_id": "<levelset_question_generator_agent_id>"
    },
    {
      "node_id": "join_results",
      "node_type": "JOIN",
      "config": {
        "aggregation_strategy": "merge",
        "output_key": "level_set_results"
      }
    },
    {
      "node_id": "save_results",
      "node_type": "AGENT",
      "agent_id": "<results_saver_agent_id>",
      "config": {
        "description": "Save questions to Go API and extraction to Google Drive"
      }
    }
  ],
  "edges": [
    {"source_node": "__start__", "target_node": "document_processing"},
    {"source_node": "document_processing", "target_node": "planner"},
    {"source_node": "planner", "target_node": "parallel_generators"},
    {"source_node": "parallel_generators", "target_node": "levelset_generator"},
    {"source_node": "levelset_generator", "target_node": "join_results"},
    {"source_node": "join_results", "target_node": "save_results"},
    {"source_node": "save_results", "target_node": "__end__"}
  ]
}
```

### 8.2 Graph Visualization

```
[START]
   │
   ▼
[document_processing] ──── SUBGRAPH ────────────────────────┐
│  [ocr] → [analyze] → [gen_instructions] → [extract] → [verify]  │
└───────────────────────────────────────────────────────────┘
   │
   ▼
[planner] ── Uses extracted problems as reference content for planning
   │
   ▼
[parallel_generators] ── Fan-out per level set
   │
   ├────┼────┤
   ▼    ▼    ▼
[gen] [gen] [gen] ── Each uses extracted problems as reference
   │    │    │
   └────┼────┘
        ▼
[join_results]
        │
        ▼
[save_results] ── Uses: go_api_callback + google_drive tools
        │
        ▼
      [END]
```

This workflow does not exist in the Go API. It is only possible because the orchestrator supports subgraphs and composable workflows.

---

## 9. Integration with Go API (HTTP Tool Callbacks)

The agent-orchestrator runs as a separate service. The Go API integrates with it through HTTP calls.

### 9.1 Go API → Orchestrator

The Go API triggers workflow executions when users interact with the UI:

```
Go API Handler                    Agent Orchestrator
─────────────                     ──────────────────
POST /document-processing    →    POST /api/v1/executions (document processing workflow)
GET  /document-processing/status →    GET /api/v1/executions/{id} (poll status)
                                  GET /api/v1/executions/{id}/stream (SSE events)

POST /wizard-sessions        →    POST /api/v1/executions (wizard workflow)
POST /wizard-sessions/confirm →   POST /api/v1/executions (resume with plan_confirmed=true)
GET  /wizard-sessions/status →    GET /api/v1/executions/{id}

POST /questions/generate     →    POST /api/v1/executions (simple generation workflow)
```

### 9.2 Orchestrator → Go API

Agents use the `go_api_callback` tool to call back to the Go API:

| Callback | Purpose | Go API Endpoint |
|---|---|---|
| Fetch lesson context | Get lesson name, skills, level sets, grade, subject | `GET /api/lessons/{id}/full` |
| Fetch existing counts | Get current question counts per level set | `GET /api/levelsets/{id}/question-count` |
| Save questions | Save generated questions to database | `POST /api/questions/bulk` |
| Accept questions | Mark questions as accepted | `POST /api/wizard-sessions/{id}/accept` |
| Update status | Report progress back to Go API | `PUT /api/wizard-sessions/{id}/status` |

### 9.3 Status Mapping

| Orchestrator Status | Go API Wizard Phase |
|---|---|
| `PENDING` | `pending` |
| `RUNNING` (at planner node) | `planning` |
| `RUNNING` (at confirmation_gate, routed to __end__) | `plan_complete` |
| `RUNNING` (at parallel_generators) | `generating` |
| `COMPLETED` | `completed` |
| `FAILED` | `failed` |

### 9.4 SSE Streaming Integration

The Go API can proxy the orchestrator's SSE stream to the frontend:

```go
// In Go API handler
func (h *Handler) StreamWizardProgress(w http.ResponseWriter, r *http.Request) {
    executionID := chi.URLParam(r, "executionId")

    // Proxy SSE from orchestrator
    resp, _ := http.Get(fmt.Sprintf("%s/api/v1/executions/%s/stream", orchestratorURL, executionID))
    defer resp.Body.Close()

    w.Header().Set("Content-Type", "text/event-stream")
    scanner := bufio.NewScanner(resp.Body)
    for scanner.Scan() {
        fmt.Fprintf(w, "%s\n", scanner.Text())
        w.(http.Flusher).Flush()
    }
}
```

Events emitted during execution:

```json
{"event_type": "node_start", "node_id": "planner", "timestamp": "..."}
{"event_type": "node_complete", "node_id": "planner", "data": {"plan": [...]}, "timestamp": "..."}
{"event_type": "node_start", "node_id": "levelset_generator", "data": {"parallel_item": {"levelSetCode": "7.1.1"}}}
{"event_type": "node_complete", "node_id": "levelset_generator", "data": {"questions": [...]}}
{"event_type": "execution_complete", "data": {"all_questions": [...]}}
```

---

## 10. Improvements Over the Go Implementation

### 10.1 Parallel Execution Without Fixed Worker Pool

**Go API:** Fixed pool of 3 goroutines with channel-based job distribution. If a lesson has 10 level sets, they are processed 3 at a time.

**Orchestrator:** LangGraph `Send` API enables true data-parallel fan-out. All level sets execute concurrently. The number of parallel executions is limited only by API rate limits, not hardcoded worker counts.

### 10.2 Checkpointed State Instead of In-Memory Sessions

**Go API:** Wizard sessions stored in-memory (`QuestionGenerationWizardSession`). Server restart loses all session state. No way to inspect intermediate state.

**Orchestrator:** PostgreSQL-backed checkpointing via LangGraph. Every node execution creates a state snapshot. Benefits:
- Survive restarts — resume from last checkpoint
- Inspect intermediate state at any node
- Support multi-turn interactions (plan → confirm → generate)
- Debug failed workflows by examining state at each step

### 10.3 Composable Workflows via Subgraphs

**Go API:** Document processing and question generation are completely separate code paths with no composition.

**Orchestrator:** The document processing pipeline can be embedded as a subgraph inside the wizard workflow or the end-to-end pipeline. The same pipeline definition is reused, not duplicated.

### 10.4 Declarative Routing Instead of Procedural If/Else

**Go API:** Control flow is embedded in handler code with explicit `if/else` branches and background channel messages.

**Orchestrator:** Router nodes with declarative condition expressions. The confirmation gate, diagram routing, and any future branching logic are defined as data, not code.

### 10.5 Provider-Agnostic Agent Definitions

**Go API:** LLM provider selection is configured globally or per-operation in Go code. Changing a provider requires code changes and redeployment.

**Orchestrator:** Each agent has its own `llm_config` with `provider`, `model_name`, and `max_tokens`. Change providers per-agent via API calls without redeployment. Mix providers in a single workflow (e.g., Anthropic for generation, OpenAI for validation).

### 10.6 Streaming Execution Events

**Go API:** Status polling via `GET /status` endpoint. No real-time progress updates during generation.

**Orchestrator:** SSE streaming via `GET /executions/{id}/stream`. Real-time events for each node start/complete. The frontend can show which level set is currently being generated.

### 10.7 Structured Output Validation

**Go API:** Manual JSON parsing with `extractJSONFromResponse()` that strips markdown code blocks and finds `{...}` boundaries. Fragile.

**Orchestrator:** `create_model_with_structured_output()` uses provider-native structured output (e.g., OpenAI function calling, Anthropic tool use) to guarantee valid JSON matching the schema. No manual parsing needed.

### 10.8 Tool-Based Architecture

**Go API:** Agents are pure LLM calls with no tool access. OCR, file operations, and API calls are done in Go handler code before/after the LLM call.

**Orchestrator:** Agents have access to tools (OCR, HTTP, file writer, calculator, custom tools). An agent can autonomously decide to call OCR, fetch additional context, or validate its own output using the tool loop (up to 10 iterations).

### 10.9 Reusable Workflow Templates

**Go API:** Each workflow is hardcoded in handler files. Creating a variation requires duplicating code.

**Orchestrator:** Workflows are stored as database records with `is_template = true`. Create variations by duplicating templates and modifying nodes/edges via API. No code changes needed for new workflow variations.

### 10.10 Centralized Execution History

**Go API:** AI usage tracked via `ai_usage_logs` table, but workflow execution history is ephemeral (in-memory sessions).

**Orchestrator:** Full execution history with per-node step records, input/output data, timestamps, and error messages. Every execution is persisted and queryable via `GET /api/v1/executions`.
