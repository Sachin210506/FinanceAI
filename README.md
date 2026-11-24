# FinanceAI

FinanceAI helps turn a finance software idea into a concise requirements draft and an SDLC recommendation. It uses a local language model and a reference corpus of finance and software engineering documents.

## How it works

1. The user enters a project brief.
2. Hybrid retrieval (BM25 keyword search and Chroma vector search) finds relevant passages from `backend/corpus/`.
3. The Requirements Agent drafts a summary and up to six distinct requirements, each with a type and risk level.
4. The SDLC Agent recommends one of seven models: Waterfall, V-Model, Agile, Spiral, Iterative, RAD, or Prototyping. It briefly explains the choice and two alternatives.

Both agents use the local Ollama model `qwen2.5:1.5b`. The app has a Python FastAPI backend and a React frontend.

## Requirements

- Python 3.12 or later
- Node.js and npm
- Ollama installed, with `qwen2.5:1.5b` downloaded

## Run on Windows

From the project folder, open PowerShell.

1. Create the local environment file once:

   ```powershell
   Copy-Item backend\.env.example backend\.env
   ```

   If `backend\.env` already exists, keep it and skip this step.

2. Download the model once:

   ```powershell
   ollama pull qwen2.5:1.5b
   ```

3. Make sure Ollama is running, then start the backend:

   ```powershell
   .\run.ps1
   ```

   The backend API runs at `http://127.0.0.1:8002`. On first start, the script creates `backend\.venv` and installs the Python dependencies.

4. In a second PowerShell window, start the frontend:

   ```powershell
   cd frontend
   npm install
   npm run dev
   ```

   Open the local URL printed by Vite, usually `http://localhost:5173`.

## Configuration and data

Local settings belong in `backend/.env`. Git ignores this file; `backend/.env.example` contains the default Ollama settings. The reference documents are in `backend/corpus/`.

## Limitations

This project produces drafts, not verified requirements or regulatory advice. Review generated requirements, evidence, and SDLC recommendations before relying on them. A small local model can omit details or make incorrect suggestions.
