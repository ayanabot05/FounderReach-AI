/**
 * Real-time Audit Progress Tracker Component
 * 
 * Shows transparent live status of each stage in the autonomous audit.
 */

export class AuditProgressComponent {
  constructor() {
    this.element = null;
    this.steps = [
      { id: "dns", title: "DNS & Network Reachability", desc: "Checking apex/www resolution, SSL certificate, and HTTP status." },
      { id: "seo", title: "Search Engine Optimization (SEO)", desc: "Auditing meta titles, descriptions, canonical links, and sitemaps." },
      { id: "aeo", title: "Answer Engine Optimization (AEO)", desc: "Testing direct-answer readiness and FAQ structured data." },
      { id: "geo", title: "Generative Engine Optimization (GEO)", desc: "Analyzing entity representation for Perplexity, ChatGPT, and Gemini." },
      { id: "fixes", title: "Fix Generation & Demand Discovery", desc: "Crafting copy-paste code snippets and locating real customer demand." }
    ];
  }

  render() {
    const card = document.createElement("section");
    card.className = "card audit-progress-card";
    card.id = "audit-progress-section";
    card.style.display = "none";

    card.innerHTML = `
      <div style="display: flex; align-items: center; justify-content: space-between;">
        <div style="display: flex; align-items: center; gap: 0.75rem;">
          <span class="badge badge-cyan">AUTONOMOUS AUDIT IN PROGRESS</span>
          <span class="pulse-dot"></span>
        </div>
        <span id="scan-progress-percent" style="font-family: var(--font-mono); font-size: 0.85rem; color: var(--accent-cyan);">0%</span>
      </div>

      <div class="step-tracker" id="tracker-list">
        ${this.steps.map((step, idx) => `
          <div class="tracker-item" id="tracker-step-${idx}">
            <div class="tracker-icon">${idx + 1}</div>
            <div class="tracker-body">
              <div class="tracker-title">${step.title}</div>
              <div class="tracker-desc">${step.desc}</div>
            </div>
          </div>
        `).join("")}
      </div>
    `;

    this.element = card;
    return card;
  }

  show() {
    if (this.element) {
      this.element.style.display = "block";
      this.element.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }

  hide() {
    if (this.element) {
      this.element.style.display = "none";
    }
  }

  updateProgress(currentStepIndex) {
    if (!this.element) return;
    const percentEl = this.element.querySelector("#scan-progress-percent");
    const percent = Math.min(100, Math.round(((currentStepIndex + 1) / this.steps.length) * 100));
    if (percentEl) percentEl.textContent = `${percent}%`;

    this.steps.forEach((_, idx) => {
      const item = this.element.querySelector(`#tracker-step-${idx}`);
      if (!item) return;

      if (idx < currentStepIndex) {
        item.className = "tracker-item completed";
        item.querySelector(".tracker-icon").innerHTML = "✓";
      } else if (idx === currentStepIndex) {
        item.className = "tracker-item active";
        item.querySelector(".tracker-icon").innerHTML = `<span class="pulse-dot"></span>`;
      } else {
        item.className = "tracker-item";
        item.querySelector(".tracker-icon").textContent = idx + 1;
      }
    });
  }
}
