/**
 * API Client for FounderReach AI
 */

export class ApiClient {
  constructor(baseUrl = "") {
    this.baseUrl = baseUrl;
  }

  getAuthHeaders(token = null) {
    const activeToken = token || localStorage.getItem("founderreach_token");
    const headers = { "Content-Type": "application/json" };
    if (activeToken) {
      headers["Authorization"] = `Bearer ${activeToken}`;
    }
    return headers;
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

  // P2: Auth API Methods
  async register({ email, password, name, activeDomain }) {
    const res = await fetch(`${this.baseUrl}/api/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        password,
        name: name || "",
        active_domain: activeDomain || ""
      })
    });

    if (!res.ok) {
      let errText = "Registration failed";
      try {
        const errJson = await res.json();
        errText = errJson.detail || errText;
      } catch (e) {}
      throw new Error(errText);
    }

    return await res.json();
  }

  async login({ email, password }) {
    const res = await fetch(`${this.baseUrl}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    if (!res.ok) {
      let errText = "Invalid email or password";
      try {
        const errJson = await res.json();
        errText = errJson.detail || errText;
      } catch (e) {}
      throw new Error(errText);
    }

    return await res.json();
  }

  async getMe(token = null) {
    const res = await fetch(`${this.baseUrl}/api/auth/me`, {
      headers: this.getAuthHeaders(token)
    });

    if (!res.ok) {
      throw new Error("Session invalid or expired");
    }

    return await res.json();
  }

  // P3: Scheduler & Monitoring API Methods
  async getMonitoredDomains() {
    const res = await fetch(`${this.baseUrl}/api/monitor/domains`);
    if (!res.ok) throw new Error("Failed to load monitored domains");
    return await res.json();
  }

  async addMonitoredDomain(domain, frequencyHours = 6) {
    const res = await fetch(`${this.baseUrl}/api/monitor/domains`, {
      method: "POST",
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ domain, frequency_hours: frequencyHours })
    });
    if (!res.ok) throw new Error("Failed to monitor domain");
    return await res.json();
  }

  async deleteMonitoredDomain(domain) {
    const res = await fetch(`${this.baseUrl}/api/monitor/domains/${encodeURIComponent(domain)}`, {
      method: "DELETE",
      headers: this.getAuthHeaders()
    });
    if (!res.ok) throw new Error("Failed to remove domain from monitoring");
    return await res.json();
  }

  async scanDomainNow(domain) {
    const res = await fetch(`${this.baseUrl}/api/monitor/scan-now`, {
      method: "POST",
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ domain })
    });
    if (!res.ok) throw new Error("Scan trigger failed");
    return await res.json();
  }

  // P4: Reddit Connector API Methods
  async getRedditStatus() {
    const res = await fetch(`${this.baseUrl}/api/reddit/status`);
    if (!res.ok) throw new Error("Failed to get Reddit connector status");
    return await res.json();
  }

  async getRedditFeed(query = "SaaS", limit = 10) {
    const res = await fetch(`${this.baseUrl}/api/reddit/feed?query=${encodeURIComponent(query)}&limit=${limit}`);
    if (!res.ok) throw new Error("Failed to fetch Reddit feed");
    return await res.json();
  }

  async healthCheck() {
    const res = await fetch(`${this.baseUrl}/api/health`);
    return await res.json();
  }

  // Stripe Billing API Methods
  async createCheckoutSession({ planId, successUrl, cancelUrl, customerEmail }) {
    const res = await fetch(`${this.baseUrl}/api/billing/create-checkout-session`, {
      method: "POST",
      headers: this.getAuthHeaders(),
      body: JSON.stringify({
        plan_id: planId,
        success_url: successUrl,
        cancel_url: cancelUrl,
        customer_email: customerEmail || ""
      })
    });
    if (!res.ok) {
      let errText = "Checkout creation failed";
      try {
        const errJson = await res.json();
        errText = errJson.detail || errText;
      } catch (e) {}
      throw new Error(errText);
    }
    return await res.json();
  }

  // Super Admin API Methods
  async getAdminStats() {
    const res = await fetch(`${this.baseUrl}/api/admin/stats`, {
      headers: this.getAuthHeaders()
    });
    if (!res.ok) {
      let err = "Failed to load admin stats";
      try {
        const j = await res.json();
        err = j.detail || err;
      } catch (e) {}
      throw new Error(err);
    }
    return await res.json();
  }

  async getAdminUsers(page = 1, limit = 20, search = "") {
    const query = new URLSearchParams({ page, limit });
    if (search) query.set("search", search);
    const res = await fetch(`${this.baseUrl}/api/admin/users?${query.toString()}`, {
      headers: this.getAuthHeaders()
    });
    if (!res.ok) throw new Error("Failed to load users");
    return await res.json();
  }

  async setAdminUserRole(userId, role) {
    const res = await fetch(`${this.baseUrl}/api/admin/users/${encodeURIComponent(userId)}/role`, {
      method: "POST",
      headers: this.getAuthHeaders(),
      body: JSON.stringify({ role })
    });
    if (!res.ok) {
      let err = "Failed to update user role";
      try {
        const j = await res.json();
        err = j.detail || err;
      } catch (e) {}
      throw new Error(err);
    }
    return await res.json();
  }

  async deleteAdminUser(userId) {
    const res = await fetch(`${this.baseUrl}/api/admin/users/${encodeURIComponent(userId)}`, {
      method: "DELETE",
      headers: this.getAuthHeaders()
    });
    if (!res.ok) throw new Error("Failed to delete user");
    return await res.json();
  }

  async getAdminPayments(page = 1, limit = 20, status = "") {
    const query = new URLSearchParams({ page, limit });
    if (status) query.set("status", status);
    const res = await fetch(`${this.baseUrl}/api/admin/payments?${query.toString()}`, {
      headers: this.getAuthHeaders()
    });
    if (!res.ok) throw new Error("Failed to load payments");
    return await res.json();
  }

  async getAdminAudits(page = 1, limit = 20, domain = "") {
    const query = new URLSearchParams({ page, limit });
    if (domain) query.set("domain", domain);
    const res = await fetch(`${this.baseUrl}/api/admin/audits?${query.toString()}`, {
      headers: this.getAuthHeaders()
    });
    if (!res.ok) throw new Error("Failed to load audit logs");
    return await res.json();
  }
}
