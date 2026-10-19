/**
 * Founder-Friendly Website Audit Form Component
 * 
 * Designed specifically for non-technical founders:
 * - Simple, plain-English questions
 * - Clear placeholder guidance
 * - Instant validation & single-click trigger
 */

export class AuditFormComponent {
  constructor({ onSubmit, onDemoClick }) {
    this.onSubmit = onSubmit;
    this.onDemoClick = onDemoClick;
    this.element = null;
  }

  render() {
    const card = document.createElement("section");
    card.className = "card";
    card.id = "audit-form-section";

    card.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 1.5rem;">
        <div>
          <h2 style="font-size: 1.35rem; font-weight: 700; margin-bottom: 0.35rem;">Audit Your Business in 60 Seconds</h2>
          <p class="form-hint">No technical setup or passwords required. We perform a read-only public scan and give you exact copy-paste fixes.</p>
        </div>
        <button type="button" id="btn-quick-demo" class="btn btn-secondary btn-sm" title="Load an example product profile">
          ⚡ Try Example Demo
        </button>
      </div>

      <form id="audit-form">
        <div class="grid-2">
          <div class="form-group">
            <label class="form-label" for="input-url">
              <span>Website URL</span>
              <span class="form-hint">Must be public HTTPS</span>
            </label>
            <input 
              type="url" 
              id="input-url" 
              class="input-text" 
              placeholder="https://yourstartup.com" 
              required
            >
          </div>

          <div class="form-group">
            <label class="form-label" for="input-name">
              <span>Business / Startup Name</span>
              <span class="form-hint">What you call your brand</span>
            </label>
            <input 
              type="text" 
              id="input-name" 
              class="input-text" 
              placeholder="e.g. FounderReach AI" 
              required
            >
          </div>
        </div>

        <div class="form-group">
          <label class="form-label" for="input-desc">
            <span>What does your product do in one sentence?</span>
            <span class="form-hint">Used for your search title, AI bio, and meta tags</span>
          </label>
          <input 
            type="text" 
            id="input-desc" 
            class="input-text" 
            placeholder="e.g. Autonomous growth agent that audits websites, identifies SEO/AEO fixes, and finds customer demand." 
            required
          >
        </div>

        <div class="grid-2">
          <div class="form-group">
            <label class="form-label" for="input-audience">
              <span>Who is your target customer?</span>
              <span class="form-hint">Who writes the check?</span>
            </label>
            <input 
              type="text" 
              id="input-audience" 
              class="input-text" 
              placeholder="e.g. Non-technical founders, indie hackers, small agencies" 
              required
            >
          </div>

          <div class="form-group">
            <label class="form-label" for="input-pain">
              <span>What is their #1 biggest frustration?</span>
              <span class="form-hint">What problem do they search Google/Reddit for?</span>
            </label>
            <input 
              type="text" 
              id="input-pain" 
              class="input-text" 
              placeholder="e.g. Spending $70/mo on SEO tools with zero actual customers" 
              required
            >
          </div>
        </div>

        <div style="display: flex; justify-content: flex-end; gap: 1rem; margin-top: 1.25rem;">
          <button type="submit" id="btn-submit-audit" class="btn btn-primary" style="min-width: 200px;">
            <span id="btn-text">Run Autonomous Audit</span>
            <span id="btn-icon">→</span>
          </button>
        </div>
      </form>
    `;

    this.element = card;
    this.attachEvents(card);
    return card;
  }

  attachEvents(card) {
    const form = card.querySelector("#audit-form");
    const demoBtn = card.querySelector("#btn-quick-demo");

    demoBtn.addEventListener("click", () => {
      card.querySelector("#input-url").value = "https://founderreach.ai";
      card.querySelector("#input-name").value = "FounderReach AI";
      card.querySelector("#input-desc").value = "Autonomous growth agent that audits websites, fixes SEO/AEO/GEO issues, and discovers real customer demand.";
      card.querySelector("#input-audience").value = "Early-stage founders, indie builders, bootstrapped businesses";
      card.querySelector("#input-pain").value = "Zero traffic after launch and unable to afford $70/mo SEO suites";
      if (this.onDemoClick) this.onDemoClick();
    });

    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const payload = {
        url: card.querySelector("#input-url").value.trim(),
        businessName: card.querySelector("#input-name").value.trim(),
        description: card.querySelector("#input-desc").value.trim(),
        targetAudience: card.querySelector("#input-audience").value.trim(),
        painPoint: card.querySelector("#input-pain").value.trim()
      };
      if (this.onSubmit) this.onSubmit(payload);
    });
  }

  setLoading(isLoading) {
    if (!this.element) return;
    const btn = this.element.querySelector("#btn-submit-audit");
    const text = this.element.querySelector("#btn-text");
    const icon = this.element.querySelector("#btn-icon");

    if (isLoading) {
      btn.disabled = true;
      text.textContent = "Scanning Website...";
      icon.innerHTML = `<span class="pulse-dot" style="display: inline-block;"></span>`;
    } else {
      btn.disabled = false;
      text.textContent = "Run Autonomous Audit";
      icon.textContent = "→";
    }
  }
}
