"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import {
  ArrowLeft,
  User,
  Mail,
  Shield,
  Calendar,
  LogOut,
} from "lucide-react";

export default function SettingsPage() {
  const router = useRouter();
  const { user, loading: authLoading, isAuthenticated, logout } = useAuth();

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
