"use client";

import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import {
  Brain,
  FileSearch,
  MessageSquareText,
  ShieldCheck,
  Sparkles,
  ArrowRight,
  BookOpen,
  Zap,
  Globe,
} from "lucide-react";

export default function LandingPage() {
  const { isAuthenticated } = useAuth();

  return (
    <div style={{ minHeight: "100vh" }}>
      {/* ── Navigation ──────────────────────────── */}
      <nav
        style={{
          position: "fixed",
          top: 0,
          left: 0,
          right: 0,
          zIndex: 50,
          padding: "16px 32px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          background: "rgba(10, 10, 15, 0.8)",
          backdropFilter: "blur(20px)",
          borderBottom: "1px solid var(--border-subtle)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <Brain size={28} style={{ color: "var(--accent-primary)" }} />
          <span
            style={{
              fontSize: "20px",
              fontWeight: 700,
              letterSpacing: "-0.02em",
            }}
            className="gradient-text"
          >
            AI Research Assistant
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <Link href="/login" className="btn btn-ghost">
            Sign In
          </Link>
          <Link href="/workspace" className="btn btn-primary">
            Open Workspace <ArrowRight size={16} />
          </Link>
        </div>
      </nav>

      {/* ── Hero Section ────────────────────────── */}
      <section
        style={{
          minHeight: "100vh",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          textAlign: "center",
          padding: "120px 24px 80px",
          position: "relative",
        }}
      >
        {/* Decorative orbs */}
        <div
          style={{
            position: "absolute",
            width: "400px",
            height: "400px",
            borderRadius: "50%",
            background:
              "radial-gradient(circle, rgba(124, 92, 252, 0.15) 0%, transparent 70%)",
            top: "10%",
            left: "10%",
            filter: "blur(60px)",
          }}
          className="animate-float"
        />
        <div
          style={{
            position: "absolute",
            width: "300px",
            height: "300px",
            borderRadius: "50%",
            background:
              "radial-gradient(circle, rgba(92, 225, 230, 0.12) 0%, transparent 70%)",
            bottom: "20%",
            right: "15%",
            filter: "blur(60px)",
          }}
          className="animate-float stagger-3"
        />

        <div
          className="animate-fade-in-up"
          style={{
            position: "relative",
            zIndex: 1,
            maxWidth: "800px",
          }}
        >
          <div
            className="badge badge-accent"
            style={{ marginBottom: "24px", fontSize: "13px" }}
          >
            <Sparkles size={14} /> Powered by RAG + LLM + MCP
          </div>

          <h1
            style={{
              fontSize: "clamp(2.5rem, 5vw, 4rem)",
              fontWeight: 800,
              lineHeight: 1.1,
              letterSpacing: "-0.03em",
              marginBottom: "24px",
            }}
          >
            Research smarter with{" "}
            <span className="gradient-text">AI-powered</span> document analysis
          </h1>

          <p
            style={{
              fontSize: "18px",
              color: "var(--text-secondary)",
              maxWidth: "600px",
              margin: "0 auto 40px",
              lineHeight: 1.6,
            }}
          >
            Upload your documents, ask questions in natural language, and receive
            cited, trustworthy answers grounded in your actual sources.
          </p>

          <div style={{ display: "flex", gap: "16px", justifyContent: "center" }}>
            <Link
              href={isAuthenticated ? "/workspace" : "/register"}
              className="btn btn-primary btn-lg animate-pulse-glow"
            >
              Start Researching <ArrowRight size={18} />
            </Link>
            <Link
              href="#features"
              className="btn btn-secondary btn-lg"
            >
              Learn More
            </Link>
          </div>
        </div>
      </section>

      {/* ── Features Section ────────────────────── */}
      <section
        id="features"
        style={{
          padding: "100px 24px",
          maxWidth: "1200px",
          margin: "0 auto",
        }}
      >
        <div
          style={{ textAlign: "center", marginBottom: "64px" }}
          className="animate-fade-in-up"
        >
          <h2
            style={{
              fontSize: "2.2rem",
              fontWeight: 700,
              marginBottom: "16px",
              letterSpacing: "-0.02em",
            }}
          >
            Everything you need for{" "}
            <span className="gradient-text">deep research</span>
          </h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "16px" }}>
            A complete research workflow, from document ingestion to cited
            answers.
          </p>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(300px, 1fr))",
            gap: "24px",
          }}
        >
          {[
            {
              icon: <FileSearch size={28} />,
              title: "Document Intelligence",
              desc: "Upload PDFs, text files, and web pages. Our RAG pipeline chunks, embeds, and indexes everything for instant retrieval.",
              color: "var(--accent-primary)",
            },
            {
              icon: <MessageSquareText size={28} />,
              title: "Conversational AI",
              desc: "Ask questions naturally. The AI synthesizes answers from your documents with precise citations and page references.",
              color: "var(--accent-secondary)",
            },
            {
              icon: <ShieldCheck size={28} />,
              title: "Cited & Trustworthy",
              desc: "Every answer traces back to source documents. See exactly which passages informed the response.",
              color: "var(--success)",
            },
            {
              icon: <BookOpen size={28} />,
              title: "Document Library",
              desc: "Manage your research corpus with upload tracking, status monitoring, and full-text search capabilities.",
              color: "#f59e0b",
            },
            {
              icon: <Zap size={28} />,
              title: "MCP Tool Integration",
              desc: "Extend the assistant with external tools and APIs through the Model Context Protocol for richer answers.",
              color: "#ec4899",
            },
            {
              icon: <Globe size={28} />,
              title: "Web Page Ingestion",
              desc: "Paste any public URL and the system automatically fetches, parses, and indexes the content.",
              color: "#06b6d4",
            },
          ].map((feature, i) => (
            <div
              key={i}
              className="glass-card animate-fade-in-up"
              style={{
                padding: "32px",
                animationDelay: `${i * 0.1}s`,
                opacity: 0,
              }}
            >
              <div
                style={{
                  width: "52px",
                  height: "52px",
                  borderRadius: "var(--radius-md)",
                  background: `${feature.color}15`,
                  border: `1px solid ${feature.color}30`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: feature.color,
                  marginBottom: "20px",
                }}
              >
                {feature.icon}
              </div>
              <h3
                style={{
                  fontSize: "18px",
                  fontWeight: 600,
                  marginBottom: "10px",
                }}
              >
                {feature.title}
              </h3>
              <p style={{ color: "var(--text-secondary)", fontSize: "14px", lineHeight: 1.6 }}>
                {feature.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* ── CTA Section ─────────────────────────── */}
      <section
        style={{
          padding: "80px 24px",
          textAlign: "center",
        }}
      >
        <div
          className="glass-card"
          style={{
            maxWidth: "700px",
            margin: "0 auto",
            padding: "60px 40px",
            background: "rgba(124, 92, 252, 0.05)",
            borderColor: "rgba(124, 92, 252, 0.15)",
          }}
        >
          <h2
            style={{
              fontSize: "1.8rem",
              fontWeight: 700,
              marginBottom: "16px",
            }}
          >
            Ready to supercharge your research?
          </h2>
          <p
            style={{
              color: "var(--text-secondary)",
              marginBottom: "32px",
              fontSize: "15px",
            }}
          >
            Join and start getting AI-powered answers grounded in your own
            documents.
          </p>
          <Link
            href={isAuthenticated ? "/workspace" : "/register"}
            className="btn btn-primary btn-lg"
          >
            Get Started Free <ArrowRight size={18} />
          </Link>
        </div>
      </section>

      {/* ── Footer ──────────────────────────────── */}
      <footer
        style={{
          padding: "32px",
          textAlign: "center",
          borderTop: "1px solid var(--border-subtle)",
          color: "var(--text-muted)",
          fontSize: "13px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px" }}>
          <Brain size={16} style={{ color: "var(--accent-primary)" }} />
          AI Research Assistant · Built with RAG + LLM + MCP
        </div>
      </footer>
    </div>
  );
}
