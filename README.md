# Module 1 — Prompt Engineering Capstone

> Grid University · Gen AI Training Program
> Modules covered: Prompt Engineering, LLM APIs, Guardrails, Basic Observability, Production best practices.

This branch is the **target** of your submission Pull Request for Module 1. Branch off this branch, build your project, then open a PR back into `prompt`. An AI reviewer will analyze your work phase-by-phase and post detailed feedback as a PR comment. For the full submission flow, see the [`main` branch README](https://github.com/griddynamics/gridu-genai/blob/main/README.md).

---

## Overview

You will implement a conversational AI application with two primary functionalities: **synthetic data generation** and **natural-language data querying** ("Talk to your data"). The work is broken down into phases — the first two are mandatory, the third is optional.

By the end of the project, you must deliver a working UI and present both the results and the source code to your instructor.

---

## Technical requirements

| # | Requirement |
|---|---|
| 1 | **LLM:** Gemini 2.0 Flash or newer. Use streaming, function calling, and JSON / structured output where appropriate. |
| 2 | **SDK:** Google GenAI SDK with **Vertex AI auth** through a GCP project. No plain API keys. |
| 3 | **UI:** Streamlit *or* Gradio. |
| 4 | **DB:** PostgreSQL. |
| 5 | **Containerisation:** Docker (`Dockerfile` and/or `docker-compose.yml`). |
| 6 | **Observability:** Langfuse (tracing wired into the running app). |

---

## Phase 1 — Synthetic Data Generation

### Functional requirements

- The system generates consistent, valid data for the provided DDL schema (up to 5–7 tables): correct types, null handling, date/time formats, primary and foreign keys honoured.
- The user can iteratively modify the generated data through textual feedback ("make 30% of `column_a` nulls", "replace value X with Y in all tables", etc.).
- Generated data is downloadable as **CSV / ZIP** *and* persisted so the *Talk to your data* tab can use it.

### UI requirements

- Sidebar with two main tabs: **Data Generation** and **Talk to your data**.
- *Data Generation* tab must include:
  - DDL upload (`.sql`, `.txt`, or `.ddl`).
  - Prompt input (text box for instructions).
  - Generation parameters including **temperature**.
  - **Generate** button to trigger the run.
  - Per-table preview of generated data.
  - Per-table edit-by-prompt with a **Submit** button to apply changes.

### Sample conversational flow

```
User uploads library_mgmt.ddl with instructions:
  - generate ~20 records per table
  - 20% of dates in table C should be null
  - dates between Nov 2023 and June 2025

System: [shows generated tables]
User: Make 30% nulls in column A
System: [updates the data]
User: Replace value A with value B in all tables
System: [updates the data]
User: Looks good, save it
System: [link to download as CSV/ZIP]
```

---

## Phase 2 — Chat with Your Data

The system must provide a conversational interface to query the generated data in natural language.

- Conversational UI with text input, conversation history, and **streamed** responses.
- Automatic SQL generation **and** execution against the dataset:
  - Support joins and aggregation functions.
  - Display both the **source SQL** and the **tabular result**.
  - *(Optional)* allow queries to be edited from the UI.
- Data visualisations using **Seaborn** (or an equivalent plotting library), rendered inside the conversational flow.

### Guardrails (basic)

- Detect prompt-injection / jailbreak attempts.
- Keep the assistant on topic.
- *(Optional, schema-dependent)* PII tokenisation (masking) for user queries.

### Observability

- Set up Langfuse and wire it to the application to trace the chat pipeline.
- *(Optional)* Alerts for jailbreak attempts and online evals.

### Sample conversational flow

```
User:   What are the top-performing departments in Q3 2025 based on profits?
System: [SQL query as a code block]
        [tabular result]
User:   Add info about how many sales each department made.
System: [updated SQL query + tabular result]
User:   Make a bar plot (short department name, total sales per month).
System: [bar plot image]
User:   All bars the same colour, use blue.
System: [updated bar plot]
```

---

## Phase 3 — Advanced Text-to-SQL *(Optional)*

Improve "Talk to your data" accuracy on larger datasets with vector-based example retrieval and dynamic schema selection.

- Add `text query → SQL query` examples and pull relevant ones from a vector store at generation time.
- Dynamically choose which table schemas to load into the LLM context.

> Anything marked *(Optional)* in this spec will **not** lower your grade. Skip it without penalty.

---

## Provided resources

This branch ships with three sample DDL schemas under `resources/schemas/`:

- `library_mgmt.ddl` — small library management database.
- `restaurants.ddl` — restaurant ordering domain.
- `company_employee.ddl` — HR / payroll domain.

You may use any of these (or your own) for testing. A reference UI mock-up is provided at `resources/images/ui_sample.png`.

---

## How to submit

1. Branch off `prompt`: `git checkout prompt && git checkout -b <your-name>/prompt-submission`.
2. Build your project on that branch. The reviewer will read **everything you commit** (excluding `.github/`, caches, and binary assets).
3. Open a Pull Request targeting the `prompt` branch.
4. The AI reviewer runs automatically. A single PR comment summarises the verdict, the technical requirements check, and a per-phase analysis with action items.
5. Push more commits to re-trigger the review. The bot updates its existing comment in place.

Good luck — and have fun.
