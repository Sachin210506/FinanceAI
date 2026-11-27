"""FastAPI Server for FinanceAI — Hybrid RAG + 2-Agent Pipeline."""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import agents
from rag import HybridRAG 

app = FastAPI(title="FinanceAI — 2-Agent Hybrid RAG", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

rag = HybridRAG()


class AnalyzeRequest(BaseModel):
    brief: str = Field(min_length=10, description="Financial software project brief")


@app.get("/api/health")
async def health():
    return {
        "status": "online",
        "model": agents.MODEL_NAME,
        "corpus_chunks": len(rag.chunks),
        "rag_mode": "Hybrid (BM25 + ChromaDB Vector)",
    }


@app.post("/api/analyze")
async def analyze(req: AnalyzeRequest):
    brief = req.brief.strip()
    if len(brief) < 10:
        raise HTTPException(status_code=400, detail="Please enter a project brief of at least 10 characters.")

    try:
        # 1. Hybrid RAG retrieval for Agent 1 (finance + security + requirements)
        print(f"[FinanceAI] 1/3 Retrieving Hybrid RAG evidence...", flush=True)
        evidence = rag.search(brief, top_k=3)

        # 2. Agent 1: Generate Finance SRS
        print(f"[FinanceAI] 2/3 Agent 1 drafting Finance SRS ({agents.MODEL_NAME})...", flush=True)
        srs_markdown = await agents.run_requirements_agent(brief, evidence)
        if not srs_markdown:
            raise RuntimeError("Agent 1 returned an empty requirements specification.")

        # 3. Hybrid RAG retrieval for Agent 2 (SDLC selection criteria + governance)
        sdlc_query = (
            "SDLC model selection criteria: stable requirements, formal verification, changing scope, "
            "risk analysis, planned increments, tight delivery, user feedback, prototypes. "
            f"Project brief: {brief}"
        )
        sdlc_evidence = rag.search(sdlc_query, top_k=2)

        # 4. Agent 2: Select & justify SDLC from the 7 models
        print(f"[FinanceAI] 3/3 Agent 2 evaluating 7 SDLC models...", flush=True)
        sdlc_markdown = await agents.run_sdlc_agent(brief, srs_markdown, sdlc_evidence)
        if not sdlc_markdown:
            raise RuntimeError("Agent 2 returned an empty SDLC recommendation.")
        print("[FinanceAI] Done.", flush=True)

        full_document = f"{srs_markdown}\n\n---\n\n{sdlc_markdown}"

        return {
            "brief": brief,
            "evidence": [
                {
                    "id": e["id"],
                    "source": e["source"],
                    "category": e["category"],
                    "score": e["score"],
                    "preview": e["text"][:220] + ("..." if len(e["text"]) > 220 else ""),
                }
                for e in evidence
            ],
            "requirements": srs_markdown,
            "sdlc": sdlc_markdown,
            "document": full_document,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc


FRONTEND_DIST = Path(__file__).parent.parent / "frontend" / "dist"
if FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
