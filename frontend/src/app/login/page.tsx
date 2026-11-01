"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { Brain, Mail, Lock, ArrowRight, AlertCircle } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login(email, password);
      router.push("/workspace");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: "24px",
      }}
    >
      <div
        className="glass-card animate-fade-in-up"
        style={{
          width: "100%",
          maxWidth: "420px",
          padding: "40px",
        }}
      >
        <div style={{ textAlign: "center", marginBottom: "32px" }}>
          <div
            style={{
              width: "56px",
              height: "56px",
              borderRadius: "var(--radius-lg)",
              background: "rgba(124, 92, 252, 0.12)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              margin: "0 auto 16px",
            }}
          >
            <Brain size={28} style={{ color: "var(--accent-primary)" }} />
          </div>
          <h1 style={{ fontSize: "24px", fontWeight: 700, marginBottom: "6px" }}>
            Welcome back
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>
            Sign in to your research workspace
          </p>
        </div>

        {error && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              padding: "10px 14px",
              background: "rgba(248, 113, 113, 0.1)",
              border: "1px solid rgba(248, 113, 113, 0.2)",
              borderRadius: "var(--radius-md)",
              color: "var(--error)",
              fontSize: "13px",
              marginBottom: "20px",
            }}
          >
            <AlertCircle size={16} />
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "16px" }}>
            <label
              style={{
                display: "block",
                fontSize: "13px",
                color: "var(--text-secondary)",
                marginBottom: "6px",
                fontWeight: 500,
              }}
            >
              Email
            </label>
            <div style={{ position: "relative" }}>
              <Mail
                size={16}
                style={{
                  position: "absolute",
                  left: "12px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: "var(--text-muted)",
                }}
              />
              <input
                id="login-email"
                type="email"
                className="input"
                style={{ paddingLeft: "38px" }}
                placeholder="you@example.com"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
          </div>

          <div style={{ marginBottom: "24px" }}>
            <label
              style={{
                display: "block",
                fontSize: "13px",
                color: "var(--text-secondary)",
                marginBottom: "6px",
                fontWeight: 500,
              }}
            >
              Password
            </label>
            <div style={{ position: "relative" }}>
              <Lock
                size={16}
                style={{
                  position: "absolute",
                  left: "12px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  color: "var(--text-muted)",
                }}
              />
              <input
                id="login-password"
                type="password"
                className="input"
                style={{ paddingLeft: "38px" }}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
          </div>

          <button
            id="login-submit"
            type="submit"
            className="btn btn-primary"
            style={{ width: "100%", marginBottom: "16px" }}
            disabled={loading}
          >
            {loading ? (
              <div className="spinner" />
            ) : (
              <>
                Sign In <ArrowRight size={16} />
              </>
            )}
          </button>
        </form>

        <p
          style={{
            textAlign: "center",
            fontSize: "13px",
            color: "var(--text-tertiary)",
          }}
        >
          Don&apos;t have an account?{" "}
          <Link
            href="/register"
            style={{ color: "var(--accent-primary)", textDecoration: "none" }}
          >
            Create one
          </Link>
        </p>
      </div>
    </div>
  );
}
