"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { documentsApi } from "@/lib/api";
import type { Document, DocumentChunk } from "@/types";
import {
  ArrowLeft,
  Upload,
  Globe,
  FileText,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Clock,
  Hash,
  ExternalLink,
  Search,
  X,
  RotateCw,
  Layers,
  Copy,
  Check,
  GitCompare,
  Sparkles,
} from "lucide-react";

type FileTypeFilter = "all" | "pdf" | "text" | "url";
type StatusFilter = "all" | "indexed" | "processing" | "error";

export default function LibraryPage() {
  const router = useRouter();
  const { loading: authLoading, isAuthenticated } = useAuth();

  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [urlInput, setUrlInput] = useState("");
  const [ingesting, setIngesting] = useState(false);
  const [error, setError] = useState("");

  // Search & Filter state
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedQuery, setDebouncedQuery] = useState("");
  const [selectedType, setSelectedType] = useState<FileTypeFilter>("all");
  const [selectedStatus, setSelectedStatus] = useState<StatusFilter>("all");

  // Retry state
  const [retryingId, setRetryingId] = useState<string | null>(null);

  // Chunks Modal state
  const [selectedDocForChunks, setSelectedDocForChunks] = useState<Document | null>(null);
  const [chunks, setChunks] = useState<DocumentChunk[]>([]);
  const [chunksLoading, setChunksLoading] = useState(false);
  const [chunksError, setChunksError] = useState("");
  const [copiedChunkId, setCopiedChunkId] = useState<string | null>(null);

  // Phase 4: Multi-document selection for Compare & Research Reports
  const [selectedDocIds, setSelectedDocIds] = useState<string[]>([]);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  // Debounce search query changes
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedQuery(searchQuery);
    }, 250);
    return () => clearTimeout(handler);
  }, [searchQuery]);

  // Fetch documents with active filters
  const loadDocuments = useCallback(
    async (showSpinner = false) => {
      if (!isAuthenticated) return;
      if (showSpinner) setLoading(true);

      try {
        const result = await documentsApi.list({
          query: debouncedQuery.trim() || undefined,
          file_type: selectedType === "all" ? undefined : selectedType,
          status: selectedStatus === "all" ? undefined : selectedStatus,
        });
        setDocuments(result.items);
      } catch (err) {
        console.error("Failed to load documents:", err);
      } finally {
        if (showSpinner) setLoading(false);
      }
    },
    [isAuthenticated, debouncedQuery, selectedType, selectedStatus]
  );

  // Initial load and filter change trigger
  useEffect(() => {
    let active = true;
    if (isAuthenticated) {
      documentsApi
        .list({
          query: debouncedQuery.trim() || undefined,
          file_type: selectedType === "all" ? undefined : selectedType,
          status: selectedStatus === "all" ? undefined : selectedStatus,
        })
        .then((result) => {
          if (active) {
            setDocuments(result.items);
            setLoading(false);
          }
        })
        .catch((err) => {
          console.error("Failed to load documents:", err);
          if (active) {
            setLoading(false);
          }
        });
    }
    return () => {
      active = false;
    };
  }, [isAuthenticated, debouncedQuery, selectedType, selectedStatus]);

  // Real-time polling when any document is in pending or processing state
  useEffect(() => {
    if (!isAuthenticated) return;

    const hasActiveIngestion = documents.some(
      (doc) => doc.status === "pending" || doc.status === "processing"
    );

    if (!hasActiveIngestion) return;

    const intervalId = setInterval(() => {
      documentsApi
        .list({
          query: debouncedQuery.trim() || undefined,
          file_type: selectedType === "all" ? undefined : selectedType,
          status: selectedStatus === "all" ? undefined : selectedStatus,
        })
        .then((result) => {
          setDocuments(result.items);
        })
        .catch((err) => {
          console.error("Ingestion polling error:", err);
        });
    }, 3000);

    return () => clearInterval(intervalId);
  }, [isAuthenticated, documents, debouncedQuery, selectedType, selectedStatus]);

  // ESC key listener to close chunk viewer modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setSelectedDocForChunks(null);
      }
    };
    if (selectedDocForChunks) {
      window.addEventListener("keydown", handleKeyDown);
      return () => window.removeEventListener("keydown", handleKeyDown);
    }
  }, [selectedDocForChunks]);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setError("");
    setUploading(true);

    try {
      for (const file of Array.from(files)) {
        const doc = await documentsApi.upload(file);
        setDocuments((prev) => [doc, ...prev]);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleIngestUrl = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!urlInput.trim()) return;

    setError("");
    setIngesting(true);

    try {
      const doc = await documentsApi.ingestUrl(urlInput.trim());
      setDocuments((prev) => [doc, ...prev]);
      setUrlInput("");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "URL ingestion failed");
    } finally {
      setIngesting(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await documentsApi.delete(id);
      setDocuments((prev) => prev.filter((d) => d.id !== id));
      if (selectedDocForChunks?.id === id) {
        setSelectedDocForChunks(null);
      }
    } catch (err) {
      console.error("Delete failed:", err);
    }
  };

  const handleRetry = async (docId: string) => {
    setError("");
    setRetryingId(docId);
    try {
      const updatedDoc = await documentsApi.retry(docId);
      setDocuments((prev) =>
        prev.map((d) => (d.id === docId ? updatedDoc : d))
      );
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Retry failed");
    } finally {
      setRetryingId(null);
    }
  };

  const handleOpenChunks = async (doc: Document) => {
    setSelectedDocForChunks(doc);
    setChunksLoading(true);
    setChunksError("");
    setChunks([]);

    try {
      const chunkList = await documentsApi.getChunks(doc.id);
      setChunks(chunkList);
    } catch (err: unknown) {
      setChunksError(
        err instanceof Error ? err.message : "Failed to load document chunks"
      );
    } finally {
      setChunksLoading(false);
    }
  };

  const handleCopyChunk = (chunkId: string, content: string) => {
    navigator.clipboard.writeText(content);
    setCopiedChunkId(chunkId);
    setTimeout(() => {
      setCopiedChunkId(null);
    }, 2000);
  };

  const toggleSelectDoc = (id: string) => {
    setSelectedDocIds((prev) =>
      prev.includes(id) ? prev.filter((d) => d !== id) : [...prev, id]
    );
  };

  const handleLaunchCompare = () => {
    if (selectedDocIds.length < 2) return;
    router.push(`/workspace?action=compare&docs=${selectedDocIds.join(",")}`);
  };

  const handleLaunchReport = () => {
    if (selectedDocIds.length === 0) return;
    router.push(`/workspace?action=report&docs=${selectedDocIds.join(",")}`);
  };

  const statusConfig: Record<string, { icon: React.ReactNode; className: string }> = {
    indexed: {
      icon: <CheckCircle2 size={14} />,
      className: "badge-success",
    },
    pending: {
      icon: <Clock size={14} />,
      className: "badge-warning",
    },
    processing: {
      icon: <Loader2 size={14} className="animate-spin" style={{ animation: "spin 1s linear infinite" }} />,
      className: "badge-accent",
    },
    error: {
      icon: <AlertCircle size={14} />,
      className: "badge-error",
    },
  };

  if (authLoading || loading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div className="spinner spinner-lg" />
      </div>
    );
  }

  return (
    <div style={{ minHeight: "100vh", padding: "24px", maxWidth: "1050px", margin: "0 auto" }}>
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
          <h1 style={{ fontSize: "24px", fontWeight: 700 }}>Document Library</h1>
          <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>
            Upload, search, filter, and inspect your research sources
          </p>
        </div>
      </div>

      {/* Ingestion Section */}
      <div
        className="glass-card"
        style={{ padding: "24px", marginBottom: "24px" }}
      >
        <div
          style={{
            display: "flex",
            gap: "16px",
            flexWrap: "wrap",
            alignItems: "flex-end",
          }}
        >
          {/* File Upload */}
          <div style={{ flex: 1, minWidth: "200px" }}>
            <label
              style={{
                display: "block",
                fontSize: "13px",
                fontWeight: 500,
                color: "var(--text-secondary)",
                marginBottom: "6px",
              }}
            >
              Upload Files
            </label>
            <input
              ref={fileInputRef}
              id="file-upload"
              type="file"
              accept=".pdf,.txt,.md,.markdown,.docx,.csv"
              multiple
              onChange={handleFileUpload}
              style={{ display: "none" }}
            />
            <button
              className="btn btn-secondary"
              style={{ width: "100%" }}
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              {uploading ? (
                <>
                  <div className="spinner" /> Uploading...
                </>
              ) : (
                <>
                  <Upload size={16} /> Choose Files (PDF, TXT, MD, DOCX, CSV)
                </>
              )}
            </button>
          </div>

          {/* URL Ingestion */}
          <form
            onSubmit={handleIngestUrl}
            style={{ flex: 2, minWidth: "300px", display: "flex", gap: "8px" }}
          >
            <div style={{ flex: 1 }}>
              <label
                style={{
                  display: "block",
                  fontSize: "13px",
                  fontWeight: 500,
                  color: "var(--text-secondary)",
                  marginBottom: "6px",
                }}
              >
                Ingest Web Page
              </label>
              <input
                id="url-input"
                className="input"
                type="url"
                placeholder="https://example.com/article"
                value={urlInput}
                onChange={(e) => setUrlInput(e.target.value)}
              />
            </div>
            <button
              id="ingest-url-btn"
              type="submit"
              className="btn btn-primary"
              style={{ alignSelf: "flex-end" }}
              disabled={ingesting || !urlInput.trim()}
            >
              {ingesting ? (
                <div className="spinner" />
              ) : (
                <>
                  <Globe size={16} /> Ingest
                </>
              )}
            </button>
          </form>
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
              marginTop: "16px",
            }}
          >
            <AlertCircle size={16} />
            {error}
          </div>
        )}
      </div>

      {/* Search and Filters Bar */}
      <div
        className="glass-card"
        style={{
          padding: "16px 20px",
          marginBottom: "20px",
          display: "flex",
          flexDirection: "column",
          gap: "12px",
        }}
      >
        {/* Search Row */}
        <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
          <div style={{ position: "relative", flex: 1 }}>
            <Search
              size={16}
              style={{
                position: "absolute",
                left: "14px",
                top: "50%",
                transform: "translateY(-50%)",
                color: "var(--text-muted)",
              }}
            />
            <input
              id="library-search-input"
              className="input"
              style={{
                paddingLeft: "38px",
                paddingRight: searchQuery ? "36px" : "14px",
              }}
              type="text"
              placeholder="Search documents by title, filename, or URL..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery("")}
                style={{
                  position: "absolute",
                  right: "10px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "transparent",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                  padding: "4px",
                  borderRadius: "var(--radius-full)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
                title="Clear search"
              >
                <X size={14} />
              </button>
            )}
          </div>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => loadDocuments(false)}
            title="Refresh document list"
          >
            <RotateCw size={14} />
          </button>
        </div>

        {/* Filter Chips Row */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "12px",
            paddingTop: "6px",
            borderTop: "1px solid var(--border-subtle)",
          }}
        >
          {/* File Type Chips */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
            <span style={{ fontSize: "12px", color: "var(--text-muted)", marginRight: "4px" }}>
              Type:
            </span>
            {(
              [
                { id: "all", label: "All Types" },
                { id: "pdf", label: "PDFs" },
                { id: "text", label: "Text / MD" },
                { id: "url", label: "Web / URLs" },
              ] as const
            ).map((filter) => {
              const active = selectedType === filter.id;
              return (
                <button
                  key={filter.id}
                  onClick={() => setSelectedType(filter.id)}
                  style={{
                    padding: "4px 10px",
                    fontSize: "12px",
                    fontWeight: 500,
                    borderRadius: "var(--radius-full)",
                    border: `1px solid ${
                      active ? "var(--accent-primary)" : "var(--border-subtle)"
                    }`,
                    background: active
                      ? "var(--accent-primary)"
                      : "var(--surface-glass)",
                    color: active ? "#ffffff" : "var(--text-secondary)",
                    cursor: "pointer",
                    transition: "all var(--transition-fast)",
                  }}
                >
                  {filter.label}
                </button>
              );
            })}
          </div>

          {/* Status Chips */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px", flexWrap: "wrap" }}>
            <span style={{ fontSize: "12px", color: "var(--text-muted)", marginRight: "4px" }}>
              Status:
            </span>
            {(
              [
                { id: "all", label: "All" },
                { id: "indexed", label: "Indexed" },
                { id: "processing", label: "Processing" },
                { id: "error", label: "Failed" },
              ] as const
            ).map((filter) => {
              const active = selectedStatus === filter.id;
              return (
                <button
                  key={filter.id}
                  onClick={() => setSelectedStatus(filter.id)}
                  style={{
                    padding: "4px 10px",
                    fontSize: "12px",
                    fontWeight: 500,
                    borderRadius: "var(--radius-full)",
                    border: `1px solid ${
                      active ? "var(--accent-primary)" : "var(--border-subtle)"
                    }`,
                    background: active
                      ? "var(--accent-primary)"
                      : "var(--surface-glass)",
                    color: active ? "#ffffff" : "var(--text-secondary)",
                    cursor: "pointer",
                    transition: "all var(--transition-fast)",
                  }}
                >
                  {filter.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Document List */}
      {documents.length === 0 ? (
        <div
          className="glass-card"
          style={{
            padding: "60px 24px",
            textAlign: "center",
          }}
        >
          <FileText
            size={48}
            style={{ color: "var(--text-muted)", marginBottom: "16px" }}
          />
          <h3 style={{ fontSize: "18px", fontWeight: 600, marginBottom: "8px" }}>
            {searchQuery || selectedType !== "all" || selectedStatus !== "all"
              ? "No matching documents"
              : "No documents yet"}
          </h3>
          <p style={{ color: "var(--text-secondary)", fontSize: "14px" }}>
            {searchQuery || selectedType !== "all" || selectedStatus !== "all"
              ? "Try adjusting your search query or filter chips"
              : "Upload a file or ingest a URL to get started"}
          </p>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {documents.map((doc, idx) => {
            const isSelected = selectedDocIds.includes(doc.id);
            return (
            <div
              key={doc.id}
              className="glass-card animate-fade-in"
              style={{
                padding: "16px 20px",
                display: "flex",
                flexDirection: "column",
                gap: "10px",
                animationDelay: `${idx * 0.04}s`,
                border: isSelected
                  ? "1px solid var(--accent-primary)"
                  : undefined,
                background: isSelected
                  ? "rgba(124, 92, 252, 0.05)"
                  : undefined,
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "14px",
                }}
              >
                {/* Selection Checkbox */}
                <input
                  type="checkbox"
                  id={`select-doc-${doc.id}`}
                  checked={isSelected}
                  onChange={() => toggleSelectDoc(doc.id)}
                  disabled={doc.status !== "indexed"}
                  style={{
                    cursor: doc.status === "indexed" ? "pointer" : "not-allowed",
                    width: "16px",
                    height: "16px",
                    accentColor: "var(--accent-primary)",
                    flexShrink: 0,
                  }}
                  title={
                    doc.status === "indexed"
                      ? "Select for comparison or report"
                      : "Only indexed documents can be selected"
                  }
                />

                {/* Icon */}
                <div
                  style={{
                    width: "42px",
                    height: "42px",
                    borderRadius: "var(--radius-md)",
                    background:
                      doc.file_type === "url"
                        ? "rgba(6, 182, 212, 0.1)"
                        : doc.file_type === "pdf"
                        ? "rgba(248, 113, 113, 0.1)"
                        : "rgba(124, 92, 252, 0.1)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    flexShrink: 0,
                  }}
                >
                  {doc.file_type === "url" ? (
                    <Globe size={18} style={{ color: "#06b6d4" }} />
                  ) : (
                    <FileText
                      size={18}
                      style={{
                        color:
                          doc.file_type === "pdf"
                            ? "var(--error)"
                            : "var(--accent-primary)",
                      }}
                    />
                  )}
                </div>

                {/* Info */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      fontSize: "14px",
                      fontWeight: 600,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                    title={doc.filename}
                  >
                    {doc.filename}
                  </div>
                  <div
                    style={{
                      display: "flex",
                      alignItems: "center",
                      gap: "12px",
                      marginTop: "4px",
                      fontSize: "12px",
                      color: "var(--text-muted)",
                    }}
                  >
                    <span style={{ fontWeight: 600 }}>{doc.file_type.toUpperCase()}</span>
                    {doc.file_size && (
                      <span>{(doc.file_size / 1024).toFixed(0)} KB</span>
                    )}
                    <span style={{ display: "flex", alignItems: "center", gap: "3px" }}>
                      <Hash size={11} /> {doc.chunk_count} {doc.chunk_count === 1 ? "chunk" : "chunks"}
                    </span>
                  </div>
                </div>

                {/* Status Badge */}
                <span
                  className={`badge ${statusConfig[doc.status]?.className || ""}`}
                >
                  {statusConfig[doc.status]?.icon} {doc.status}
                </span>

                {/* Actions */}
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                  {/* Retry Button on Error */}
                  {doc.status === "error" && (
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => handleRetry(doc.id)}
                      disabled={retryingId === doc.id}
                      style={{
                        padding: "5px 10px",
                        fontSize: "12px",
                        gap: "6px",
                      }}
                      title="Retry ingestion"
                    >
                      <RotateCw
                        size={13}
                        className={retryingId === doc.id ? "animate-spin" : ""}
                        style={
                          retryingId === doc.id
                            ? { animation: "spin 1s linear infinite" }
                            : undefined
                        }
                      />
                      Retry
                    </button>
                  )}

                  {/* View Chunks Button */}
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => handleOpenChunks(doc)}
                    style={{
                      padding: "5px 10px",
                      fontSize: "12px",
                      gap: "6px",
                      color: "var(--text-secondary)",
                    }}
                    title="View extracted chunks and token stats"
                  >
                    <Layers size={14} />
                    View Chunks
                  </button>

                  {/* Source URL link */}
                  {doc.source_url && (
                    <a
                      href={doc.source_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-ghost btn-icon btn-sm"
                      title="Open source URL"
                    >
                      <ExternalLink size={14} />
                    </a>
                  )}

                  {/* Delete Button */}
                  <button
                    className="btn btn-ghost btn-icon btn-sm"
                    onClick={() => handleDelete(doc.id)}
                    title="Delete document"
                    style={{ color: "var(--text-muted)" }}
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              {/* Error Explanation Banner if status is error */}
              {doc.status === "error" && doc.error_message && (
                <div
                  style={{
                    display: "flex",
                    alignItems: "flex-start",
                    gap: "8px",
                    padding: "8px 12px",
                    background: "rgba(248, 113, 113, 0.08)",
                    border: "1px solid rgba(248, 113, 113, 0.2)",
                    borderRadius: "var(--radius-sm)",
                    color: "var(--error)",
                    fontSize: "12px",
                    lineHeight: "1.4",
                  }}
                >
                  <AlertCircle size={14} style={{ flexShrink: 0, marginTop: "2px" }} />
                  <div style={{ flex: 1 }}>
                    <strong>Ingestion error:</strong> {doc.error_message}
                  </div>
                </div>
              )}
            </div>
            );
          })}
        </div>
      )}

      {/* Floating Multi-Doc Action Bar */}
      {selectedDocIds.length > 0 && (
        <div
          id="library-floating-actions"
          style={{
            position: "fixed",
            bottom: "28px",
            left: "50%",
            transform: "translateX(-50%)",
            background: "rgba(18, 18, 26, 0.95)",
            backdropFilter: "blur(16px)",
            border: "1px solid var(--accent-primary)",
            boxShadow: "0 8px 32px rgba(0, 0, 0, 0.4), 0 0 16px rgba(124, 92, 252, 0.25)",
            borderRadius: "var(--radius-lg)",
            padding: "10px 20px",
            display: "flex",
            alignItems: "center",
            gap: "14px",
            zIndex: 100,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span
              style={{
                width: "22px",
                height: "22px",
                borderRadius: "50%",
                background: "var(--accent-primary)",
                color: "#fff",
                fontSize: "12px",
                fontWeight: 700,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              {selectedDocIds.length}
            </span>
            <span style={{ fontSize: "13px", fontWeight: 500, color: "var(--text-primary)" }}>
              {selectedDocIds.length === 1 ? "1 document selected" : `${selectedDocIds.length} documents selected`}
            </span>
          </div>

          <div style={{ height: "20px", width: "1px", background: "var(--border-subtle)" }} />

          <button
            id="lib-compare-btn"
            className="btn btn-primary btn-sm"
            onClick={handleLaunchCompare}
            disabled={selectedDocIds.length < 2}
            style={{
              gap: "6px",
              opacity: selectedDocIds.length < 2 ? 0.5 : 1,
              cursor: selectedDocIds.length < 2 ? "not-allowed" : "pointer",
            }}
            title={selectedDocIds.length < 2 ? "Select at least 2 documents to compare" : "Compare selected documents"}
          >
            <GitCompare size={14} />
            Compare {selectedDocIds.length >= 2 ? `(${selectedDocIds.length})` : "(Min 2)"}
          </button>

          <button
            id="lib-report-btn"
            className="btn btn-secondary btn-sm"
            onClick={handleLaunchReport}
            style={{ gap: "6px" }}
            title="Generate research report from selected documents"
          >
            <Sparkles size={14} />
            Generate Report
          </button>

          <button
            id="lib-clear-btn"
            className="btn btn-ghost btn-sm"
            onClick={() => setSelectedDocIds([])}
            style={{ fontSize: "12px", color: "var(--text-muted)" }}
          >
            Clear
          </button>
        </div>
      )}

      {/* ── View Chunks Modal ──────────────────────────────── */}
      {selectedDocForChunks && (
        <div
          role="dialog"
          aria-modal="true"
          onClick={() => setSelectedDocForChunks(null)}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 999,
            backgroundColor: "rgba(0, 0, 0, 0.7)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            style={{
              backgroundColor: "var(--bg-secondary)",
              border: "1px solid var(--border-default)",
              borderRadius: "var(--radius-lg)",
              width: "100%",
              maxWidth: "780px",
              maxHeight: "88vh",
              display: "flex",
              flexDirection: "column",
              boxShadow: "var(--shadow-lg)",
              overflow: "hidden",
            }}
          >
            {/* Modal Header */}
            <div
              style={{
                padding: "16px 20px",
                borderBottom: "1px solid var(--border-subtle)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "12px",
              }}
            >
              <div style={{ minWidth: 0, flex: 1 }}>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <h2
                    style={{
                      fontSize: "16px",
                      fontWeight: 600,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {selectedDocForChunks.filename}
                  </h2>
                  <span className="badge badge-accent" style={{ fontSize: "11px" }}>
                    Chunks ({chunks.length})
                  </span>
                </div>
                <p style={{ fontSize: "12px", color: "var(--text-muted)", marginTop: "2px" }}>
                  Extracted sections, token counts, and page metadata for vector search
                </p>
              </div>
              <button
                className="btn btn-ghost btn-icon btn-sm"
                onClick={() => setSelectedDocForChunks(null)}
                title="Close modal (Esc)"
              >
                <X size={18} />
              </button>
            </div>

            {/* Modal Content */}
            <div
              style={{
                padding: "20px",
                overflowY: "auto",
                flex: 1,
                display: "flex",
                flexDirection: "column",
                gap: "14px",
              }}
            >
              {chunksLoading ? (
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    padding: "48px 0",
                    gap: "12px",
                  }}
                >
                  <div className="spinner spinner-lg" />
                  <p style={{ fontSize: "13px", color: "var(--text-muted)" }}>
                    Loading chunks...
                  </p>
                </div>
              ) : chunksError ? (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "10px",
                    padding: "14px",
                    background: "rgba(248, 113, 113, 0.1)",
                    border: "1px solid rgba(248, 113, 113, 0.25)",
                    borderRadius: "var(--radius-md)",
                    color: "var(--error)",
                    fontSize: "13px",
                  }}
                >
                  <AlertCircle size={18} />
                  <span>{chunksError}</span>
                </div>
              ) : chunks.length === 0 ? (
                <div
                  style={{
                    textAlign: "center",
                    padding: "48px 0",
                    color: "var(--text-muted)",
                    fontSize: "14px",
                  }}
                >
                  No chunks extracted yet for this document.
                </div>
              ) : (
                chunks.map((chunk) => (
                  <div
                    key={chunk.id}
                    style={{
                      background: "var(--bg-tertiary)",
                      border: "1px solid var(--border-subtle)",
                      borderRadius: "var(--radius-md)",
                      padding: "14px",
                      display: "flex",
                      flexDirection: "column",
                      gap: "10px",
                    }}
                  >
                    {/* Chunk Meta Header */}
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "space-between",
                        flexWrap: "wrap",
                        gap: "8px",
                      }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span
                          className="badge"
                          style={{
                            background: "var(--bg-elevated)",
                            fontWeight: 600,
                            color: "var(--text-primary)",
                          }}
                        >
                          Chunk #{chunk.chunk_index + 1}
                        </span>
                        {chunk.page_number !== null && (
                          <span className="badge badge-accent">
                            Page {chunk.page_number}
                          </span>
                        )}
                        <span
                          style={{
                            fontSize: "11px",
                            color: "var(--text-muted)",
                          }}
                        >
                          ~{chunk.token_count} words
                        </span>
                      </div>

                      <button
                        className="btn btn-ghost btn-sm"
                        style={{ padding: "4px 8px", fontSize: "11px", gap: "4px" }}
                        onClick={() => handleCopyChunk(chunk.id, chunk.content)}
                        title="Copy chunk text"
                      >
                        {copiedChunkId === chunk.id ? (
                          <>
                            <Check size={12} style={{ color: "var(--success)" }} /> Copied
                          </>
                        ) : (
                          <>
                            <Copy size={12} /> Copy
                          </>
                        )}
                      </button>
                    </div>

                    {/* Chunk Content Text */}
                    <pre
                      style={{
                        background: "var(--bg-primary)",
                        padding: "12px",
                        borderRadius: "var(--radius-sm)",
                        border: "1px solid var(--border-subtle)",
                        fontSize: "13px",
                        lineHeight: "1.6",
                        color: "var(--text-primary)",
                        fontFamily: "var(--font-sans)",
                        whiteSpace: "pre-wrap",
                        wordBreak: "break-word",
                        maxHeight: "220px",
                        overflowY: "auto",
                      }}
                    >
                      {chunk.content}
                    </pre>
                  </div>
                ))
              )}
            </div>

            {/* Modal Footer */}
            <div
              style={{
                padding: "12px 20px",
                borderTop: "1px solid var(--border-subtle)",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                background: "var(--bg-primary)",
              }}
            >
              <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                Showing {chunks.length} total segments
              </span>
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setSelectedDocForChunks(null)}
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
