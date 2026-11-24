# FinanceAI
# FinanceAI

FinanceAI turns a project idea into a finance focused requirements draft and SDLC recommendation.

## How it works

1. A hybrid search retrieves relevant passages from the local finance and software engineering corpus (BM25 + Chroma vector search).
2. The Requirements Agent uses the project brief and retrieved evidence to draft requirements.
3. The SDLC Agent uses the brief, requirements, and relevant evidence to recommend one of seven models: Waterfall, V-Model, Agile, Spiral, Iterative, RAD, or Prototyping.

The app uses a React frontend, a Python FastAPI backend, and a local Ollama model (`qwen2.5:1.5b`).

## Run on Windows

1. Install Python, Node.js, and [Ollama](https://ollama.com/download).
2. Download the model once: `ollama pull qwen2.5:1.5b`.
3. Copy `backend/.env.example` to `backend/.env` and adjust values if needed. Keep `.env` private.
4. Run `./run.ps1` from this folder. The backend is available at `http://127.0.0.1:8002`.
5. In a second terminal, run `cd frontend`, `npm install`, then `npm run dev` to open the React interface (Vite prints its local URL).

The first backend start creates `backend/.venv` and installs the Python requirements. Ollama must be running locally.
