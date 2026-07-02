
***

## What We Are Building

ERA-Lite is a **direct improvement** on Google's ERA system (published Nature 2026), targeting every known weakness of the original:

> *"ERA is powerful but impractical. We make it practical without sacrificing the core optimization loop."*

**Core thesis**: A single engineer with free-tier LLMs and a laptop can build an autonomous research optimization system that outperforms Google's ERA on cost, speed, and practical utility — by replacing expensive infrastructure with intelligent agents, memory, and simpler deployment.

***

## What ERA Is Actually For

ERA is **not** mainly a DSA/LeetCode system. DSA problems are used for prototyping. The real targets are machine-scorable scientific and engineering tasks (scRNA-seq, time-series, Kaggle ML competitions). ERA-Lite is built to handle both DSA (PASS/FAIL) and ML (Continuous Score) tasks autonomously.

***

## Current Status — Phase 4 Complete (Production Distributed Stack & UX Polish)

### What is working right now
- **Distributed Architecture**: Fully containerized using `docker-compose`. 
- **Async Execution Queue**: FastAPI offloads heavy AI search to Celery Workers via Redis. Jobs persist if the server restarts.
- **Observability**: Flower UI monitors Celery worker queues at port `5555`.
- **Graceful Cancellation**: Users can click "Cancel Run" in the UI. The ManagerAgent checks a DB status flag between iterations and stops safely without crashing Celery.
- **Docker-in-Docker Path Resolution**: `ExecutorAgent` correctly maps container paths to host paths using `HOST_PROJECT_DIR` so the Celery Worker can spawn sandbox containers.
- **Clean Structure**: Codebase split into `api/`, `core/`, `db/`, `ui/` packages.
- **Provider Agnostic**: LLM provider (OpenAI/NVIDIA) configured entirely via `.env`.
- **Multi-Agent PUCT Search**: `ManagerAgent` orchestrates `Generator`, `Executor`, and `Critic` agents using True PUCT math (balancing exploitation and exploration).
- **Dataset ML Mode**: Auto-detects metrics, injects 5-row CSV preview into LLM context, writes full XGBoost/sklearn pipelines with `try/except` self-debugging.
- **Research IDE UI**: Streamlit dashboard with interactive tree map (breakthrough edges, crown node), AI reasoning logs, and CSV previews.
- **Fat ML Sandbox**: Isolated Docker execution with `numpy`, `pandas`, `scikit-learn`, `xgboost`, `lightgbm` (no network access).

***

## LLM / API Configuration

The system is provider-agnostic. It uses the OpenAI SDK but can hit any compatible endpoint.

### `.env` Configuration
```env
# For OpenAI:
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-xxxxxxxxxxxx
LLM_MODEL=gpt-4o

# For NVIDIA NIM (Free Tier):
# LLM_BASE_URL=https://integrate.api.nvidia.com/v1
# LLM_API_KEY=nvapi-xxxxxxxxxxxx
# LLM_MODEL=z-ai/glm-5.1

# Celery/Redis Config
REDIS_URL=redis://redis:6379/0

# Docker-in-Docker Host Path (Crucial for mounting sandbox volumes)
HOST_PROJECT_DIR=C:/Users/YourName/Path/To/ERA-Lite-Final
```
*Note: `llm_utils.py` includes an aggressive exponential backoff wrapper `[5, 15, 30, 60]` for 429 errors.*

***

## File Structure

```text
ERA-Lite-Final/
├── api/                  # FastAPI Backend & Celery Worker
│   ├── main.py           # API endpoints & file upload handling
│   └── worker.py         # Celery task queue (soft_time_limit=1200s)
├── core/                 # Core AI Logic & Agents
│   ├── agents.py         # Multi-Agent system + PUCT Node Pool + Docker execution
│   ├── critic.py         # Adversarial review agent
│   ├── era_loop.py       # Orchestrator (pre-processing & routing)
│   ├── llm_utils.py      # Shared LLM client + rate limiting
│   ├── memory_agent.py   # Tag extraction & memory formatting
│   └── rag_agent.py      # arXiv + Semantic Scholar search
├── db/                   # Database logic
│   └── storage.py        # SQLite (experiments, nodes, memory, tree)
├── ui/                   # Streamlit Frontend
│   └── main.py           # Research IDE Dashboard (Tree, Inspector, Cancel Button)
├── sandbox/              # Dockerfile for ML sandbox
├── .env.example
├── .gitignore
├── Dockerfile            # Dockerfile for the main app (API/Worker/UI) + Docker CLI
├── docker-compose.yml    # Orchestration file (Redis, API, Worker, UI, Flower)
├── requirements.txt
└── README.md
```

***

## Architecture — Current Shape

