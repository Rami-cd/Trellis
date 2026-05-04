# Trellis 🔍
### Graph-Augmented Code Intelligence Engine

> Ask questions about any Python codebase in natural language. Trellis understands your code structurally — not just as text.

---

## What is Trellis?

Trellis is a code intelligence system that builds a knowledge graph from your codebase and uses it to answer questions with precision.

Unlike traditional RAG systems that chunk code into text snippets, Trellis treats code as what it actually is — a graph of functions, classes, modules, and the relationships between them.

```
"How does the indexer work end to end?"
"What is the relationship between BaseEmbedder and JinaEmbedder?"
"How does hybrid search combine BM25 and vector results?"
"What database operations does the indexer trigger?"
```

All answered accurately. From your actual code.

---

## Architecture

```
                        ┌─────────────────────────────┐
                        │         Your Codebase       │
                        └──────────────┬──────────────┘
                                       │
                              ┌────────▼────────┐
                              │   AST Parser    │
                              │  (Tree-sitter)  │
                              └────────┬────────┘
                                       │
                              ┌────────▼────────┐
                              │  Graph Builder  │
                              │  nodes + edges  │
                              │  DEFINES, CALLS │
                              │  INHERITS, etc. │
                              └────────┬────────┘
                                       │
                    ┌──────────────────┼──────────────────┐
                    │                  │                  │
           ┌────────▼───────┐ ┌────────▼───────┐ ┌────────▼────┐
           │  LLM Summaries │ │   Embeddings   │ │  BM25 Index │
           │                │ │ (jina-code-v2) │ │  (in-memory)│
           └────────┬───────┘ └────────┬───────┘ └──────┬──────┘
                    │                  │                │
                    └──────────────────┼────────────────┘
                                       │
                              ┌────────▼────────┐
                              │    Postgres     │
                              │   + pgvector    │
                              └────────┬────────┘
                                       │
                            ┌──────────▼──────────┐
                            │    Query Pipeline   │
                            │                     │
                            │  1. Hybrid Search   │
                            │     BM25 + Vector   │
                            │     RRF Fusion      │
                            │                     │
                            │  2. Graph Expansion │
                            │     Recursive CTE   │
                            │     Bidirectional   │
                            │                     │
                            │  3. Prompt Assembly │
                            │     Token-budgeted  │
                            │                     │
                            │  4. LLM Generation  │
                            └──────────┬──────────┘
                                       │
                              ┌────────▼────────┐
                              │     Answer      │
                              └─────────────────┘
```

---

## Why Graph RAG for Code?

Standard RAG chunks text at arbitrary boundaries, even overlapping chunking falls short. Code has explicit structure: functions, classes, inheritance chains, call graphs. Chunking destroys that structure.

Trellis uses the structure instead:

| Approach | What it does | Limitation |
|----------|-------------|------------|
| Vector-only RAG | Semantic similarity search | Misses structural relationships |
| LLM-extracted graph | LLM infers relationships | Slow, incomplete, non-deterministic |
| **Trellis (AST-derived graph)** | **Deterministic structural parsing** | **None at this level** |

This architecture is validated by [January 2026 research](https://arxiv.org/abs/2601.08773) showing AST-derived graphs outperform both vector-only and LLM-extracted approaches on multi-hop architectural reasoning tasks.

---

## Core Components

### 1. AST Graph Builder
- Tree-sitter based Python parser
- Extracts: `module`, `class`, `function` nodes
- Resolves edges: `DEFINES`, `CALLS`, `INHERITS`, `IMPORTS`
- Multi-pass resolver with class-aware `self.method()` resolution
- Stores graph in PostgreSQL with stable hash-based node IDs

### 2. Semantic Augmentation
- LLM-generated summaries per node at index time
- Structured format: behavior, inputs, outputs, side effects
- Batched with token-aware splitting and exponential backoff

### 3. Hybrid Retrieval
- **BM25** (rank-bm25): exact keyword matching
- **Dense vector search** (pgvector + jina-embeddings-v2-base-code): semantic matching
- **RRF fusion**: Reciprocal Rank Fusion with k=60
- Same strategy used by production Elasticsearch

### 4. Graph Expansion
- Recursive CTE in Postgres, no application-level graph traversal
- Depth-limited with cycle detection via path arrays
- Returns subgraph of nodes + edges for context assembly

### 5. Prompt Assembly
- Structured context: `[PRIMARY]`, `[RELATED]`, `[RELATIONSHIPS]`
- Three-tier token budget: truncate related → truncate primary → hard cap
- Module nodes filtered, structural anchors only
- Edge relationships with qualified names

---

## Stack

| Layer | Technology |
|-------|-----------|
| Parsing | Tree-sitter |
| Graph storage | PostgreSQL |
| Vector storage | pgvector (HNSW index) |
| Embeddings | jina-embeddings-v2-base-code (8192 token context) |
| BM25 | rank-bm25 |
| Summaries | Gemini 2.5 Flash |
| Generation | Gemini 2.5 Flash |
| Backend | FastAPI |
| Infra | Docker + Docker Compose |

---

## Getting Started

### Prerequisites
- Docker + Docker Compose
- Ollama (for local embeddings)
- Gemini API key (free tier works for small repos)

### Setup

```bash
# clone
git clone https://github.com/yourusername/trellis
cd trellis

# environment
cp .env.example .env
# add your GEMINI_API_KEY to .env

# start compose
docker compose up --build

# the api capabilities will be added later
```

#### **NOTE: you can change Dockerfile to stop the main.py from running right away if you have different plan.**
#### **main.py works normally as long as jina and postgres containers are working.**

### Index a repository

```bash
# index your codebase
TRELLIS_REPO_PATH=/path/to/your/project python -m app.main
```

---

## Results

Tested on Trellis' own codebase (~115 nodes, ~3000 lines of Python)

More tests in the future will be conducted with more languages too, but it require access to more tokens and calls than what the free model offers.

**Very low hallucination with a light model on a the tests, with Trellis code base being fairly complex.**

---

## Roadmap

- [ ] REST API endpoints (`/index`, `/query`)
- [ ] Frontend chat interface
- [ ] Conversation layer (session state, follow-up detection)
- [ ] Re-ranking layer (multi-factor scoring)
- [ ] SWE-QA benchmark evaluation (Flask split, 48 queries)
- [ ] Multi-language support (JavaScript, TypeScript, Java)
- [ ] Config file understanding (.env, docker-compose, requirements.txt)
- [ ] Incremental re-indexing

---

## Research Alignment

This system independently converged on the architecture validated in:

- **"Reliable Graph-RAG for Codebases: AST-Derived Graphs vs LLM-Extracted Knowledge Graphs"** (January 2026) (still needs some progress)
- **"Retrieval-Augmented Generation with Graphs"** (GraphRAG survey, January 2025)
- **PathRAG** — path-based subgraph expansion over neighborhood flooding

---

## License

MIT

---

*8GB RAM. 0$ needed. Free models.*