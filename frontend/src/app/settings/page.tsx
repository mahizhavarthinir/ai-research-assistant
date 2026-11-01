"use client";

import { useState, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { integrationsApi } from "@/lib/api";
import type { Integration, IntegrationsHealthResponse } from "@/types";
import {
  ArrowLeft,
  User,
  Mail,
  Shield,
  Calendar,
  LogOut,
  Cpu,
  Wrench,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
} from "lucide-react";

export default function SettingsPage() {
  const router = useRouter();
  const { user, loading: authLoading, isAuthenticated, logout } = useAuth();

  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [health, setHealth] = useState<IntegrationsHealthResponse | null>(null);
  const [loadingIntegrations, setLoadingIntegrations] = useState(true);
  const [integrationsError, setIntegrationsError] = useState<string | null>(null);

  const fetchIntegrations = useCallback(async () => {
    setLoadingIntegrations(true);
    setIntegrationsError(null);
    try {
      const [items, healthData] = await Promise.all([
        integrationsApi.list(),
        integrationsApi.health(),
      ]);
      setIntegrations(items);
      setHealth(healthData);
    } catch (err: unknown) {
      setIntegrationsError(
        err instanceof Error ? err.message : "Failed to load tools & integrations"
      );
    } finally {
      setLoadingIntegrations(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    if (isAuthenticated) {
      Promise.all([integrationsApi.list(), integrationsApi.health()])
        .then(([items, healthData]) => {
          if (active) {
            setIntegrations(items);
            setHealth(healthData);
            setLoadingIntegrations(false);
          }
        })
        .catch((err: unknown) => {
          if (active) {
            setIntegrationsError(
              err instanceof Error ? err.message : "Failed to load tools & integrations"
            );
            setLoadingIntegrations(false);
          }
        });
    }
    return () => {
      active = false;
    };
  }, [isAuthenticated]);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  const handleLogout = async () => {
    await logout();
    router.push("/");
  };

  if (authLoading || !user) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div className="spinner spinner-lg" />
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", padding: "24px", maxWidth: "700px", margin: "0 auto" }}>
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "16px",
          marginBottom: "32px",
        }}
      >
        <Link href="/workspace" className="btn btn-ghost btn-icon">
          <ArrowLeft size={18} />
        </Link>
        <div>
          <h1 style={{ fontSize: "24px", fontWeight: 700 }}>Settings</h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>
            Manage your account and preferences
          </p>
        </div>
      </div>

      {/* Profile Card */}
      <div
        className="glass-card animate-fade-in-up"
        style={{ padding: "32px", marginBottom: "24px" }}
      >
        <h2
          style={{
            fontSize: "16px",
            fontWeight: 600,
            marginBottom: "24px",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <User size={18} style={{ color: "var(--accent-primary)" }} />
          Profile
        </h2>

        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Avatar & Name */}
          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            <div
              style={{
                width: "56px",
                height: "56px",
                borderRadius: "50%",
                background: "var(--accent-gradient)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: "22px",
                fontWeight: 700,
                color: "white",
              }}
            >
              {user.username[0].toUpperCase()}
            </div>
            <div>
              <div style={{ fontSize: "18px", fontWeight: 600 }}>
                {user.full_name || user.username}
              </div>
              <div style={{ color: "var(--text-secondary)", fontSize: "14px" }}>
                @{user.username}
              </div>
            </div>
          </div>

          {/* Details */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "1fr 1fr",
              gap: "16px",
            }}
          >
            <div
              style={{
                padding: "14px 16px",
                background: "var(--bg-secondary)",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  fontSize: "12px",
                  color: "var(--text-muted)",
                  marginBottom: "4px",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                <Mail size={12} /> Email
              </div>
              <div style={{ fontSize: "14px" }}>{user.email}</div>
            </div>

            <div
              style={{
                padding: "14px 16px",
                background: "var(--bg-secondary)",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  fontSize: "12px",
                  color: "var(--text-muted)",
                  marginBottom: "4px",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                <Shield size={12} /> Role
              </div>
              <div style={{ fontSize: "14px" }}>
                <span className={`badge ${user.is_admin ? "badge-accent" : "badge-success"}`}>
                  {user.is_admin ? "Admin" : "Member"}
                </span>
              </div>
            </div>

            <div
              style={{
                padding: "14px 16px",
                background: "var(--bg-secondary)",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  fontSize: "12px",
                  color: "var(--text-muted)",
                  marginBottom: "4px",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                <Calendar size={12} /> Joined
              </div>
              <div style={{ fontSize: "14px" }}>
                {new Date(user.created_at).toLocaleDateString("en-US", {
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}
              </div>
            </div>

            <div
              style={{
                padding: "14px 16px",
                background: "var(--bg-secondary)",
                borderRadius: "var(--radius-md)",
                border: "1px solid var(--border-subtle)",
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  fontSize: "12px",
                  color: "var(--text-muted)",
                  marginBottom: "4px",
                  textTransform: "uppercase",
                  letterSpacing: "0.05em",
                }}
              >
                Status
              </div>
              <div style={{ fontSize: "14px" }}>
                <span className={`badge ${user.is_active ? "badge-success" : "badge-error"}`}>
                  {user.is_active ? "Active" : "Inactive"}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Active Tools & Integrations Card */}
      <div
        className="glass-card animate-fade-in-up stagger-1"
        style={{ padding: "32px", marginBottom: "24px" }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            marginBottom: "20px",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div>
            <h2
              style={{
                fontSize: "16px",
                fontWeight: 600,
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <Cpu size={18} style={{ color: "var(--accent-primary)" }} />
              Active Tools & Integrations
            </h2>
            <p style={{ color: "var(--text-secondary)", fontSize: "13px", marginTop: "4px" }}>
              Backend MCP and built-in research tools available for AI agent execution
            </p>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            {health && (
              <span
                className={`badge ${
                  health.status === "healthy" ? "badge-success" : "badge-warning"
                }`}
              >
                {health.status === "healthy" ? (
                  <CheckCircle2 size={12} style={{ marginRight: "4px" }} />
                ) : (
                  <AlertCircle size={12} style={{ marginRight: "4px" }} />
                )}
                {health.enabled_tools !== undefined
                  ? `${health.enabled_tools} Active`
                  : health.status}
              </span>
            )}
            <button
              onClick={fetchIntegrations}
              className="btn btn-ghost btn-sm"
              title="Refresh tool status"
              disabled={loadingIntegrations}
              style={{ padding: "6px" }}
            >
              <RefreshCw size={14} className={loadingIntegrations ? "spinner" : ""} />
            </button>
          </div>
        </div>

        {loadingIntegrations ? (
          <div style={{ padding: "32px", textAlign: "center" }}>
            <div className="spinner spinner-md" style={{ margin: "0 auto 12px" }} />
            <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>Checking registered tools...</p>
          </div>
        ) : integrationsError ? (
          <div
            style={{
              padding: "16px",
              background: "rgba(248, 113, 113, 0.1)",
              border: "1px solid rgba(248, 113, 113, 0.2)",
              borderRadius: "var(--radius-md)",
              display: "flex",
              alignItems: "center",
              gap: "10px",
              color: "var(--error)",
              fontSize: "13px",
            }}
          >
            <AlertCircle size={16} />
            <span>{integrationsError}</span>
          </div>
        ) : integrations.length === 0 ? (
          <div
            style={{
              padding: "24px",
              textAlign: "center",
              background: "var(--bg-secondary)",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--border-subtle)",
            }}
          >
            <p style={{ fontSize: "14px", color: "var(--text-muted)" }}>
              No tools or integrations currently registered on this backend.
            </p>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {integrations.map((item) => (
              <div
                key={item.id}
                style={{
                  padding: "14px 16px",
                  background: "var(--bg-secondary)",
                  borderRadius: "var(--radius-md)",
                  border: "1px solid var(--border-subtle)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  gap: "16px",
                }}
              >
                <div style={{ display: "flex", alignItems: "flex-start", gap: "12px", minWidth: 0 }}>
                  <div
                    style={{
                      width: "36px",
                      height: "36px",
                      borderRadius: "var(--radius-md)",
                      background: item.tool_type === "mcp" ? "rgba(99, 102, 241, 0.15)" : "rgba(16, 185, 129, 0.15)",
                      color: item.tool_type === "mcp" ? "var(--accent-primary)" : "var(--success)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                    }}
                  >
                    {item.tool_type === "mcp" ? <Cpu size={18} /> : <Wrench size={18} />}
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                      <span style={{ fontSize: "14px", fontWeight: 600, fontFamily: "var(--font-mono, monospace)" }}>
                        {item.name}
                      </span>
                      <span
                        style={{
                          fontSize: "11px",
                          padding: "1px 6px",
                          borderRadius: "4px",
                          background: "rgba(255, 255, 255, 0.06)",
                          border: "1px solid var(--border-subtle)",
                          color: "var(--text-muted)",
                          textTransform: "uppercase",
                          letterSpacing: "0.05em",
                        }}
                      >
                        {item.tool_type}
                      </span>
                    </div>
                    <p
                      style={{
                        fontSize: "12px",
                        color: "var(--text-secondary)",
                        marginTop: "3px",
                        lineHeight: 1.4,
                      }}
                    >
                      {item.description}
                    </p>
                  </div>
                </div>

                <div style={{ flexShrink: 0 }}>
                  <span className={`badge ${item.is_enabled ? "badge-success" : "badge-muted"}`}>
                    {item.is_enabled ? "Ready" : "Disabled"}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Danger Zone */}
      <div
        className="glass-card animate-fade-in-up stagger-2"
        style={{
          padding: "32px",
          borderColor: "rgba(248, 113, 113, 0.15)",
        }}
      >
        <h2
          style={{
            fontSize: "16px",
            fontWeight: 600,
            marginBottom: "16px",
            color: "var(--error)",
          }}
        >
          Account Actions
        </h2>
        <button className="btn btn-danger" onClick={handleLogout}>
          <LogOut size={16} /> Sign Out
        </button>
      </div>
    </div>
  );
}
