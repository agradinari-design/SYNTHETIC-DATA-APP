# Rubric — Prompt Engineering Capstone

This rubric governs the AI review for submissions targeting the **`prompt`** branch. Apply it together with the generic evaluation philosophy in your system prompt.

---

## Mandatory technical requirements (singletons)

Each item below is named **explicitly** in the spec and is **non-optional**. Verify with `import` + call site in the student's source. Substitution is acceptable when the role is filled by an equivalent tool — note it.

| Requirement | What to look for | Acceptable substitutions |
|---|---|---|
| **Gemini LLM** (2.0 Flash or newer) | A model name like `gemini-*` passed to the SDK; actual `generate_content` calls in the app's chat/SQL path. | A newer Gemini model (2.5 / 3.x) is fine and not a substitution. A non-Gemini LLM is a substitution — note it. |
| **Google GenAI SDK with Vertex AI auth** | `from google import genai` or `from google.cloud import aiplatform`; client instantiated with `vertexai=True` / `project=...` / `location=...`, or via `aiplatform.init(...)`. **The spec rules out plain API keys.** | If the student uses `genai.Client(api_key=...)` instead of Vertex AI auth, that is a substitution — note "API key auth used instead of Vertex AI". Do not fail. |
| **UI — Streamlit *or* Gradio** | `import streamlit` / `import gradio` and an entrypoint script that runs the UI. Either one satisfies the slot. | A custom FastAPI + React UI fills the same role — substitution. |
| **PostgreSQL** | A real Postgres connection string (`postgresql://` or `psycopg`/`SQLAlchemy` engine pointing at Postgres). A running Postgres in `docker-compose.yml` counts as supporting evidence. | SQLite or MySQL → substitution. Note which is used. |
| **Docker** | A non-trivial `Dockerfile` (with a working entrypoint) and/or `docker-compose.yml` defining real services. An empty `FROM python` with no `CMD`/`ENTRYPOINT` is not enough. | None. Docker itself is the requirement. |
| **Langfuse** | `from langfuse` import in app code; a `Langfuse(...)` client initialised and used to trace LLM calls or chat turns. Just listing it in `requirements.txt` is **not** evidence. | Equivalent tracing tool (e.g., LangSmith, OpenTelemetry to Phoenix/Arize) → substitution. |

---

## Mandatory phases

### Phase 1 — Synthetic Data Generation (`P1`)

The capability must be wired into the running app, not just exist as a class.

- Data-generation engine parses DDL (`.sql` / `.txt` / `.ddl`) and produces consistent, valid data: types, nulls, dates, PKs, FKs honoured.
- User can iteratively modify generated data via textual feedback (a prompt → updated rows for that table).
- Generated data is downloadable as CSV / ZIP **and** persisted so the *Talk to your data* tab can read it.
- UI shape:
  - Sidebar with two tabs: **Data Generation** and **Talk to your data**.
  - *Data Generation* tab: DDL upload, prompt text box, generation parameters including **temperature**, **Generate** button, per-table preview, per-table edit-by-prompt + **Submit** button.

When you write the phase analysis, be explicit about **which sub-items are wired into the UI** and which are stubs.

### Phase 2 — Chat with Your Data (`P2`)

- Conversational UI with text input, conversation history, and streamed responses (not blocking text).
- Automatic SQL generation **and execution** against the data; queries must support joins and aggregations (verify by reading the prompt template or function-calling setup).
- The UI shows **both** the generated SQL query **and** the tabular result.
- Data visualisations via **Seaborn** or equivalent plotting library — used inside the chat flow, not as a separate script.
- Guardrails: prompt-injection / jailbreak detection (look for a moderation prompt, a guardrails library like `guardrails-ai` / `nemo-guardrails`, or a custom check).
- Guardrails: the assistant stays on topic (a system prompt that constrains scope counts; flag it as weak if it is the only mechanism).
- Langfuse tracing covers the chat pipeline turns (not just one event).

---

## What is explicitly OPTIONAL — never penalise

- **Phase 3 — Advanced Text-to-SQL** is `*(Optional)*` in the spec. Vector search for SQL examples, few-shot retrieval, dynamic schema selection — all optional.
- **PII data tokenisation** in Phase 2 guardrails is `(Optional, schema-dependent)`.
- **Modifiable queries from the UI** in Phase 2 is `(Optional)`.
- **Alerts for jailbreak / online evals** in Phase 2 observability is `(Optional)`.

Do not list any of these as gaps. Do not mention them in the action items unless the student claims to have done them but the implementation is broken.

---

## Common tripwires for this module

