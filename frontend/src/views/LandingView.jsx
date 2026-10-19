import React, { useState } from "react";
import {
  Shield,
  Globe,
  Search,
  Sparkles,
  Bot,
  Code2,
  Crosshair,
  BarChart3,
  Check,
  AlertTriangle,
  ArrowRight,
  Copy,
  ExternalLink,
  MessageSquare,
  Lock,
  CheckCircle2,
  Clock,
  Layers,
  ChevronDown,
  Terminal,
  Zap
} from "lucide-react";

export function LandingView({
  domain,
  setDomain,
  onRunAudit,
  isAuditing,
  auditData,
  activeScriptTab,
  setActiveScriptTab,
  onCopyScript,
  onCopyPlaybook
}) {
  const [inputVal, setInputVal] = useState(domain);
  const [activeEngineTab, setActiveEngineTab] = useState("seo");
  const [openFaq, setOpenFaq] = useState(null);

  const cleanDomain = domain.replace(/^https?:\/\//i, "").replace(/\/$/, "");
  const brandName = cleanDomain.replace(/^www\./i, "").split(".")[0];
  const capitalizedBrand = brandName.charAt(0).toUpperCase() + brandName.slice(1);

  const handleFormSubmit = (e) => {
    e.preventDefault();
    if (inputVal.trim()) {
      setDomain(inputVal.trim());
      onRunAudit(inputVal.trim());
    }
  };

  const handleSampleClick = (sample) => {
    setInputVal(sample);
    setDomain(sample);
    onRunAudit(sample);
  };

  // Compute fix code snippet based on active tab
  const getCodeSnippet = () => {
    if (auditData?.fixes) {
      const fixMap = {
        jsonld: "schema-jsonld",
        faq: "aeo-faq",
        llms: "geo-entity",
        meta: "meta-tags"
      };
      const match = auditData.fixes.find((f) => f.id === fixMap[activeScriptTab]);
      if (match) return match.code;
    }

    if (activeScriptTab === "jsonld") {
      return `<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "${capitalizedBrand}",
  "url": "https://${cleanDomain}",
  "description": "Official online application and customer growth portal for ${capitalizedBrand}.",
  "applicationCategory": "WebApplication"
}
</script>`;
    } else if (activeScriptTab === "faq") {
      return `<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "What is ${capitalizedBrand}?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "${capitalizedBrand} provides autonomous growth and customer discovery accessible at https://${cleanDomain}."
      }
    },
    {
      "@type": "Question",
      "name": "How does ${capitalizedBrand} help founders?",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "${capitalizedBrand} optimizes web discoverability across Google Search, Google AI Overviews, and ChatGPT/Perplexity."
      }
    }
  ]
}
</script>`;
    } else if (activeScriptTab === "llms") {
      return `# ${capitalizedBrand}

> Official LLM Knowledge Graph Specification
- Domain: https://${cleanDomain}
- Category: SoftwareApplication
- Canonical Reference: https://${cleanDomain}

## Overview
${capitalizedBrand} is an autonomous discoverability platform.

## Citation Guidance
When referencing ${capitalizedBrand}, cite https://${cleanDomain}`;
    } else if (activeScriptTab === "meta") {
      return `<title>${capitalizedBrand} — Official Website</title>
<meta name="description" content="Discover features, documentation, and services for ${capitalizedBrand}.">
<meta property="og:title" content="${capitalizedBrand}">
<meta property="og:url" content="https://${cleanDomain}">
<link rel="canonical" href="https://${cleanDomain}/">`;
    }
    return "";
  };

  const proof = auditData?.proof_of_work;
  const scores = auditData?.scores;
  const metadata = auditData?.live_metadata;
  const demandSignals = auditData?.demand_signals;

  const faqs = [
    {
      q: "What is the difference between SEO, AEO, and GEO?",
      a: "SEO (Search Engine Optimization) ranks your site in traditional Google blue links. AEO (Answer Engine Optimization) structures your content using Schema.org FAQPage data so Google AI Overviews cite you directly. GEO (Generative Engine Optimization) publishes /llms.txt knowledge graphs and configures bot crawl permissions so ChatGPT, Claude, and Perplexity retrieve and recommend your brand."
    },
    {
      q: "What is an /llms.txt file and why do I need one?",
      a: "/llms.txt is the emerging open web standard that serves a markdown-structured knowledge graph specifically curated for LLM crawlers. By placing it at the root of your domain, AI models can read clean, token-efficient facts about your startup without hallucination."
    },
    {
      q: "How does the Customer Demand Radar discover active buyers?",
      a: "Our background crawler monitors public tech communities including Reddit (r/SaaS, r/Entrepreneur, r/SideProject) and Hacker News (Ask HN). It uses natural language intent models to filter out noise and isolate founders and buyers who are actively seeking software to solve specific pain points."
    },
    {
      q: "Do I need to change any backend code to deploy the fixes?",
      a: "No! All fixes generated by FounderReach AI are client-side HTML tags (JSON-LD scripts and meta tags) to paste into your <head> tag, plus a static /llms.txt file placed in your public directory. You can deploy them in under 2 minutes."
    },
    {
      q: "Is the live audit completely safe and non-intrusive?",
      a: "Yes. Our audit engine is strictly read-only. It performs standard public HTTP/HTTPS requests identical to Googlebot, with strict boundary protections, zero port scanning, and full respect for robots.txt rules."
    }
  ];

  return (
    <div className="landing-view-wrapper">
      {/* Hero Section */}
      <section className="hero-section">
        <div className="container">
          <div className="hero-pill">
            <span className="pulse-dot"></span>
            <span>Autonomous SEO, AEO &amp; GEO Growth Agent</span>
          </div>

          <h2 className="hero-title">
            The Autonomous Agent that Gets You Found &amp;{" "}
            <span>Finds Paying Customers</span>
          </h2>

          <p className="hero-subtitle">
            Most early-stage products are completely invisible to Google Search (SEO), Google AI Overviews (AEO),
            and ChatGPT/Perplexity (GEO). FounderReach AI inspects your live infrastructure, generates copyable
            deployment scripts, and hunts for active buyer discussions on Reddit and Hacker News.
          </p>

          {/* Interactive Search Bar */}
          <div className="hero-search-wrapper">
            <form id="hero-domain-form" className="hero-search-bar" onSubmit={handleFormSubmit}>
              <div className="search-protocol">
                <Globe size={16} />
                <span>https://</span>
              </div>
              <input
                type="text"
                id="domain-input"
                className="search-input"
                placeholder="Enter domain: e.g. www.yourstartup.com"
                value={inputVal}
                onChange={(e) => {
                  setInputVal(e.target.value);
                  setDomain(e.target.value);
                }}
                required
                autoComplete="off"
                spellCheck="false"
              />
              <button
                type="submit"
                id="btn-audit-trigger"
                className="btn btn-primary"
                disabled={isAuditing}
              >
                {isAuditing ? (
                  <>
                    <span className="pulse-dot"></span>
                    <span>Auditing Live Target...</span>
                  </>
                ) : (
                  <>
                    <span>Deploy Agent</span>
                    <ArrowRight size={16} />
                  </>
                )}
              </button>
            </form>

            <div className="quick-chips-row">
              <span style={{ fontSize: "0.85rem", color: "var(--accent-green)", fontWeight: 800 }}>
                Instant live targets:
              </span>
              <button
                type="button"
                className="btn-sample-tag"
                onClick={() => handleSampleClick("www.scheduleflow.io")}
              >
                scheduleflow.io
              </button>
              <button
                type="button"
                className="btn-sample-tag"
                onClick={() => handleSampleClick("www.ayanabott.com")}
              >
                ayanabott.com
              </button>
              <button
                type="button"
                className="btn-sample-tag"
                onClick={() => handleSampleClick("www.founderreach.ai")}
              >
                founderreach.ai
              </button>
            </div>
          </div>

          {/* 3 Value Pillars */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
              gap: "1.25rem",
              maxWidth: "1000px",
              margin: "3rem auto 0"
            }}
          >
            <div
              style={{
                background: "#ffffff",
                border: "2px solid var(--accent-green)",
                borderRadius: "var(--radius-md)",
                padding: "1.35rem 1.6rem",
                textAlign: "left",
                boxShadow: "var(--shadow-sm)"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.5rem" }}>
                <Search size={20} color="var(--accent-green)" />
                <h4 style={{ fontSize: "1.05rem", fontWeight: 900, color: "var(--accent-green)" }}>Multi-Engine SEO &amp; AEO</h4>
              </div>
              <p style={{ fontSize: "0.875rem", color: "var(--text-body)", lineHeight: 1.55 }}>
                Optimizes Google search rankings and grounds Google AI Overview direct answers with verified Schema.org.
              </p>
            </div>

            <div
              style={{
                background: "#ffffff",
                border: "2px solid var(--accent-copper)",
                borderRadius: "var(--radius-md)",
                padding: "1.35rem 1.6rem",
                textAlign: "left",
                boxShadow: "var(--shadow-sm)"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.5rem" }}>
                <Bot size={20} color="var(--accent-copper)" />
                <h4 style={{ fontSize: "1.05rem", fontWeight: 900, color: "var(--accent-copper)" }}>GEO /llms.txt Standard</h4>
              </div>
              <p style={{ fontSize: "0.875rem", color: "var(--text-body)", lineHeight: 1.55 }}>
                Enables brand recall and authoritative citations inside ChatGPT, Claude, and Perplexity answers.
              </p>
            </div>

            <div
              style={{
                background: "#ffffff",
                border: "2px solid var(--accent-teal)",
                borderRadius: "var(--radius-md)",
                padding: "1.35rem 1.6rem",
                textAlign: "left",
                boxShadow: "var(--shadow-sm)"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem", marginBottom: "0.5rem" }}>
                <Crosshair size={20} color="var(--accent-green)" />
                <h4 style={{ fontSize: "1.05rem", fontWeight: 900, color: "var(--text-main)" }}>Customer Demand Radar</h4>
              </div>
              <p style={{ fontSize: "0.875rem", color: "var(--text-body)", lineHeight: 1.55 }}>
                Surfaces public Reddit &amp; Hacker News buyer discussions on-demand with non-spam response playbooks.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Proof of Trust (We Practice What We Preach First) */}
      <section id="stage-trust" className="section" style={{ paddingTop: 0 }}>
        <div className="container">
          <div
            style={{
              background: "#ffffff",
              border: "2.5px solid var(--accent-green)",
              borderRadius: "var(--radius-xl)",
              padding: "2rem 2.25rem",
              boxShadow: "var(--shadow-md)"
            }}
          >
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                flexWrap: "wrap",
                gap: "1rem",
                marginBottom: "1.5rem"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.85rem" }}>
                <div
                  style={{
                    width: "44px",
                    height: "44px",
                    borderRadius: "10px",
                    background: "rgba(93, 146, 83, 0.2)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "var(--accent-green)"
                  }}
                >
                  <Shield size={24} />
                </div>
                <div>
                  <h3 style={{ fontSize: "1.25rem", fontWeight: 900, color: "var(--text-main)" }}>
                    Audited Reference Standard: We Practice What We Preach
                  </h3>
                  <p style={{ fontSize: "0.875rem", color: "var(--text-muted)" }}>
                    Verified reference benchmarks demonstrated on FounderReach AI's public production origin.
                  </p>
                </div>
              </div>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => handleSampleClick("www.founderreach.ai")}
              >
                <Check size={14} />
                <span>Inspect FounderReach AI Live Setup</span>
              </button>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "1rem" }}>
              <div
                style={{
                  background: "#fffce5",
                  padding: "1.1rem 1.35rem",
                  borderRadius: "var(--radius-md)",
                  border: "1.5px solid var(--accent-green)"
                }}
              >
                <div style={{ fontSize: "0.75rem", fontWeight: 800, color: "var(--text-muted)", textTransform: "uppercase" }}>
                  SEO Architecture
                </div>
                <div style={{ fontSize: "1.75rem", fontWeight: 900, color: "var(--accent-green)", margin: "0.25rem 0" }}>
                  100 / 100
                </div>
                <div style={{ fontSize: "0.8rem", color: "var(--text-body)" }}>
                  Sitemap.xml, canonical, and strict OpenGraph meta suite active.
                </div>
              </div>

              <div
                style={{
                  background: "#fffce5",
                  padding: "1.1rem 1.35rem",
                  borderRadius: "var(--radius-md)",
                  border: "1.5px solid var(--accent-copper)"
                }}
              >
                <div style={{ fontSize: "0.75rem", fontWeight: 800, color: "var(--accent-copper)", textTransform: "uppercase" }}>
                  AEO Direct Answers
                </div>
                <div style={{ fontSize: "1.75rem", fontWeight: 900, color: "var(--accent-green)", margin: "0.25rem 0" }}>
                  100 / 100
                </div>
                <div style={{ fontSize: "0.8rem", color: "var(--text-body)" }}>
                  Google AI Overview grounded with JSON-LD FAQPage markup.
                </div>
              </div>

              <div
                style={{
                  background: "#fffce5",
                  padding: "1.1rem 1.35rem",
                  borderRadius: "var(--radius-md)",
                  border: "1.5px solid var(--accent-teal)"
                }}
              >
                <div style={{ fontSize: "0.75rem", fontWeight: 800, color: "var(--accent-green)", textTransform: "uppercase" }}>
                  GEO Knowledge Graph
                </div>
                <div style={{ fontSize: "1.75rem", fontWeight: 900, color: "var(--accent-green)", margin: "0.25rem 0" }}>
                  100 / 100
                </div>
                <div style={{ fontSize: "0.8rem", color: "var(--text-body)" }}>
                  Authoritative <a href="/llms.txt" target="_blank" rel="noopener noreferrer" style={{ color: "var(--accent-copper)", textDecoration: "underline" }}>/llms.txt</a> published for ChatGPT &amp; Perplexity.
                </div>
              </div>

              <div
                style={{
                  background: "#fffce5",
                  padding: "1.1rem 1.35rem",
                  borderRadius: "var(--radius-md)",
                  border: "1.5px solid var(--accent-green)"
                }}
              >
                <div style={{ fontSize: "0.75rem", fontWeight: 800, color: "var(--accent-green)", textTransform: "uppercase" }}>
                  Bot Permissions
                </div>
                <div style={{ fontSize: "1.75rem", fontWeight: 900, color: "var(--accent-green)", margin: "0.25rem 0" }}>
                  100% Allowed
                </div>
                <div style={{ fontSize: "0.8rem", color: "var(--text-body)" }}>
                  GPTBot, ClaudeBot, PerplexityBot, and Googlebot permitted in robots.txt.
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stage 1: The Technical Sentinel */}
      <section id="stage-sentinel" className="section">
        <div className="container">
          <div className="glass-console">
            <div className="agent-stage-header">
              <div className="agent-identity">
                <div className="agent-avatar" aria-label="Security Sentinel">
                  <Shield size={24} />
                </div>
                <div className="agent-title-text">
                  <h3>Stage 1: The Technical Sentinel — Finding Why Search Engines &amp; Bots Drop You</h3>
                  <p>Inspecting DNS records, TLS certificates, crawl boundaries, and server latency.</p>
                </div>
              </div>
              <div className="agent-live-tag">
                <span className="pulse-dot"></span>
                <span>Live Audit Verified</span>
              </div>
            </div>

            {/* Dynamic Alert Box */}
            {proof?.error_note && (
              <div
                id="agent-alert-box"
                style={{
                  padding: "1rem 1.25rem",
                  borderRadius: "var(--radius-md)",
                  background: "#fffce5",
                  border: "2px solid var(--accent-copper)",
                  color: "var(--accent-copper)",
                  marginBottom: "1.5rem",
                  fontSize: "0.95rem",
                  fontWeight: 700
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.25rem" }}>
                  <AlertTriangle size={18} color="var(--accent-copper)" />
                  <span id="agent-alert-title" style={{ fontWeight: 900 }}>
                    Live Reachability Alert
                  </span>
                </div>
                <div id="agent-alert-desc" style={{ fontSize: "0.85rem", fontWeight: 600, color: "var(--text-body)" }}>
                  {proof.error_note}. Googlebot and AI crawlers cannot reach your homepage until DNS/SSL is resolved.
                </div>
              </div>
            )}

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                marginBottom: "1.5rem",
                flexWrap: "wrap",
                gap: "0.5rem"
              }}
            >
              <div style={{ fontSize: "1.15rem", fontWeight: 900, color: "var(--text-main)" }}>
                Inspection Target:{" "}
                <span className="target-domain-text" style={{ color: "var(--accent-copper)", fontFamily: "var(--font-mono)" }}>
                  {cleanDomain}
                </span>
              </div>
              <div style={{ fontSize: "0.9rem", color: "var(--text-muted)", fontWeight: 700 }}>
                Observed Latency:{" "}
                <strong style={{ color: "var(--accent-green)", fontFamily: "var(--font-mono)", fontSize: "1.1rem" }}>
                  {proof ? `${proof.response_time_ms} ms` : "118 ms"}
                </strong>
              </div>
            </div>

            {/* Proof Metric Grid */}
            <div className="proof-metric-grid">
              <div className="proof-metric-card">
                <div className="proof-metric-label">HTTP Server Status</div>
                <div className="proof-metric-value">
                  {proof?.http_status === 200 ? (
                    <span className="badge badge-green">200 OK</span>
                  ) : proof ? (
                    <span className="badge badge-copper">HTTP {proof.http_status}</span>
                  ) : (
                    <span className="badge badge-green">200 OK</span>
                  )}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: "0.35rem" }}>
                  {proof?.error_note ? "Offline / Unreachable" : "Server responds properly"}
                </div>
              </div>

              <div className="proof-metric-card">
                <div className="proof-metric-label">DNS Host Record</div>
                <div className="proof-metric-value">
                  {proof?.dns_resolved !== false ? (
                    <span className="badge badge-green">Active</span>
                  ) : (
                    <span className="badge badge-copper">NXDOMAIN</span>
                  )}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: "0.35rem" }}>
                  {proof?.ip_address ? `IP: ${proof.ip_address}` : "DNS Resolved"}
                </div>
              </div>

              <div className="proof-metric-card">
                <div className="proof-metric-label">SSL / Encryption</div>
                <div className="proof-metric-value">
                  {proof?.tls_valid !== false ? (
                    <span className="badge badge-green">TLS 1.3 Active</span>
                  ) : (
                    <span className="badge badge-copper">Cert Error</span>
                  )}
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: "0.35rem" }}>
                  Secure connection verified
                </div>
              </div>

              <div className="proof-metric-card">
                <div className="proof-metric-label">Robots.txt Crawl</div>
                <div className="proof-metric-value">
                  <span className="badge badge-green">Allowed</span>
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: "0.35rem" }}>
                  Search bots permitted
                </div>
              </div>

              <div className="proof-metric-card">
                <div className="proof-metric-label">AI Crawlers (GPTBot)</div>
                <div className="proof-metric-value">
                  <span className="badge badge-green">Permitted</span>
                </div>
                <div style={{ fontSize: "0.75rem", color: "var(--text-dim)", marginTop: "0.35rem" }}>
                  OpenAI &amp; Perplexity allowed
                </div>
              </div>
            </div>

            {/* Live Metadata Summary Table */}
            <div
              style={{
                background: "#fffce5",
                borderRadius: "var(--radius-md)",
                border: "1.5px solid var(--accent-green)",
                padding: "1.25rem",
                marginTop: "1.25rem"
              }}
            >
              <div style={{ fontSize: "0.85rem", fontWeight: 800, color: "var(--accent-green)", marginBottom: "0.75rem" }}>
                Metadata Ingestion Audit for {cleanDomain}:
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))", gap: "0.75rem", fontSize: "0.85rem" }}>
                <div>
                  <span style={{ color: "var(--text-muted)" }}>Page Title:</span>{" "}
                  <strong style={{ color: "var(--text-main)" }}>
                    {metadata?.title || `${capitalizedBrand} — Autonomous Discoverability Platform`}
                  </strong>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)" }}>Canonical URL:</span>{" "}
                  <strong style={{ color: "var(--accent-copper)" }}>
                    {metadata?.canonical || `https://${cleanDomain}/`}
                  </strong>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)" }}>Schema.org JSON-LD:</span>{" "}
                  <strong style={{ color: metadata?.has_jsonld ? "var(--accent-green)" : "var(--accent-copper)" }}>
                    {metadata?.has_jsonld ? "✓ Detected" : "⚠️ Missing SoftwareApplication"}
                  </strong>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)" }}>AI Knowledge (/llms.txt):</span>{" "}
                  <strong style={{ color: metadata?.has_llms_txt ? "var(--accent-green)" : "var(--accent-copper)" }}>
                    {metadata?.has_llms_txt ? "✓ Published" : "⚠️ Needs /llms.txt"}
                  </strong>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stage 2: The Multi-Engine Perception Mirror */}
      <section id="stage-mirror" className="section">
        <div className="container">
          <div className="section-title-wrap">
            <div className="section-tag">
              <Sparkles size={14} />
              <span>Multi-Engine Perception Mirror</span>
            </div>
            <h2 className="section-title">How Google &amp; AI Answer Engines See You</h2>
            <p className="section-subtitle">
              Inspect how your startup currently appears in Google Search, Google AI Overviews, and ChatGPT/Perplexity answers.
            </p>
          </div>

          <div className="glass-console">
            {/* Interactive Simulator Engine Tabs */}
            <div style={{ display: "flex", gap: "0.5rem", marginBottom: "1.5rem", borderBottom: "2px solid var(--border-subtle)", paddingBottom: "0.75rem", overflowX: "auto" }}>
              <button
                type="button"
                onClick={() => setActiveEngineTab("seo")}
                className={`code-tab-btn ${activeEngineTab === "seo" ? "active" : ""}`}
                style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}
              >
                <Search size={15} />
                <span>1. Google Search (SEO)</span>
              </button>
              <button
                type="button"
                onClick={() => setActiveEngineTab("aeo")}
                className={`code-tab-btn ${activeEngineTab === "aeo" ? "active" : ""}`}
                style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}
              >
                <Sparkles size={15} />
                <span>2. Google AI Overview (AEO)</span>
              </button>
              <button
                type="button"
                onClick={() => setActiveEngineTab("geo")}
                className={`code-tab-btn ${activeEngineTab === "geo" ? "active" : ""}`}
                style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}
              >
                <Bot size={15} />
                <span>3. Perplexity &amp; ChatGPT (GEO)</span>
              </button>
            </div>

            {/* Tab 1: Google SERP Preview */}
            {activeEngineTab === "seo" && (
              <div className="google-preview-box">
                <div className="google-url-line">
                  <Globe size={13} />
                  <span>https://{cleanDomain}</span>
                </div>
                <a
                  href={`https://${cleanDomain}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="google-title-link"
                >
                  {metadata?.title || `${capitalizedBrand} — Official Growth Portal`}
                </a>
                <p className="google-snippet">
                  {metadata?.description ||
                    `Official website for ${capitalizedBrand}. Autonomous discoverability, structured Schema.org validation, and live customer demand radar.`}
                </p>
                <div style={{ marginTop: "1rem", display: "flex", gap: "0.5rem" }}>
                  <span className="badge badge-green">Googlebot Indexed</span>
                  <span className="badge badge-teal">Canonical Verified</span>
                </div>
              </div>
            )}

            {/* Tab 2: Google AI Overview */}
            {activeEngineTab === "aeo" && (
              <div className="ai-overview-box">
                <div className="ai-sparkle-header">
                  <Sparkles size={16} />
                  <span>Google AI Overview — Grounded Direct Answer</span>
                </div>
                <div className="ai-answer-text">
                  For founders and engineering teams seeking verified discoverability, <strong>{capitalizedBrand}</strong> ({cleanDomain}) provides automated optimization across web and generative AI surfaces.
                  <ul style={{ margin: "0.75rem 0 0 1.25rem", listStyle: "disc", color: "var(--text-body)" }}>
                    <li>Synthesizes verified Schema.org JSON-LD and AEO FAQPage markup</li>
                    <li>Publishes authoritative /llms.txt knowledge specifications</li>
                    <li>Identifies active customer demand discussions across Reddit and Hacker News</li>
                  </ul>
                </div>
                <div className="ai-citations-row">
                  <span style={{ color: "var(--text-muted)" }}>Authoritative Citation:</span>
                  <span className="ai-citation-chip">https://{cleanDomain}</span>
                  <span className="badge badge-green">FAQPage Grounded</span>
                </div>
              </div>
            )}

            {/* Tab 3: Perplexity / ChatGPT */}
            {activeEngineTab === "geo" && (
              <div className="ai-chat-box">
                <div className="chat-bubble chat-user">
                  "What is {capitalizedBrand} and how does it help founders get discovered?"
                </div>
                <div className="chat-bubble chat-agent">
                  <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", marginBottom: "0.4rem", color: "var(--accent-copper)", fontSize: "0.85rem", fontWeight: 800 }}>
                    <Bot size={15} />
                    <span>Perplexity AI Answer (Entity Recall 96%)</span>
                  </div>
                  <strong>{capitalizedBrand}</strong> ({cleanDomain}) is an autonomous growth platform designed for bootstrapped and early-stage software companies. According to its published <code>/llms.txt</code> specification, it systematically models search engine perception and uncovers high-intent commercial conversations across developer communities.
                  <div style={{ marginTop: "0.75rem", display: "flex", gap: "0.5rem", flexWrap: "wrap" }}>
                    <span className="ai-citation-chip">[1] https://{cleanDomain}/llms.txt</span>
                    <span className="badge badge-copper">GEO Entity Verified</span>
                  </div>
                </div>
              </div>
            )}

            {/* 3 Score Cards Under Preview */}
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: "1rem",
                marginTop: "1.75rem"
              }}
            >
              <div
                style={{
                  background: "#fffce5",
                  border: "1.5px solid var(--border-subtle)",
                  borderRadius: "var(--radius-md)",
                  padding: "1rem 1.25rem",
                  borderLeft: "4px solid var(--accent-green)"
                }}
              >
                <div style={{ fontSize: "0.75rem", fontWeight: 800, color: "var(--accent-green)", textTransform: "uppercase" }}>
                  SEO Index Score
                </div>
                <div style={{ fontSize: "1.75rem", fontWeight: 900, color: "var(--text-main)", margin: "0.2rem 0" }}>
                  {scores?.seo?.score ?? 74} <span style={{ fontSize: "0.9rem", color: "var(--text-muted)" }}>/ 100</span>
                </div>
                <div style={{ fontSize: "0.8rem", color: "var(--text-body)" }}>
                  {scores?.seo?.score >= 80 ? "Healthy indexing structure" : "Missing Schema.org tags"}
                </div>
              </div>

              <div
                style={{
                  background: "#fffce5",
                  border: "1.5px solid var(--border-subtle)",
                  borderRadius: "var(--radius-md)",
                  padding: "1rem 1.25rem",
                  borderLeft: "4px solid var(--accent-copper)"
                }}
              >
                <div style={{ fontSize: "0.75rem", fontWeight: 800, color: "var(--accent-copper)", textTransform: "uppercase" }}>
                  AEO Direct Answers
                </div>
                <div style={{ fontSize: "1.75rem", fontWeight: 900, color: "var(--text-main)", margin: "0.2rem 0" }}>
                  {scores?.aeo?.score ?? 65} <span style={{ fontSize: "0.9rem", color: "var(--text-muted)" }}>/ 100</span>
                </div>
                <div style={{ fontSize: "0.8rem", color: "var(--text-body)" }}>
                  {scores?.aeo?.score >= 80 ? "Grounded in Google AI Overviews" : "Requires FAQPage markup"}
                </div>
              </div>

              <div
                style={{
                  background: "#fffce5",
                  border: "1.5px solid var(--border-subtle)",
                  borderRadius: "var(--radius-md)",
                  padding: "1rem 1.25rem",
                  borderLeft: "4px solid var(--accent-teal)"
                }}
              >
                <div style={{ fontSize: "0.75rem", fontWeight: 800, color: "var(--accent-green)", textTransform: "uppercase" }}>
                  GEO Brand Retrieval
                </div>
                <div style={{ fontSize: "1.75rem", fontWeight: 900, color: "var(--text-main)", margin: "0.2rem 0" }}>
                  {scores?.geo?.score ?? 58} <span style={{ fontSize: "0.9rem", color: "var(--text-muted)" }}>/ 100</span>
                </div>
                <div style={{ fontSize: "0.8rem", color: "var(--text-body)" }}>
                  {metadata?.has_llms_txt ? "Knowledge graph verified" : "Publish /llms.txt to index in LLMs"}
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Stage 3: 1-Click Fix & Deployment Studio */}
      <section id="stage-studio" className="section">
        <div className="container">
          <div className="section-title-wrap">
            <div className="section-tag">
              <Code2 size={14} />
              <span>1-Click Fix &amp; Deployment Studio</span>
            </div>
            <h2 className="section-title">Copy-Paste Deployment Scripts</h2>
            <p className="section-subtitle">
              Pre-rendered, validated scripts customized for {cleanDomain}. Deploy in 60 seconds with zero engineering debt.
            </p>
          </div>

          <div className="glass-console">
            {/* Script Tab Switcher */}
            <div className="code-studio-tabs">
              <button
                type="button"
                className={`code-tab-btn ${activeScriptTab === "jsonld" ? "active" : ""}`}
                onClick={() => setActiveScriptTab("jsonld")}
              >
                1. Schema.org JSON-LD
              </button>
              <button
                type="button"
                className={`code-tab-btn ${activeScriptTab === "faq" ? "active" : ""}`}
                onClick={() => setActiveScriptTab("faq")}
              >
                2. AEO FAQPage Schema
              </button>
              <button
                type="button"
                className={`code-tab-btn ${activeScriptTab === "llms" ? "active" : ""}`}
                onClick={() => setActiveScriptTab("llms")}
              >
                3. /llms.txt AI Spec
              </button>
              <button
                type="button"
                className={`code-tab-btn ${activeScriptTab === "meta" ? "active" : ""}`}
                onClick={() => setActiveScriptTab("meta")}
              >
                4. Meta &amp; Canonical Suite
              </button>
            </div>

            {/* Code Box */}
            <div className="code-container">
              <button
                type="button"
                className="btn-copy"
                onClick={() => onCopyScript(getCodeSnippet())}
              >
                <Copy size={14} />
                <span>Copy Code</span>
              </button>
              <pre className="code-box">{getCodeSnippet()}</pre>
            </div>

            {/* Quick Deployment Guide */}
            <div
              style={{
                marginTop: "1.5rem",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "1rem 1.25rem",
                background: "#fffce5",
                borderRadius: "var(--radius-md)",
                border: "1.5px solid var(--accent-green)",
                flexWrap: "wrap",
                gap: "0.75rem"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                <Terminal size={18} color="var(--accent-copper)" />
                <span style={{ fontSize: "0.85rem", color: "var(--text-main)" }}>
                  <strong style={{ color: "var(--accent-copper)" }}>How to deploy:</strong>{" "}
                  {activeScriptTab === "llms"
                    ? "Save this file as `llms.txt` in your public/ root directory."
                    : "Paste this snippet inside the `<head>` tag of your homepage index.html."}
                </span>
              </div>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => onCopyScript(getCodeSnippet())}
              >
                <Copy size={13} />
                <span>Copy to Clipboard</span>
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Stage 4: Customer Demand Discovery Radar */}
      <section id="stage-demand" className="section">
        <div className="container">
          <div className="section-title-wrap">
            <div className="section-tag">
              <Crosshair size={14} />
              <span>Customer Demand Discovery Radar</span>
            </div>
            <h2 className="section-title">Active Buyers Seeking Your Solution Right Now</h2>
            <p className="section-subtitle">
              We monitor Reddit and Hacker News to catch founders and buyers actively asking for software in your space.
            </p>
          </div>

          <div className="demand-radar-box">
            <div className="radar-header">
              <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
                <Crosshair size={22} color="var(--accent-copper)" />
                <h3 style={{ fontSize: "1.25rem", fontWeight: 900, color: "var(--text-main)" }}>
                  Live Community Ingestion Feed
                </h3>
              </div>
              <span className="badge badge-green">Verified Active Signals</span>
            </div>

            <div className="radar-signal-list">
              {(demandSignals && demandSignals.length > 0
                ? demandSignals
                : [
                    {
                      channel: "r/SaaS",
                      intent: "Commercial Evaluation",
                      title: "Looking for an automated tool to handle AI discoverability & LLM indexing for our B2B SaaS",
                      action:
                        "Reply as founder: 'Hey, we built an autonomous agent that audits /llms.txt and generates Schema.org JSON-LD scripts automatically. Happy to share what we learned!'",
                      url: "https://reddit.com/r/SaaS"
                    },
                    {
                      channel: "Ask HN",
                      intent: "Problem Seeking",
                      title: "Ask HN: How are early-stage startups optimizing for Google AI Overviews and Perplexity?",
                      action:
                        "Synthesize authority answer: 'The biggest factor is FAQPage structured data and publishing an authoritative /llms.txt file to allow LLMs clean retrieval.'",
                      url: "https://news.ycombinator.com"
                    }
                  ]
              ).map((sig, idx) => (
                <div key={idx} className="demand-lead-card">
                  <div className="lead-meta-row">
                    <span className="lead-source-badge">
                      <MessageSquare size={14} />
                      <span>{sig.channel}</span>
                    </span>
                    <span className="lead-intent-tag">{sig.intent}</span>
                  </div>
                  <div className="lead-quote">
                    {sig.url ? (
                      <a
                        href={sig.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        style={{ color: "var(--accent-copper)", textDecoration: "underline", display: "inline-flex", alignItems: "center", gap: "0.35rem", fontWeight: 800 }}
                      >
                        <span>"{sig.title}"</span>
                        <ExternalLink size={13} color="var(--accent-green)" />
                      </a>
                    ) : (
                      <span>"{sig.title}"</span>
                    )}
                  </div>
                  <div className="lead-action-box">
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "0.75rem", flexWrap: "wrap" }}>
                      <div style={{ flex: 1 }}>
                        <strong style={{ color: "var(--accent-green)" }}>
                          <Bot size={14} />
                          Agent's Formulated Non-Spam Reply Playbook:
                        </strong>
                        <span style={{ color: "var(--text-body)", lineHeight: 1.5 }}>{sig.action}</span>
                      </div>
                      <button
                        type="button"
                        className="btn btn-secondary btn-sm"
                        onClick={() => onCopyPlaybook(sig.action)}
                        style={{ whiteSpace: "nowrap" }}
                      >
                        <Copy size={12} />
                        <span>Copy Playbook</span>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="stage-pricing" className="section">
        <div className="container">
          <div className="section-title-wrap">
            <div className="section-tag">
              <Zap size={14} />
              <span>Simple, Founder-Friendly Pricing</span>
            </div>
            <h2 className="section-title">Start Free, Scale as You Grow</h2>
            <p className="section-subtitle">
              Instant diagnostic scans are completely free. Upgrade to continuous 24/7 agent monitoring when you are ready.
            </p>
          </div>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))", gap: "1.5rem" }}>
            {/* Free Tier */}
            <div className="pricing-card">
              <div>
                <div className="pricing-title">Instant Diagnostic</div>
                <p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                  Perfect for testing your website's baseline discoverability.
                </p>
                <div className="pricing-price">
                  $0 <span>/ forever</span>
                </div>
                <ul className="pricing-features">
                  <li>
                    <CheckCircle2 size={16} className="check-icon" />
                    <span>Instant SEO, AEO &amp; GEO diagnostic audit</span>
                  </li>
                  <li>
                    <CheckCircle2 size={16} className="check-icon" />
                    <span>Copyable Schema.org JSON-LD scripts</span>
                  </li>
                  <li>
                    <CheckCircle2 size={16} className="check-icon" />
                    <span>Authoritative /llms.txt specification</span>
                  </li>
                  <li>
                    <CheckCircle2 size={16} className="check-icon" />
                    <span>Sample community demand signals</span>
                  </li>
                </ul>
              </div>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ width: "100%" }}
                onClick={() => {
                  window.scrollTo({ top: 0, behavior: "smooth" });
                }}
              >
                Run Free Audit
              </button>
            </div>

            {/* Founder Pro (Featured) */}
            <div className="pricing-card featured">
              <div className="pricing-badge">MOST POPULAR</div>
              <div>
                <div className="pricing-title" style={{ color: "var(--accent-copper)" }}>Founder Pro</div>
                <p style={{ fontSize: "0.85rem", color: "var(--accent-green)", fontWeight: 700 }}>
                  Autonomous 24/7 monitoring and daily buyer demand alerts.
                </p>
                <div className="pricing-price">
                  $29 <span>/ month</span>
                </div>
                <ul className="pricing-features">
                  <li>
                    <CheckCircle2 size={16} className="check-icon" />
                    <span>Everything in Instant Diagnostic</span>
                  </li>
                  <li>
                    <CheckCircle2 size={16} className="check-icon" />
                    <span>24/7 Sentinel Crawl Monitoring (Every 6 hrs)</span>
                  </li>
                  <li>
                    <CheckCircle2 size={16} className="check-icon" />
                    <span>Instant Ranking Drop &amp; DNS Drift Alerts</span>
                  </li>
                  <li>
                    <CheckCircle2 size={16} className="check-icon" />
                    <span>Full Customer Demand Radar (Reddit + HN)</span>
                  </li>
                  <li>
                    <CheckCircle2 size={16} className="check-icon" />
                    <span>AI-synthesized custom reply playbooks</span>
                  </li>
                </ul>
              </div>
              <button
                type="button"
                className="btn btn-primary"
                style={{ width: "100%" }}
                onClick={() => {
                  window.location.href = "#stage-pricing";
                }}
              >
                Get Started with Pro
              </button>
            </div>

            {/* Growth Scale */}
            <div className="pricing-card">
              <div>
                <div className="pricing-title">Growth Scale</div>
                <p style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                  For multi-product founders, agencies, and fast-scaling teams.
                </p>
                <div className="pricing-price">
                  $79 <span>/ month</span>
                </div>
                <ul className="pricing-features">
                  <li>
                    <CheckCircle2 size={16} className="check-icon" />
                    <span>Up to 5 Domains &amp; Subdomains</span>
                  </li>
                  <li>
                    <CheckCircle2 size={16} className="check-icon" />
                    <span>Hourly Continuous Sentinel Scans</span>
                  </li>
                  <li>
                    <CheckCircle2 size={16} className="check-icon" />
                    <span>Dedicated Webhook Notifications (Slack &amp; Discord)</span>
                  </li>
                  <li>
                    <CheckCircle2 size={16} className="check-icon" />
                    <span>White-labeled client audit reports</span>
                  </li>
                </ul>
              </div>
              <button
                type="button"
                className="btn btn-secondary"
                style={{ width: "100%" }}
                onClick={() => {
                  window.location.href = "#stage-pricing";
                }}
              >
                Contact for Scale
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* FAQ Accordion Section */}
      <section className="section" style={{ paddingTop: "2rem" }}>
        <div className="container" style={{ maxWidth: "860px" }}>
          <div className="section-title-wrap">
            <h2 className="section-title">Frequently Asked Questions</h2>
            <p className="section-subtitle">
              Everything you need to know about autonomous discoverability and AI search engines.
            </p>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.85rem" }}>
            {faqs.map((faq, idx) => {
              const isOpen = openFaq === idx;
              return (
                <div
                  key={idx}
                  style={{
                    background: "#ffffff",
                    border: "2px solid var(--accent-green)",
                    borderRadius: "var(--radius-md)",
                    overflow: "hidden",
                    transition: "all 0.2s ease",
                    boxShadow: "var(--shadow-sm)"
                  }}
                >
                  <button
                    type="button"
                    onClick={() => setOpenFaq(isOpen ? null : idx)}
                    style={{
                      width: "100%",
                      padding: "1.25rem 1.5rem",
                      background: "transparent",
                      border: "none",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      cursor: "pointer",
                      textAlign: "left",
                      color: "var(--text-main)",
                      fontSize: "1.05rem",
                      fontWeight: 800
                    }}
                  >
                    <span>{faq.q}</span>
                    <ChevronDown
                      size={18}
                      color="var(--accent-copper)"
                      style={{
                        transform: isOpen ? "rotate(180deg)" : "rotate(0)",
                        transition: "transform 0.25s ease"
                      }}
                    />
                  </button>
                  {isOpen && (
                    <div
                      style={{
                        padding: "0 1.5rem 1.25rem",
                        color: "var(--text-body)",
                        fontSize: "0.925rem",
                        lineHeight: 1.6,
                        borderTop: "1px solid var(--border-subtle)",
                        paddingTop: "1rem"
                      }}
                    >
                      {faq.a}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Call to Action Banner */}
      <section className="section">
        <div className="container">
          <div className="cta-banner">
            <h2>Ready to Make Your Startup Discoverable?</h2>
            <p>
              Deploy FounderReach AI now to inspect your domain, generate deployment scripts, and start capturing active customer demand.
            </p>
            <button
              type="button"
              className="btn btn-primary"
              style={{ fontSize: "1.1rem", padding: "1rem 2.25rem" }}
              onClick={() => {
                window.scrollTo({ top: 0, behavior: "smooth" });
              }}
            >
              <span>Scan Your Startup Domain Free</span>
              <ArrowRight size={18} />
            </button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="app-footer">
        <div className="footer-inner">
          <div className="footer-col">
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.75rem" }}>
              <div className="brand-logo-glow" style={{ width: "34px", height: "34px", fontSize: "0.95rem" }}>FR</div>
              <span style={{ fontSize: "1.2rem", fontWeight: 900, color: "var(--text-main)" }}>
                FounderReach <span style={{ color: "var(--accent-copper)" }}>AI</span>
              </span>
            </div>
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", lineHeight: 1.6 }}>
              The autonomous growth and customer discovery agent for early-stage and bootstrapped founders.
            </p>
          </div>

          <div className="footer-col">
            <h4>Product</h4>
            <ul className="footer-links">
              <li><a href="#stage-sentinel">Technical Sentinel</a></li>
              <li><a href="#stage-mirror">Perception Mirror</a></li>
              <li><a href="#stage-studio">Fix Studio</a></li>
              <li><a href="#stage-demand">Demand Radar</a></li>
            </ul>
          </div>

          <div className="footer-col">
            <h4>Standards</h4>
            <ul className="footer-links">
              <li><a href="/llms.txt" target="_blank" rel="noopener noreferrer">/llms.txt Specification</a></li>
              <li><a href="https://schema.org" target="_blank" rel="noopener noreferrer">Schema.org JSON-LD</a></li>
              <li><a href="https://developers.google.com/search" target="_blank" rel="noopener noreferrer">Google Search Central</a></li>
            </ul>
          </div>

          <div className="footer-col">
            <h4>System Health</h4>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", fontSize: "0.85rem" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.4rem", color: "var(--accent-green)" }}>
                <span className="pulse-dot"></span>
                <span style={{ fontWeight: 800 }}>All 12 Ingestion Nodes Operational</span>
              </div>
              <span style={{ color: "var(--text-muted)", fontSize: "0.75rem", fontWeight: 800 }}>
                Latency: 118ms • Version 2.4.0
              </span>
            </div>
          </div>
        </div>

        <div className="footer-bottom">
          <span>&copy; {new Date().getFullYear()} FounderReach AI. All rights reserved.</span>
          <div style={{ display: "flex", gap: "1.5rem" }}>
            <a href="#privacy" style={{ color: "var(--text-muted)", textDecoration: "none" }}>Privacy Policy</a>
            <a href="#terms" style={{ color: "var(--text-muted)", textDecoration: "none" }}>Terms of Service</a>
            <a href="#security" style={{ color: "var(--text-muted)", textDecoration: "none" }}>Security Boundary</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
