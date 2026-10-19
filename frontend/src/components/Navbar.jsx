import React, { useState } from "react";
import { LayoutDashboard, Zap, User, LogOut, Menu, X, ShieldAlert } from "lucide-react";

export function Navbar({ currentView, setCurrentView, user, setUser, onTryDemo }) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className="app-header">
      <div className="header-inner">
        <button
          type="button"
          onClick={() => {
            setCurrentView("landing");
            setMobileMenuOpen(false);
          }}
          className="brand-wrapper"
        >
          <div className="brand-logo-glow">FR</div>
          <div className="brand-text">
            <h1>
              FounderReach <span>AI</span>
            </h1>
            <p className="brand-tagline">Autonomous SEO, AEO &amp; GEO Growth Agent</p>
          </div>
        </button>

        {/* Desktop Navigation Links */}
        <nav className="header-nav desktop-only">
          {currentView === "landing" ? (
            <>
              <a href="#stage-trust">Proof of Trust</a>
              <a href="#stage-sentinel">1. Sentinel</a>
              <a href="#stage-mirror">2. Perception Mirror</a>
              <a href="#stage-studio">3. Fix Studio</a>
              <a href="#stage-demand">4. Demand Radar</a>
              <a href="#stage-pricing">Pricing</a>
            </>
          ) : (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setCurrentView("landing")}
              style={{ fontWeight: 800 }}
            >
              ← Back to Overview
            </button>
          )}

          <button
            type="button"
            className={`btn btn-sm ${currentView === "dashboard" ? "btn-primary" : "btn-secondary"}`}
            onClick={() => setCurrentView("dashboard")}
            style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}
          >
            <LayoutDashboard size={14} />
            <span>Growth Dashboard</span>
          </button>

          {user?.role === "admin" && (
            <button
              type="button"
              className={`btn btn-sm ${currentView === "admin" ? "btn-primary" : "btn-secondary"}`}
              onClick={() => setCurrentView("admin")}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.4rem",
                borderColor: "var(--accent-copper)",
                color: currentView === "admin" ? undefined : "var(--accent-copper)",
                fontWeight: 800
              }}
            >
              <ShieldAlert size={14} />
              <span>Admin Console</span>
            </button>
          )}

          {currentView === "landing" && (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={onTryDemo}
              style={{ display: "inline-flex", alignItems: "center", gap: "0.35rem" }}
              title="Inspect scheduleflow.io demo"
            >
              <Zap size={13} color="var(--accent-copper)" />
              <span style={{ color: "var(--accent-green)" }}>Instant Demo</span>
            </button>
          )}

          {user ? (
            <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => setCurrentView("dashboard")}
                style={{ display: "inline-flex", alignItems: "center", gap: "0.35rem", fontWeight: 800 }}
              >
                <User size={13} color="var(--accent-green)" />
                <span>{user.name.split(" ")[0]}</span>
              </button>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => {
                  setUser(null);
                  localStorage.removeItem("founderreach_user");
                }}
                title="Sign Out"
                style={{ padding: "0.45rem", color: "var(--accent-copper)" }}
              >
                <LogOut size={13} />
              </button>
            </div>
          ) : (
            <button
              type="button"
              className="btn btn-primary btn-sm"
              onClick={() => setCurrentView("auth")}
            >
              Sign In
            </button>
          )}
        </nav>

        {/* Mobile Toggle Button */}
        <button
          type="button"
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          style={{
            display: "none",
            background: "transparent",
            border: "none",
            color: "var(--text-main)",
            cursor: "pointer",
            padding: "0.5rem"
          }}
          className="mobile-toggle-btn"
          aria-label="Toggle Navigation Menu"
        >
          {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
        </button>
      </div>

      {/* Mobile Menu Dropdown */}
      {mobileMenuOpen && (
        <div
          style={{
            padding: "1rem 1.5rem",
            background: "#fffad3",
            borderTop: "2px solid var(--accent-green)",
            display: "flex",
            flexDirection: "column",
            gap: "0.75rem"
          }}
        >
          {currentView === "landing" ? (
            <>
              <a
                href="#stage-trust"
                onClick={() => setMobileMenuOpen(false)}
                style={{ color: "var(--text-main)", textDecoration: "none", padding: "0.4rem 0", fontWeight: 800 }}
              >
                Proof of Trust
              </a>
              <a
                href="#stage-sentinel"
                onClick={() => setMobileMenuOpen(false)}
                style={{ color: "var(--text-main)", textDecoration: "none", padding: "0.4rem 0", fontWeight: 800 }}
              >
                1. Sentinel Ingestion
              </a>
              <a
                href="#stage-mirror"
                onClick={() => setMobileMenuOpen(false)}
                style={{ color: "var(--text-main)", textDecoration: "none", padding: "0.4rem 0", fontWeight: 800 }}
              >
                2. Perception Mirror
              </a>
              <a
                href="#stage-studio"
                onClick={() => setMobileMenuOpen(false)}
                style={{ color: "var(--text-main)", textDecoration: "none", padding: "0.4rem 0", fontWeight: 800 }}
              >
                3. Fix Studio
              </a>
              <a
                href="#stage-demand"
                onClick={() => setMobileMenuOpen(false)}
                style={{ color: "var(--text-main)", textDecoration: "none", padding: "0.4rem 0", fontWeight: 800 }}
              >
                4. Demand Radar
              </a>
              <a
                href="#stage-pricing"
                onClick={() => setMobileMenuOpen(false)}
                style={{ color: "var(--text-main)", textDecoration: "none", padding: "0.4rem 0", fontWeight: 800 }}
              >
                Pricing
              </a>
            </>
          ) : (
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => {
                setCurrentView("landing");
                setMobileMenuOpen(false);
              }}
            >
              ← Back to Overview
            </button>
          )}

          <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.5rem" }}>
            <button
              type="button"
              className={`btn btn-sm ${currentView === "dashboard" ? "btn-primary" : "btn-secondary"}`}
              onClick={() => {
                setCurrentView("dashboard");
                setMobileMenuOpen(false);
              }}
              style={{ flex: 1 }}
            >
              <LayoutDashboard size={14} />
              <span>Dashboard</span>
            </button>

            {user?.role === "admin" && (
              <button
                type="button"
                className={`btn btn-sm ${currentView === "admin" ? "btn-primary" : "btn-secondary"}`}
                onClick={() => {
                  setCurrentView("admin");
                  setMobileMenuOpen(false);
                }}
                style={{ flex: 1, borderColor: "var(--accent-copper)", color: currentView === "admin" ? undefined : "var(--accent-copper)" }}
              >
                <ShieldAlert size={14} />
                <span>Admin</span>
              </button>
            )}

            {!user && (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={() => {
                  setCurrentView("auth");
                  setMobileMenuOpen(false);
                }}
                style={{ flex: 1 }}
              >
                Sign In
              </button>
            )}
          </div>
        </div>
      )}
    </header>
  );
}