- **`langfuse` in requirements but never imported.** Treat as `missing`, not present.
- **Docker file is a stub** (e.g., only `FROM python:3.11` with no install, no copy, no entrypoint). Treat as `missing`.
- **PostgreSQL is in `docker-compose.yml` but the app uses SQLite at runtime.** That is `substituted` (SQLite is what actually backs the app), not `present`.
- **The student wraps the LLM with `google-generativeai` (AI Studio) instead of Vertex AI.** That is a substitution per the spec — note it explicitly.
- **Generated data is downloadable but never persisted for "Talk to your data".** The connection between the two tabs is part of the requirement — flag it as a gap in `P1`.

---

## Per-phase output expectations

For each phase, your `phase_analysis` entry should include:
- A short paragraph in `evidence` describing what you found, with at least one file:line citation.
- Concrete `gaps` bullets — one bullet per missing sub-item.
- Concrete `suggestions` — one or two actionable next steps the student can take *today*.

In `technical_requirements`, include **one row per item in the table above**, in the order shown.

---

## Original task specification (source of truth)

# Prompt Engineering — Capstone Project

> Course author: **Grid University**
> Modules covered: Prompt Engineering, LLM APIs, Guardrails, Basic Observability, Production best practices.

## Overview

The goal of this capstone is to implement a conversational AI application with two primary functionalities: **synthetic data generation** and **natural-language data querying**. The work is broken down into three distinct phases:

- **Phase 1** — develop a core data-generation engine. The engine must interpret provided SQL schemas, identifying tables, columns, data types, and constraints. A data-generation module must then use this parsed information to create realistic synthetic data, respecting all defined constraints (especially foreign keys) to ensure data integrity. The system must be able to generate a configurable amount of data — for example, ~1000 rows per table.
- **Phases 2 and 3** — implement the **Conversational Core** module that lets users query SQL data with natural language ("talk to your data") and present results as text, tables, and plots.

By the end of the project, the student must deliver a user-friendly UI and present both the results and the source code to the professor.

---

## Technical Requirements

| # | Requirement |
|---|---|
| 1 | **LLM:** Gemini 2.0 Flash (or newer). Use streaming, function calling, and JSON / structured output where appropriate. |
| 2 | **SDK:** Google GenAI SDK with Vertex AI auth through a GCP project. |
| 3 | **UI:** Streamlit or Gradio. |
| 4 | **DB:** PostgreSQL. |
| 5 | **Containerisation:** Docker. |
| 6 | **Observability:** Langfuse. |

---

## Practice 1 — Phase 1: Synthetic Data Generation

### Functional Requirements

- The system must generate consistent and valid data for the provided DDL schema (up to 5–7 tables) and instructions: data types, null values, date/time formats, primary and foreign keys, etc.
- The system must allow the user to modify the generated data through textual feedback.
- Generated data must be downloadable as CSV / ZIP archive and stored in the system so that it is later accessible in the *Talk to your data* tab.

### UI Requirements

1. **Sidebar** with main tabs: *Data Generation*, *Talk to your data*.
2. **Data Generation tab:**
   - User can upload a file with a DDL schema (`.sql`, `.txt`, or `.ddl`).
   - User can add text instructions (prompt) for the data in a text box.
   - User can set additional generation parameters such as temperature.
   - Generation happens after the user clicks **Generate**.
   - After generation, the user can preview each generated table.
   - User can apply changes to each table by entering a prompt and clicking **Submit**.

---

## Practice 2 — Phase 2: Chat with Your Data

The system must provide a conversational interface that lets users interact with the data using natural-language text input.

1. The system must display the conversation history and stream system responses.
2. The system must automatically generate and execute relevant SQL queries against the underlying data source(s):
   - SQL joins and aggregation functions are supported.
   - Both the source query and the tabular output must be shown.
   - *(Optional)* Queries are modifiable from the UI.
3. The system must generate data visualisations using the Python **Seaborn** library (or similar) and provide the results within the conversational interface.

### Guardrails (basic)

- Detect prompt-injection / jailbreak attempts.
- Make sure the AI assistant stays on topic.
- *(Optional, schema-dependent)* PII data tokenisation (masking) for user queries.

### Observability

- Set up Langfuse and connect it to the application for tracing.
- *(Optional)* Set up alerts for jailbreak attempts and online evals.

---

## Practice 3 — Phase 3 *(Optional)*: Advanced Text-to-SQL

Improve the *Talk to your data* accuracy by incorporating Vector Search so that the solution works for bigger datasets with a lower error rate, and leverage few-shot examples.

### Possible Improvements

- Add examples for *text query → SQL query* and pull relevant samples on the generation step from a vector store.
- Dynamically select which table schemas to pull into the LLM context.
