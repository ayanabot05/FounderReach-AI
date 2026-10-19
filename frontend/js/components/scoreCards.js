/**
 * Scorecards Component (SEO / AEO / GEO)
 * 
 * Provides clear 0-100 scores, letter grades, and plain-English summaries
 * so non-technical founders understand exactly where they stand without jargon.
 */

export class ScoreCardsComponent {
  constructor() {
    this.element = null;
  }

  getGradeClass(score) {
    if (score >= 80) return "grade-good";
    if (score >= 50) return "grade-warn";
    return "grade-poor";
  }

  render(scores) {
    if (!scores) return document.createElement("div");

    const container = document.createElement("div");
    container.className = "grid-3";
    container.id = "scorecards-grid";

    const keys = ["seo", "aeo", "geo"];
    const badges = {
      seo: "Google Search",
      aeo: "Direct AI Overviews",
      geo: "ChatGPT / Perplexity / Gemini"
    };

    keys.forEach(key => {
      const item = scores[key];
      if (!item) return;

      const gradeClass = this.getGradeClass(item.score);
      const card = document.createElement("div");
      card.className = "score-card";

      card.innerHTML = `
        <div>
          <div class="score-top">
            <div>
              <span class="badge badge-cyan" style="margin-bottom: 0.5rem;">${badges[key]}</span>
              <div class="score-title">${item.title}</div>
            </div>
            <div class="score-circle ${gradeClass}">
              ${item.score}
            </div>
          </div>
          <p class="score-summary">${item.summary}</p>
        </div>

        <div style="margin-top: 1.25rem; padding-top: 0.75rem; border-top: 1px solid var(--border-subtle); display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem;">
          <span style="color: var(--text-dim);">Grade Rating</span>
          <span style="font-weight: 700; color: var(--text-main);">${item.grade} (${item.score}/100)</span>
        </div>
      `;

      container.appendChild(card);
    });

    this.element = container;
    return container;
  }
}
