# InterviewPrep — LangGraph-Based RAG

A RAG application for preparing for **project-focused technical interviews** using information from my actual projects.

Instead of generating generic interview answers, the system retrieves evidence from project sources such as **GitHub, Notion, and Google Sheets** and uses that context to generate grounded answers about architecture, implementation choices, and engineering trade-offs.

The project explores **hybrid retrieval, LangGraph orchestration, evidence grading, conditional retrieval fallback, and LLM workflow tracing**.

> This is a portfolio and learning project demonstrating RAG and backend engineering patterns. It is not presented as a fully production-ready AI platform.

---

## Why I Built It

During technical interviews, questions often go beyond *what* was built:

* Why did you choose PostgreSQL?
* Why LangGraph instead of a normal workflow?
* What trade-offs did you make?
* What would you change if the system needed to scale?
* How does retrieval work in your project?

The answers are often spread across repositories, documentation, and project notes.

InterviewPrep creates a searchable knowledge layer over those sources and uses retrieved evidence to help answer these questions.

---

## How It Works

```text id="egh1zy"
User Question
      │
      ▼
Query Routing
      │
      ▼
Hybrid Retrieval
(Vector + Lexical)
      │
      ▼
Evidence Grading
      │
      ├── Sufficient ──────────────┐
      │                            │
      └── Insufficient             │
              │                    │
              ▼                    │
       Retrieval Fallback          │
       ├── GitHub Live             │
       └── Web Search              │
              │                    │
              └─────────┬──────────┘
                        ▼
                 Answer Generation
                        │
                        ▼
               Grounded Response
```

The workflow is orchestrated using **LangGraph**. Some nodes use LLM reasoning while others perform deterministic retrieval, transformation, or API operations.

---

## Key Features

### Hybrid Retrieval

Combines:

* semantic search using **pgvector**
* lexical/keyword search
* **Reciprocal Rank Fusion (RRF)** for combining ranked results

This helps retrieve both conceptual matches and exact technical terms such as framework names, configuration options, and filenames.

### Evidence Grading

Retrieved evidence is evaluated before answer generation.

If the available project knowledge appears insufficient, the workflow can request additional information instead of immediately generating an answer.

### GitHub Live Fallback

GitHub content is normally indexed into the knowledge base.

When indexed evidence appears insufficient, the workflow can query GitHub directly for current repository information.

```text id="wwa8b3"
Indexed Knowledge → Normal retrieval
GitHub API        → Query-time fallback
```

This provides a freshness/recovery path without making live API retrieval the default for every question.

### External Web Search

Tavily can provide supplementary technical information when a question requires external context.

Project sources establish **what I actually built**, while web results provide supporting technical context.

### Automatic Knowledge Synchronization

GitHub, Notion, and Google Sheets content can be synchronized through webhooks and scheduled jobs.

This reduces manual re-indexing, although external API or ingestion failures can still cause the indexed knowledge to become temporarily stale.

### LLM Workflow Tracing

**Langfuse** is used to inspect model calls, prompts, latency, token usage, and workflow execution.

This provides LLM workflow tracing rather than complete infrastructure monitoring.

---

## Tech Stack

| Area                     | Technologies                               |
| ------------------------ | ------------------------------------------ |
| **Orchestration**        | LangGraph, LangChain                       |
| **LLMs**                 | Google Gemini, Groq                        |
| **Retrieval**            | PostgreSQL, pgvector, Hybrid Search, RRF   |
| **Backend**              | Python 3.12, FastAPI, SQLAlchemy, Pydantic |
| **Migrations**           | Alembic                                    |
| **Conversation Storage** | MongoDB                                    |
| **External Retrieval**   | GitHub API, Tavily                         |
| **Observability**        | Langfuse, Structured Logging               |
| **Frontend**             | Next.js, React, TypeScript, Tailwind CSS   |
| **Development**          | Docker, Docker Compose, Pytest, uv         |

---

## Local Setup

```bash id="4p9t9e"
git clone https://github.com/amit-agarwal2267/InterviewPrep-Agentic-RAG.git
cd InterviewPrep-Agentic-RAG

uv sync
cp .env.example .env

uv run alembic upgrade head
uv run api
```

Or start the local stack with Docker:

```bash id="sdnsfr"
docker compose up --build
```

Run tests:

```bash id="8d3uv4"
uv run pytest tests/
```

---

## Current Limitations

This project intentionally leaves several areas for further evaluation:

* Hybrid retrieval has not yet been benchmarked against a vector-only baseline.
* The LLM evidence grader adds additional latency and should be compared with rerankers or smaller classifiers.
* MongoDB and PostgreSQL could potentially be consolidated into a single datastore.
* APScheduler currently fits the simple deployment model; multi-instance deployment would require a different scheduling strategy.
* Authentication, rate limiting, infrastructure monitoring, load testing, and deployment orchestration would be required before treating the system as production-ready.

---

## What I Learned

This project helped me explore the engineering trade-offs behind building a RAG system beyond a basic:

```text id="cvad1y"
embed → retrieve → prompt → answer
```

In particular, it focuses on **retrieval quality, evidence sufficiency, source freshness, conditional fallback, provenance, workflow orchestration, and observability** — while also exposing where additional AI-system complexity needs to justify its cost.
