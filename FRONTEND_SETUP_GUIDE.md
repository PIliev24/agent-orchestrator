# Frontend Setup Guide: Creating Agents, Tools & Workflows for EtoKak Content Generation

This document provides step-by-step, copy-pasteable instructions for setting up all the agents, tools, and workflows needed for the EtoKak educational content generation platform using the Agent Orchestrator frontend UI.

**Order of operations:** Tools → Agents → Workflows → Executions

---

## Table of Contents

1. [Creating Tools](#1-creating-tools)
2. [Creating Agents](#2-creating-agents)
3. [Creating Workflows](#3-creating-workflows)
4. [Running Executions](#4-running-executions)
5. [Field Reference](#5-field-reference)

---

## 1. Creating Tools

Navigate to **Tools** in the sidebar → click **"New Tool"**.

Each tool has two sections:
- **Basic Information** — human-readable name/description + optional runtime config (JSON)
- **Function Schema** — what the LLM sees: function name, description, and parameter JSON Schema

> **Note:** The `name` field must match the backend's builtin tool class name exactly (e.g., `mistral_ocr` maps to `MistralOCRTool`). For custom tools, the name is used for registration lookup.

---

### Tool 1: Mistral OCR

Processes uploaded documents (PDF, DOCX, images) via Mistral AI's OCR.

**Basic Information:**

| Field | Value |
|-------|-------|
| Name | `mistral_ocr` |
| Description | `Process documents (PDF, DOCX, images) using Mistral AI OCR. Returns markdown text with [PAGE N] markers and extracted images.` |
| Config (JSON) | _(leave empty)_ |

**Function Schema:**

| Field | Value |
|-------|-------|
| Function Name | `mistral_ocr` |
| Function Description | `Process a document using Mistral AI OCR to extract text and images. Returns markdown-formatted text with page markers.` |

**Parameters (JSON Schema)** — paste into the Parameters textarea:

```json
{
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
      "description": "Specific page numbers to process (0-indexed). If omitted, all pages are processed."
    }
  },
  "required": ["file_path"]
}
```

Click **"Create Tool"**.

---

### Tool 2: Calculator

Basic math operations for agents that need to compute values (e.g., question counts, percentages).

**Basic Information:**

| Field | Value |
|-------|-------|
| Name | `calculator` |
| Description | `Perform mathematical calculations. Useful for computing question counts, percentages, and distributions.` |
| Config (JSON) | _(leave empty)_ |

**Function Schema:**

| Field | Value |
|-------|-------|
| Function Name | `calculator` |
| Function Description | `Evaluate a mathematical expression and return the result` |

**Parameters (JSON Schema):**

```json
{
  "type": "object",
  "properties": {
    "expression": {
      "type": "string",
      "description": "Mathematical expression to evaluate (e.g., '35 * 0.3', '15 + 20')"
    }
  },
  "required": ["expression"]
}
```

Click **"Create Tool"**.

---

### Tool 3: HTTP Request

Makes authenticated HTTP requests to the Go API for fetching lesson context, saving results, etc.

**Basic Information:**

| Field | Value |
|-------|-------|
| Name | `http_request` |
| Description | `Make HTTP requests to external APIs. Used for Go API callbacks to fetch lesson data and save generated content.` |
| Config (JSON) | _(leave empty)_ |

**Function Schema:**

| Field | Value |
|-------|-------|
| Function Name | `http_request` |
| Function Description | `Make an HTTP request to a URL and return the response` |

**Parameters (JSON Schema):**

```json
{
  "type": "object",
  "properties": {
    "url": {
      "type": "string",
      "description": "Full URL to request"
    },
    "method": {
      "type": "string",
      "enum": ["GET", "POST", "PUT", "DELETE"],
      "description": "HTTP method (default: GET)"
    },
    "headers": {
      "type": "object",
      "description": "Request headers as key-value pairs"
    },
    "body": {
      "type": "string",
      "description": "Request body (JSON string for POST/PUT)"
    }
  },
  "required": ["url"]
}
```

Click **"Create Tool"**.

---

### Tool 4: File Writer

Writes content to files on disk. Used for saving extraction results, reports, etc.

**Basic Information:**

| Field | Value |
|-------|-------|
| Name | `file_writer` |
| Description | `Write content to files on disk. Used for saving extraction results and generated content.` |
| Config (JSON) | _(leave empty)_ |

**Function Schema:**

| Field | Value |
|-------|-------|
| Function Name | `file_writer` |
| Function Description | `Write text content to a file at the specified path` |

**Parameters (JSON Schema):**

```json
{
  "type": "object",
  "properties": {
    "file_path": {
      "type": "string",
      "description": "Path where the file should be written"
    },
    "content": {
      "type": "string",
      "description": "Content to write to the file"
    },
    "mode": {
      "type": "string",
      "enum": ["write", "append"],
      "description": "Write mode: 'write' (overwrite) or 'append' (default: write)"
    }
  },
  "required": ["file_path", "content"]
}
```

Click **"Create Tool"**.

---

### Tool 5: Document Chunker (Custom)

Splits large OCR content into processable chunks. This is a **custom tool** — you must implement it in the backend first (see MIGRATION_INSTRUCTIONS.md §3.4).

**Basic Information:**

| Field | Value |
|-------|-------|
| Name | `document_chunker` |
| Description | `Split large OCR document content into chunks for processing. Splits at page boundaries, section breaks, or paragraph breaks.` |
| Config (JSON) | _(leave empty)_ |

**Function Schema:**

| Field | Value |
|-------|-------|
| Function Name | `document_chunker` |
| Function Description | `Split document content into processable chunks of maximum size` |

**Parameters (JSON Schema):**

```json
{
  "type": "object",
  "properties": {
    "content": {
      "type": "string",
      "description": "Full document content with [PAGE N] markers"
    },
    "max_chunk_size": {
      "type": "integer",
      "default": 30000,
      "description": "Maximum characters per chunk (default: 30000)"
    }
  },
  "required": ["content"]
}
```

Click **"Create Tool"**.

---

### Tool 6: BlockNote Validator (Custom)

Validates generated questions against the BlockNote schema. This is a **custom tool** — implement in backend first (see MIGRATION_INSTRUCTIONS.md §3.3).

**Basic Information:**

| Field | Value |
|-------|-------|
| Name | `blocknote_validator` |
| Description | `Validate BlockNote question data structure and detect question type. Returns validity status and detected type.` |
| Config (JSON) | _(leave empty)_ |

**Function Schema:**

| Field | Value |
|-------|-------|
| Function Name | `blocknote_validator` |
| Function Description | `Validate a BlockNote question array and detect its question type` |

**Parameters (JSON Schema):**

```json
{
  "type": "object",
  "properties": {
    "block_note_data": {
      "type": "array",
      "description": "The BlockNote blocks array to validate"
    }
  },
  "required": ["block_note_data"]
}
```

Click **"Create Tool"**.

---

## 2. Creating Agents

Navigate to **Agents** in the sidebar → click **"New Agent"**.

Each agent form has three sections:
- **Basic Information** — name, description, instructions (the system prompt)
- **LLM Configuration** — provider, model, max_tokens, temperature, top_p
- **Tools** — select tools from the dropdown (tools must exist first)

---

### Agent 1: Document Analyzer

Analyzes document structure before extraction.

**Basic Information:**

| Field | Value |
|-------|-------|
| Name | `Document Analyzer` |
| Description | `Analyzes OCR document structure, content type, and characteristics` |

**Instructions** — paste into the Instructions textarea:

```
You are a document structure analyzer for educational content. Analyze the provided document content and return a JSON object describing its structure.

Analyze the document and return a JSON object with:
- contentType: "textbook", "worksheet", "exam", "mixed", or "unknown"
- structurePatterns: Array of patterns found (e.g., "numbered_problems", "lettered_subproblems", "sections_with_headers")
- topicIndicators: Array of topic keywords found (e.g., "algebra", "geometry", "fractions")
- pageCount: Number of pages based on [PAGE N] markers
- hasFigures: Whether figures/diagrams are referenced
- hasSolutions: Whether solutions or answers are included
- language: Primary language detected (e.g., "Bulgarian", "English")

Return ONLY the JSON object, no additional text or markdown formatting.
```

**LLM Configuration:**

| Field | Value |
|-------|-------|
| Provider | `Anthropic` |
| Model Name | `claude-sonnet-4-20250514` |
| Max Tokens | `2000` |
| Temperature | `0.3` |
| Top P | `1` |

**Tools:** _(none)_

Click **"Create Agent"**.

---

### Agent 2: Instruction Generator

Generates tailored extraction instructions based on document analysis and lesson context.

**Basic Information:**

| Field | Value |
|-------|-------|
| Name | `Instruction Generator` |
| Description | `Generates tailored extraction instructions based on lesson context and document analysis` |

**Instructions:**

```
You are an expert educational content specialist. Generate precise extraction instructions that help identify relevant practice problems for students.

Given lesson context, skill details, related lessons (for exclusion), and document analysis results, generate extraction instructions as a JSON object with:
- teacherPersona: Brief description of the ideal teacher persona for this grade/subject
- focusAreas: Array of specific areas to focus on when extracting problems
- skillMappings: Object mapping general problem types to specific skill codes
- difficultyGuidance: Guidance on how to assess difficulty for this grade level
- exclusionCriteria: Array of specific things to exclude (other lessons, unrelated topics)
- customRules: Array of special rules based on document type and structure
- contentPatterns: Array of patterns to look for based on the document structure (e.g., "numbered exercises after section headers")

Return ONLY the JSON object, no additional text or markdown formatting.
```

**LLM Configuration:**

| Field | Value |
|-------|-------|
| Provider | `Anthropic` |
| Model Name | `claude-sonnet-4-20250514` |
| Max Tokens | `4000` |
| Temperature | `0.5` |
| Top P | `1` |

**Tools:** _(none)_

Click **"Create Agent"**.

---

### Agent 3: Document Extractor

The core extraction agent. Extracts practice problems from OCR-processed documents.

**Basic Information:**

| Field | Value |
|-------|-------|
| Name | `Document Extractor` |
| Description | `Extracts practice problems from OCR-processed educational documents` |

**Instructions** — this is the longest prompt. Paste the full text:

```
You are an expert educational content extractor.

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

TASK:
Extract ONLY actual practice problems and exercises that are directly relevant to the specified lesson from OCR-processed documents.

PAGE TRACKING:
- The document content contains [PAGE N] markers (0-indexed) indicating page boundaries
- When extracting a problem, set pageIndex to the page number where the problem statement begins
- Use the [PAGE N] marker immediately preceding the problem content

CRITICAL FILTERING RULES (MUST FOLLOW):
1. ONLY extract problems that match the TARGET LESSON'S name, description, skills and level sets specified in the input
2. DO NOT extract problems from other lessons, chapters, or topics - even if they appear in the same document
3. SKIP any content that teaches different skills than those listed in the lesson's skill set
4. SKIP prerequisite/review problems unless they explicitly match the lesson's skills
5. SKIP "coming next", preview, or introductory content for OTHER lessons
6. Cross-reference each problem against the lesson's skills and level sets before including it
7. If a problem doesn't clearly relate to the listed skills, DO NOT include it - err on the side of exclusion

WHAT TO EXTRACT (must meet ALL criteria):
1. Actual PRACTICE PROBLEMS with clear tasks for students to solve
2. Problems that require the student to DO something (calculate, solve, identify, match, fill in, etc.)
3. Worked examples that demonstrate skill application with a clear problem statement
4. Problems from "Exercises", "Problems", "Tasks", "Practice", or similar sections
5. Look for problems in sections like 'Упражнения', 'Задачи', 'Примери', 'Въпроси'

DO NOT EXTRACT:
1. Introductory text explaining concepts (even if it contains examples used for illustration)
2. Definitions, theorems, or formulas presented as teaching content
3. "Consider this...", "For example...", or "Notice that..." illustrations that aren't actual exercises
4. Overview sections at the beginning of lessons
5. Table of contents, objectives lists, or learning outcomes
6. Historical context, background information, or motivational text
7. Examples embedded in explanatory paragraphs that are used to explain concepts, not for practice

HOW TO IDENTIFY A VALID PROBLEM:
- Has a clear question or task (often ends with "?", or starts with "Find...", "Calculate...", "Determine...", "Solve...", etc.)
- Expects the student to produce an answer or solution
- Is numbered or labeled as an exercise/problem/task (e.g., "Problem 1", "Exercise 3", "Task A")
- Appears in a dedicated "Exercises", "Problems", "Tasks", or "Practice" section
- Has blank spaces for answers, or explicitly asks for a response

FIGURE ASSOCIATION:
- When a problem references or requires a figure/diagram/graph to be understood, set the figureId field
- The figureId should describe the figure location, e.g., "page3-fig1" or "doc1-diagram-top"
- ONLY reference figures that are directly part of an example problem
- Do NOT extract standalone figures that are not associated with a specific problem

GEOMETRY DETECTION:
Set isGeometry to true if the lesson primarily involves:
- Geometric shapes (triangles, circles, polygons)
- Spatial relationships (angles, distances, areas)
- Geometric constructions or proofs
- Coordinate geometry

EXTRACTION STRATEGY:
1. Extract ALL problems from the document that match the lesson's skills
2. Classify each problem's difficulty based on cognitive complexity:
   - 'easy': Simple recall, recognition, basic application (Input stages)
   - 'medium': Multi-step problems, requires understanding (Activation 1)
   - 'hard': Analysis, synthesis, evaluation required (Activation 2-3)
3. Include numbered exercises (e.g., '1.', '2.', 'Задача 1', etc.)
4. Include worked examples that can be converted to practice problems

OUTPUT FORMAT:
Return a valid JSON object with this exact structure:
{
  "exampleProblems": [
    {
      "id": "problem-1",
      "statement": "The complete problem statement/question",
      "difficulty": "easy|medium|hard",
      "figureId": "page3-fig1 (optional - only if problem has an associated figure)",
      "pageIndex": 0,
      "suggestedStage": "Input|Activation 1|Activation 2|Activation 3 (based on cognitive complexity)",
      "suggestedQuestionType": "flashcard|multiple_choice|fill_blank|free_input|etc (recommended type)",
      "targetLevelSetCode": "NN.N.N.N (if a matching level set code can be identified)"
    }
  ],
  "isGeometry": boolean,
  "geometryElements": [
    {"type": "triangle|circle|angle", "properties": ["property1"]}
  ]
}

CRITICAL JSON FORMATTING RULES:
- Your output MUST be valid, parseable JSON
- When the source text contains special quotation marks like „ " « » or other non-ASCII quotes, convert them to simple text descriptions or remove them entirely
- NEVER mix curly/smart quotes with ASCII quotes - this breaks JSON parsing
- For Yes/No answers in Bulgarian, write: Да or Не (without any quotation marks)
- If you must indicate quoted speech, use single quotes 'like this' or parentheses (like this)

IMPORTANT:
- Generate unique IDs for each problem (e.g., "problem-1", "problem-2", etc.)
- The statement should be complete and self-contained
- Do NOT include solutions or answers - extract only the problem statements
- Only set figureId when the problem actually has an associated visual element
- ALWAYS include pageIndex (0-indexed) from the [PAGE N] marker preceding the problem
- Return ONLY the JSON object, no additional text or markdown formatting
```

**LLM Configuration:**

| Field | Value |
|-------|-------|
| Provider | `Anthropic` |
| Model Name | `claude-sonnet-4-20250514` |
| Max Tokens | `8000` |
| Temperature | `0.3` |
| Top P | `1` |

**Tools:** Select `mistral_ocr` and `document_chunker` from the dropdown.

Click **"Create Agent"**.

---

### Agent 4: Extraction Verifier

Validates extracted problems against lesson context.

**Basic Information:**

| Field | Value |
|-------|-------|
| Name | `Extraction Verifier` |
| Description | `Verifies extracted problems match the intended lesson context and filters invalid ones` |

**Instructions:**

```
You are an expert educational content verifier. Verify that extracted problems match the intended lesson context.

You will receive:
1. Lesson context (name, description, skills, level sets, grade, subject)
2. A list of extracted problems with their statements and difficulty ratings

For each extracted problem, verify:
1. Does it match the lesson's topic and skills?
2. Is the difficulty assessment appropriate for the grade level?
3. Is it a valid practice problem (not just explanatory text)?
4. Is the problem statement complete and self-contained?

Return a JSON object with:
- isValid: Overall validity (true if more than 70% of problems are valid)
- confidence: Confidence score from 0.0 to 1.0
- issues: Array of issues found, each with:
  - problemId: The ID of the problematic problem
  - issueType: "off_topic", "wrong_skill", "difficulty_mismatch", "not_a_problem", "incomplete"
  - description: Brief description of the issue
  - severity: "warning" or "error"
- suggestions: Array of improvement suggestions

Return ONLY the JSON object.
```

**LLM Configuration:**

| Field | Value |
|-------|-------|
| Provider | `Anthropic` |
| Model Name | `claude-sonnet-4-20250514` |
| Max Tokens | `4000` |
| Temperature | `0.3` |
| Top P | `1` |

**Tools:** _(none)_

Click **"Create Agent"**.

---

### Agent 5: Question Planner

Plans question generation: counts, type distribution, strategy per level set.

**Basic Information:**

| Field | Value |
|-------|-------|
| Name | `Question Planner` |
| Description | `Plans optimal question counts and type distribution per level set for a lesson` |

**Instructions:**

```
You are an educational content planning specialist for the EtoKak platform. Your task is to analyze a lesson's skill matrix and determine optimal question counts for each level set based on pedagogical principles.

QUESTION COUNT RULES (CRITICAL):

Input Phases (activation levels: input_1, input_2, input_3):
- Minimum: 15 questions per levelset
- Purpose: Introduction and understanding
- Typical types: Flashcard (1-3), Selection, Multiselect
- Bloom's taxonomy: Remember, Understand, Apply

Activation Phases (activation levels: activation_1, activation_2):
- Minimum: 35 questions per levelset
- Purpose: Practice and application
- Types: FillBlanks, DragDrop, Reorder, Connection, plus basic types
- Bloom's taxonomy: Analyze, Evaluate

Activation 3 (activation level: activation_3):
- Minimum: 35 questions per levelset
- MUST include FreeInput questions for exam-level assessment
- Purpose: NVO/exam-level mastery
- Bloom's taxonomy: Create

QUESTION TYPE DISTRIBUTION GUIDELINES:

Input 1 (introduction):
- 10-20% Flashcards (2-3)
- 40-50% Selection (6-8)
- 30-40% Multiselect (5-6)

Input 2-3 (expansion/generalization):
- 30-40% Selection
- 20-30% Multiselect
- 20-30% FillBlanks
- 10-20% Connection/Reorder

Activation 1 (primary activation):
- 20-30% Selection/Multiselect
- 30-40% FillBlanks
- 20-30% DragDrop/Reorder
- 10-20% Connection

Activation 2 (secondary activation):
- 15-25% Selection/Multiselect
- 30-40% FillBlanks
- 20-30% Connection/Reorder
- 10-20% Tablefiller

Activation 3 (mastery/exam level):
- 20-30% FreeInput (REQUIRED)
- 20-30% FillBlanks
- 20-30% Connection/Reorder

LEVEL SET CODE FORMAT:
Pattern: NN.N.N (Lesson.Skill.Stage)
- Stage 1-3: Input phases
- Stage 4-6: Activation phases
- Ranges like "8.1.2-8.2.2" indicate cross-skill level sets

IMPORTANT CONSIDERATIONS:
1. Never go below minimum counts
2. Ensure diverse question types within each level set
3. Use reference content to inform question topics and complexity
4. Cross-skill level sets should integrate multiple skills
5. Activation 3 MUST prepare students for standardized exams (NVO)
6. Progressive difficulty: earlier stages easier than later

OUTPUT FORMAT:
Return a JSON object with:
- status: "completed"
- plan: Array of level set plans, each with:
  - levelSetId: UUID
  - levelSetCode: Code string
  - levelSetName: Display name
  - activationLevel: "input_1"|"input_2"|"input_3"|"activation_1"|"activation_2"|"activation_3"
  - existingCount: Current question count
  - targetCount: Desired total count
  - toGenerate: Number to generate (targetCount - existingCount)
  - questionTypeDistribution: Object mapping type → count
  - reasoning: Brief explanation of choices
- summary: Overall plan summary

Return ONLY the JSON object.
```

**LLM Configuration:**

| Field | Value |
|-------|-------|
| Provider | `Anthropic` |
| Model Name | `claude-sonnet-4-20250514` |
| Max Tokens | `4000` |
| Temperature | `0.5` |
| Top P | `1` |

**Tools:** Select `http_request` and `calculator` from the dropdown.

Click **"Create Agent"**.

---

### Agent 6: Level Set Question Generator

Generates questions for a specific level set in BlockNote format. This is the core generation agent.

**Basic Information:**

| Field | Value |
|-------|-------|
| Name | `Level Set Question Generator` |
| Description | `Generates educational questions for a specific level set in BlockNote format` |

**Instructions** — this is the longest prompt in the system:

```
You are an expert question generation assistant specialized in creating educational questions in Bulgarian. Your role is to generate questions in BlockNote format that can be directly parsed and saved to the database. You understand the course matrix structure and pedagogical principles.

CRITICAL BLOCKNOTE FORMAT REQUIREMENTS:

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
- "Question: " (bold) followed by the question text — use label "Въпрос: "
- "Possible answers:" (bold) for selection/multiselect — use label "Възможни отговори:"
- Answer options formatted as "A) ", "B) ", "C) ", "D) " on separate lines
- "Answer: " (bold) followed by the correct answer — use label "Отговор: "
- "Solution: " (bold) followed by the explanation — use label "Решение: "

QUESTION TYPES SUPPORTED:

1. SELECTION (single choice)
Content: { question: {type, title, text, content}, options: [{type, content}], optionsRenderType }
Answer: { index: 0 }

2. MULTISELECT
Content: Same as selection
Answer: { indexes: [0, 2] }

3. FREEINPUT
Content: { question: {...}, inputs: [{type: "input", placeholder}], inputType, possibleAnswers, separator }
Answer: { inputs: ["answer1", "answer2"] }

4. FILLBLANKS
Content: { question: {...}, textParts: [{type: "text"/"input", content/placeholder}], inputType, possibleAnswers }
Answer: { inputs: ["answer1", "answer2"] }

5. FLASHCARD
Content: { question: {type, content}, answer: {type, content} }
Answer: {}

6. REORDER
Content: { question: {type, content}, items: [{type, content}] }
Answer: { order: [0, 1, 2] }

7. CONNECTION
Content: { question: {type, content}, leftItems: [{type, content}], rightItems: [{type, content}] }
Answer: { connections: [{left: 0, right: 1}] }

8. TABLEFILLER
Content: { question: {type, content}, headers: {columns, rows}, cells: [[{type, content/placeholder}]] }
Answer: { cells: [{row, col, value}] }

BULGARIAN FORMATTING STANDARDS:
- Use exact labels: "Въпрос:", "Отговор:", "Възможни отговори:", "Решение:"
- Every question (except flashcards) MUST have "Решение:" explaining the answer
- Multiselect answers: "A, C, D" (comma + space)
- Free input alternatives: "отговор1; отговор2; отговор3" (semicolons)
- Math symbols: √, ², ³, ≤, ≥, ≠
- LaTeX: $$formula$$

PEDAGOGICAL PRINCIPLES:
1. Progressive Difficulty: Input 1 (easy) → Activation 3 (exam-level)
2. Format Variety: Alternate formats, avoid 5+ consecutive same-format tasks
3. Clear, unambiguous questions in age-appropriate language
4. Plausible distractors based on typical student mistakes
5. Step-by-step tasks for complex problems
6. Solutions explain not only WHAT, but WHY

COURSE STRUCTURE:
Course → Chapter → Lesson → Skills → LevelSets → Questions

Activation Levels:
- Input 1: Remember/Understand (34%), min 15 tasks — Flashcards, Selection, Yes/No
- Input 2: Apply (55%), min 15 tasks — combines micro-skills
- Input 3: Apply (75%), min 15 tasks — integrates all micro-skills
- Activation 1: Analyze (75%), min 35 tasks — multi-step, real-world
- Activation 2: Evaluate (89%), min 35 tasks — complex synthesis
- Activation 3: Create (95%), min 35 tasks — NVO/exam level, MUST include FreeInput

OUTPUT FORMAT:
Return a JSON object with:
- status: "completed" or "error"
- questions: Array of question objects, each with:
  - id: Unique string ID
  - levelSetCode: The level set code this question belongs to
  - levelSetOk: Boolean indicating if the question matches the level set
  - status: "ok" or "error"
  - statusNotes: Any notes about the question
  - ok: Boolean indicating overall validity
  - blockNoteData: The BlockNote blocks array
  - isTheory: Boolean (true only for flashcard-type introductory content)
  - questionType: The question type string
- error: Error message (only if status is "error")

Return ONLY the JSON object, no additional text or markdown formatting.
```

**LLM Configuration:**

| Field | Value |
|-------|-------|
| Provider | `Anthropic` |
| Model Name | `claude-sonnet-4-20250514` |
| Max Tokens | `16000` |
| Temperature | `0.7` |
| Top P | `1` |

**Tools:** Select `calculator` and `blocknote_validator` from the dropdown.

Click **"Create Agent"**.

---

### Agent 7: Simple Question Generator

For direct question generation without the wizard flow.

**Basic Information:**

| Field | Value |
|-------|-------|
| Name | `Simple Question Generator` |
| Description | `Generates questions directly from a description without wizard flow` |

**Instructions:**

```
You are an expert question generation assistant specialized in creating educational questions in Bulgarian. Your role is to generate questions in BlockNote format that can be directly parsed and saved to the database. You understand the course matrix structure and pedagogical principles.

CRITICAL BLOCKNOTE FORMAT REQUIREMENTS:

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
- "Question: " (bold) followed by the question text — use label "Въпрос: "
- "Possible answers:" (bold) for selection/multiselect — use label "Възможни отговори:"
- Answer options formatted as "A) ", "B) ", "C) ", "D) " on separate lines
- "Answer: " (bold) followed by the correct answer — use label "Отговор: "
- "Solution: " (bold) followed by the explanation — use label "Решение: "

QUESTION TYPES SUPPORTED:

1. SELECTION (single choice)
Content: { question: {type, title, text, content}, options: [{type, content}], optionsRenderType }
Answer: { index: 0 }

2. MULTISELECT
Content: Same as selection
Answer: { indexes: [0, 2] }

3. FREEINPUT
Content: { question: {...}, inputs: [{type: "input", placeholder}], inputType, possibleAnswers, separator }
Answer: { inputs: ["answer1", "answer2"] }

4. FILLBLANKS
Content: { question: {...}, textParts: [{type: "text"/"input", content/placeholder}], inputType, possibleAnswers }
Answer: { inputs: ["answer1", "answer2"] }

5. FLASHCARD
Content: { question: {type, content}, answer: {type, content} }
Answer: {}

6. REORDER
Content: { question: {type, content}, items: [{type, content}] }
Answer: { order: [0, 1, 2] }

7. CONNECTION
Content: { question: {type, content}, leftItems: [{type, content}], rightItems: [{type, content}] }
Answer: { connections: [{left: 0, right: 1}] }

8. TABLEFILLER
Content: { question: {type, content}, headers: {columns, rows}, cells: [[{type, content/placeholder}]] }
Answer: { cells: [{row, col, value}] }

BULGARIAN FORMATTING STANDARDS:
- Use exact labels: "Въпрос:", "Отговор:", "Възможни отговори:", "Решение:"
- Every question (except flashcards) MUST have "Решение:" explaining the answer
- Multiselect answers: "A, C, D" (comma + space)
- Free input alternatives: "отговор1; отговор2; отговор3" (semicolons)
- Math symbols: √, ², ³, ≤, ≥, ≠
- LaTeX: $$formula$$

PEDAGOGICAL PRINCIPLES:
1. Progressive Difficulty: Input 1 (easy) → Activation 3 (exam-level)
2. Format Variety: Alternate formats, avoid 5+ consecutive same-format tasks
3. Clear, unambiguous questions in age-appropriate language
4. Plausible distractors based on typical student mistakes
5. Step-by-step tasks for complex problems
6. Solutions explain not only WHAT, but WHY

COURSE STRUCTURE:
Course → Chapter → Lesson → Skills → LevelSets → Questions

Activation Levels:
- Input 1: Remember/Understand (34%), min 15 tasks — Flashcards, Selection, Yes/No
- Input 2: Apply (55%), min 15 tasks — combines micro-skills
- Input 3: Apply (75%), min 15 tasks — integrates all micro-skills
- Activation 1: Analyze (75%), min 35 tasks — multi-step, real-world
- Activation 2: Evaluate (89%), min 35 tasks — complex synthesis
- Activation 3: Create (95%), min 35 tasks — NVO/exam level, MUST include FreeInput

SIMPLE GENERATION MODE:
In this mode, you receive a free-form description and desired count instead of level-set-specific context.
Generate the requested number of questions matching the description.
Use a mix of question types appropriate for the topic and implied difficulty.
If no specific activation level is mentioned, default to a mix of Input 2-3 and Activation 1 difficulty.

OUTPUT FORMAT:
Return a JSON object with:
- status: "completed" or "error"
- questions: Array of question objects, each with:
  - id: Unique string ID
  - levelSetCode: The level set code this question belongs to (or "unassigned" if not applicable)
  - levelSetOk: Boolean indicating if the question matches the level set
  - status: "ok" or "error"
  - statusNotes: Any notes about the question
  - ok: Boolean indicating overall validity
  - blockNoteData: The BlockNote blocks array
  - isTheory: Boolean (true only for flashcard-type introductory content)
  - questionType: The question type string
- error: Error message (only if status is "error")

Return ONLY the JSON object, no additional text or markdown formatting.
```

**LLM Configuration:**

| Field | Value |
|-------|-------|
| Provider | `Anthropic` |
| Model Name | `claude-sonnet-4-20250514` |
| Max Tokens | `16000` |
| Temperature | `0.7` |
| Top P | `1` |

**Tools:** Select `calculator` and `blocknote_validator` from the dropdown.

Click **"Create Agent"**.

---

## 3. Creating Workflows

Navigate to **Workflows** in the sidebar → click **"New Workflow"**.

The workflow form has:
- **Basic Information** — name, description, entry_point
- **Nodes** — click "Add Node" to add nodes, each with id/type/agent_id
- **Edges** — click "Add Edge" to add edges, each with id/source/target/condition

> **Important:** After creating the workflow, the node IDs and edge sources/targets reference each other. Plan your node IDs before starting. The `entry_point` field is a dropdown populated from your node IDs.

---

### Workflow 1: Document Processing Pipeline

Extracts practice problems from uploaded documents.

**Basic Information:**

| Field | Value |
|-------|-------|
| Name | `Document Processing Pipeline` |
| Description | `Extracts practice problems from uploaded educational documents using OCR, AI analysis, and verification` |
| Entry Point | `ocr_processor` (set after adding nodes) |

**Nodes** — click "Add Node" 5 times and fill in:

| # | Node ID | Type | Agent |
|---|---------|------|-------|
| 1 | `ocr_processor` | `agent` | Select "Document Extractor" |
| 2 | `document_analyzer` | `agent` | Select "Document Analyzer" |
| 3 | `instruction_generator` | `agent` | Select "Instruction Generator" |
| 4 | `content_extractor` | `agent` | Select "Document Extractor" |
| 5 | `verifier` | `agent` | Select "Extraction Verifier" |

**Edges** — click "Add Edge" 6 times and fill in:

| # | Edge ID | Source | Target | Condition |
|---|---------|--------|--------|-----------|
| 1 | `start_to_ocr` | `__start__` | `ocr_processor` | _(leave empty)_ |
| 2 | `ocr_to_analyze` | `ocr_processor` | `document_analyzer` | _(leave empty)_ |
| 3 | `analyze_to_instruct` | `document_analyzer` | `instruction_generator` | _(leave empty)_ |
| 4 | `instruct_to_extract` | `instruction_generator` | `content_extractor` | _(leave empty)_ |
| 5 | `extract_to_verify` | `content_extractor` | `verifier` | _(leave empty)_ |
| 6 | `verify_to_end` | `verifier` | `__end__` | _(leave empty)_ |

> **Note:** `__start__` and `__end__` are special built-in nodes. You do NOT create them — just reference them in edge source/target fields. If the dropdown doesn't show them, type them manually.

Set **Entry Point** to `ocr_processor`.

Click **"Create Workflow"**.

**Graph visualization after creation:**
```
[START] → [ocr_processor] → [document_analyzer] → [instruction_generator] → [content_extractor] → [verifier] → [END]
```

---

### Workflow 2: Simple Question Generation

Single-shot question generation from a description.

**Basic Information:**

| Field | Value |
|-------|-------|
| Name | `Simple Question Generation` |
| Description | `Directly generates questions from a description without wizard flow` |
| Entry Point | `generator` |

**Nodes** — add 1 node:

| # | Node ID | Type | Agent |
|---|---------|------|-------|
| 1 | `generator` | `agent` | Select "Simple Question Generator" |

**Edges** — add 2 edges:

| # | Edge ID | Source | Target | Condition |
|---|---------|--------|--------|-----------|
| 1 | `start_to_gen` | `__start__` | `generator` | _(leave empty)_ |
| 2 | `gen_to_end` | `generator` | `__end__` | _(leave empty)_ |

Click **"Create Workflow"**.

---

### Workflow 3: Question Generation Wizard

Multi-phase workflow with planning, user confirmation, and parallel generation.

**Basic Information:**

| Field | Value |
|-------|-------|
| Name | `Question Generation Wizard` |
| Description | `Multi-phase question generation with planning, user confirmation, and parallel generation per level set` |
| Entry Point | `fetch_context` |

**Nodes** — add 5 nodes:

| # | Node ID | Type | Agent |
|---|---------|------|-------|
| 1 | `fetch_context` | `agent` | Select "Question Planner" |
| 2 | `planner` | `agent` | Select "Question Planner" |
| 3 | `confirmation_gate` | `router` | _(none — router type)_ |
| 4 | `parallel_generators` | `parallel` | _(none — parallel type)_ |
| 5 | `levelset_generator` | `agent` | Select "Level Set Question Generator" |

**Edges** — add 7 edges:

| # | Edge ID | Source | Target | Condition |
|---|---------|--------|--------|-----------|
| 1 | `start_to_fetch` | `__start__` | `fetch_context` | _(leave empty)_ |
| 2 | `fetch_to_plan` | `fetch_context` | `planner` | _(leave empty)_ |
| 3 | `plan_to_gate` | `planner` | `confirmation_gate` | _(leave empty)_ |
| 4 | `gate_to_parallel` | `confirmation_gate` | `parallel_generators` | `state.get('plan_confirmed', False) == True` |
| 5 | `gate_to_end` | `confirmation_gate` | `__end__` | `default` |
| 6 | `parallel_to_gen` | `parallel_generators` | `levelset_generator` | _(leave empty)_ |
| 7 | `gen_to_end` | `levelset_generator` | `__end__` | _(leave empty)_ |

Click **"Create Workflow"**.

**How the wizard works in practice:**

1. **Phase 1 — Planning:** Start an execution with `lesson_id`, `course_id`, `selected_level_set_ids`. The workflow runs `fetch_context` → `planner` → `confirmation_gate`. Since `plan_confirmed` is not set, the router sends to `__end__`. The output contains the plan.

2. **Phase 2 — User confirms:** Your Go API presents the plan to the user. User reviews and optionally edits targets.

3. **Phase 3 — Resume with confirmation:** Start a new execution on the same `thread_id` with `plan_confirmed: true` and the (possibly modified) plan. The workflow resumes from `confirmation_gate`, routes to `parallel_generators`, fans out to `levelset_generator` for each level set, and collects results.

---

## 4. Running Executions

### From the UI

1. Navigate to **Executions** → click **"New Execution"**
2. Select a workflow from the dropdown
3. The **Skill Context** form appears (all fields optional):
   - **Subject** — e.g., `Математика`
   - **Topic** — e.g., `Еднакви триъгълници`
   - **Difficulty Level** — select from: Beginner, Intermediate, Advanced
   - **Target Audience** — e.g., `7 клас`
   - **Content Type** — e.g., `practice_problems`
   - **Learning Objectives** — one per line
   - **Additional Context (JSON)** — paste full lesson context here
4. Click **"Start Execution"**
5. The SSE stream begins — you'll see:
   - Real-time progress bar
   - Node completion events
   - Workflow diagram with active/completed nodes highlighted
   - Event log with timestamps

### From the API (for programmatic use)

**Document Processing:**

```bash
curl -X POST http://localhost:8000/api/v1/executions \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "<document_processing_workflow_id>",
    "input": {
      "document_path": "/uploads/textbook_chapter4.pdf",
      "lesson_id": "uuid-of-lesson",
      "lesson_context": {
        "lesson_name": "Еднакви триъгълници",
        "lesson_description": "Признаци за еднаквост на триъгълници",
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
```

**Simple Question Generation:**

```bash
curl -X POST http://localhost:8000/api/v1/executions \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "<simple_question_generation_workflow_id>",
    "input": {
      "description": "Generate 10 multiple-choice questions about equivalent triangles for 7th grade in Bulgarian",
      "count": 10
    }
  }'
```

**Wizard — Phase 1 (Planning):**

```bash
curl -X POST http://localhost:8000/api/v1/executions \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "<wizard_workflow_id>",
    "input": {
      "lesson_id": "uuid-of-lesson",
      "course_id": "uuid-of-course",
      "selected_level_set_ids": ["ls-uuid-1", "ls-uuid-2", "ls-uuid-3"]
    }
  }'
```

**Wizard — Phase 3 (Resume with confirmation):**

```bash
curl -X POST http://localhost:8000/api/v1/executions \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "<wizard_workflow_id>",
    "thread_id": "<thread_id_from_phase_1>",
    "input": {
      "plan_confirmed": true,
      "plan": [
        {
          "levelSetId": "ls-uuid-1",
          "levelSetCode": "7.1.1",
          "toGenerate": 15,
          "questionTypeDistribution": {
            "Flashcard": 3,
            "Selection": 7,
            "Multiselect": 5
          }
        }
      ]
    }
  }'
```

**Stream execution events (SSE):**

```bash
curl -N http://localhost:8000/api/v1/executions/<execution_id>/stream \
  -H "X-API-Key: your-api-key"
```

---

## 5. Field Reference

### Agent Form Fields

| Field | Location | Required | Range/Options | Description |
|-------|----------|----------|---------------|-------------|
| Name | Basic Info | Yes | max 100 chars | Display name |
| Description | Basic Info | No | max 500 chars | Brief description |
| Instructions | Basic Info | No | max 10,000 chars | System prompt — the AI's behavior instructions |
| Provider | LLM Config | Yes | OpenAI, Anthropic, Google, Azure OpenAI | LLM provider |
| Model Name | LLM Config | Yes | text | Model identifier (e.g., `claude-sonnet-4-20250514`) |
| Max Tokens | LLM Config | No | positive integer | Maximum output tokens (default: 4096) |
| Temperature | LLM Config | No | 0.0–2.0, step 0.1 | Randomness (default: 0.7) |
| Top P | LLM Config | No | 0.0–1.0, step 0.1 | Nucleus sampling (default: 1) |
| Tools | Tools section | No | multi-select | Select from existing tools |

### Tool Form Fields

| Field | Location | Required | Description |
|-------|----------|----------|-------------|
| Name | Basic Info | Yes | Must match backend builtin name for builtin tools |
| Description | Basic Info | No | Human-readable description |
| Config (JSON) | Basic Info | No | Runtime configuration JSON |
| Function Name | Function Schema | Yes | LLM-facing function identifier |
| Function Description | Function Schema | No | LLM-facing description of when/how to use the tool |
| Parameters | Function Schema | No | JSON Schema defining the function's input parameters |

### Workflow Form Fields

| Field | Location | Required | Description |
|-------|----------|----------|-------------|
| Name | Basic Info | Yes | Workflow display name |
| Description | Basic Info | No | Workflow description |
| Entry Point | Basic Info | No | Starting node ID (select from node IDs) |
| Node ID | Nodes array | Yes | Unique identifier (e.g., `ocr_processor`) |
| Node Type | Nodes array | Yes | `agent`, `router`, `parallel`, `join`, `subgraph` |
| Node Agent | Nodes array | No | Agent to execute (only for `agent` type nodes) |
| Edge ID | Edges array | Yes | Unique identifier (e.g., `start_to_ocr`) |
| Edge Source | Edges array | Yes | Source node ID (or `__start__`) |
| Edge Target | Edges array | Yes | Target node ID (or `__end__`) |
| Edge Condition | Edges array | No | Python expression for router edges |

### Execution Input Fields

| Field | Location | Required | Description |
|-------|----------|----------|-------------|
| Workflow | Workflow selector | Yes | Which workflow to execute |
| Subject | Skill Context | No | Educational subject |
| Topic | Skill Context | No | Specific topic |
| Difficulty Level | Skill Context | No | beginner / intermediate / advanced |
| Target Audience | Skill Context | No | Grade level or audience |
| Content Type | Skill Context | No | Type of content to generate |
| Learning Objectives | Skill Context | No | One objective per line |
| Additional Context | Skill Context | No | Free-form JSON with full lesson context |
