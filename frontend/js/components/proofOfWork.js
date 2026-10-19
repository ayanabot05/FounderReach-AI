/**
 * Proof of Work & Diagnostic Evidence Component
 * 
 * Crucial for founder trust: Displays transparent, verifiable proof of what was inspected,
 * network response times, server headers, and indexing permissions.
 */

export class ProofOfWorkComponent {
  constructor() {
    this.element = null;
  }

  render(proof, business) {
    if (!proof) return document.createElement("div");

    const section = document.createElement("section");
    section.className = "card proof-section";
    section.id = "proof-of-work-section";

    const httpBadge = proof.http_status === 200 
      ? `<span class="badge badge-emerald">HTTP ${proof.http_status} OK</span>`
      : `<span class="badge badge-rose">HTTP ${proof.http_status}</span>`;

    const dnsBadge = proof.dns_status.includes("Verified")
      ? `<span class="badge badge-emerald">✓ ${proof.dns_status}</span>`
      : `<span class="badge badge-rose">⚠ ${proof.dns_status}</span>`;

    section.innerHTML = `
      <div class="proof-header">
        <div>
          <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.25rem;">
            <span class="badge badge-cyan">VERIFIED WORK PROOF</span>
            <span style="font-size: 0.8rem; color: var(--text-dim);">Evidence-Backed Inspection</span>
          </div>
          <h3 style="font-size: 1.15rem; font-weight: 700;">Diagnostic Audit Log for ${business.domain || business.url}</h3>
        </div>
        <div style="text-align: right;">
          <span style="font-size: 0.75rem; color: var(--text-dim); display: block;">Response Latency</span>
          <span style="font-family: var(--font-mono); font-size: 1rem; color: var(--accent-cyan); font-weight: 700;">${proof.response_time_ms} ms</span>
        </div>
      </div>

      <div class="proof-grid">
        <div class="proof-item">
          <div class="proof-item-label">Target URL</div>
          <div class="proof-item-value" style="font-size: 0.85rem; word-break: break-all;">
            <a href="${proof.inspected_url}" target="_blank" rel="noopener noreferrer" style="color: var(--accent-cyan); text-decoration: none;">
              ${proof.inspected_url} ↗
            </a>
          </div>
        </div>

        <div class="proof-item">
          <div class="proof-item-label">HTTP Server Status</div>
          <div class="proof-item-value">${httpBadge}</div>
        </div>

        <div class="proof-item">
          <div class="proof-item-label">DNS & Host Resolution</div>
          <div class="proof-item-value">${dnsBadge}</div>
        </div>

        <div class="proof-item">
          <div class="proof-item-label">SSL / Encryption</div>
          <div class="proof-item-value">
            <span class="badge badge-emerald">✓ ${proof.ssl_status}</span>
          </div>
        </div>

        <div class="proof-item">
          <div class="proof-item-label">Robots.txt Crawlability</div>
          <div class="proof-item-value">
            <span class="badge badge-emerald">${proof.robots_txt_status}</span>
          </div>
        </div>

        <div class="proof-item">
          <div class="proof-item-label">XML Sitemap</div>
          <div class="proof-item-value">
            <span class="badge ${proof.sitemap_xml_status.includes('Detected') ? 'badge-emerald' : 'badge-amber'}">
              ${proof.sitemap_xml_status}
            </span>
          </div>
        </div>
      </div>

      <div style="background: var(--bg-code); border: 1px solid var(--border-subtle); border-radius: var(--radius-sm); padding: 0.85rem 1rem;">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
          <span style="font-size: 0.8rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em;">AI Crawler Permissions Matrix</span>
          <span style="font-size: 0.75rem; color: var(--text-dim);">Live Verification</span>
        </div>
        <div style="display: flex; gap: 1.5rem; flex-wrap: wrap; font-size: 0.85rem;">
          <div><strong style="color: #cbd5e1;">GPTBot (ChatGPT):</strong> <span style="color: #34d399;">${proof.ai_crawler_access.gpt_bot}</span></div>
          <div><strong style="color: #cbd5e1;">PerplexityBot:</strong> <span style="color: #34d399;">${proof.ai_crawler_access.perplexity_bot}</span></div>
          <div><strong style="color: #cbd5e1;">Google-Extended (Gemini):</strong> <span style="color: #34d399;">${proof.ai_crawler_access.google_extended}</span></div>
        </div>
      </div>
    `;

    this.element = section;
    return section;
  }
}
