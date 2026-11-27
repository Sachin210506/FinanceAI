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

Do not add acceptance criteria, priorities, verification methods, approval statuses, traceability, journeys, generic risk sections, or boilerplate. If a regulatory claim depends on retrieved evidence, cite its filename. If applicability is unclear, mark it as needing validation."""

SDLC_PROMPT = """You are Agent 2: Finance SDLC Process Architect.

Use the original brief and Agent 1 requirements to recommend one model. Do not rewrite the requirements or greet.

Choose the model whose defining project driver is best supported by the brief and requirements. Distinguish the models as follows:
- Waterfall: The scope and requirements are agreed and stable before development; work proceeds through planned sequential phases. Stability alone points to Waterfall, not V-Model.
- V-Model: The project explicitly requires formal verification and validation planned alongside each development phase, with traceability from requirements to corresponding tests. Routine testing, security, or finance context alone is not enough.
- Agile: The team expects priorities or requirements to change through frequent stakeholder feedback and short delivery cycles. Other models can also iterate; continuous adaptation is the distinguishing driver here.
- Spiral: Significant technical, security, or financial risks must be analyzed and reduced in repeated cycles before committing to the next step. Use this for risk-driven development, not just unclear user-interface needs.
- Iterative: Deliver a usable core first, then add planned capabilities in successive versions. The main driver is staged product growth.
- RAD: A genuinely short deadline combines with modular scope, reusable components, and frequent user workshops to assemble the product quickly. Do not assume a deadline unless the brief gives one.
- Prototyping: User needs or workflows are unclear, so prototypes and user feedback are needed to discover or validate requirements before building the final solution.

Compare all seven models against the same stated project facts; do not use model order as a preference and use your own understanding about models to distiguish them. Use only drivers supported by the brief or requirements. Finance context, generic security, and ordinary testing do not imply V-Model. Do not invent deadlines, approvals, stable scope, or uncertainty. If no defining driver is stated, give a provisional recommendation and identify the missing information rather than defaulting to a model.
Output Markdown only, at most 220 words, with each section exactly once:

# SDLC Recommendation
## Chosen Model
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