```text
User UI (Streamlit)      ← submits DSA tests OR ML CSV dataset           ✅ Done
     ↓
API Layer (FastAPI)      ← serializes task and pushes to Redis           ✅ Done
     ↓
Celery Worker            ← picks up task, runs ManagerAgent              ✅ Done
     ↓
ManagerAgent             ← PUCT Node Pool (Exploitation vs Exploration)  ✅ Done
     ↓
GeneratorAgent           ← generates/mutates DSA or full ML pipelines    ✅ Done
     ↓
ExecutorAgent            ← Docker execution (Fat Image) + parses SCORE   ✅ Done
     ↓
CriticAgent              ← reviews solutions > 90% score                 ✅ Done
     ↓
Storage (SQLite)         ← saves nodes, builds tree, saves memory        ✅ Done
```

***

## ERA Paper vs ERA-Lite

### Google ERA does
- PUCT-style tree search, 300–1000 nodes per experiment
- Frontier model quality + large-scale infra
- No explicit memory across experiments
- No explicit critic layer

### ERA-Lite does
- **True PUCT Expandable Node Pool** (balances high scores with unvisited nodes)
- Memory across experiments via SQLite (saves winning DSA & ML pipelines)
- Critic Agent against reward hacking
- Fat Docker sandbox (runs XGBoost/LightGBM) on a single laptop
- Provider-agnostic (OpenAI or free NVIDIA NIM)
- ML-ready continuous scoring (`SCORE: X.XX`) with `try/except` self-debugging
- FastAPI + Celery + Streamlit Full-Stack Distributed UI with Graceful Cancellation

***

## Strict Roadmap

| Day | Goal | Status |
|---|---|---|
| 1-6 | Core loop, Docker, SQLite, Critic, Memory, RAG | ✅ Done |
| 7 | Multi-agent transition + Expandable Node Pool + ML Scoring | ✅ Done |
| 8 | FastAPI backend | ✅ Done |
| 9 | Streamlit/dashboard UI + Tree Visualization | ✅ Done |
| 10 | PUCT Algorithm + Research IDE UI + ML Testing | ✅ Done |
| 11 | Auto-Detect Metrics, Data Preview, AI Reasoning Logs, UI Polish | ✅ Done |
| 12 | Production stack (Celery, Redis, Docker Compose) | ✅ Done |
| 13 | Graceful Cancel, Path Mismatch Fixes, Self-Debugging Prompts | ✅ Done |
| 14 | CI/CD (GitHub Actions) & Auth (JWT) | ⬜ Future |

***

## Key Architectural Decisions

| Decision | Reason |
|---|---|
| True PUCT Expandable Node Pool | Balances exploitation (mutating high scores) and exploration (trying unvisited nodes) to avoid local optima, exactly like Google's ERA. |
| Fat ML Docker Image | Allows execution of numpy, pandas, scikit-learn, xgboost without network access inside the sandbox. |
| Inject 5-Row CSV Preview into Prompt | Gives the LLM zero-shot understanding of column names and data types without needing to manually specify schema. |
| Auto-Detect Metric | AI reads the problem and data preview, deciding autonomously whether to print `SCORE: {accuracy}` or `SCORE: {r2_score}`. |
| Store AI "Reasoning" per Node | Provides full transparency in the UI so researchers can see *why* a mutation was chosen. |
| Separate DB Context from LLM Context | The DB stores clean problem statements; the LLM receives enhanced prompts with data previews. |
| Celery + Redis Queue | Decouples long-running AI search from the FastAPI event loop, making the system fault-tolerant. |
| `try/except` Self-Debugging | ML pipelines catch their own errors and print `SCORE: 0.0`, allowing the mutation engine to read the traceback and fix the bug in the next iteration instead of crashing. |
| `HOST_PROJECT_DIR` Mapping | Solves the Docker-in-Docker path mismatch so the Celery Worker container can tell the host Docker daemon exactly where to mount the sandbox files. |
| Graceful Cancel Flag | Users can stop an experiment. The ManagerAgent checks the DB status between iterations and breaks the loop safely without killing the Celery process. |

***

## Environment Setup (New Machine)

```bash
git clone https://github.com/Praveen-a6/ERA-improved-MVP.git
cd ERA-improved-MVP

# 1. Setup environment
cp .env.example .env
# (Edit .env with your API keys and HOST_PROJECT_DIR)

# 2. Build the ML Sandbox
docker build -t era-sandbox ./sandbox

# 3. Spin up the Distributed Stack (API, Worker, UI, Redis, Flower)
docker-compose up --build
```
- **Streamlit UI**: `http://localhost:8501`
- **FastAPI Docs**: `http://localhost:8000/docs`
- **Flower (Celery Monitor)**: `http://localhost:5555`
```