"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { Brain, Mail, Lock, User, ArrowRight, AlertCircle, UserCircle } from "lucide-react";

export default function RegisterPage() {
  const router = useRouter();
  const { register } = useAuth();

  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    setLoading(true);
    try {
      await register(email, username, password, fullName || undefined);
      router.push("/workspace");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
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
            Create your account
          </h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>
            Start your AI-powered research journey
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
          <div style={{ marginBottom: "14px" }}>
            <label
              style={{
                display: "block",
                fontSize: "13px",
                color: "var(--text-secondary)",
                marginBottom: "6px",
                fontWeight: 500,
              }}
            >
              Full Name <span style={{ color: "var(--text-muted)" }}>(optional)</span>
            </label>
            <div style={{ position: "relative" }}>
              <UserCircle
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
                id="register-fullname"
                type="text"
                className="input"
                style={{ paddingLeft: "38px" }}
                placeholder="John Doe"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
              />
            </div>
          </div>

          <div style={{ marginBottom: "14px" }}>
            <label
              style={{
                display: "block",
                fontSize: "13px",
                color: "var(--text-secondary)",
                marginBottom: "6px",
                fontWeight: 500,
              }}
            >
              Username
            </label>
            <div style={{ position: "relative" }}>
              <User
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
                id="register-username"
                type="text"
                className="input"
                style={{ paddingLeft: "38px" }}
                placeholder="johndoe"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                pattern="^[a-zA-Z0-9_]+$"
                minLength={3}
                required
              />
            </div>
          </div>

          <div style={{ marginBottom: "14px" }}>
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
                id="register-email"
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
                id="register-password"
                type="password"
                className="input"
                style={{ paddingLeft: "38px" }}
                placeholder="Min 8 characters"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={8}
                required
              />
            </div>
          </div>

          <button
            id="register-submit"
            type="submit"
            className="btn btn-primary"
            style={{ width: "100%", marginBottom: "16px" }}
            disabled={loading}
          >
            {loading ? (
              <div className="spinner" />
            ) : (
              <>
                Create Account <ArrowRight size={16} />
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
          Already have an account?{" "}
          <Link
            href="/login"
            style={{ color: "var(--accent-primary)", textDecoration: "none" }}
          >
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
