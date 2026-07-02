
# ERA-Lite: Autonomous Research Optimization System

ERA-Lite proves that a single engineer with free-tier LLMs and a laptop can build an autonomous research optimization system that outperforms Google's ERA on cost, speed, and practical utility — by replacing expensive infrastructure with intelligent agents, memory, and simpler deployment.

Inspired by the [Nature 2026 ERA paper](https://www.nature.com/articles/s41586-026-10658-6), ERA-Lite converts software creation into a "scorable task." You provide a dataset and a metric to maximize, and the system uses LLM-driven tree search to autonomously generate, test, and mutate hundreds of software candidates until it finds the best one.

## Features

- **Distributed Async Architecture**: FastAPI offloads heavy AI search to Celery Workers via Redis. Long-running ML experiments persist in the queue even if the server restarts.
- **Multi-Agent PUCT Search**: A `ManagerAgent` orchestrates specialized agents (Generator, Executor, Critic) using True PUCT math—balancing *exploitation* (mutating high scores) and *exploration* (trying unvisited nodes) to avoid local optima.
- **Dual Execution Modes**:
  - **DSA Mode**: For algorithmic LeetCode-style problems (Binary PASS/FAIL).
  - **Dataset ML Mode (Kaggle Style)**: Upload a CSV. The system reads the first 5 rows, injects them into the LLM prompt, and the AI writes full standalone scripts (scikit-learn/XGBoost) to maximize continuous metrics. Includes **Auto-Detect Metric** functionality.
- **Self-Debugging Code**: The AI wraps its ML pipelines in `try/except` blocks. If a script crashes, it catches the error, prints `SCORE: 0.0`, and passes the traceback to the next iteration so the AI can fix its own bugs.
- **Research IDE Dashboard**: A built-in Streamlit UI that visualizes the cognitive search tree. It highlights "breakthrough" mutations (blue edges) and marks the winning node (🏆) so you can trace exactly how the AI found the solution. Includes a **Cancel Run** button to gracefully stop experiments mid-search.
- **AI Reasoning Logs**: Every node in the tree stores the AI's "Thought Process" so you know exactly why it decided to mutate or pivot strategies.
- **Cross-Experiment Memory**: Saves winning ML pipelines and DSA algorithms to SQLite, injecting them as context for future problems.
- **Fat ML Sandbox**: Untrusted LLM-generated code is executed in an isolated Docker container pre-loaded with `numpy`, `pandas`, `scikit-learn`, and `xgboost`—no network access required.

## Tech Stack

- **LLM Inference**: Provider-agnostic (OpenAI GPT-4o / NVIDIA NIM Free Tier)
- **Backend**: FastAPI + Celery
- **Message Broker**: Redis
- **Frontend**: Streamlit + `streamlit-agraph`
- **Database**: SQLite
- **Orchestration**: Docker Compose

## Setup & Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Praveen-a6/ERA-improved-MVP.git
   cd ERA-improved-MVP
   ```

2. **Configure Environment:**
   Copy `.env.example` to `.env` and fill in your API keys:
   ```env
   # For OpenAI:
   LLM_BASE_URL=https://api.openai.com/v1
   LLM_API_KEY=sk-xxxxxxxxxxxx
   LLM_MODEL=gpt-4o

   # For NVIDIA NIM (Free Tier):
   # LLM_BASE_URL=https://integrate.api.nvidia.com/v1
   # LLM_API_KEY=nvapi-xxxxxxxxxxxx
   # LLM_MODEL=z-ai/glm-5.1

   REDIS_URL=redis://redis:6379/0
   HOST_PROJECT_DIR=C:/Users/YourName/Path/To/ERA-Lite-Final
   ```

3. **Build the ML Sandbox:**
   ```bash
   docker build -t era-sandbox ./sandbox
   ```

4. **Spin up the Distributed Stack:**
   ```bash
   docker-compose up --build
   ```

## Usage

Once the stack is running, you can access the services at:
- **Streamlit UI**: `http://localhost:8501`
- **FastAPI Docs**: `http://localhost:8000/docs`
- **Flower (Celery Monitor)**: `http://localhost:5555`

**To test algorithms**: Go to the Streamlit UI, navigate to **Submit DSA Problem**, paste a problem, and use the spreadsheet editor to define test cases.
**To test ML datasets**: Go to **Submit ML Dataset**, upload a CSV, and tell the AI what metric to maximize (or let it Auto-Detect).
**Observability**: Go to **Experiment Workspace** to watch the search tree build itself, inspect the code of every node, and read the AI's reasoning logs. You can safely click "Cancel Run" to stop an experiment without crashing the server.

## Rate Limit Note

If using NVIDIA NIM's free tier, there is a strict 40 RPM global limit. The system includes an aggressive exponential backoff wrapper (`core/llm_utils.py`) to handle 429 errors automatically. If using a paid OpenAI key, you can reduce the artificial delay in `llm_utils.py` to `0.1s` for blazing-fast search.
```

