# Trellis 🔍
### Graph-Augmented Code Intelligence Engine

> Ask questions about any Python codebase in natural language. Trellis understands your code structurally — not just as text.

[![MIT License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com)
[![Linkedin](https://www.linkedin.com/posts/rami-cheikh-3b27272b8_graphrag-llms-softwarearchitecture-ugcPost-7460859361444343808-287M?utm_source=share&utm_medium=member_desktop&rcm=ACoAAExIJ3YBjmKt6QsQqj46H4WAr0fGXV6gBV4)]

---

## What is Trellis?

Trellis is a code intelligence system that builds a **knowledge graph** from your codebase and uses it to answer natural language questions with structural precision.

Unlike traditional RAG systems that chunk code into arbitrary text snippets, Trellis treats code as what it actually is — a graph of functions, classes, modules, and the relationships between them.

```
"How does the indexer work end to end?"
"What is the relationship between BaseEmbedder and JinaEmbedder?"
"How does hybrid search combine BM25 and vector results?"
"What database operations does the indexer trigger?"
```

Designed to answer using structural code relationships. From your actual code.

---

## Benchmark Results

Evaluated on the **SWE-QA-Benchmark** (Flask split) — a public code QA dataset on Hugging Face
([swe-qa/SWE-QA-Benchmark](https://huggingface.co/datasets/swe-qa/SWE-QA-Benchmark)),
48 ground-truth architectural questions across a production Python codebase (930 nodes).

| Run | Configuration | Overall Score |
|-----|-------------|---------------|
| Baseline | BM25 only — no embeddings, no summaries | 3.25 / 5 |
| **Full system** | **Hybrid retrieval + graph expansion + LLM summaries + embeddings** | **4.50 / 5** |

**Full system score breakdown:**

<img width="1640" height="922" alt="Metric (2)" src="https://github.com/user-attachments/assets/50ec108b-b64d-4628-b7c6-9db8ac840b02" />

**Score distribution (full system, 48 questions):**

| Score | Count | Share |
|-------|-------|-------|
| 5 — Perfect | 35 | 73% |
| 4 — Good | 7 | 15% |
| 3 — Partial | 2 | 4% |
| 2 — Weak | 3 | 6% |
| 1 — Failed | 1 | 2% |

The single remaining failure involves implicit behavioral coupling not expressed in the code structure — a retrieval problem, not an architectural one.

Evaluated using Gemini as judge against human-written ground truth answers. Questions sourced from Flask's production codebase covering inheritance chains, deferred registration mechanisms, context lifecycle management, serialization pipelines, and CLI architectures.

---

## Architecture

<img width="2802" height="1103" alt="Blank diagram" src="https://github.com/user-attachments/assets/fe17d8c5-02d3-4b25-9154-718add07e923"/>

---

## Why Graph RAG for Code?

Standard RAG chunks text at arbitrary boundaries. Even overlapping chunking falls short because code has **explicit structure**: functions, classes, inheritance chains, call graphs. Chunking destroys that structure.

Trellis uses the structure instead:

| Approach | What it does | Limitation |
|----------|-------------|------------|
| Vector-only RAG | Semantic similarity search | Misses structural relationships |
| LLM-extracted graph | LLM infers relationships | Slow, incomplete, non-deterministic |
| **Trellis (AST-derived graph)** | **Deterministic structural parsing** | **Requires accurate parser coverage and relationship extraction** |

This aligns with findings in SWE-bench research ([Jimenez et al., 2023](https://arxiv.org/abs/2310.06770)) showing that real-world code understanding requires reasoning across multiple functions, classes, and files simultaneously — exactly what flat retrieval fails to do.

---

## Core Components

### 1. AST Graph Builder
- Tree-sitter based Python parser
- Extracts: `module`, `class`, `function` nodes with structured attributes
- Resolves edges: `DEFINES`, `CALLS`, `INHERITS`, `IMPORTS`
- Multi-pass resolver with class-aware `self.method()` resolution
- Content-hash based incremental re-indexing — only changed nodes are re-summarized and re-embedded
- Stable SHA1 node IDs with SHA256 content fingerprinting

### 2. Semantic Augmentation
- LLM-generated summaries per node at index time (Gemini 2.5 Flash)
- Structured format: behavior, inputs, outputs, side effects
- Batched with token-aware splitting and exponential backoff
- Neighboring docstring extraction as structured node attribute

### 3. Hybrid Retrieval
- **BM25** (rank-bm25): exact keyword matching
- **Dense vector search** (pgvector + Gemini text-embedding-004): semantic matching
- **RRF fusion**: Reciprocal Rank Fusion with k=60
- Same strategy used by production Elasticsearch

### 4. Graph Expansion
- Recursive CTE in Postgres — no application-level graph traversal
- Depth-limited with cycle detection via path arrays
- Bidirectional traversal returning full subgraph of nodes and edges

### 5. Prompt Assembly
- Structured context: `[PRIMARY]`, `[RELATED]`, `[RELATIONSHIPS]`
- Three-tier token budget: truncate related → truncate primary → hard cap
- Module nodes filtered, structural anchors only
- Edge relationships with qualified names for full context

### 6. Conversation Layer
- Session-aware multi-turn conversation
- Follow-up detection and context carryover across turns
- Per-repo conversation history stored in PostgreSQL

---

## Stack

| Layer | Technology |
|-------|-----------|
| Parsing | Tree-sitter |
| Graph storage | PostgreSQL |
| Vector storage | pgvector (HNSW index) |
| Embeddings | Gemini text-embedding-004 |
| BM25 | rank-bm25 |
| Summaries | Gemini 2.5 Flash |
| Generation | Gemini 2.5 Flash |
| Backend | FastAPI |
| Frontend | React |
| Infra | Docker + Docker Compose |

---

## Getting Started

### Prerequisites
- Docker + Docker Compose
- Gemini API key (free tier sufficient for small-to-medium repos)

### Setup

```bash
# clone
git clone https://github.com/Rami-cd/Trellis
cd Trellis

# environment
cp .env.example .env
# add your GEMINI_API_KEY to .env

# start all services
docker compose up --build
```

### Index a repository

```bash
POST /repositories/{repo_id}/index
```

Or use the frontend — navigate to `http://localhost:3000`, add your repo path, and click Index.

### Query

```bash
POST /repositories/{repo_id}/query
{
  "question": "How does the hybrid search combine BM25 and vector results?"
}
```

---

## Incremental Re-indexing

Trellis tracks content hashes per node. On re-index:

- **Unchanged nodes** — skipped entirely, no API calls made
- **Changed nodes** — re-summarized and re-embedded
- **New nodes** — summarized and embedded
- **Deleted nodes** — removed from graph and embeddings

This means re-indexing after a small change is fast and cheap regardless of repo size.

---

## Roadmap

- [ ] Multi-language support (JavaScript, TypeScript, Java)
- [ ] Config file understanding (.env, docker-compose, YAML)
- [ ] Re-ranking layer (multi-factor scoring)
- [ ] SWE-bench Lite evaluation
- [ ] Larger benchmark (multi-repo, multi-language)

---

## Research Alignment

Trellis independently converged on the architecture studied in:

- **SWE-bench: Can Language Models Resolve Real-World GitHub Issues?** — Jimenez et al., ICLR 2024 ([arxiv:2310.06770](https://arxiv.org/abs/2310.06770)) — establishes that real code understanding requires multi-file, multi-function structural reasoning
- **Retrieval-Augmented Generation with Graphs** (GraphRAG survey, 2025) — validates graph-structured retrieval over flat vector search for complex reasoning
- **PathRAG** — path-based subgraph expansion over neighborhood flooding, aligned with Trellis's graph expansion strategy

---

## License

MIT

---

*Built on 8GB RAM. Runs entirely on free-tier APIs.*
