/**
 * API Client for FounderReach AI
 */

export class ApiClient {
  constructor(baseUrl = "") {
    this.baseUrl = baseUrl;
  }

  async auditWebsite(payload) {
    const res = await fetch(`${this.baseUrl}/api/audit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: payload.url,
        business_name: payload.business_name || payload.businessName || "",
        description: payload.description || "",
        target_audience: payload.target_audience || payload.targetAudience || "",
        pain_point: payload.pain_point || payload.painPoint || ""
      })
    });

    if (!res.ok) {
      let errText = "Audit service error";
      try {
        const errJson = await res.json();
        errText = errJson.detail || errText;
      } catch (e) {}
      throw new Error(errText);
    }

    return await res.json();
  }

  async healthCheck() {
    const res = await fetch(`${this.baseUrl}/api/health`);
    return await res.json();
  }
}
