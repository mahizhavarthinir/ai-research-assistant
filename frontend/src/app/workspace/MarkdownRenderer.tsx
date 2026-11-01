"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import React from "react";
import { Copy, Check } from "lucide-react";

interface MarkdownRendererProps {
  content: string;
  onCitationClick?: (citationIndex: number) => void;
}

function CodeBlockPre({ children }: { children?: React.ReactNode }) {
  const [copied, setCopied] = React.useState(false);

  const extractText = (node: React.ReactNode): string => {
    if (typeof node === "string") return node;
    if (typeof node === "number") return String(node);
    if (!node) return "";
    if (Array.isArray(node)) return node.map(extractText).join("");
    if (React.isValidElement(node)) {
      return extractText((node.props as { children?: React.ReactNode })?.children);
    }
    return "";
  };

  const handleCopy = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const text = extractText(children);
    if (text) {
      navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div
      style={{
        position: "relative",
        marginTop: "0.6em",
        marginBottom: "0.8em",
      }}
    >
      <button
        type="button"
        onClick={handleCopy}
        style={{
          position: "absolute",
          top: "8px",
          right: "8px",
          zIndex: 10,
          display: "inline-flex",
          alignItems: "center",
          gap: "4px",
          padding: "3px 8px",
          fontSize: "11px",
          fontWeight: 500,
          borderRadius: "var(--radius-sm)",
          background: "rgba(30, 30, 48, 0.85)",
          border: "1px solid var(--border-default)",
          color: copied ? "var(--success)" : "var(--text-secondary)",
          cursor: "pointer",
          backdropFilter: "blur(4px)",
          transition: "all 0.15s ease",
        }}
        title="Copy code to clipboard"
      >
        {copied ? (
          <>
            <Check size={12} style={{ color: "var(--success)" }} /> Copied
          </>
        ) : (
          <>
            <Copy size={12} /> Copy
          </>
        )}
      </button>
      <pre
        style={{
          background: "rgba(0, 0, 0, 0.45)",
          border: "1px solid var(--border-subtle)",
          borderRadius: "var(--radius-md)",
          padding: "16px",
          paddingTop: "28px",
          overflowX: "auto",
          fontSize: "0.88em",
          margin: 0,
        }}
      >
        {children}
      </pre>
    </div>
  );
}

/**
 * Renders markdown content with proper formatting:
 * headings, bold, italic, code blocks, lists, tables, links,
 * and interactive clickable citation badges.
 */
