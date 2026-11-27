import { useEffect, useState } from "react";
import { Download, FileText, RotateCcw, Sparkles } from "lucide-react";
import { renderMarkdown } from "./markdown";

interface EvidenceItem {
  id: string;
  source: string;
  category: string;
  score: number;
  preview: string;
}

interface AnalysisResult {
  brief: string;
  evidence: EvidenceItem[];
  requirements: string;
  sdlc: string;
  document: string;
}

interface HealthStatus {
  status: string;
  model: string;
  corpus_chunks: number;
  rag_mode: string;
}

type TabKey = "document" | "requirements" | "sdlc" | "evidence";

const SAMPLE_BRIEFS = [
  {
    label: "UPI Payment Wallet",
    text: "Build a mobile UPI payment wallet for Indian retail users with biometric 2FA for transactions above Rs 2,000, encrypted QR scanning, instant settlement ledger, KYC verification, and RBI digital payment security compliance.",
  },
  {
    label: "Ambiguous Lending App",
    text: "A micro-lending mobile app where the client is unsure about the exact credit scoring workflow and user dashboard, so the team needs frequent feedback cycles and rapid mockups to clarify requirements.",
  },
  {
    label: "SEBI Trading Portal",
    text: "Design a stock brokerage order-management platform with strict SEBI CSCRF audit logging, ISO 20022 settlement messaging, role-based access control, and high-availability failover.",
  },
];

