/**
 * Copyable Fix Cards Component
 * 
 * The core value delivery for founders:
 * Provides ready-to-use, copy-paste code snippets with 1-click copy functionality
 * and plain-English explanations of where to place them.
 */

import { showToast } from "./toast.js";

export class FixCardsComponent {
  constructor({ onTabChange }) {
    this.onTabChange = onTabChange;
    this.element = null;
    this.activeCategory = "all";
  }

  render(fixes, demandSignals) {
    const container = document.createElement("section");
    container.className = "card";
    container.id = "fixes-section";

    container.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem; flex-wrap: wrap; gap: 1rem;">
        <div>
          <h2 style="font-size: 1.35rem; font-weight: 700;">Actionable Fix Proposals (Ready to Copy)</h2>
          <p class="form-hint">Click "Copy Code" on any card and paste it directly into your website head or files.</p>
        </div>
      </div>

      <div class="tabs-nav" id="fixes-tabs">
        <button type="button" class="tab-btn active" data-category="all">All Fixes (${fixes.length + (demandSignals ? demandSignals.length : 0)})</button>
        <button type="button" class="tab-btn" data-category="SEO">SEO Fixes</button>
        <button type="button" class="tab-btn" data-category="AEO">AEO & FAQs</button>
        <button type="button" class="tab-btn" data-category="GEO">GEO & AI Memory</button>
        <button type="button" class="tab-btn" data-category="DEMAND">Customer Demand</button>
      </div>

      <div id="fixes-list"></div>
    `;

    this.element = container;
    this.attachTabs(container, fixes, demandSignals);
    this.renderCards(container.querySelector("#fixes-list"), fixes, demandSignals, "all");
    return container;
  }

  attachTabs(container, fixes, demandSignals) {
    const tabs = container.querySelectorAll(".tab-btn");
    tabs.forEach(tab => {
      tab.addEventListener("click", () => {
        tabs.forEach(t => t.classList.remove("active"));
        tab.classList.add("active");
        const category = tab.getAttribute("data-category");
        this.activeCategory = category;
        this.renderCards(container.querySelector("#fixes-list"), fixes, demandSignals, category);
      });
    });
  }

  renderCards(listContainer, fixes, demandSignals, category) {
    listContainer.innerHTML = "";

    // 1. Filter Code Fixes
    const filteredFixes = category === "all" 
      ? fixes 
      : (category === "DEMAND" ? [] : fixes.filter(f => f.category === category));

    filteredFixes.forEach(fix => {
      const card = document.createElement("div");
      card.className = "fix-card";
      card.innerHTML = `
        <div class="fix-header">
          <div class="fix-title-wrap">
            <span class="badge ${fix.badge_class || 'badge-cyan'}">${fix.category}</span>
            <span class="fix-title">${fix.title}</span>
          </div>
          <span style="font-size: 0.75rem; color: var(--text-dim);">${fix.id}</span>
        </div>
        <div class="fix-body">
          <p class="fix-explanation">${fix.explanation}</p>
          <div class="fix-instruction">
            <span>📍 Placement:</span>
            <span>${fix.instruction}</span>
          </div>
          <div class="code-container">
            <button type="button" class="btn-copy">Copy Code</button>
            <pre class="code-box"><code>${this.escapeHtml(fix.code)}</code></pre>
          </div>
        </div>
      `;

      const copyBtn = card.querySelector(".btn-copy");
      copyBtn.addEventListener("click", () => {
        navigator.clipboard.writeText(fix.code).then(() => {
          copyBtn.textContent = "Copied! ✓";
          showToast(`Copied ${fix.title} to clipboard!`);
          setTimeout(() => { copyBtn.textContent = "Copy Code"; }, 2000);
        }).catch(err => {
          console.error("Failed to copy:", err);
          showToast("Failed to copy to clipboard", "error");
        });
      });

      listContainer.appendChild(card);
    });

    // 2. Render Demand Signals (if category matches "all" or "DEMAND")
    if ((category === "all" || category === "DEMAND") && demandSignals && demandSignals.length > 0) {
      demandSignals.forEach((signal, idx) => {
        const demandCard = document.createElement("div");
        demandCard.className = "fix-card";
        demandCard.innerHTML = `
          <div class="fix-header">
            <div class="fix-title-wrap">
              <span class="badge badge-emerald">CUSTOMER DEMAND</span>
              <span class="fix-title">${signal.channel} — Active Lead Opportunity</span>
            </div>
            <span style="font-size: 0.75rem; color: var(--text-dim);">Opportunity #${idx + 1}</span>
          </div>
          <div class="fix-body">
            <p class="fix-explanation"><strong>Search Pattern:</strong> "${signal.query}"</p>
            <div class="fix-instruction">
              <span style="color: #34d399;">🎯 Intent Type:</span>
              <span style="color: var(--text-main);">${signal.intent}</span>
            </div>
            <div class="code-container" style="background: rgba(16, 185, 129, 0.05); border-color: rgba(16, 185, 129, 0.2);">
              <div style="font-size: 0.85rem; color: #a7f3d0; line-height: 1.5;">
                <strong>Recommended Acquisition Action:</strong><br>
                ${signal.action}
              </div>
            </div>
          </div>
        `;
        listContainer.appendChild(demandCard);
      });
    }

    if (listContainer.children.length === 0) {
      listContainer.innerHTML = `
        <div style="text-align: center; padding: 2rem; color: var(--text-dim);">
          No fixes found for this category.
        </div>
      `;
    }
  }

  escapeHtml(str) {
    return str
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }
}
