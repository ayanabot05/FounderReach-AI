import React, { useState, useEffect, useCallback } from "react";
import {
  ShieldAlert,
  Users,
  CreditCard,
  Activity,
  Database,
  RefreshCw,
  Search,
  Trash2,
  UserCheck,
  UserX,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Layers,
  ArrowRight,
  TrendingUp,
  Server
} from "lucide-react";
import { ApiClient } from "../api/client";

const apiClient = new ApiClient();

export function AdminView({ user, onNavigateDashboard }) {
  const [activeTab, setActiveTab] = useState("overview"); // "overview" | "users" | "payments" | "audits" | "system"
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [actionNotice, setActionNotice] = useState(null);

  // Data states
  const [stats, setStats] = useState(null);
  
  // Users tab state
  const [usersList, setUsersList] = useState([]);
  const [usersTotal, setUsersTotal] = useState(0);
  const [usersPage, setUsersPage] = useState(1);
  const [usersSearch, setUsersSearch] = useState("");
  const [usersLoading, setUsersLoading] = useState(false);

  // Payments tab state
  const [paymentsList, setPaymentsList] = useState([]);
  const [paymentsTotal, setPaymentsTotal] = useState(0);
  const [paymentsPage, setPaymentsPage] = useState(1);
  const [paymentsStatus, setPaymentsStatus] = useState("");
  const [paymentsLoading, setPaymentsLoading] = useState(false);

  // Audits tab state
  const [auditsList, setAuditsList] = useState([]);
  const [auditsTotal, setAuditsTotal] = useState(0);
  const [auditsPage, setAuditsPage] = useState(1);
  const [auditsDomain, setAuditsDomain] = useState("");
  const [auditsLoading, setAuditsLoading] = useState(false);

  const notify = (msg, isErr = false) => {
    setActionNotice({ message: msg, isError: isErr });
    setTimeout(() => setActionNotice(null), 4000);
  };

  // Fetch stats overview
  const fetchStats = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiClient.getAdminStats();
      setStats(data);
    } catch (err) {
      setError(err.message || "Failed to load admin stats");
    } finally {
      setLoading(false);
    }
  }, []);

  // Fetch users
  const fetchUsers = useCallback(async (page = 1, search = "") => {
    try {
      setUsersLoading(true);
      const data = await apiClient.getAdminUsers(page, 15, search);
      setUsersList(data.users || []);
      setUsersTotal(data.total || 0);
      setUsersPage(data.page || 1);
    } catch (err) {
      notify("Failed to fetch users: " + err.message, true);
    } finally {
      setUsersLoading(false);
    }
  }, []);

  // Fetch payments
  const fetchPayments = useCallback(async (page = 1, status = "") => {
    try {
      setPaymentsLoading(true);
      const data = await apiClient.getAdminPayments(page, 15, status);
      setPaymentsList(data.payments || []);
      setPaymentsTotal(data.total || 0);
      setPaymentsPage(data.page || 1);
    } catch (err) {
      notify("Failed to fetch payments: " + err.message, true);
    } finally {
      setPaymentsLoading(false);
    }
  }, []);

  // Fetch audits
  const fetchAudits = useCallback(async (page = 1, domain = "") => {
    try {
      setAuditsLoading(true);
      const data = await apiClient.getAdminAudits(page, 15, domain);
      setAuditsList(data.audits || []);
      setAuditsTotal(data.total || 0);
      setAuditsPage(data.page || 1);
    } catch (err) {
      notify("Failed to fetch audit records: " + err.message, true);
    } finally {
      setAuditsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  useEffect(() => {
    if (activeTab === "users") fetchUsers(usersPage, usersSearch);
    if (activeTab === "payments") fetchPayments(paymentsPage, paymentsStatus);
    if (activeTab === "audits") fetchAudits(auditsPage, auditsDomain);
  }, [activeTab, usersPage, paymentsPage, auditsPage, fetchUsers, fetchPayments, fetchAudits, usersSearch, paymentsStatus, auditsDomain]);

  const handleRoleToggle = async (userId, currentRole) => {
    const newRole = currentRole === "admin" ? "user" : "admin";
    if (window.confirm(`Are you sure you want to change this user's role to ${newRole.toUpperCase()}?`)) {
      try {
        await apiClient.setAdminUserRole(userId, newRole);
        notify(`User role updated to ${newRole}`);
        fetchUsers(usersPage, usersSearch);
      } catch (err) {
        notify(err.message, true);
      }
    }
  };

  const handleDeleteUser = async (userId, userEmail) => {
    if (window.confirm(`PERMANENT ACTION: Delete user ${userEmail}? This will revoke their access.`)) {
      try {
        await apiClient.deleteAdminUser(userId);
        notify(`User ${userEmail} deleted successfully`);
        fetchUsers(usersPage, usersSearch);
      } catch (err) {
        notify(err.message, true);
      }
    }
  };

  return (
    <div className="dashboard-container" style={{ maxWidth: 1240, margin: "0 auto", padding: "2rem 1.5rem" }}>
      {/* Top Banner / Breadcrumb */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem", flexWrap: "wrap", gap: "1rem" }}>
        <div>
          <div style={{ display: "inline-flex", alignItems: "center", gap: "0.5rem", background: "var(--accent-green)", color: "#fffad3", padding: "0.25rem 0.65rem", fontWeight: 800, fontSize: "0.75rem", borderRadius: 4, textTransform: "uppercase", letterSpacing: "0.05em" }}>
            <ShieldAlert size={14} /> Master Executive Console
          </div>
          <h1 style={{ fontSize: "2rem", fontWeight: 900, marginTop: "0.5rem", marginBottom: "0.25rem" }}>
            FounderReach Administration
          </h1>
          <p style={{ color: "var(--text-muted)", fontSize: "0.9rem" }}>
            Manage SaaS users, payments, rate limits, Supabase sync, and autonomous audit telemetry.
          </p>
        </div>

        <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => {
              fetchStats();
              if (activeTab === "users") fetchUsers(usersPage, usersSearch);
              if (activeTab === "payments") fetchPayments(paymentsPage, paymentsStatus);
              if (activeTab === "audits") fetchAudits(auditsPage, auditsDomain);
              notify("Console data refreshed");
            }}
            style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}
          >
            <RefreshCw size={13} /> Refresh
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={onNavigateDashboard}
            style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}
          >
            Switch to Client Dashboard →
          </button>
        </div>
      </div>

      {actionNotice && (
        <div style={{
          padding: "0.85rem 1.25rem",
          marginBottom: "1.5rem",
          borderRadius: 6,
          background: actionNotice.isError ? "#ffebee" : "#e8f5e9",
          border: `2px solid ${actionNotice.isError ? "#c62828" : "var(--accent-green)"}`,
          color: actionNotice.isError ? "#c62828" : "var(--accent-green)",
          fontWeight: 700,
          display: "flex",
          alignItems: "center",
          gap: "0.5rem"
        }}>
          {actionNotice.isError ? <AlertTriangle size={18} /> : <CheckCircle2 size={18} />}
          <span>{actionNotice.message}</span>
        </div>
      )}

      {/* Tabs */}
      <div style={{
        display: "flex",
        gap: "0.5rem",
        borderBottom: "2px solid var(--accent-green)",
        marginBottom: "2rem",
        overflowX: "auto",
        paddingBottom: "2px"
      }}>
        {[
          { id: "overview", label: "Executive Overview", icon: Activity },
          { id: "users", label: `User Management (${stats?.total_users ?? "…"})`, icon: Users },
          { id: "payments", label: `Payments & Revenue ($${stats?.total_revenue?.toFixed(2) ?? "0"})`, icon: CreditCard },
          { id: "audits", label: `Audit Feed (${stats?.total_audits ?? "…"})`, icon: Server },
          { id: "system", label: "System Health & Config", icon: Database }
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              onClick={() => setActiveTab(tab.id)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.5rem",
                padding: "0.75rem 1.25rem",
                border: "none",
                background: isActive ? "var(--accent-green)" : "transparent",
                color: isActive ? "#fffad3" : "var(--text-main)",
                fontWeight: 800,
                fontSize: "0.9rem",
                cursor: "pointer",
                borderRadius: "6px 6px 0 0",
                whiteSpace: "nowrap"
              }}
            >
              <Icon size={16} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* TAB 1: EXECUTIVE OVERVIEW */}
      {activeTab === "overview" && (
        <div>
          {loading && !stats ? (
            <p>Loading executive telemetry...</p>
          ) : error ? (
            <div style={{ color: "red", padding: "1rem", border: "1px solid red" }}>{error}</div>
          ) : (
            <>
              {/* KPI Grid */}
              <div style={{
                display: "grid",
                gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
                gap: "1.25rem",
                marginBottom: "2rem"
              }}>
                <div className="card" style={{ padding: "1.5rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)", fontSize: "0.85rem", fontWeight: 700 }}>
                    <span>TOTAL REGISTERED USERS</span>
                    <Users size={18} color="var(--accent-green)" />
                  </div>
                  <div style={{ fontSize: "2.4rem", fontWeight: 900, marginTop: "0.5rem", color: "var(--text-main)" }}>
                    {stats.total_users}
                  </div>
                  <div style={{ fontSize: "0.8rem", color: "var(--accent-green)", fontWeight: 700, marginTop: "0.4rem" }}>
                    Verified Accounts in DB
                  </div>
                </div>

                <div className="card" style={{ padding: "1.5rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)", fontSize: "0.85rem", fontWeight: 700 }}>
                    <span>GROSS REVENUE</span>
                    <TrendingUp size={18} color="var(--accent-copper)" />
                  </div>
                  <div style={{ fontSize: "2.4rem", fontWeight: 900, marginTop: "0.5rem", color: "var(--accent-copper)" }}>
                    ${stats.total_revenue.toLocaleString("en-US", { minimumFractionDigits: 2 })}
                  </div>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 700, marginTop: "0.4rem" }}>
                    Stripe Checkout Volume
                  </div>
                </div>

                <div className="card" style={{ padding: "1.5rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)", fontSize: "0.85rem", fontWeight: 700 }}>
                    <span>LIFETIME AUDITS RUN</span>
                    <Activity size={18} color="var(--accent-green)" />
                  </div>
                  <div style={{ fontSize: "2.4rem", fontWeight: 900, marginTop: "0.5rem", color: "var(--text-main)" }}>
                    {stats.total_audits}
                  </div>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 700, marginTop: "0.4rem" }}>
                    Cached Snapshot History
                  </div>
                </div>

                <div className="card" style={{ padding: "1.5rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", color: "var(--text-muted)", fontSize: "0.85rem", fontWeight: 700 }}>
                    <span>MONITORED CLIENT DOMAINS</span>
                    <Layers size={18} color="var(--accent-green)" />
                  </div>
                  <div style={{ fontSize: "2.4rem", fontWeight: 900, marginTop: "0.5rem", color: "var(--text-main)" }}>
                    {stats.monitored_domains}
                  </div>
                  <div style={{ fontSize: "0.8rem", color: "var(--text-muted)", fontWeight: 700, marginTop: "0.4rem" }}>
                    Autonomous 6h Scans
                  </div>
                </div>
              </div>

              {/* Day-to-Day Operational Health Matrix */}
              <div className="card" style={{ padding: "1.5rem", marginBottom: "2rem" }}>
                <h3 style={{ fontSize: "1.2rem", fontWeight: 800, marginBottom: "1rem" }}>
                  Autonomous Engine Telemetry &amp; Gateway Health
                </h3>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "1rem" }}>
                  <div style={{ padding: "1rem", border: "1px solid var(--accent-green)", borderRadius: 6, background: "rgba(10,50,30,0.03)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: 800 }}>
                      <Database size={16} color="var(--accent-green)" />
                      <span>Primary Database</span>
                    </div>
                    <div style={{ marginTop: "0.5rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <span className="badge badge-success" style={{ background: stats.supabase_enabled ? "#2e7d32" : "#555" }}>
                        {stats.database.toUpperCase()}
                      </span>
                      <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                        {stats.supabase_enabled ? "Supabase Cloud Connected" : "Local SQLite Active (Supabase unconfigured)"}
                      </span>
                    </div>
                  </div>

                  <div style={{ padding: "1rem", border: "1px solid var(--accent-green)", borderRadius: 6, background: "rgba(10,50,30,0.03)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: 800 }}>
                      <CreditCard size={16} color="var(--accent-green)" />
                      <span>Payment Processor</span>
                    </div>
                    <div style={{ marginTop: "0.5rem", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                      <span className="badge badge-success" style={{ background: stats.stripe_enabled ? "#2e7d32" : "#e65100" }}>
                        {stats.stripe_enabled ? "STRIPE LIVE" : "STRIPE SANDBOX"}
                      </span>
                      <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                        {stats.stripe_enabled ? "Live Webhooks Ready" : "Test Checkout Fallback Active"}
                      </span>
                    </div>
                  </div>

                  <div style={{ padding: "1rem", border: "1px solid var(--accent-green)", borderRadius: 6, background: "rgba(10,50,30,0.03)" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: 800 }}>
                      <Clock size={16} color="var(--accent-green)" />
                      <span>Audit TTL &amp; Rate Limiter</span>
                    </div>
                    <div style={{ marginTop: "0.5rem", fontSize: "0.85rem", color: "var(--text-muted)" }}>
                      Cache TTL: <strong>{stats.cache_ttl_seconds}s (1 hr)</strong> | Sliding IP Limit: <strong>{stats.rate_limit_per_minute} req/min</strong>
                    </div>
                  </div>
                </div>
              </div>

              {/* Quick view of recent items */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
                {/* Recent Users */}
                <div className="card" style={{ padding: "1.25rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                    <h4 style={{ fontWeight: 800, fontSize: "1rem" }}>Recent Users</h4>
                    <button type="button" className="btn btn-secondary btn-sm" onClick={() => setActiveTab("users")}>View All →</button>
                  </div>
                  {stats.recent_users && stats.recent_users.length > 0 ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                      {stats.recent_users.map((u) => (
                        <div key={u.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.5rem 0", borderBottom: "1px solid #eee" }}>
                          <div>
                            <div style={{ fontWeight: 700, fontSize: "0.85rem" }}>{u.email}</div>
                            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{u.name || "Anonymous Founder"}</div>
                          </div>
                          <span className={`badge ${u.role === "admin" ? "badge-danger" : "badge-neutral"}`} style={{ fontSize: "0.7rem" }}>
                            {u.role.toUpperCase()}
                          </span>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>No user accounts registered yet.</p>
                  )}
                </div>

                {/* Recent Payments */}
                <div className="card" style={{ padding: "1.25rem" }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                    <h4 style={{ fontWeight: 800, fontSize: "1rem" }}>Recent Payments</h4>
                    <button type="button" className="btn btn-secondary btn-sm" onClick={() => setActiveTab("payments")}>View All →</button>
                  </div>
                  {stats.recent_payments && stats.recent_payments.length > 0 ? (
                    <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                      {stats.recent_payments.map((p) => (
                        <div key={p.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.5rem 0", borderBottom: "1px solid #eee" }}>
                          <div>
                            <div style={{ fontWeight: 700, fontSize: "0.85rem" }}>{p.plan}</div>
                            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{p.created_at ? new Date(p.created_at).toLocaleDateString() : ""}</div>
                          </div>
                          <div style={{ textAlign: "right" }}>
                            <div style={{ fontWeight: 800, color: "var(--accent-copper)" }}>
                              ${((p.amount_cents || 0) / 100).toFixed(2)}
                            </div>
                            <span className="badge badge-success" style={{ fontSize: "0.65rem" }}>
                              {p.status}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>No checkout transactions recorded yet.</p>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      )}

      {/* TAB 2: USER MANAGEMENT */}
      {activeTab === "users" && (
        <div>
          <div className="card" style={{ padding: "1.5rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem", flexWrap: "wrap", gap: "1rem" }}>
              <div>
                <h3 style={{ fontSize: "1.25rem", fontWeight: 800 }}>User Accounts</h3>
                <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
                  {usersTotal} registered users found in database
                </p>
              </div>

              {/* Search */}
              <div style={{ display: "flex", gap: "0.5rem", alignItems: "center" }}>
                <div style={{ position: "relative" }}>
                  <input
                    type="text"
                    placeholder="Search by email or name..."
                    value={usersSearch}
                    onChange={(e) => setUsersSearch(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter") fetchUsers(1, usersSearch); }}
                    style={{
                      padding: "0.5rem 0.75rem 0.5rem 2rem",
                      borderRadius: 4,
                      border: "1px solid var(--accent-green)",
                      background: "#fff",
                      fontSize: "0.85rem",
                      width: 240
                    }}
                  />
                  <Search size={14} style={{ position: "absolute", left: "0.6rem", top: "50%", transform: "translateY(-50%)", color: "var(--text-muted)" }} />
                </div>
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => fetchUsers(1, usersSearch)}
                >
                  Filter
                </button>
              </div>
            </div>

            {usersLoading ? (
              <p>Loading users...</p>
            ) : usersList.length === 0 ? (
              <p style={{ color: "var(--text-muted)" }}>No users matched your search criteria.</p>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
                  <thead>
                    <tr style={{ borderBottom: "2px solid var(--accent-green)", textAlign: "left" }}>
                      <th style={{ padding: "0.75rem" }}>User</th>
                      <th style={{ padding: "0.75rem" }}>Role</th>
                      <th style={{ padding: "0.75rem" }}>Active Domain</th>
                      <th style={{ padding: "0.75rem" }}>Registered</th>
                      <th style={{ padding: "0.75rem" }}>Last Login</th>
                      <th style={{ padding: "0.75rem", textAlign: "right" }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {usersList.map((u) => (
                      <tr key={u.id} style={{ borderBottom: "1px solid #e0e0e0" }}>
                        <td style={{ padding: "0.75rem" }}>
                          <div style={{ fontWeight: 800 }}>{u.name || "—"}</div>
                          <div style={{ color: "var(--text-muted)", fontSize: "0.8rem" }}>{u.email}</div>
                        </td>
                        <td style={{ padding: "0.75rem" }}>
                          <span
                            className={`badge ${u.role === "admin" ? "badge-danger" : "badge-neutral"}`}
                            style={{ fontWeight: 800 }}
                          >
                            {u.role.toUpperCase()}
                          </span>
                        </td>
                        <td style={{ padding: "0.75rem" }}>
                          {u.active_domain ? (
                            <span style={{ fontFamily: "monospace", color: "var(--accent-green)", fontWeight: 700 }}>
                              {u.active_domain}
                            </span>
                          ) : (
                            <span style={{ color: "#999" }}>None</span>
                          )}
                        </td>
                        <td style={{ padding: "0.75rem", color: "var(--text-muted)" }}>
                          {u.created_at ? new Date(u.created_at).toLocaleDateString() : "—"}
                        </td>
                        <td style={{ padding: "0.75rem", color: "var(--text-muted)" }}>
                          {u.last_login ? new Date(u.last_login).toLocaleString() : "Never"}
                        </td>
                        <td style={{ padding: "0.75rem", textAlign: "right" }}>
                          <div style={{ display: "inline-flex", gap: "0.4rem" }}>
                            <button
                              type="button"
                              className="btn btn-secondary btn-sm"
                              onClick={() => handleRoleToggle(u.id, u.role)}
                              title={u.role === "admin" ? "Revoke admin role" : "Grant admin role"}
                              style={{ padding: "0.3rem 0.5rem" }}
                            >
                              {u.role === "admin" ? <UserX size={14} color="#c62828" /> : <UserCheck size={14} color="var(--accent-green)" />}
                            </button>
                            <button
                              type="button"
                              className="btn btn-secondary btn-sm"
                              onClick={() => handleDeleteUser(u.id, u.email)}
                              title="Delete user"
                              style={{ padding: "0.3rem 0.5rem", color: "#c62828" }}
                            >
                              <Trash2 size={14} />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination Controls */}
            {usersTotal > 15 && (
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "1.5rem" }}>
                <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                  Showing page {usersPage} of {Math.ceil(usersTotal / 15)}
                </span>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={usersPage <= 1}
                    onClick={() => fetchUsers(usersPage - 1, usersSearch)}
                  >
                    Previous
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={usersPage >= Math.ceil(usersTotal / 15)}
                    onClick={() => fetchUsers(usersPage + 1, usersSearch)}
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 3: PAYMENTS & BILLING */}
      {activeTab === "payments" && (
        <div>
          <div className="card" style={{ padding: "1.5rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem", flexWrap: "wrap", gap: "1rem" }}>
              <div>
                <h3 style={{ fontSize: "1.25rem", fontWeight: 800 }}>Stripe Transactions &amp; Revenue</h3>
                <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
                  {paymentsTotal} recorded checkouts and subscriptions
                </p>
              </div>

              <div style={{ display: "flex", gap: "0.5rem" }}>
                <select
                  value={paymentsStatus}
                  onChange={(e) => {
                    setPaymentsStatus(e.target.value);
                    fetchPayments(1, e.target.value);
                  }}
                  style={{
                    padding: "0.45rem 0.75rem",
                    border: "1px solid var(--accent-green)",
                    borderRadius: 4,
                    background: "#fff",
                    fontSize: "0.85rem"
                  }}
                >
                  <option value="">All Statuses</option>
                  <option value="completed">Completed / Paid</option>
                  <option value="pending">Pending</option>
                  <option value="failed">Failed</option>
                </select>
              </div>
            </div>

            {paymentsLoading ? (
              <p>Loading payments...</p>
            ) : paymentsList.length === 0 ? (
              <p style={{ color: "var(--text-muted)" }}>No transaction records found.</p>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
                  <thead>
                    <tr style={{ borderBottom: "2px solid var(--accent-green)", textAlign: "left" }}>
                      <th style={{ padding: "0.75rem" }}>Transaction ID</th>
                      <th style={{ padding: "0.75rem" }}>Plan / Offering</th>
                      <th style={{ padding: "0.75rem" }}>Customer</th>
                      <th style={{ padding: "0.75rem" }}>Amount</th>
                      <th style={{ padding: "0.75rem" }}>Status</th>
                      <th style={{ padding: "0.75rem" }}>Date</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paymentsList.map((p) => (
                      <tr key={p.id} style={{ borderBottom: "1px solid #e0e0e0" }}>
                        <td style={{ padding: "0.75rem", fontFamily: "monospace", fontSize: "0.75rem" }}>
                          {p.id.substring(0, 12)}...
                        </td>
                        <td style={{ padding: "0.75rem", fontWeight: 800 }}>
                          {p.plan}
                        </td>
                        <td style={{ padding: "0.75rem", color: "var(--text-muted)" }}>
                          {p.stripe_customer_id || p.user_id || "Guest Founder"}
                        </td>
                        <td style={{ padding: "0.75rem", fontWeight: 900, color: "var(--accent-copper)" }}>
                          ${((p.amount_cents || 0) / 100).toFixed(2)} {p.currency?.toUpperCase() || "USD"}
                        </td>
                        <td style={{ padding: "0.75rem" }}>
                          <span className={`badge ${p.status === "completed" ? "badge-success" : "badge-neutral"}`}>
                            {p.status}
                          </span>
                        </td>
                        <td style={{ padding: "0.75rem", color: "var(--text-muted)" }}>
                          {p.created_at ? new Date(p.created_at).toLocaleString() : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {paymentsTotal > 15 && (
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "1.5rem" }}>
                <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                  Showing page {paymentsPage} of {Math.ceil(paymentsTotal / 15)}
                </span>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={paymentsPage <= 1}
                    onClick={() => fetchPayments(paymentsPage - 1, paymentsStatus)}
                  >
                    Previous
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={paymentsPage >= Math.ceil(paymentsTotal / 15)}
                    onClick={() => fetchPayments(paymentsPage + 1, paymentsStatus)}
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 4: AUDIT FEED & TELEMETRY */}
      {activeTab === "audits" && (
        <div>
          <div className="card" style={{ padding: "1.5rem" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1.5rem", flexWrap: "wrap", gap: "1rem" }}>
              <div>
                <h3 style={{ fontSize: "1.25rem", fontWeight: 800 }}>Audit Logs &amp; Proof of Work</h3>
                <p style={{ color: "var(--text-muted)", fontSize: "0.85rem" }}>
                  {auditsTotal} audit snapshots stored across monitored domains
                </p>
              </div>

              <div style={{ display: "flex", gap: "0.5rem" }}>
                <input
                  type="text"
                  placeholder="Filter by domain..."
                  value={auditsDomain}
                  onChange={(e) => setAuditsDomain(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") fetchAudits(1, auditsDomain); }}
                  style={{
                    padding: "0.5rem 0.75rem",
                    border: "1px solid var(--accent-green)",
                    borderRadius: 4,
                    background: "#fff",
                    fontSize: "0.85rem",
                    width: 200
                  }}
                />
                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={() => fetchAudits(1, auditsDomain)}
                >
                  Filter
                </button>
              </div>
            </div>

            {auditsLoading ? (
              <p>Loading audit snapshots...</p>
            ) : auditsList.length === 0 ? (
              <p style={{ color: "var(--text-muted)" }}>No audits recorded yet.</p>
            ) : (
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.85rem" }}>
                  <thead>
                    <tr style={{ borderBottom: "2px solid var(--accent-green)", textAlign: "left" }}>
                      <th style={{ padding: "0.75rem" }}>Domain</th>
                      <th style={{ padding: "0.75rem" }}>Overall</th>
                      <th style={{ padding: "0.75rem" }}>SEO</th>
                      <th style={{ padding: "0.75rem" }}>AEO</th>
                      <th style={{ padding: "0.75rem" }}>GEO</th>
                      <th style={{ padding: "0.75rem" }}>Latency</th>
                      <th style={{ padding: "0.75rem" }}>Timestamp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {auditsList.map((a) => (
                      <tr key={a.id} style={{ borderBottom: "1px solid #e0e0e0" }}>
                        <td style={{ padding: "0.75rem", fontWeight: 800 }}>
                          <span style={{ fontFamily: "monospace", color: "var(--accent-green)" }}>
                            {a.domain}
                          </span>
                        </td>
                        <td style={{ padding: "0.75rem", fontWeight: 900 }}>
                          {a.overall_score}/100
                        </td>
                        <td style={{ padding: "0.75rem" }}>{a.seo_score}</td>
                        <td style={{ padding: "0.75rem" }}>{a.aeo_score}</td>
                        <td style={{ padding: "0.75rem" }}>{a.geo_score}</td>
                        <td style={{ padding: "0.75rem", color: "var(--text-muted)" }}>
                          {a.response_time_ms ? `${a.response_time_ms}ms` : "—"}
                        </td>
                        <td style={{ padding: "0.75rem", color: "var(--text-muted)" }}>
                          {a.created_at ? new Date(a.created_at).toLocaleString() : "—"}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {auditsTotal > 15 && (
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "1.5rem" }}>
                <span style={{ fontSize: "0.85rem", color: "var(--text-muted)" }}>
                  Showing page {auditsPage} of {Math.ceil(auditsTotal / 15)}
                </span>
                <div style={{ display: "flex", gap: "0.5rem" }}>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={auditsPage <= 1}
                    onClick={() => fetchAudits(auditsPage - 1, auditsDomain)}
                  >
                    Previous
                  </button>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    disabled={auditsPage >= Math.ceil(auditsTotal / 15)}
                    onClick={() => fetchAudits(auditsPage + 1, auditsDomain)}
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* TAB 5: SYSTEM HEALTH & CONFIGURATION */}
      {activeTab === "system" && (
        <div>
          <div className="card" style={{ padding: "1.5rem", marginBottom: "1.5rem" }}>
            <h3 style={{ fontSize: "1.25rem", fontWeight: 800, marginBottom: "0.5rem" }}>
              Day-to-Day Operations &amp; Deployment Configuration
            </h3>
            <p style={{ color: "var(--text-muted)", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
              Active runtime settings loaded from server environment variables (.env).
            </p>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "1.5rem" }}>
              <div style={{ padding: "1rem", border: "1px solid #ddd", borderRadius: 6, background: "#fafafa" }}>
                <h4 style={{ fontWeight: 800, marginBottom: "0.75rem" }}>Master Admin Identity</h4>
                <div style={{ fontSize: "0.85rem", display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                  <div>Bootstrap Email: <strong>{stats?.admin_email || "admin@founderreach.ai"}</strong></div>
                  <div>Role: <span className="badge badge-danger">SUPER ADMIN</span></div>
                  <div>Access Token: JWT (24-hour expiration)</div>
                </div>
              </div>

              <div style={{ padding: "1rem", border: "1px solid #ddd", borderRadius: 6, background: "#fafafa" }}>
                <h4 style={{ fontWeight: 800, marginBottom: "0.75rem" }}>Client Boundary Policy</h4>
                <div style={{ fontSize: "0.85rem", display: "flex", flexDirection: "column", gap: "0.4rem" }}>
                  <div>Read-Only Inspection: <strong style={{ color: "var(--accent-green)" }}>ENFORCED</strong></div>
                  <div>Client Modification: <strong style={{ color: "var(--accent-copper)" }}>FORBIDDEN (0 writes)</strong></div>
                  <div>Automated Posting: <strong style={{ color: "var(--accent-copper)" }}>DISABLED (Drafts only)</strong></div>
                </div>
              </div>
            </div>
          </div>

          <div className="card" style={{ padding: "1.5rem" }}>
            <h4 style={{ fontWeight: 800, marginBottom: "0.5rem" }}>How to configure production keys:</h4>
            <p style={{ fontSize: "0.85rem", color: "var(--text-muted)", marginBottom: "1rem" }}>
              Update the environment variables on Railway / Vercel:
            </p>
            <pre style={{
              background: "#1e1e1e",
              color: "#d4d4d4",
              padding: "1rem",
              borderRadius: 6,
              fontSize: "0.8rem",
              overflowX: "auto"
            }}>
{`# Admin Access
ADMIN_EMAIL="admin@founderreach.ai"
ADMIN_PASSWORD="YourStrongSecurePassword123!"

# Stripe Live Integration
STRIPE_SECRET_KEY="sk_live_..."
STRIPE_PUBLISHABLE_KEY="pk_live_..."
STRIPE_WEBHOOK_SECRET="whsec_..."

# Supabase Storage Integration
SUPABASE_URL="https://your-project.supabase.co"
SUPABASE_SECRET_KEY="your-supabase-service-role-key"
SUPABASE_ENABLED="true"`}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