export function App() {
  const [brief, setBrief] = useState("");
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>("document");

  useEffect(() => {
    fetch("/api/health")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => setHealth(data))
      .catch(() => setHealth(null));
  }, []);

  const handleAnalyze = async (overrideText?: string) => {
    const promptText = (overrideText ?? brief).trim();
    if (promptText.length < 10) {
      setError("Please enter a project brief of at least 10 characters.");
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await fetch("/api/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ brief: promptText }),
      });
      const payload = await res.json();
      if (!res.ok) {
        throw new Error(payload.detail || "The analysis could not be completed.");
      }
      setResult(payload);
      setActiveTab("document");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to connect to backend.";
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleDownload = () => {
    if (!result) return;
    const blob = new Blob([result.document], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "financeai-srs-sdlc.md";
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">F</span>
          <span>
            Finance<b>AI</b>
          </span>
        </div>
        <div className="sidebar-rule" />
        <p className="eyebrow">Local Workspace</p>
        <nav>
          <a className="nav-item active" href="#workspace">
            <span className="nav-dot" />
            Requirements workspace
          </a>
          <a className="nav-item" href="#how-it-works">
            <span className="nav-dot outline" />
            How it works
          </a>
        </nav>

        <div className="sidebar-bottom">
          <p className="eyebrow">Processing</p>
          <p className="local-status">
            <span className={`status-dot ${health ? "" : "offline"}`} />
            {health ? `Ollama (${health.model})` : "Backend offline"}
          </p>
          <p className="muted small">
            {health ? `${health.corpus_chunks} indexed corpus chunks` : "Run run.ps1 to start server"}
          </p>
        </div>
      </aside>

      <main className="main-content" id="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">Finance Requirements Engineering</p>
            <h1>Project workspace</h1>
          </div>
          <div className="topbar-meta">Hybrid RAG (BM25 + Vector) · 2-Agent Pipeline</div>
        </header>

        <section className="intro-card">
          <div>
            <p className="eyebrow" style={{ color: "#9fd6c9" }}>
              FINANCE AI
            </p>
            <h2>Turn a finance product brief into grounded requirements and an SDLC plan.</h2>
            <p className="intro-copy">
              Describe your banking, payments, lending, or trading system. FinanceAI retrieves local regulatory
              evidence, structures IEEE-style requirements, and selects the best lifecycle from 7 SDLC models.
            </p>
          </div>
        </section>

        <section className="workspace-grid">
          <div className="input-panel panel">
            <div className="panel-heading">
              <div>
                <p className="eyebrow">01 · Project Brief</p>
                <h3>What are you building?</h3>
              </div>
              <span className="counter">{brief.length.toLocaleString()}</span>
            </div>

            <textarea
              value={brief}
              onChange={(e) => setBrief(e.target.value)}
              placeholder="Example: Build a UPI payment app with biometric 2FA, encrypted QR scanning, KYC onboarding, audit trails, and RBI security compliance..."
            />

            <div className="sample-row">
              <span className="muted small">Examples:</span>
              {SAMPLE_BRIEFS.map((sample) => (
                <button
                  key={sample.label}
                  className="chip-btn"
                  type="button"
                  onClick={() => {
                    setBrief(sample.text);
                    handleAnalyze(sample.text);
                  }}
                >
                  {sample.label}
                </button>
              ))}
            </div>

            <div className="input-footer">
              <span className="muted small">Use fictional or anonymised project details only.</span>
              <button
                className="primary-button"
                type="button"
                disabled={loading}
                onClick={() => handleAnalyze()}
              >
                <Sparkles size={15} />
                {loading ? "Analyzing..." : "Generate analysis →"}
              </button>
            </div>
          </div>

          <div className="steps-panel panel" id="how-it-works">
            <p className="eyebrow">02 · Process</p>
            <h3>What happens next</h3>
            <ol className="process-list">
              <li>
                <span>1</span>
                <div>
                  <b>Hybrid RAG retrieval</b>
                  <p>Fuses BM25 + ChromaDB vector search over RBI, SEBI, ISO 20022, and NIST docs.</p>
                </div>
              </li>
              <li>
                <span>2</span>
                <div>
                  <b>Agent 1 · Requirements</b>
                  <p>Generates traceable SRS with acceptance criteria, risks, and evidence citations.</p>
                </div>
              </li>
              <li>
                <span>3</span>
                <div>
                  <b>Agent 2 · SDLC Architect</b>
                  <p>Evaluates Waterfall, V-Model, Agile, Spiral, Iterative, RAD, and Prototyping.</p>
                </div>
              </li>
            </ol>
            <div className="evidence-chip">BM25 + ChromaDB Vector · Ollama qwen2.5:1.5b · FastAPI</div>
          </div>
        </section>

        {loading && (
          <section className="loading-section">
            <div className="loader" />
            <div>
              <b>Running Hybrid RAG & 2-Agent Pipeline</b>
              <p className="muted small" style={{ margin: "4px 0 0" }}>
                Agent 1 is drafting the Finance SRS, then Agent 2 will select the optimal SDLC model.
              </p>
            </div>
          </section>
        )}

        {error && <div className="error-banner">{error}</div>}

        {result && (
          <section className="result-section">
            <div className="result-heading">
              <div>
                <p className="eyebrow accent">03 · Review Output</p>
                <h2>Analysis ready</h2>
              </div>
              <div className="result-actions">
                <button className="secondary-button" type="button" onClick={handleDownload}>
                  <Download size={14} />
                  Download Markdown
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  onClick={() => {
                    setResult(null);
                    window.scrollTo({ top: 0, behavior: "smooth" });
                  }}
                >
                  <RotateCcw size={14} />
                  New brief
                </button>
              </div>
            </div>

            <div className="result-tabs">
              <button
                className={`tab ${activeTab === "document" ? "active" : ""}`}
                onClick={() => setActiveTab("document")}
              >
                Complete document
              </button>
              <button
                className={`tab ${activeTab === "requirements" ? "active" : ""}`}
                onClick={() => setActiveTab("requirements")}
              >
                Requirements (Agent 1)
              </button>
              <button
                className={`tab ${activeTab === "sdlc" ? "active" : ""}`}
                onClick={() => setActiveTab("sdlc")}
              >
                SDLC Recommendation (Agent 2)
              </button>
              <button
                className={`tab ${activeTab === "evidence" ? "active" : ""}`}
                onClick={() => setActiveTab("evidence")}
              >
                Retrieved Evidence ({result.evidence.length})
              </button>
            </div>

            <article className="result-card">
              {activeTab === "evidence" ? (
                <div className="evidence-grid">
                  {result.evidence.map((item) => (
                    <div key={item.id} className="evidence-item">
                      <div className="evidence-item-head">
                        <span>
                          <FileText size={13} style={{ verticalAlign: "middle", marginRight: 6 }} />
                          {item.source}
                        </span>
                        <span>RRF Score: {item.score}</span>
                      </div>
                      <p className="muted small" style={{ margin: 0 }}>
                        {item.preview}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <div
                  dangerouslySetInnerHTML={{
                    __html: renderMarkdown(
                      activeTab === "requirements"
                        ? result.requirements
                        : activeTab === "sdlc"
                          ? result.sdlc
                          : result.document
                    ),
                  }}
                />
              )}
            </article>
          </section>
        )}

        <footer>FinanceAI · Local Requirements Engineering Workspace</footer>
      </main>
    </div>
  );
}
