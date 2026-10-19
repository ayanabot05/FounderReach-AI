import React, { useState } from "react";
import { User, Mail, Lock, ArrowLeft } from "lucide-react";

export function AuthView({ onAuthSuccess, onBackToLanding }) {
  const [isSignUp, setIsSignUp] = useState(false);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!email || !password) return;

    setIsLoading(true);
    setTimeout(() => {
      const user = {
        name: isSignUp ? (name || "Founder") : "Founder Alex",
        email: email,
        token: "tok_" + Math.random().toString(36).substring(2, 10),
        activeDomain: "www.scheduleflow.io"
      };
      localStorage.setItem("founderreach_user", JSON.stringify(user));
      setIsLoading(false);
      onAuthSuccess(user);
    }, 600);
  };

  const handleSocialAuth = (provider) => {
    setIsLoading(true);
    setTimeout(() => {
      const user = {
        name: provider === "Google" ? "Alex Rivers (Google)" : "alex-founder (GitHub)",
        email: `alex@${provider.toLowerCase()}.user`,
        provider: provider,
        token: "tok_" + Math.random().toString(36).substring(2, 10),
        activeDomain: "www.scheduleflow.io"
      };
      localStorage.setItem("founderreach_user", JSON.stringify(user));
      setIsLoading(false);
      onAuthSuccess(user);
    }, 600);
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
          maxWidth: "440px",
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
            {isSignUp ? "Create your local workspace profile" : "Local demo workspace session for founders"}
          </p>
          <div style={{ marginTop: "0.75rem", padding: "0.45rem 0.75rem", background: "#fffce5", border: "1px solid var(--accent-copper)", borderRadius: "var(--radius-sm)", fontSize: "0.75rem", color: "var(--text-body)", fontWeight: 600 }}>
            Local Demo Mode: Authenticates in browser storage. No server database or client passwords collected.
          </div>
        </div>

        {/* Tab Switcher */}
        <div style={{ display: "flex", background: "var(--bg-secondary)", borderRadius: "var(--radius-md)", padding: "0.25rem", marginBottom: "1.5rem", border: "1.5px solid var(--border-subtle)" }}>
          <button
            type="button"
            onClick={() => setIsSignUp(false)}
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
            onClick={() => setIsSignUp(true)}
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

        {/* Social Buttons */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.75rem", marginBottom: "1.25rem" }}>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => handleSocialAuth("Google")}
            style={{ justifyContent: "center", gap: "0.5rem", fontWeight: 700, padding: "0.65rem", background: "#ffffff" }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24">
              <path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.66-5.17 3.66-9.17z"/>
              <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.25v3.15C3.26 21.36 7.34 24 12 24z"/>
              <path fill="#FBBC05" d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.25C.45 8.18 0 9.99 0 12s.45 3.82 1.25 5.42l4.03-3.15z"/>
              <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.34 0 3.26 2.64 1.25 6.58l4.03 3.15c.95-2.83 3.6-4.98 6.72-4.98z"/>
            </svg>
            <span>Google</span>
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => handleSocialAuth("GitHub")}
            style={{ justifyContent: "center", gap: "0.5rem", fontWeight: 700, padding: "0.65rem", background: "#ffffff" }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor">
              <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z"/>
            </svg>
            <span>GitHub</span>
          </button>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", margin: "1.25rem 0" }}>
          <div style={{ flex: 1, height: "1px", background: "var(--border-subtle)" }}></div>
          <span style={{ fontSize: "0.8rem", color: "var(--text-dim)", textTransform: "uppercase" }}>or email</span>
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
              Password
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
              <span>{isSignUp ? "Create Founder Account →" : "Sign In to Console →"}</span>
            )}
          </button>
        </form>

        <p style={{ textAlign: "center", fontSize: "0.75rem", color: "var(--text-dim)", marginTop: "1.5rem" }}>
          By signing in you agree to FounderReach AI's strict read-only boundary terms. We never collect client passwords.
        </p>
      </div>
    </div>
  );
}