export default function MarkdownRenderer({ content, onCitationClick }: MarkdownRendererProps) {
  // Pre-process citation markers like [1], [2] to interactive anchor links [#cit-1], [#cit-2]
  // Protecting both fenced code blocks (```...```) and inline code (`...`)
  const processedContent = React.useMemo(() => {
    if (!content) return "";
    const parts = content.split(/(```[\s\S]*?```|`[^`]+`)/g);
    return parts
      .map((part) => {
        if (part.startsWith("`")) {
          return part;
        }
        return part.replace(/\[(\d+)\](?!\()/g, "[$1](#cit-$1)");
      })
      .join("");
  }, [content]);

  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        // Headings
        h1: ({ children }) => (
          <h1
            style={{
              fontSize: "1.5rem",
              fontWeight: 700,
              marginTop: "1.2em",
              marginBottom: "0.5em",
              lineHeight: 1.3,
            }}
          >
            {children}
          </h1>
        ),
        h2: ({ children }) => (
          <h2
            style={{
              fontSize: "1.25rem",
              fontWeight: 600,
              marginTop: "1em",
              marginBottom: "0.4em",
              lineHeight: 1.3,
              color: "var(--text-primary)",
            }}
          >
            {children}
          </h2>
        ),
        h3: ({ children }) => (
          <h3
            style={{
              fontSize: "1.1rem",
              fontWeight: 600,
              marginTop: "0.8em",
              marginBottom: "0.3em",
              lineHeight: 1.4,
            }}
          >
            {children}
          </h3>
        ),
        // Paragraphs
        p: ({ children }) => (
          <p
            style={{
              marginTop: "0.4em",
              marginBottom: "0.6em",
              lineHeight: 1.7,
            }}
          >
            {children}
          </p>
        ),
        // Lists
        ul: ({ children }) => (
          <ul
            style={{
              paddingLeft: "1.5em",
              marginTop: "0.3em",
              marginBottom: "0.6em",
            }}
          >
            {children}
          </ul>
        ),
        ol: ({ children }) => (
          <ol
            style={{
              paddingLeft: "1.5em",
              marginTop: "0.3em",
              marginBottom: "0.6em",
            }}
          >
            {children}
          </ol>
        ),
        li: ({ children }) => (
          <li style={{ marginBottom: "0.25em", lineHeight: 1.6 }}>{children}</li>
        ),
        // Code blocks
        code: ({ className, children, ...props }) => {
          const isInline = !className;
          if (isInline) {
            return (
              <code
                style={{
                  background: "rgba(124, 92, 252, 0.1)",
                  border: "1px solid rgba(124, 92, 252, 0.2)",
                  borderRadius: "4px",
                  padding: "2px 6px",
                  fontSize: "0.88em",
                  fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                  color: "var(--accent-secondary)",
                }}
                {...props}
              >
                {children}
              </code>
            );
          }
          return (
            <code
              className={className}
              style={{
                display: "block",
                fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
                fontSize: "0.85em",
                lineHeight: 1.6,
              }}
              {...props}
            >
              {children}
            </code>
          );
        },
        pre: CodeBlockPre,
        // Blockquotes
        blockquote: ({ children }) => (
          <blockquote
            style={{
              borderLeft: "3px solid var(--accent-primary)",
              paddingLeft: "16px",
              margin: "0.6em 0",
              color: "var(--text-secondary)",
              fontStyle: "italic",
            }}
          >
            {children}
          </blockquote>
        ),
        // Horizontal rule
        hr: () => (
          <hr
            style={{
              border: "none",
              borderTop: "1px solid var(--border-subtle)",
              margin: "1em 0",
            }}
          />
        ),
        // Links & Interactive Citations
        a: ({ href, children }) => {
          if (href && href.startsWith("#cit-")) {
            const citIndex = parseInt(href.replace("#cit-", ""), 10);
            return (
              <button
                type="button"
                className="citation-pill"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onCitationClick?.(citIndex);
                }}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: "1px 5px",
                  fontSize: "11px",
                  fontWeight: 600,
                  lineHeight: "16px",
                  borderRadius: "4px",
                  background: "rgba(124, 92, 252, 0.18)",
                  color: "var(--accent-secondary)",
                  border: "1px solid rgba(124, 92, 252, 0.35)",
                  cursor: "pointer",
                  margin: "0 2px",
                  verticalAlign: "baseline",
                  transition: "all 0.15s ease",
                }}
                title={`Jump to Source [${citIndex}]`}
              >
                [{citIndex}]
              </button>
            );
          }
          return (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              style={{
                color: "var(--accent-primary)",
                textDecoration: "underline",
                textUnderlineOffset: "2px",
              }}
            >
              {children}
            </a>
          );
        },
        // Tables
        table: ({ children }) => (
          <div style={{ overflowX: "auto", marginTop: "0.5em", marginBottom: "0.8em" }}>
            <table
              style={{
                borderCollapse: "collapse",
                width: "100%",
                fontSize: "0.9em",
              }}
            >
              {children}
            </table>
          </div>
        ),
        th: ({ children }) => (
          <th
            style={{
              border: "1px solid var(--border-subtle)",
              padding: "8px 12px",
              textAlign: "left",
              fontWeight: 600,
              background: "rgba(124, 92, 252, 0.08)",
            }}
          >
            {children}
          </th>
        ),
        td: ({ children }) => (
          <td
            style={{
              border: "1px solid var(--border-subtle)",
              padding: "8px 12px",
            }}
          >
            {children}
          </td>
        ),
        // Strong / em
        strong: ({ children }) => (
          <strong style={{ fontWeight: 600, color: "var(--text-primary)" }}>
            {children}
          </strong>
        ),
        em: ({ children }) => (
          <em style={{ fontStyle: "italic" }}>{children}</em>
        ),
      }}
    >
      {processedContent}
    </ReactMarkdown>
  );
}
