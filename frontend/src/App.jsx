import React, { useState, useEffect } from "react";
import { ThreeCanvas } from "./components/ThreeCanvas";
import { Navbar } from "./components/Navbar";
import { Toast } from "./components/Toast";
import { LandingView } from "./views/LandingView";
import { AuthView } from "./views/AuthView";
import { DashboardView } from "./views/DashboardView";
import { ApiClient } from "./api/client";

const apiClient = new ApiClient();

export function App() {
  const [currentView, setCurrentView] = useState("landing");
  const [domain, setDomain] = useState("www.scheduleflow.io");
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem("founderreach_user");
      return stored ? JSON.parse(stored) : null;
    } catch (e) {
      return null;
    }
  });

  const [auditData, setAuditData] = useState(null);
  const [isAuditing, setIsAuditing] = useState(false);
  const [activeScriptTab, setActiveScriptTab] = useState("jsonld");
  const [pulseTrigger, setPulseTrigger] = useState(0);
  const [toasts, setToasts] = useState([]);

  const addToast = (message, type = "success") => {
    const id = Date.now() + Math.random();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3800);
  };

  const removeToast = (id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const runAudit = async (targetDomain, showToast = true) => {
    const clean = (targetDomain || domain).trim().replace(/^https?:\/\//i, "").replace(/\/$/, "");
    if (!clean) return;

    setIsAuditing(true);
    setPulseTrigger((p) => p + 1);
    if (showToast) addToast(`Agent inspecting ${clean}...`, "info");

    try {
      const brand = clean.replace(/^www\./i, "").split(".")[0];
      const capitalized = brand.charAt(0).toUpperCase() + brand.slice(1);

      const result = await apiClient.auditWebsite({
        url: `https://${clean}`,
        businessName: capitalized,
        description: "",
        targetAudience: "",
        painPoint: ""
      });

      setAuditData(result);
      setPulseTrigger((p) => p + 1);
      if (showToast) addToast(`Live audit completed for ${clean}!`, "success");
    } catch (err) {
      console.error("Audit error:", err);
      if (showToast) addToast("Inspection failed: " + (err.message || "Network error"), "error");
    } finally {
      setIsAuditing(false);
    }
  };

  // Do not perform live network audits on mount; audits are explicitly initiated by the user

  const handleCopyScript = (code) => {
    navigator.clipboard.writeText(code).then(() => {
      addToast("Deployment script copied to clipboard!", "success");
    }).catch(() => {
      addToast("Failed to copy script", "error");
    });
  };

  const handleCopyPlaybook = (playbook) => {
    navigator.clipboard.writeText(playbook).then(() => {
      addToast("Acquisition playbook copied to clipboard!", "success");
    }).catch(() => {
      addToast("Failed to copy playbook", "error");
    });
  };

  const handleAuthSuccess = (authenticatedUser) => {
    setUser(authenticatedUser);
    addToast(`Welcome back, ${authenticatedUser.name}!`, "success");
    setCurrentView("dashboard");
  };

  return (
    <div className="app-root">
      {/* 3D Spatial Network Canvas (Main Verse) */}
      <ThreeCanvas pulseTrigger={pulseTrigger} />

      {/* Persistent Navigation */}
      <Navbar
        currentView={currentView}
        setCurrentView={setCurrentView}
        user={user}
        setUser={setUser}
        onTryDemo={() => {
          setDomain("www.scheduleflow.io");
          runAudit("www.scheduleflow.io");
        }}
      />

      {/* Main Routed View */}
      {currentView === "landing" && (
        <LandingView
          domain={domain}
          setDomain={(d) => {
            setDomain(d);
            setPulseTrigger((p) => p + 1);
          }}
          onRunAudit={runAudit}
          isAuditing={isAuditing}
          auditData={auditData}
          activeScriptTab={activeScriptTab}
          setActiveScriptTab={setActiveScriptTab}
          onCopyScript={handleCopyScript}
          onCopyPlaybook={handleCopyPlaybook}
        />
      )}

      {currentView === "auth" && (
        <AuthView
          onAuthSuccess={handleAuthSuccess}
          onBackToLanding={() => setCurrentView("landing")}
        />
      )}

      {currentView === "dashboard" && (
        <DashboardView
          domain={domain}
          setDomain={(d) => {
            setDomain(d);
            setPulseTrigger((p) => p + 1);
          }}
          auditData={auditData}
          onRunAudit={runAudit}
          isAuditing={isAuditing}
          onCopyPlaybook={handleCopyPlaybook}
          onCopyScript={handleCopyScript}
        />
      )}

      {/* Floating Notifications */}
      <Toast toasts={toasts} onDismiss={removeToast} />
    </div>
  );
}
