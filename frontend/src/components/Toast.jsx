import React from "react";
import { CheckCircle2, AlertTriangle, Info, X } from "lucide-react";

export function Toast({ toasts, onDismiss }) {
  if (!toasts || toasts.length === 0) return null;

  return (
    <div
      id="toast-container"
      style={{
        position: "fixed",
        bottom: "24px",
        right: "24px",
        zIndex: 9999,
        display: "flex",
        flexDirection: "column",
        gap: "10px",
        maxWidth: "400px"
      }}
    >
      {toasts.slice(-2).map((toast) => (
        <div
          key={toast.id}
          className={`toast-notification toast-${toast.type || "success"}`}
          style={{
            background: "#ffffff",
            borderRadius: "var(--radius-md)",
            padding: "0.9rem 1.25rem",
            boxShadow: "0 10px 25px -5px rgba(93, 146, 83, 0.25)",
            border: toast.type === "error" ? "2px solid #d46d25" : "2px solid #5d9253",
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
            color: "#182e14",
            animation: "toastIn 0.25s cubic-bezier(0.16, 1, 0.3, 1)"
          }}
        >
          {toast.type === "error" ? (
            <AlertTriangle size={18} color="#d46d25" style={{ flexShrink: 0 }} />
          ) : toast.type === "info" ? (
            <Info size={18} color="#5d9253" style={{ flexShrink: 0 }} />
          ) : (
            <CheckCircle2 size={18} color="#5d9253" style={{ flexShrink: 0 }} />
          )}
          <span style={{ fontSize: "0.875rem", fontWeight: 800, flex: 1, lineHeight: 1.4 }}>
            {toast.message}
          </span>
          <button
            type="button"
            onClick={() => onDismiss(toast.id)}
            style={{
              border: "none",
              background: "transparent",
              cursor: "pointer",
              color: "#496843",
              padding: "4px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              borderRadius: "4px"
            }}
            aria-label="Dismiss notification"
          >
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}
