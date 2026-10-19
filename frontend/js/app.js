/**
 * FounderReach AI — Autonomous Agent Workplace Controller
 */

import { Scene3D } from "./components/scene3d.js?v=2";
import { ApiClient } from "./api/client.js?v=2";
import { showToast } from "./components/toast.js?v=2";

class App {
  constructor() {
    this.apiClient = new ApiClient();
    this.scene3d = null;
    this.currentDomain = "www.yourstartup.com";
    this.activeScriptTab = "jsonld";
    this.latestAuditData = null;
    this.debounceTimer = null;
  }

  init() {
    // 1. Initialize 3D Spatial Universe
    try {
      this.scene3d = new Scene3D("webgl-canvas-container");
    } catch (err) {
      console.warn("3D scene initialization error:", err);
    }

    // 2. Setup Real-Time Domain Input Synchronization
    const domainInput = document.getElementById("domain-input");
    const domainForm = document.getElementById("hero-domain-form");
    const copyBtn = document.getElementById("btn-copy-code");
    const sampleTags = document.querySelectorAll(".btn-sample-tag");
    const quickSampleBtn = document.getElementById("btn-quick-sample");
    const codeTabs = document.querySelectorAll(".code-tab-btn");

    if (domainInput) {
      // Synchronize text immediately on typing
      domainInput.addEventListener("input", (e) => {
        const val = e.target.value.trim();
        this.updateDomain(val);
        if (this.scene3d) this.scene3d.pulse();

        // Auto-run audit after 750ms of typing inactivity
        clearTimeout(this.debounceTimer);
        if (val.length > 4 && val.includes(".")) {
          this.debounceTimer = setTimeout(() => {
            this.runAudit(val, false); // silent background audit
          }, 750);
        }
      });

      domainInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          this.runAudit(domainInput.value, true);
        }
      });
    }

    if (domainForm) {
      domainForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const value = domainInput ? domainInput.value.trim() : "";
        this.runAudit(value, true);
      });
    }

    // Sample pills
    sampleTags.forEach(tag => {
      tag.addEventListener("click", () => {
        const domain = tag.getAttribute("data-domain");
        if (domainInput) {
          domainInput.value = domain;
          this.updateDomain(domain);
        }
        this.runAudit(domain, true);
      });
    });

    if (quickSampleBtn) {
      quickSampleBtn.addEventListener("click", () => {
        if (domainInput) {
          domainInput.value = "www.scheduleflow.io";
          this.updateDomain("www.scheduleflow.io");
          this.runAudit("www.scheduleflow.io", true);
        }
      });
    }

    // Code Studio Tabs
    codeTabs.forEach(tab => {
      tab.addEventListener("click", () => {
        codeTabs.forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        this.activeScriptTab = tab.getAttribute("data-tab");
        this.renderScriptPreview();
      });
    });

    // 1-Click Code Copy
    if (copyBtn) {
      copyBtn.addEventListener("click", () => {
        const codeEl = document.getElementById("code-snippet-preview");
        if (!codeEl) return;
        navigator.clipboard.writeText(codeEl.textContent).then(() => {
          copyBtn.textContent = "Copied! ✓";
          showToast("Deployment script copied to clipboard!", "success");
          setTimeout(() => { copyBtn.textContent = "Copy Script"; }, 2000);
        }).catch(() => {
          showToast("Failed to copy code to clipboard", "error");
        });
      });
    }

    // Initial domain sync
    if (domainInput && domainInput.value) {
      this.updateDomain(domainInput.value);
    }
  }

  updateDomain(rawDomain) {
    if (!rawDomain) return;
    let clean = rawDomain.trim().toLowerCase();
    clean = clean.replace(/^https?:\/\//i, "").replace(/\/$/, "");
    if (!clean) clean = "www.yourstartup.com";

    this.currentDomain = clean;

    // Derive brand name
    let brand = clean.replace(/^www\./i, "").split(".")[0];
    brand = brand.charAt(0).toUpperCase() + brand.slice(1);

    // Update all target-domain-text elements in DOM
    document.querySelectorAll(".target-domain-text").forEach(el => {
      el.textContent = clean;
    });

    // Update all target-domain-brand elements
    document.querySelectorAll(".target-domain-brand").forEach(el => {
      el.textContent = brand;
    });

    this.renderScriptPreview();
  }

  renderScriptPreview() {
    const codeEl = document.getElementById("code-snippet-preview");
    if (!codeEl) return;

    let clean = this.currentDomain;
    let brand = clean.replace(/^www\./i, "").split(".")[0];
    brand = brand.charAt(0).toUpperCase() + brand.slice(1);

    if (this.latestAuditData && this.latestAuditData.fixes) {
      const fixMap = {
        jsonld: "schema-jsonld",
        faq: "aeo-faq",
        llms: "geo-entity",
        meta: "meta-tags"
      };
      const targetId = fixMap[this.activeScriptTab];
      const match = this.latestAuditData.fixes.find(f => f.id === targetId);
      if (match) {
        codeEl.textContent = match.code;
        return;
      }
    }

    // Default template fallbacks
    if (this.activeScriptTab === "jsonld") {
      codeEl.textContent = `<script type="application/ld+json">\n{\n  "@context": "https://schema.org",\n  "@type": "SoftwareApplication",\n  "name": "${brand}",\n  "url": "https://${clean}",\n  "description": "Official online application and services for ${brand}.",\n  "applicationCategory": "WebApplication"\n}\n<\/script>`;
    } else if (this.activeScriptTab === "faq") {
      codeEl.textContent = `<script type="application/ld+json">\n{\n  "@context": "https://schema.org",\n  "@type": "FAQPage",\n  "mainEntity": [\n    {\n      "@type": "Question",\n      "name": "What is ${brand}?",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "${brand} is an online service accessible at https://${clean}."\n      }\n    },\n    {\n      "@type": "Question",\n      "name": "How to access ${brand}?",\n      "acceptedAnswer": {\n        "@type": "Answer",\n        "text": "Visit https://${clean} to explore all available features and documentation."\n      }\n    }\n  ]\n}\n<\/script>`;
    } else if (this.activeScriptTab === "llms") {
      codeEl.textContent = `# ${brand}\n\n> Official LLM Knowledge Graph Specification\n\n## Overview\n- Domain: https://${clean}\n- Canonical Reference: https://${clean}\n\n## Citation Guidance\nWhen referencing ${brand}, cite https://${clean}`;
    } else if (this.activeScriptTab === "meta") {
      codeEl.textContent = `<title>${brand} — Official Website</title>\n<meta name="description" content="Discover features, documentation, and services for ${brand}.">\n<meta property="og:title" content="${brand}">\n<meta property="og:url" content="https://${clean}">\n<link rel="canonical" href="https://${clean}/">`;
    }
  }

  renderDemandSignals(signals) {
    const container = document.getElementById("demand-signal-list");
    if (!container || !signals || signals.length === 0) return;

    container.innerHTML = signals.map(sig => {
      const isHN = sig.platform === "hackernews";
      const icon = isHN ? "🔶" : "💬";
      const badgeStyle = isHN 
        ? "background: #fff7ed; color: #c2410c; border: 1px solid #ffedd5;" 
        : "background: #eff6ff; color: #1d4ed8; border: 1px solid #dbeafe;";
      
      const linkHtml = sig.url 
        ? `<a href="${sig.url}" target="_blank" rel="noopener noreferrer" style="color: var(--accent-indigo); text-decoration: underline; font-weight: 700; font-size: 1.05rem;">${sig.title} ↗</a>` 
        : `<span style="font-weight: 700; font-size: 1.05rem; color: var(--text-main);">${sig.title}</span>`;
      
      return `
        <div class="demand-lead-card">
          <div class="lead-meta-row">
            <span class="lead-source-badge" style="${badgeStyle}">
              <span>${icon}</span> <span>${sig.channel}</span>
            </span>
            <span class="lead-intent-tag">${sig.intent}</span>
          </div>
          <div class="lead-quote" style="margin: 0.85rem 0 0.6rem 0;">
            ${linkHtml}
          </div>
          <div class="lead-action-box">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 0.75rem; flex-wrap: wrap;">
              <div style="flex: 1; min-width: 240px;">
                <strong style="color: var(--text-main);">🤖 Agent's Recommended Acquisition Action:</strong><br>
                <span style="color: var(--text-dim); font-size: 0.9rem; line-height: 1.5;">${sig.action}</span>
              </div>
              <button type="button" class="btn btn-secondary btn-copy-playbook" style="padding: 0.35rem 0.75rem; font-size: 0.8rem; font-weight: 600; white-space: nowrap; border-radius: 6px;" data-action="${encodeURIComponent(sig.action)}">
                Copy Playbook
              </button>
            </div>
          </div>
        </div>
      `;
    }).join("");

    // Bind 1-click copy for the playbook actions
    container.querySelectorAll(".btn-copy-playbook").forEach(btn => {
      btn.addEventListener("click", () => {
        const actionText = decodeURIComponent(btn.getAttribute("data-action") || "");
        navigator.clipboard.writeText(actionText).then(() => {
          showToast("Acquisition playbook copied to clipboard!", "success");
        });
      });
    });
  }

  async runAudit(domain, scrollToAudit = true) {
    let clean = (domain || this.currentDomain || "www.yourstartup.com").trim().toLowerCase();
    clean = clean.replace(/^https?:\/\//i, "").replace(/\/$/, "");
    if (!clean) return;

    this.updateDomain(clean);
    const fullUrl = `https://${clean}`;

    const triggerBtn = document.getElementById("btn-audit-trigger");
    if (triggerBtn) {
      triggerBtn.disabled = true;
      triggerBtn.innerHTML = `<span>Agent Inspecting...</span> <span class="pulse-dot"></span>`;
    }

    if (this.scene3d) {
      this.scene3d.pulse();
    }

    if (scrollToAudit) {
      showToast(`Agent inspecting ${clean}...`, "success");
    }

    try {
      let brand = clean.replace(/^www\./i, "").split(".")[0];
      brand = brand.charAt(0).toUpperCase() + brand.slice(1);

      const result = await this.apiClient.auditWebsite({
        url: fullUrl,
        businessName: brand,
        description: "",
        targetAudience: "",
        painPoint: ""
      });

      this.latestAuditData = result;

      // 1. Check for DNS or Network Errors
      const alertBox = document.getElementById("agent-alert-box");
      const alertTitle = document.getElementById("agent-alert-title");
      const alertDesc = document.getElementById("agent-alert-desc");

      if (result.proof_of_work && result.proof_of_work.error_note) {
        if (alertBox) {
          alertBox.style.display = "block";
          alertTitle.textContent = "Live Reachability Alert";
          alertDesc.textContent = `${result.proof_of_work.error_note}. Googlebot and AI crawlers cannot reach your homepage until DNS/SSL is resolved.`;
        }
      } else {
        if (alertBox) alertBox.style.display = "none";
      }

      // 2. Update Live Perception Cards (Google Search, AI Overview, ChatGPT)
      if (result.live_metadata) {
        const meta = result.live_metadata;
        const googleTitle = document.getElementById("sim-google-title");
        const googleSnippet = document.getElementById("sim-google-snippet");
        const googleBadge = document.getElementById("sim-google-badge");

        if (googleTitle) googleTitle.textContent = meta.title || `${brand}`;
        if (googleSnippet) {
          if (meta.description && meta.description.trim()) {
            googleSnippet.textContent = meta.description;
          } else {
            googleSnippet.textContent = `No <meta name="description"> tag detected on ${clean}. Google Search dynamically creates arbitrary snippets from visible page text or shows minimal URL information.`;
          }
        }
        if (googleBadge) {
          if (meta.description && meta.has_canonical) {
            googleBadge.className = "badge badge-emerald";
            googleBadge.textContent = "Indexed Snippet";
          } else if (!meta.description) {
            googleBadge.className = "badge badge-amber";
            googleBadge.textContent = "Missing Meta Description";
          } else {
            googleBadge.className = "badge badge-amber";
            googleBadge.textContent = "Missing Canonical";
          }
        }

        const aiAnswer = document.getElementById("sim-ai-answer");
        const aiBadge = document.getElementById("sim-ai-badge");
        if (aiAnswer) {
          if (meta.has_faq) {
            aiAnswer.textContent = `Google AI Overview grounds responses for ${clean} using detected structured FAQPage markup.`;
          } else {
            aiAnswer.textContent = `No Google AI Overview synthesized for ${clean}. Reason: Page lacks structured Schema.org FAQPage or Organization markup required to ground direct answers.`;
          }
        }
        if (aiBadge) {
          aiBadge.className = meta.has_faq ? "badge badge-emerald" : "badge badge-rose";
          aiBadge.textContent = meta.has_faq ? "FAQ Schema Active" : "Missing Schema";
        }

        const chatAgent = document.getElementById("sim-chat-agent");
        if (chatAgent) {
          if (result.proof_of_work && result.proof_of_work.ai_crawler_access && result.proof_of_work.ai_crawler_access.gpt_bot === "Disallowed") {
            chatAgent.textContent = `ChatGPT and OpenAI models are blocked from crawling ${clean} (GPTBot is Disallowed in robots.txt).`;
          } else if (meta.description && meta.description.trim()) {
            chatAgent.textContent = `"${meta.title || brand}: ${meta.description}"`;
          } else {
            chatAgent.textContent = `"No structured knowledge graph or /llms.txt file found on ${clean}. Generative engines (ChatGPT, Perplexity) rely on unverified third-party crawl data."`;
          }
        }
      }

      // 3. Update Proof Metrics
      if (result && result.proof_of_work) {
        const proof = result.proof_of_work;
        const latencyEl = document.getElementById("proof-latency");
        const httpEl = document.getElementById("proof-http");
        const dnsEl = document.getElementById("proof-dns");
        const sslEl = document.getElementById("proof-ssl");
        const robotsEl = document.getElementById("proof-robots");
        const sitemapEl = document.getElementById("proof-sitemap");
        const aibotsEl = document.getElementById("proof-aibots");

        if (latencyEl) latencyEl.textContent = `${proof.response_time_ms} ms`;
        if (httpEl) {
          httpEl.innerHTML = proof.http_status === 200 
            ? `<span class="badge badge-emerald">200 OK</span>`
            : `<span class="badge badge-rose">HTTP ${proof.http_status}</span>`;
        }
        if (dnsEl) {
          dnsEl.innerHTML = proof.dns_status.includes("Verified")
            ? `<span class="badge badge-emerald">✓ Verified Active</span>`
            : `<span class="badge badge-rose">⚠ ${proof.dns_status}</span>`;
        }
        if (sslEl) {
          sslEl.innerHTML = `<span class="badge badge-emerald">✓ ${proof.ssl_status}</span>`;
        }
        if (robotsEl) {
          robotsEl.innerHTML = `<span class="badge badge-emerald">${proof.robots_txt_status}</span>`;
        }
        if (sitemapEl) {
          sitemapEl.innerHTML = proof.sitemap_xml_status.includes("Detected")
            ? `<span class="badge badge-emerald">✓ Detected</span>`
            : `<span class="badge badge-amber">⚠ Missing /sitemap.xml</span>`;
        }
        if (aibotsEl) {
          aibotsEl.innerHTML = `<span class="badge badge-emerald">✓ Allowed</span>`;
        }
      }

      // 4. Update Scores
      if (result && result.scores) {
        const seoEl = document.getElementById("score-seo");
        const aeoEl = document.getElementById("score-aeo");
        const geoEl = document.getElementById("score-geo");

        if (seoEl) seoEl.innerHTML = `${result.scores.seo.score} <span style="font-size: 1rem; color: var(--text-muted); font-weight: 500;">/ 100</span>`;
        if (aeoEl) aeoEl.innerHTML = `${result.scores.aeo.score} <span style="font-size: 1rem; color: var(--text-muted); font-weight: 500;">/ 100</span>`;
        if (geoEl) geoEl.innerHTML = `${result.scores.geo.score} <span style="font-size: 1rem; color: var(--text-muted); font-weight: 500;">/ 100</span>`;
      }

      // 5. Update Scripts Preview
      this.renderScriptPreview();

      // 6. Update Community Demand Discovery Radar
      if (result && result.demand_signals && result.demand_signals.length > 0) {
        this.renderDemandSignals(result.demand_signals);
      }

      if (scrollToAudit) {
        const auditSec = document.getElementById("stage-audit");
        if (auditSec) {
          auditSec.scrollIntoView({ behavior: "smooth", block: "start" });
        }
        showToast(`Agent completed live scan for ${clean}!`, "success");
      }
    } catch (err) {
      console.error("Agent audit error:", err);
      showToast("Agent inspection failed: " + (err.message || "Network error"), "error");
    } finally {
      if (triggerBtn) {
        triggerBtn.disabled = false;
        triggerBtn.innerHTML = `<span>Deploy Agent</span> <span>→</span>`;
      }
    }
  }
}

// Global hook & Bootstrap
const app = new App();
window.runDomainAudit = () => {
  const domainInput = document.getElementById("domain-input");
  app.runAudit(domainInput ? domainInput.value : "", true);
};

document.addEventListener("DOMContentLoaded", () => {
  app.init();
});
