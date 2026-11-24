"""Two-Agent Pipeline for FinanceAI using local Ollama."""

import os

from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:11434/v1")
MODEL_NAME = os.getenv("LLM_MODEL", "qwen2.5:1.5b")
API_KEY = os.getenv("LLM_API_KEY", "ollama")

client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY, timeout=90.0)

REQUIREMENTS_PROMPT = """You are Agent 1: Finance Requirements Analyst.

Create a concise first-draft requirements summary from the user's project brief.

Rules:
- Use the brief for project-specific facts. Use retrieved evidence only when directly relevant.
- Do not assume a country, regulation, feature, approval, or stakeholder that the brief does not specify.
- Do not invent laws or claim that anyone has approved a requirement. Put important missing facts in Open Questions.
- Include only distinct, necessary requirements. Do not repeat requirements or add generic filler.
- Do not choose or discuss an SDLC model.
- Output Markdown only, at most 300 words, using this format:

# [System Name] Requirements
## Summary
(At most two sentences.)
## Requirements
(At most 6 items. Each item must contain only: ID, requirement statement, type, and risk level. Use this format: **R1** Requirement statement. Type: Functional. Risk: Medium. Use a new ID for each distinct requirement. Keep each statement specific to the brief.)
## Open Questions
(At most 3 short questions for missing information that materially affects the requirements. Omit this section if none are needed.)

Do not add acceptance criteria, priorities, verification methods, approval statuses, traceability, journeys, generic risk sections, or boilerplate. If a regulatory claim depends on retrieved evidence, cite its filename. If applicability is unclear, mark it as needing validation."""

SDLC_PROMPT = """You are Agent 2: Finance SDLC Process Architect.

Use the original brief and Agent 1 requirements to recommend one model. Do not rewrite the requirements or greet.

Choose the model whose primary driver is best supported by the brief and requirements. Use these distinctions:
- Waterfall: requirements are clear, stable, and agreed before development, with little expected change.
- V-Model: formal verification and validation must be planned for each development stage, often due to explicit regulation or assurance needs.
- Agile: requirements are expected to evolve through frequent stakeholder feedback and short delivery cycles.
- Spiral: major technical, security, or financial uncertainties require repeated risk analysis and risk-reducing prototypes.
- Iterative: the project should deliver a core system first, then expand it through planned releases.
- RAD: a genuinely tight delivery deadline is paired with modular work, reusable components, and frequent user workshops.
- Prototyping: user needs or workflows are unclear and prototypes are needed to discover or validate them,it requires constant interaction with users to understand their need so use it when user is unsure of its requirements .

Use only drivers supported by the brief or requirements. The finance domain alone does not imply V-Model, and a general software project does not imply Agile. Do not invent deadlines, approvals, stable requirements, or uncertainty. If no driver is clear, label the recommendation provisional and state the missing information instead of treating one model as the default.

Output Markdown only, at most 220 words, with each section exactly once:

# SDLC Recommendation
## Chosen Model(Any model other than agile)
(Name exactly one of the seven models.)
## Why It Fits
(Give up to three concise reasons based on the brief or requirement IDs. Do not invent deadlines, fixed requirements, approvals, or risks.)
## Why Not These Two
(Choose two plausible alternatives and give one short, project-specific reason for each. Do not claim they are unsuitable for finance in general.)
## Considerations
(At most two concise project-specific caveats or missing facts. Omit if none.)

Do not include a decision table, lifecycle phases, generic roles, repeated conclusions, or compliance boilerplate. Do not repeat facts across sections."""


def clean_markdown(text: str) -> str:
    """Strip fences and exact repeated lines from small-model output."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()
    unique_lines = []
    seen_lines = set()
    for line in cleaned.splitlines():
        key = line.strip().casefold()
        if key and key in seen_lines:
            continue
        if key:
            seen_lines.add(key)
        unique_lines.append(line)
    return "\n".join(unique_lines).strip()


def format_evidence(evidence: list[dict]) -> str:
    if not evidence:
        return "No local evidence retrieved. Mark regulatory claims as NEEDS-VALIDATION."
    blocks = []
    for i, item in enumerate(evidence, 1):
        blocks.append(f"[{i}] {item['source']}\n{item['text']}")
    return "\n\n".join(blocks)


async def run_requirements_agent(brief: str, evidence: list[dict]) -> str:
    """Agent 1: Generates a concise, evidence-aware requirements draft."""
    user_msg = (
        f"Project Brief:\n{brief}\n\n"
        f"Retrieved Evidence:\n{format_evidence(evidence)}\n\n"
        "Write only the concise requirements document requested in your instructions. "
        "Do not repeat headings, facts, or requirements."
    )
    resp = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": REQUIREMENTS_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.2,
        max_tokens=900,
    )
    return clean_markdown(resp.choices[0].message.content or "")


async def run_sdlc_agent(brief: str, srs_markdown: str, sdlc_evidence: list[dict]) -> str:
    """Agent 2: Selects one SDLC model and briefly explains the trade-offs."""
    user_msg = (
        f"Original Project Brief:\n{brief}\n\n"
        f"Requirements Draft:\n{srs_markdown}\n\n"
        f"Retrieved SDLC Evidence:\n{format_evidence(sdlc_evidence)}\n\n"
        "Follow the concise output format. Do not repeat facts or invent project details."
    )
    resp = await client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": SDLC_PROMPT},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.2,
        max_tokens=700,
    )
    return clean_markdown(resp.choices[0].message.content or "")
