import React, { useState } from "react";
import { User, Mail, Lock, ArrowLeft, AlertCircle, CheckCircle2 } from "lucide-react";
import { ApiClient } from "../api/client";

const apiClient = new ApiClient();

export function AuthView({ onAuthSuccess, onBackToLanding }) {
  const [isSignUp, setIsSignUp] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!email || !password) return;

    setIsLoading(true);
    setErrorMessage("");
    setSuccessMessage("");

    try {
      let authResponse;
      if (isSignUp) {
        authResponse = await apiClient.register({
          email,
          password,
          name: name.trim() || email.split("@")[0],
          activeDomain: "www.scheduleflow.io"
        });
        setSuccessMessage("Account created successfully! Logging you in...");
      } else {
        authResponse = await apiClient.login({ email, password });
        setSuccessMessage("Authenticated successfully!");
      }

      const { user, token } = authResponse;
      const userProfile = {
        id: user.id,
        name: user.name,
        email: user.email,
        token: token,
        activeDomain: user.activeDomain || "www.scheduleflow.io"
      };

      // Store authenticated credentials in browser storage
      localStorage.setItem("founderreach_token", token);
      localStorage.setItem("founderreach_user", JSON.stringify(userProfile));

      setTimeout(() => {
        setIsLoading(false);
        onAuthSuccess(userProfile);
      }, 400);
    } catch (err) {
      setIsLoading(false);
      setErrorMessage(err.message || "Authentication failed. Please verify your credentials.");
    }
  };

  const handleDemoSignIn = async () => {
    setIsLoading(true);
    setErrorMessage("");
    try {
      // Automatic quick demo credentials
      const demoEmail = "founder@demo.founderreach.ai";
      const demoPass = "demo123456";
      let authResponse;
      try {
        authResponse = await apiClient.login({ email: demoEmail, password: demoPass });
      } catch (loginErr) {
        // If demo user does not exist in db yet, create it
        authResponse = await apiClient.register({
          email: demoEmail,
          password: demoPass,
          name: "Founder Alex (Demo)",
          activeDomain: "www.scheduleflow.io"
        });
      }

      const { user, token } = authResponse;
      const userProfile = {
        id: user.id,
        name: user.name,
        email: user.email,
        token: token,
        activeDomain: user.activeDomain || "www.scheduleflow.io"
      };

      localStorage.setItem("founderreach_token", token);
      localStorage.setItem("founderreach_user", JSON.stringify(userProfile));

      setIsLoading(false);
      onAuthSuccess(userProfile);
    } catch (err) {
      setIsLoading(false);
      setErrorMessage("Demo sign-in error: " + err.message);
    }
  };

  return (
    <div
      style={{
        minHeight: "calc(100vh - 80px)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "2rem 1.5rem",
        position: "relative",
        zIndex: 10
      }}
    >
      <button
        type="button"
        onClick={onBackToLanding}
        className="btn btn-secondary btn-sm"
        style={{ marginBottom: "1.5rem", display: "inline-flex", alignItems: "center", gap: "0.4rem" }}
      >
        <ArrowLeft size={14} />
        <span>Back to FounderReach AI</span>
      </button>

      <div
        style={{
          width: "100%",
          maxWidth: "460px",
          background: "#ffffff",
          border: "2px solid var(--accent-green)",
          borderRadius: "var(--radius-xl)",
          padding: "2.5rem",
          boxShadow: "var(--shadow-lg)"
        }}
      >
        <div style={{ textAlign: "center", marginBottom: "1.75rem" }}>
          <div className="brand-logo-glow" style={{ margin: "0 auto 1rem auto", width: "44px", height: "44px", fontSize: "1.15rem" }}>
            FR
          </div>
          <h2 style={{ fontSize: "1.65rem", fontWeight: 800, color: "var(--text-main)", letterSpacing: "-0.025em" }}>
            {isSignUp ? "Create Founder Account" : "Sign in to Console"}
          </h2>
          <p style={{ fontSize: "0.9rem", color: "var(--text-muted)", marginTop: "0.35rem" }}>
            {isSignUp ? "Create your multi-tenant workspace profile" : "Secure JWT authentication & domain monitoring"}
          </p>
          <div style={{ marginTop: "0.75rem", padding: "0.45rem 0.75rem", background: "#fffce5", border: "1px solid var(--accent-copper)", borderRadius: "var(--radius-sm)", fontSize: "0.75rem", color: "var(--text-body)", fontWeight: 600 }}>
            PBKDF2 Password Hashing • Signed JWT Session • Multi-Tenant SQLite Database
          </div>
        </div>

        {/* Dynamic Alerts */}
        {errorMessage && (
          <div
            style={{
              padding: "0.75rem 1rem",
              background: "#fee2e2",
              border: "1.5px solid #ef4444",
              borderRadius: "var(--radius-md)",
              color: "#991b1b",
              fontSize: "0.85rem",
              fontWeight: 700,
              marginBottom: "1.25rem",
              display: "flex",
              alignItems: "center",
              gap: "0.5rem"
            }}
          >
            <AlertCircle size={16} />
            <span>{errorMessage}</span>
          </div>
        )}

        {successMessage && (
          <div
            style={{
              padding: "0.75rem 1rem",
              background: "#ecfdf5",
              border: "1.5px solid #10b981",
              borderRadius: "var(--radius-md)",
              color: "#065f46",
              fontSize: "0.85rem",
              fontWeight: 700,
              marginBottom: "1.25rem",
              display: "flex",
              alignItems: "center",
              gap: "0.5rem"
            }}
          >
            <CheckCircle2 size={16} />
            <span>{successMessage}</span>
          </div>
        )}

        {/* Tab Switcher */}
        <div style={{ display: "flex", background: "var(--bg-secondary)", borderRadius: "var(--radius-md)", padding: "0.25rem", marginBottom: "1.5rem", border: "1.5px solid var(--border-subtle)" }}>
          <button
            type="button"
            onClick={() => {
              setIsSignUp(false);
              setErrorMessage("");
            }}
            style={{
              flex: 1,
              padding: "0.6rem 0.75rem",
              border: "none",
              background: !isSignUp ? "var(--accent-green)" : "transparent",
              fontSize: "0.9rem",
              fontWeight: 800,
              color: !isSignUp ? "#ffffff" : "var(--text-muted)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              boxShadow: !isSignUp ? "0 2px 6px rgba(93, 146, 83, 0.25)" : "none",
              transition: "all 0.2s ease"
            }}
          >
            Log In
          </button>
          <button
            type="button"
            onClick={() => {
              setIsSignUp(true);
              setErrorMessage("");
            }}
            style={{
              flex: 1,
              padding: "0.6rem 0.75rem",
              border: "none",
              background: isSignUp ? "var(--accent-green)" : "transparent",
              fontSize: "0.9rem",
              fontWeight: 800,
              color: isSignUp ? "#ffffff" : "var(--text-muted)",
              borderRadius: "var(--radius-sm)",
              cursor: "pointer",
              boxShadow: isSignUp ? "0 2px 6px rgba(93, 146, 83, 0.25)" : "none",
              transition: "all 0.2s ease"
            }}
          >
            Create Account
          </button>
        </div>

        {/* Quick 1-Click Demo Log In Button */}
        <button
          type="button"
          onClick={handleDemoSignIn}
          disabled={isLoading}
          className="btn btn-secondary btn-sm"
          style={{ width: "100%", justifyContent: "center", padding: "0.65rem", marginBottom: "1.25rem", fontWeight: 800 }}
        >
          ⚡ Instant Demo Workspace (1-Click)
        </button>

        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", margin: "1rem 0" }}>
          <div style={{ flex: 1, height: "1px", background: "var(--border-subtle)" }}></div>
          <span style={{ fontSize: "0.75rem", color: "var(--text-dim)", textTransform: "uppercase" }}>or email credentials</span>
          <div style={{ flex: 1, height: "1px", background: "var(--border-subtle)" }}></div>
        </div>

        {/* Credentials Form */}
        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
          {isSignUp && (
            <div>
              <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "0.35rem" }}>
                Full Name
              </label>
              <div style={{ position: "relative" }}>
                <User size={15} style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)", color: "var(--text-dim)" }} />
                <input
                  type="text"
                  placeholder="Alex Rivers"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  style={{
                    width: "100%",
                    padding: "0.75rem 1rem 0.75rem 2.4rem",
                    borderRadius: "var(--radius-md)",
                    border: "1px solid var(--border-subtle)",
                    background: "var(--bg-input)",
                    color: "var(--text-main)",
                    fontSize: "0.9rem",
                    fontWeight: 600
                  }}
                  required
                />
              </div>
            </div>
          )}

          <div>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "0.35rem" }}>
              Work Email
            </label>
            <div style={{ position: "relative" }}>
              <Mail size={15} style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)", color: "var(--text-dim)" }} />
              <input
                type="email"
                placeholder="alex@startup.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                style={{
                  width: "100%",
                  padding: "0.75rem 1rem 0.75rem 2.4rem",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border-subtle)",
                  background: "var(--bg-input)",
                  color: "var(--text-main)",
                  fontSize: "0.9rem",
                  fontWeight: 600
                }}
                required
              />
            </div>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.8rem", fontWeight: 700, color: "var(--text-muted)", marginBottom: "0.35rem" }}>
              Password (min. 6 characters)
            </label>
            <div style={{ position: "relative" }}>
              <Lock size={15} style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)", color: "var(--text-dim)" }} />
              <input
                type="password"
                placeholder="••••••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                style={{
                  width: "100%",
                  padding: "0.75rem 1rem 0.75rem 2.4rem",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border-subtle)",
                  background: "var(--bg-input)",
                  color: "var(--text-main)",
                  fontSize: "0.9rem",
                  fontWeight: 600
                }}
                required
              />
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            disabled={isLoading}
            style={{ width: "100%", marginTop: "0.5rem" }}
          >
            {isLoading ? (
              <span>Authenticating...</span>
            ) : (
              <span>{isSignUp ? "Create Account & Access Console →" : "Sign In to Console →"}</span>
            )}
          </button>
        </form>

        <p style={{ textAlign: "center", fontSize: "0.75rem", color: "var(--text-dim)", marginTop: "1.5rem" }}>
          By signing in you agree to FounderReach AI's strict read-only boundary terms.
        </p>
      </div>
    </div>
  );
}
