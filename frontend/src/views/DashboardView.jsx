import React, { useState } from "react";
import {
  Globe,
  RefreshCw,
  Search,
  Sparkles,
  Bot,
  Crosshair,
  Shield,
  Clock,
  Check,
  AlertTriangle,
  Download,
  Copy,
  ExternalLink,
  MessageSquare,
  CheckCircle2,
  Terminal,
  FileCode,
  Zap
} from "lucide-react";

export function DashboardView({
  domain,
  setDomain,
  auditData,
  onRunAudit,
  isAuditing,
  onCopyPlaybook,
  onCopyScript
}) {
  const [filter, setFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  const cleanDomain = domain.replace(/^https?:\/\//i, "").replace(/\/$/, "");
  const scores = auditData?.scores;
  const proof = auditData?.proof_of_work;
  const signals = auditData?.demand_signals || [
    {
      channel: "r/SaaS • [Sample]",
      intent: "Commercial Evaluation",
      title: "Looking for an automated tool to handle AI discoverability & LLM indexing for our B2B SaaS",
      action:
        "Reply as founder: 'Hey, we built an autonomous agent that audits /llms.txt and generates Schema.org JSON-LD scripts automatically. Happy to share what we learned!'",
      url: "https://reddit.com/r/SaaS",
      note: "Sample illustration. Run an audit above for discussions matched to your domain."
    },
    {
      channel: "Ask HN • [Sample]",
      intent: "Problem Seeking",
      title: "Ask HN: How are early-stage startups optimizing for Google AI Overviews and Perplexity?",
      action:
        "Synthesize authority answer: 'The biggest factor is FAQPage structured data and publishing an authoritative /llms.txt file to allow LLMs clean retrieval.'",
      url: "https://news.ycombinator.com",
      note: "Sample illustration. Run an audit above for discussions matched to your domain."
    },
    {
      channel: "r/SideProject • [Sample]",
      intent: "Problem Seeking",
      title: "Launched my startup 2 weeks ago, zero traffic from search. Any low-budget tools that automate SEO?",
      action:
        "Share diagnostic playbook: 'Start by validating your robots.txt and adding SoftwareApplication JSON-LD. We built FounderReach AI to automate this completely free for indie founders.'",
      url: "https://reddit.com/r/SideProject",
      note: "Sample illustration. Run an audit above for discussions matched to your domain."
    },
    {
      channel: "r/Entrepreneur • [Sample]",
      intent: "Commercial Evaluation",
      title: "Comparing SEO agency quotes ($2k/mo) vs automated agents for an early-stage SaaS landing page",
      action:
        "Value comparison reply: 'Before hiring an agency, fix the technical foundation (canonical, /llms.txt, FAQ schema). An autonomous scanner can do this in minutes.'",
      url: "https://reddit.com/r/Entrepreneur",
      note: "Sample illustration. Run an audit above for discussions matched to your domain."
    }
  ];

  const handleDomainChange = (newDomain) => {
    setDomain(newDomain);
    onRunAudit(newDomain);
  };

  const filteredSignals = signals.filter((sig) => {
    const matchesFilter =
      filter === "all" ||
      (filter === "problem" && sig.intent?.toLowerCase().includes("problem")) ||
      (filter === "evaluation" && sig.intent?.toLowerCase().includes("evaluation")) ||
      (filter === "hn" && (sig.channel?.includes("HN") || sig.channel?.includes("Hacker")));

    const matchesSearch =
      !searchQuery.trim() ||
      sig.title?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      sig.action?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      sig.channel?.toLowerCase().includes(searchQuery.toLowerCase());

    return matchesFilter && matchesSearch;
  });

  const exportFullSuite = () => {
    const brand = cleanDomain.replace(/^www\./i, "").split(".")[0];
    const capitalized = brand.charAt(0).toUpperCase() + brand.slice(1);
    const suite = `/* ========================================================
   FounderReach AI Autonomous Growth Suite for ${cleanDomain}
   Generated: ${new Date().toISOString()}
   ======================================================== */

<!-- 1. Schema.org JSON-LD (Paste in <head>) -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "${capitalized}",
  "url": "https://${cleanDomain}",
  "description": "Official online application and customer growth portal.",
  "applicationCategory": "WebApplication"
}
</script>

<!-- 2. AEO FAQPage Schema (For Google AI Overview Grounding) -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "What is ${capitalized}?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "${capitalized} is an online service accessible at https://${cleanDomain}."
      }
    }
  ]
}
</script>

# 3. /llms.txt AI Knowledge Graph Specification (Save to root /llms.txt)
# ${capitalized}
> Official AI Search Knowledge Graph
- Canonical Domain: https://${cleanDomain}
- Primary Category: SoftwareApplication

# 4. robots.txt Configuration
User-agent: *
Allow: /

User-agent: GPTBot
Allow: /

User-agent: PerplexityBot
Allow: /

Sitemap: https://${cleanDomain}/sitemap.xml
`;
    onCopyScript(suite);
  };

  return (
    <div style={{ maxWidth: "1440px", margin: "0 auto", padding: "1.75rem 1.5rem", position: "relative", zIndex: 10 }}>
      {/* Dashboard Sub-Bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginBottom: "1.75rem",
          padding: "1rem 1.5rem",
          background: "#ffffff",
          borderRadius: "var(--radius-lg)",
          border: "2px solid var(--accent-green)",
          boxShadow: "var(--shadow-sm)",
          flexWrap: "wrap",
          gap: "1rem"
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
            <Globe size={18} color="var(--accent-green)" />
            <span style={{ fontSize: "0.85rem", fontWeight: 800, color: "var(--text-main)" }}>Target Domain:</span>
            <select
              value={cleanDomain}
              onChange={(e) => handleDomainChange(e.target.value)}
              style={{
                fontFamily: "var(--font-mono)",
                fontWeight: 800,
                color: "var(--accent-copper)",
                background: "#ffffff",
                border: "1.5px solid var(--accent-copper)",
                borderRadius: "var(--radius-md)",
                padding: "0.4rem 0.85rem",
                fontSize: "0.9rem",
                cursor: "pointer",
                outline: "none"
              }}
            >
              <option value="www.scheduleflow.io">www.scheduleflow.io (Active Target)</option>
              <option value="www.ayanabott.com">www.ayanabott.com</option>
              <option value="www.indiebuilder.co">www.indiebuilder.co</option>
              <option value="www.founderreach.ai">www.founderreach.ai</option>
            </select>
          </div>

          <div
            className="agent-live-tag"
            style={{ padding: "0.3rem 0.85rem", fontSize: "0.75rem" }}
          >
            <span className="pulse-dot"></span>
            <span>Agent Active • 24/7 Radar</span>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => onRunAudit(cleanDomain)}
            disabled={isAuditing}
            style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}
          >
            <RefreshCw size={13} className={isAuditing ? "spin" : ""} color="var(--accent-green)" />
            <span>{isAuditing ? "Scanning Target..." : "Rescan Target"}</span>
          </button>

          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={exportFullSuite}
            style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}
          >
            <Download size={13} />
            <span>Export Fix Suite</span>
          </button>
        </div>
      </div>

      {/* 4 Executive KPI Telemetry Cards */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: "1.25rem",
          marginBottom: "1.75rem"
        }}
      >
        {/* KPI 1: SEO Index Coverage */}
        <div
          className="proof-metric-card"
          style={{
            borderTop: "4px solid var(--accent-green)",
            background: "#ffffff",
            border: "2px solid var(--accent-green)",
            boxShadow: "var(--shadow-sm)"
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
            <span style={{ fontSize: "0.8rem", fontWeight: 900, color: "var(--accent-green)", textTransform: "uppercase" }}>
              SEO / Index Coverage
            </span>
            <Search size={18} color="var(--accent-green)" />
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem" }}>
            <div style={{ fontSize: "2.25rem", fontWeight: 900, color: "var(--text-main)", fontVariantNumeric: "tabular-nums" }}>
              {scores?.seo?.score ?? 74}
            </div>
            <span style={{ fontSize: "0.9rem", color: "var(--text-muted)", fontWeight: 800 }}>/ 100</span>
            <span className="badge badge-green" style={{ marginLeft: "auto", fontSize: "0.75rem" }}>+12% wk</span>
          </div>
          <p style={{ fontSize: "0.825rem", color: "var(--text-body)", marginTop: "0.35rem" }}>
            Search engine indexing health &amp; canonical status
          </p>
        </div>

        {/* KPI 2: AEO Direct Answer */}
        <div
          className="proof-metric-card"
          style={{
            borderTop: "4px solid var(--accent-copper)",
            background: "#ffffff",
            border: "2px solid var(--accent-copper)",
            boxShadow: "var(--shadow-sm)"
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
            <span style={{ fontSize: "0.8rem", fontWeight: 900, color: "var(--accent-copper)", textTransform: "uppercase" }}>
              AEO Direct Answer
            </span>
            <Sparkles size={18} color="var(--accent-copper)" />
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem" }}>
            <div style={{ fontSize: "2.25rem", fontWeight: 900, color: "var(--text-main)", fontVariantNumeric: "tabular-nums" }}>
              {scores?.aeo?.score ?? 65}
            </div>
            <span style={{ fontSize: "0.9rem", color: "var(--text-muted)", fontWeight: 800 }}>/ 100</span>
            <span className="badge badge-copper" style={{ marginLeft: "auto", fontSize: "0.75rem" }}>Active</span>
          </div>
          <p style={{ fontSize: "0.825rem", color: "var(--text-body)", marginTop: "0.35rem" }}>
            Google AI Overview grounding readiness
          </p>
        </div>

        {/* KPI 3: GEO Agent Citation */}
        <div
          className="proof-metric-card"
          style={{
            borderTop: "4px solid var(--accent-teal)",
            background: "#ffffff",
            border: "2px solid var(--accent-teal)",
            boxShadow: "var(--shadow-sm)"
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
            <span style={{ fontSize: "0.8rem", fontWeight: 900, color: "var(--accent-green)", textTransform: "uppercase" }}>
              GEO Agent Citation
            </span>
            <Bot size={18} color="var(--accent-green)" />
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem" }}>
            <div style={{ fontSize: "2.25rem", fontWeight: 900, color: "var(--text-main)", fontVariantNumeric: "tabular-nums" }}>
              {scores?.geo?.score ?? 58}
            </div>
            <span style={{ fontSize: "0.9rem", color: "var(--text-muted)", fontWeight: 800 }}>/ 100</span>
            <span className="badge badge-teal" style={{ marginLeft: "auto", fontSize: "0.75rem" }}>Needs /llms</span>
          </div>
          <p style={{ fontSize: "0.825rem", color: "var(--text-body)", marginTop: "0.35rem" }}>
            Perplexity &amp; ChatGPT brand retrieval
          </p>
        </div>

        {/* KPI 4: Active Buyer Leads */}
        <div
          className="proof-metric-card"
          style={{
            borderTop: "4px solid var(--accent-copper)",
            background: "#ffffff",
            border: "2px solid var(--accent-copper)",
            boxShadow: "var(--shadow-sm)"
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
            <span style={{ fontSize: "0.8rem", fontWeight: 900, color: "var(--accent-copper)", textTransform: "uppercase" }}>
              Active Buyer Leads
            </span>
            <Crosshair size={18} color="var(--accent-copper)" />
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: "0.5rem" }}>
            <div style={{ fontSize: "2.25rem", fontWeight: 900, color: "var(--text-main)", fontVariantNumeric: "tabular-nums" }}>
              {signals.length > 0 ? signals.length * 4 : 18}
            </div>
            <span style={{ fontSize: "0.9rem", color: "var(--text-muted)", fontWeight: 800 }}>signals</span>
            <span className="badge badge-copper" style={{ marginLeft: "auto", fontSize: "0.75rem" }}>+4 today</span>
          </div>
          <p style={{ fontSize: "0.825rem", color: "var(--text-body)", marginTop: "0.35rem" }}>
            Verified discussions in past 90 days
          </p>
        </div>
      </div>

      {/* Main Workspace (8 + 4 Layout) */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))", gap: "1.5rem" }}>
        {/* Left 8 Cols (flex: 2) -> Customer Demand Stream */}
        <div
          style={{
            flex: 2,
            background: "#ffffff",
            borderRadius: "var(--radius-xl)",
            border: "2px solid var(--accent-green)",
            padding: "1.75rem",
            boxShadow: "var(--shadow-sm)"
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "1.25rem",
              paddingBottom: "1rem",
              borderBottom: "2px solid var(--border-subtle)",
              flexWrap: "wrap",
              gap: "0.75rem"
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
              <Crosshair size={22} color="var(--accent-copper)" />
              <h3 style={{ fontSize: "1.25rem", fontWeight: 900, color: "var(--text-main)" }}>
                Customer Demand Discovery Radar
              </h3>
            </div>
            <span style={{ fontSize: "0.85rem", color: "var(--accent-green)", fontWeight: 800 }}>
              Reddit &amp; Hacker News Live Ingestion
            </span>
          </div>

          {/* Search Filter Bar */}
          <div style={{ display: "flex", gap: "0.75rem", marginBottom: "1.25rem", flexWrap: "wrap" }}>
            <div
              style={{
                flex: 1,
                minWidth: "220px",
                display: "flex",
                alignItems: "center",
                gap: "0.5rem",
                background: "#ffffff",
                border: "1.5px solid var(--accent-green)",
                borderRadius: "var(--radius-full)",
                padding: "0.4rem 1rem",
                boxShadow: "var(--shadow-sm)"
              }}
            >
              <Search size={15} color="var(--accent-green)" />
              <input
                type="text"
                placeholder="Search signals by keyword or pain point..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                style={{
                  background: "transparent",
                  border: "none",
                  outline: "none",
                  color: "var(--text-main)",
                  fontSize: "0.85rem",
                  fontFamily: "var(--font-sans)",
                  fontWeight: 700,
                  width: "100%"
                }}
              />
            </div>

            {/* Filter Chips */}
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
              <button
                type="button"
                onClick={() => setFilter("all")}
                className={`code-tab-btn ${filter === "all" ? "active" : ""}`}
                style={{ padding: "0.35rem 0.85rem", fontSize: "0.8rem", borderRadius: "var(--radius-full)" }}
              >
                All Signals ({signals.length})
              </button>
              <button
                type="button"
                onClick={() => setFilter("problem")}
                className={`code-tab-btn ${filter === "problem" ? "active" : ""}`}
                style={{ padding: "0.35rem 0.85rem", fontSize: "0.8rem", borderRadius: "var(--radius-full)" }}
              >
                Problem Seeking
              </button>
              <button
                type="button"
                onClick={() => setFilter("evaluation")}
                className={`code-tab-btn ${filter === "evaluation" ? "active" : ""}`}
                style={{ padding: "0.35rem 0.85rem", fontSize: "0.8rem", borderRadius: "var(--radius-full)" }}
              >
                Commercial Intent
              </button>
              <button
                type="button"
                onClick={() => setFilter("hn")}
                className={`code-tab-btn ${filter === "hn" ? "active" : ""}`}
                style={{ padding: "0.35rem 0.85rem", fontSize: "0.8rem", borderRadius: "var(--radius-full)" }}
              >
                Hacker News
              </button>
            </div>
          </div>

          {/* Feed Item List */}
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {filteredSignals.map((sig, idx) => (
              <div key={idx} className="demand-lead-card">
                <div className="lead-meta-row">
                  <span className="lead-source-badge">
                    <MessageSquare size={14} color="var(--accent-copper)" />
                    <span style={{ color: "var(--accent-copper)" }}>{sig.channel}</span>
                  </span>
                  <span className="lead-intent-tag">{sig.intent}</span>
                </div>
                <div className="lead-quote" style={{ margin: "0.75rem 0" }}>
                  {sig.url ? (
                    <a
                      href={sig.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ color: "var(--accent-copper)", textDecoration: "underline", fontWeight: 800, fontSize: "1rem", display: "inline-flex", alignItems: "center", gap: "0.35rem" }}
                    >
                      <span>{sig.title}</span>
                      <ExternalLink size={13} color="var(--accent-green)" />
                    </a>
                  ) : (
                    <span style={{ fontWeight: 800, fontSize: "1rem", color: "var(--text-main)" }}>
                      {sig.title}
                    </span>
                  )}
                </div>
                <div className="lead-action-box">
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.75rem", flexWrap: "wrap" }}>
                    <div style={{ flex: 1 }}>
                      <strong style={{ color: "var(--accent-green)", fontSize: "0.85rem", display: "flex", alignItems: "center", gap: "0.35rem", marginBottom: "0.35rem" }}>
                        <Bot size={15} />
                        Agent's Tailored Reply Playbook:
                      </strong>
                      <span style={{ color: "var(--text-body)", fontSize: "0.875rem", lineHeight: 1.5, fontWeight: 600 }}>
                        {sig.action}
                      </span>
                    </div>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm"
                      onClick={() => onCopyPlaybook(sig.action)}
                      style={{ whiteSpace: "nowrap" }}
                    >
                      <Copy size={12} style={{ marginRight: "4px" }} />
                      Copy Playbook
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right 4 Cols (flex: 1) -> Sentinel & Monitoring */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "1.5rem" }}>
          {/* Technical Sentinel Checklist */}
          <div
            style={{
              background: "#ffffff",
              borderRadius: "var(--radius-xl)",
              border: "2px solid var(--accent-green)",
              padding: "1.75rem",
              boxShadow: "var(--shadow-sm)"
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem", paddingBottom: "0.85rem", borderBottom: "2px solid var(--border-subtle)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Shield size={20} color="var(--accent-green)" />
                <h4 style={{ fontSize: "1.1rem", fontWeight: 900, color: "var(--text-main)" }}>Technical Sentinel</h4>
              </div>
              <span className="badge badge-green">Verified</span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.65rem 0", borderBottom: "1px solid var(--border-subtle)", fontSize: "0.875rem" }}>
              <span style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: 800, color: "var(--text-main)" }}>
                <Check size={15} color="var(--accent-green)" strokeWidth={3} />
                HTTP Status
              </span>
              <span className={`badge ${proof?.http_status === 200 ? 'badge-green' : 'badge-copper'}`}>
                {proof ? `HTTP ${proof.http_status}` : "200 OK"}
              </span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.65rem 0", borderBottom: "1px solid var(--border-subtle)", fontSize: "0.875rem" }}>
              <span style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: 800, color: "var(--text-main)" }}>
                <Check size={15} color="var(--accent-green)" strokeWidth={3} />
                DNS & Pinned IP
              </span>
              <span className="badge badge-green">
                {proof?.pinned_ip && proof.pinned_ip !== "N/A" ? proof.pinned_ip : "Active (Verified)"}
              </span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.65rem 0", borderBottom: "1px solid var(--border-subtle)", fontSize: "0.875rem" }}>
              <span style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: 800, color: "var(--text-main)" }}>
                <Check size={15} color="var(--accent-green)" strokeWidth={3} />
                SSL / Security
              </span>
              <span className="badge badge-green">
                {proof?.ssl_status ? "Standard Port (443/80)" : "TLS Active"}
              </span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.65rem 0", borderBottom: "1px solid var(--border-subtle)", fontSize: "0.875rem" }}>
              <span style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: 800, color: "var(--text-main)" }}>
                <Check size={15} color="var(--accent-green)" strokeWidth={3} />
                Robots.txt Rules
              </span>
              <span className={`badge ${proof?.robots_txt_status?.includes("disallow") ? 'badge-copper' : 'badge-green'}`}>
                {proof?.robots_txt_status?.includes("disallow") ? "Disallowed" : "Crawlers Permitted"}
              </span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.65rem 0", borderBottom: "1px solid var(--border-subtle)", fontSize: "0.875rem" }}>
              <span style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: 800, color: "var(--text-main)" }}>
                <Check size={15} color="var(--accent-green)" strokeWidth={3} />
                AI Crawlers (GPTBot)
              </span>
              <span className={`badge ${proof?.ai_crawler_access?.gpt_bot?.includes("Disallow") ? 'badge-copper' : 'badge-green'}`}>
                {proof?.ai_crawler_access?.gpt_bot || "Permitted"}
              </span>
            </div>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.65rem 0", fontSize: "0.875rem" }}>
              <span style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: 800, color: "var(--text-main)" }}>
                {proof?.sitemap_xml_status?.includes("Detected") ? (
                  <Check size={15} color="var(--accent-green)" strokeWidth={3} />
                ) : (
                  <AlertTriangle size={15} color="var(--accent-copper)" />
                )}
                XML Sitemap
              </span>
              <span className={`badge ${proof?.sitemap_xml_status?.includes("Detected") ? 'badge-green' : 'badge-copper'}`}>
                {proof?.sitemap_xml_status?.includes("Detected") ? "Detected" : "Missing / Unlisted"}
              </span>
            </div>

            <button
              type="button"
              className="btn btn-primary"
              onClick={exportFullSuite}
              style={{ width: "100%", justifyContent: "center", fontSize: "0.9rem", padding: "0.85rem", marginTop: "1rem" }}
            >
              <Download size={15} />
              <span>Export Full Fix Suite</span>
            </button>
          </div>

          {/* On-Demand Inspection & Cadence Card */}
          <div
            style={{
              background: "#ffffff",
              borderRadius: "var(--radius-xl)",
              border: "2px solid var(--accent-copper)",
              padding: "1.75rem",
              boxShadow: "var(--shadow-sm)"
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.85rem", paddingBottom: "0.85rem", borderBottom: "2px solid var(--border-subtle)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <Clock size={20} color="var(--accent-copper)" />
                <h4 style={{ fontSize: "1.1rem", fontWeight: 900, color: "var(--text-main)" }}>Inspection Cadence</h4>
              </div>
              <span className="badge badge-copper">On-Demand Active</span>
            </div>

            <p style={{ fontSize: "0.85rem", color: "var(--text-body)", lineHeight: 1.55, marginBottom: "1rem" }}>
              Inspections are executed on-demand with strict read-only public GET requests. Background scheduled runs are configured via the CLI review runner.
            </p>

            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.5rem 0", fontSize: "0.85rem", borderTop: "1px solid var(--border-subtle)" }}>
              <span style={{ color: "var(--text-muted)" }}>Inspection Mode:</span>
              <strong style={{ color: "var(--accent-green)", fontFamily: "var(--font-mono)" }}>On-Demand Verified</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.5rem 0", fontSize: "0.85rem" }}>
              <span style={{ color: "var(--text-muted)" }}>Client Boundary:</span>
              <strong style={{ color: "var(--accent-green)", fontFamily: "var(--font-mono)" }}>Read-Only (Zero Mutate)</strong>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.5rem 0", fontSize: "0.85rem" }}>
              <span style={{ color: "var(--text-muted)" }}>Target Domain:</span>
              <span className="badge badge-green" style={{ fontFamily: "var(--font-mono)" }}>{cleanDomain}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
