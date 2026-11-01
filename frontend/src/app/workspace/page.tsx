"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/hooks/useAuth";
import { chatApi, documentsApi, researchApi } from "@/lib/api";
import MarkdownRenderer from "./MarkdownRenderer";
import type {
  Conversation,
  Message,
  Citation,
  Document as LibraryDoc,
  DocumentCompareResponse,
  ResearchReportResponse,
} from "@/types";
import {
  Brain,
  Send,
  Plus,
  MessageSquare,
  Trash2,
  LogOut,
  FileText,
  Settings,
  Sparkles,
  BookOpen,
  ExternalLink,
  Menu,
  X,
  Filter,
  Search,
  Pencil,
  Check,
  Copy,
  RotateCw,
  Download,
  GitCompare,
  FileDown,
  Loader2,
} from "lucide-react";

export default function WorkspacePage() {
  const router = useRouter();
  const { user, loading: authLoading, logout, isAuthenticated } = useAuth();

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConvId, setActiveConvId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Document-scoped chat & citation interaction state
  const [documents, setDocuments] = useState<LibraryDoc[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [highlightedCitation, setHighlightedCitation] = useState<number | null>(null);

  // Phase 3 states: Search, Rename, Copy, Regenerate, Export
  const [searchConvQuery, setSearchConvQuery] = useState("");
  const [editingConvId, setEditingConvId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState("");
  const [copiedMessageId, setCopiedMessageId] = useState<string | null>(null);
  const [regenerating, setRegenerating] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [exportingFormat, setExportingFormat] = useState<string | null>(null);
  const [researchExportingFormat, setResearchExportingFormat] = useState<string | null>(null);

  // Phase 4 states: Research Suite (Multi-Doc Comparison & Research Report Generator)
  const [researchTab, setResearchTab] = useState<"compare" | "report">(() => {
    if (typeof window !== "undefined") {
      const action = new URLSearchParams(window.location.search).get("action");
      if (action === "compare" || action === "report") return action;
    }
    return "compare";
  });
  const [researchModalOpen, setResearchModalOpen] = useState(() => {
    if (typeof window !== "undefined") {
      const action = new URLSearchParams(window.location.search).get("action");
      return action === "compare" || action === "report";
    }
    return false;
  });
  const [selectedResearchDocIds, setSelectedResearchDocIds] = useState<string[]>(() => {
    if (typeof window !== "undefined") {
      const docs = new URLSearchParams(window.location.search).get("docs");
      if (docs) return docs.split(",").filter(Boolean);
    }
    return [];
  });
  const [researchTopic, setResearchTopic] = useState("");
  const [researchLoading, setResearchLoading] = useState(false);
  const [researchError, setResearchError] = useState("");
  const [compareResult, setCompareResult] = useState<DocumentCompareResponse | null>(null);
  const [reportResult, setReportResult] = useState<ResearchReportResponse | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const exportDropdownRef = useRef<HTMLDivElement>(null);

  // Redirect if not logged in
  useEffect(() => {
    if (!authLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [authLoading, isAuthenticated, router]);

  // Load conversations and available documents
  useEffect(() => {
    if (isAuthenticated) {
      chatApi.listConversations().then(setConversations).catch(console.error);
      documentsApi.list().then((res) => setDocuments(res.items)).catch(console.error);
    }
  }, [isAuthenticated]);

  // Handle URL query parameters from Library actions (e.g. /workspace?action=compare&docs=...)
  useEffect(() => {
    const timer = setTimeout(() => {
      if (typeof window !== "undefined") {
        const params = new URLSearchParams(window.location.search);
        const action = params.get("action");
        const docs = params.get("docs");
        if (action === "compare" || action === "report") {
          setResearchTab(action);
          setResearchModalOpen(true);
          if (docs) {
            setSelectedResearchDocIds(docs.split(",").filter(Boolean));
          }
        }
      }
    }, 50);
    return () => clearTimeout(timer);
  }, []);

  // Close export dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (
        exportDropdownRef.current &&
        !exportDropdownRef.current.contains(e.target as Node)
      ) {
        setExportOpen(false);
      }
    };
    if (exportOpen) {
      document.addEventListener("mousedown", handleClickOutside);
      return () => document.removeEventListener("mousedown", handleClickOutside);
    }
  }, [exportOpen]);

  const handleCitationClick = useCallback((citIdx: number) => {
    setHighlightedCitation(citIdx);
    const el = document.getElementById(`citation-${citIdx}`);
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
    setTimeout(() => {
      setHighlightedCitation((prev) => (prev === citIdx ? null : prev));
    }, 2500);
  }, []);

  // Load messages when active conversation changes
  useEffect(() => {
    let isCancelled = false;
    if (!activeConvId) {
      return;
    }

    chatApi
      .getConversation(activeConvId)
      .then((detail) => {
        if (!isCancelled) {
          setMessages(detail.messages);
        }
      })
      .catch(console.error);

    return () => {
      isCancelled = true;
    };
  }, [activeConvId]);

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || sending) return;

    const userMessage = input.trim();
    setInput("");
    setSending(true);

    // Optimistic UI: add user message immediately
    const tempUserMsg: Message = {
      id: `temp-${Date.now()}`,
      role: "user",
      content: userMessage,
      sequence_number: messages.length,
      citations: [],
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, tempUserMsg]);

    try {
      const response = await chatApi.sendMessage({
        message: userMessage,
        conversation_id: activeConvId || undefined,
        document_id: selectedDocId || undefined,
      });

      // If this was a new conversation, set it as active
      if (!activeConvId) {
        setActiveConvId(response.conversation_id);
        // Refresh conversation list
        chatApi.listConversations().then(setConversations).catch(console.error);
      }

      // Add assistant message
      const assistantMsg: Message = {
        id: response.message_id,
        role: "assistant",
        content: response.content,
        sequence_number: messages.length + 1,
        citations: response.citations,
        created_at: new Date().toISOString(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      console.error("Send failed:", err);
      // Remove optimistic message on error
      setMessages((prev) => prev.filter((m) => m.id !== tempUserMsg.id));
      setInput(userMessage);
    } finally {
      setSending(false);
      inputRef.current?.focus();
    }
  }, [input, sending, activeConvId, selectedDocId, messages.length]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const startNewChat = () => {
    setActiveConvId(null);
    setMessages([]);
    setInput("");
    setEditingConvId(null);
    inputRef.current?.focus();
  };

  const deleteConv = async (id: string) => {
    try {
      await chatApi.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (activeConvId === id) {
        setActiveConvId(null);
        setMessages([]);
      }
      if (editingConvId === id) {
        setEditingConvId(null);
      }
    } catch (err) {
      console.error("Delete failed:", err);
    }
  };

  // Conversation Rename Logic
  const handleStartRename = (convId: string, currentTitle: string) => {
    setEditingConvId(convId);
    setEditingTitle(currentTitle);
  };

  const handleSaveRename = async (convId: string) => {
    const cleanTitle = editingTitle.trim();
    if (!cleanTitle) return;

    try {
      const updated = await chatApi.updateConversation(convId, cleanTitle);
      setConversations((prev) =>
        prev.map((c) => (c.id === convId ? { ...c, title: updated.title } : c))
      );
      setEditingConvId(null);
    } catch (err) {
      console.error("Rename failed:", err);
    }
  };

  const handleCancelRename = () => {
    setEditingConvId(null);
    setEditingTitle("");
  };

  // Copy Message Content
  const handleCopyMessage = (messageId: string, content: string) => {
    navigator.clipboard.writeText(content);
    setCopiedMessageId(messageId);
    setTimeout(() => {
      setCopiedMessageId(null);
    }, 2000);
  };

  // Regenerate latest response
  const handleRegenerate = async () => {
    if (!activeConvId || regenerating || sending) return;

    setRegenerating(true);
    try {
      const response = await chatApi.regenerate(
        activeConvId,
        selectedDocId || undefined
      );

      // Replace the last assistant message with regenerated response
      setMessages((prev) => {
        const newMsgs = [...prev];
        let lastAssistIdx = -1;
        for (let i = newMsgs.length - 1; i >= 0; i--) {
          if (newMsgs[i].role === "assistant") {
            lastAssistIdx = i;
            break;
          }
        }

        if (lastAssistIdx !== -1) {
          newMsgs[lastAssistIdx] = {
            id: response.message_id,
            role: "assistant",
            content: response.content,
            sequence_number: newMsgs[lastAssistIdx].sequence_number,
            citations: response.citations,
            created_at: new Date().toISOString(),
          };
        }
        return newMsgs;
      });
    } catch (err) {
      console.error("Regenerate failed:", err);
    } finally {
      setRegenerating(false);
    }
  };

  // Export conversation as PDF, Word (.docx), Markdown, or JSON
  const handleExport = async (format: "pdf" | "docx" | "markdown" | "json") => {
    if (!activeConvId) {
      console.warn("handleExport: no activeConvId");
      return;
    }
    setExportingFormat(format);
    setExportOpen(false);

    try {
      console.log(`[Export] Fetching ${format} export for ${activeConvId}...`);
      const blob = await chatApi.exportConversation(activeConvId, format);
      console.log(`[Export] Received blob of size: ${blob.size}`);
      const activeConv = conversations.find((c) => c.id === activeConvId);
      const safeTitle =
        (activeConv?.title || "conversation")
          .replace(/[^a-zA-Z0-9_\- ]/g, "")
          .trim()
          .replace(/\s+/g, "_")
          .slice(0, 40) || "conversation";

      const extMap: Record<string, string> = {
        pdf: "pdf",
        docx: "docx",
        markdown: "md",
        json: "json",
      };
      const ext = extMap[format] || format;

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${safeTitle}.${ext}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 2000);
      console.log(`[Export] Triggered download for: ${a.download}`);
    } catch (err) {
      console.error("Export error:", err);
      alert(err instanceof Error ? err.message : "Failed to export conversation");
    } finally {
      setExportingFormat(null);
    }
  };

  const handleLogout = async () => {
    await logout();
    router.push("/");
  };

  // Phase 4: Research Suite Handlers
  const toggleResearchDocSelection = (docId: string) => {
    setSelectedResearchDocIds((prev) =>
      prev.includes(docId) ? prev.filter((id) => id !== docId) : [...prev, docId]
    );
  };

  const handleSelectAllIndexedDocs = () => {
    const indexed = documents.filter((d) => d.status === "indexed").map((d) => d.id);
    if (selectedResearchDocIds.length === indexed.length && indexed.length > 0) {
      setSelectedResearchDocIds([]);
    } else {
      setSelectedResearchDocIds(indexed);
    }
  };

  const handleRunCompare = async () => {
    if (selectedResearchDocIds.length < 2) {
      setResearchError("Please select at least 2 documents to compare.");
      return;
    }
    setResearchLoading(true);
    setResearchError("");
    try {
      const res = await researchApi.compareDocuments({
        document_ids: selectedResearchDocIds,
        topic: researchTopic.trim() || undefined,
        conversation_id: activeConvId || undefined,
      });
      setCompareResult(res);
      chatApi.listConversations().then(setConversations).catch(console.error);
    } catch (err: unknown) {
      setResearchError(err instanceof Error ? err.message : "Document comparison failed");
    } finally {
      setResearchLoading(false);
    }
  };

  const handleRunReport = async () => {
    if (!researchTopic.trim()) {
      setResearchError("Please enter a research topic or question.");
      return;
    }
    setResearchLoading(true);
    setResearchError("");
    try {
      const res = await researchApi.generateReport({
        document_ids: selectedResearchDocIds.length > 0 ? selectedResearchDocIds : undefined,
        topic: researchTopic.trim(),
        conversation_id: activeConvId || undefined,
      });
      setReportResult(res);
      chatApi.listConversations().then(setConversations).catch(console.error);
    } catch (err: unknown) {
      setResearchError(err instanceof Error ? err.message : "Report generation failed");
    } finally {
      setResearchLoading(false);
    }
  };

  const handleExportResearch = async (
    data: DocumentCompareResponse | ResearchReportResponse,
    format: "pdf" | "docx" | "markdown" | "json"
  ) => {
    setResearchExportingFormat(format);
    try {
      const blob = await researchApi.exportContent(
        data as unknown as Record<string, unknown>,
        format
      );
      const safeTitle = (data.title || "research_report")
        .replace(/[^a-zA-Z0-9_\- ]/g, "")
        .trim()
        .replace(/\s+/g, "_")
        .slice(0, 40) || "research_report";

      const extMap: Record<string, string> = {
        pdf: "pdf",
        docx: "docx",
        markdown: "md",
        json: "json",
      };
      const ext = extMap[format] || format;

      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${safeTitle}.${ext}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch (err) {
      console.error("Research export error:", err);
      alert(err instanceof Error ? err.message : "Failed to export research document");
    } finally {
      setResearchExportingFormat(null);
    }
  };

  // Filter conversations by title search
  const filteredConversations = conversations.filter((c) =>
    c.title.toLowerCase().includes(searchConvQuery.toLowerCase().trim())
  );

  // Find index of last assistant message for regenerate button
  let lastAssistantIndex = -1;
  for (let i = messages.length - 1; i >= 0; i--) {
    if (messages[i].role === "assistant") {
      lastAssistantIndex = i;
      break;
    }
  }

  if (authLoading) {
    return (
      <div style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div className="spinner spinner-lg" />
      </div>
    );
  }

  return (
    <div style={{ display: "flex", height: "100vh", overflow: "hidden" }}>
      {/* ── Sidebar ──────────────────────────────── */}
      <aside
        style={{
          width: sidebarOpen ? "280px" : "0px",
          minWidth: sidebarOpen ? "280px" : "0px",
          background: "var(--bg-secondary)",
          borderRight: "1px solid var(--border-subtle)",
          display: "flex",
          flexDirection: "column",
          transition: "all var(--transition-base)",
          overflow: "hidden",
        }}
      >
        {/* Sidebar Header */}
        <div
          style={{
            padding: "16px",
            borderBottom: "1px solid var(--border-subtle)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
            <Brain size={22} style={{ color: "var(--accent-primary)" }} />
            <span style={{ fontSize: "15px", fontWeight: 600 }} className="gradient-text">
              Research Assistant
            </span>
          </div>

          <button
            id="new-chat-btn"
            className="btn btn-secondary"
            style={{ width: "100%", fontSize: "13px", marginBottom: "12px" }}
            onClick={startNewChat}
          >
            <Plus size={16} /> New Chat
          </button>

          {/* Search Conversations Input */}
          <div style={{ position: "relative" }}>
            <Search
              size={13}
              style={{
                position: "absolute",
                left: "10px",
                top: "50%",
                transform: "translateY(-50%)",
                color: "var(--text-muted)",
              }}
            />
            <input
              id="search-chats-input"
              className="input"
              type="text"
              placeholder="Search chats..."
              value={searchConvQuery}
              onChange={(e) => setSearchConvQuery(e.target.value)}
              style={{
                paddingLeft: "28px",
                paddingRight: searchConvQuery ? "26px" : "10px",
                paddingTop: "5px",
                paddingBottom: "5px",
                fontSize: "12px",
                height: "30px",
                borderRadius: "var(--radius-sm)",
              }}
            />
            {searchConvQuery && (
              <button
                type="button"
                onClick={() => setSearchConvQuery("")}
                style={{
                  position: "absolute",
                  right: "6px",
                  top: "50%",
                  transform: "translateY(-50%)",
                  background: "transparent",
                  border: "none",
                  color: "var(--text-muted)",
                  cursor: "pointer",
                  padding: "2px",
                  display: "flex",
                  alignItems: "center",
                }}
                title="Clear search"
              >
                <X size={12} />
              </button>
            )}
          </div>
        </div>

        {/* Conversation List */}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "8px",
          }}
        >
          {filteredConversations.length === 0 ? (
            <div
              style={{
                padding: "24px 16px",
                textAlign: "center",
                color: "var(--text-muted)",
                fontSize: "13px",
              }}
            >
              {searchConvQuery ? "No matching chats" : "No conversations yet"}
            </div>
          ) : (
            filteredConversations.map((conv) => {
              const isEditing = editingConvId === conv.id;
              const isActive = activeConvId === conv.id;

              return (
                <div
                  key={conv.id}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    padding: "8px 10px",
                    borderRadius: "var(--radius-md)",
                    cursor: isEditing ? "default" : "pointer",
                    background: isActive
                      ? "var(--surface-glass-active)"
                      : "transparent",
                    transition: "background var(--transition-fast)",
                    marginBottom: "2px",
                  }}
                  onClick={() => {
                    if (!isEditing) setActiveConvId(conv.id);
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive && !isEditing)
                      (e.currentTarget as HTMLDivElement).style.background =
                        "var(--surface-glass-hover)";
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive && !isEditing)
                      (e.currentTarget as HTMLDivElement).style.background =
                        "transparent";
                  }}
                >
                  <MessageSquare
                    size={14}
                    style={{ color: "var(--text-muted)", flexShrink: 0 }}
                  />

                  {isEditing ? (
                    <div
                      style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "4px",
                        flex: 1,
                        minWidth: 0,
                      }}
                      onClick={(e) => e.stopPropagation()}
                    >
                      <input
                        autoFocus
                        value={editingTitle}
                        onChange={(e) => setEditingTitle(e.target.value)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleSaveRename(conv.id);
                          if (e.key === "Escape") handleCancelRename();
                        }}
                        className="input"
                        style={{
                          fontSize: "12px",
                          padding: "3px 6px",
                          height: "26px",
                          flex: 1,
                        }}
                      />
                      <button
                        className="btn-icon btn-ghost"
                        style={{ padding: "4px", color: "var(--success)" }}
                        onClick={() => handleSaveRename(conv.id)}
                        title="Save rename (Enter)"
                      >
                        <Check size={13} />
                      </button>
                      <button
                        className="btn-icon btn-ghost"
                        style={{ padding: "4px", color: "var(--text-muted)" }}
                        onClick={handleCancelRename}
                        title="Cancel (Esc)"
                      >
                        <X size={13} />
                      </button>
                    </div>
                  ) : (
                    <>
                      <span
                        style={{
                          flex: 1,
                          fontSize: "13px",
                          color: isActive
                            ? "var(--text-primary)"
                            : "var(--text-secondary)",
                          overflow: "hidden",
                          textOverflow: "ellipsis",
                          whiteSpace: "nowrap",
                        }}
                        title={conv.title}
                      >
                        {conv.title}
                      </span>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "2px",
                          flexShrink: 0,
                        }}
                      >
                        <button
                          className="btn-icon btn-ghost"
                          style={{
                            padding: "4px",
                            opacity: isActive ? 0.8 : 0.4,
                          }}
                          onClick={(e) => {
                            e.stopPropagation();
                            handleStartRename(conv.id, conv.title);
                          }}
                          title="Rename chat"
                        >
                          <Pencil size={12} />
                        </button>
                        <button
                          className="btn-icon btn-ghost"
                          style={{
                            padding: "4px",
                            opacity: isActive ? 0.8 : 0.4,
                          }}
                          onClick={(e) => {
                            e.stopPropagation();
                            deleteConv(conv.id);
                          }}
                          title="Delete chat"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Sidebar Footer */}
        <div
          style={{
            padding: "12px",
            borderTop: "1px solid var(--border-subtle)",
            display: "flex",
            flexDirection: "column",
            gap: "4px",
          }}
        >
          <Link
            href="/library"
            className="btn btn-ghost btn-sm"
            style={{ justifyContent: "flex-start", width: "100%" }}
          >
            <FileText size={15} /> Document Library
          </Link>
          <Link
            href="/settings"
            className="btn btn-ghost btn-sm"
            style={{ justifyContent: "flex-start", width: "100%" }}
          >
            <Settings size={15} /> Settings
          </Link>
          <button
            className="btn btn-ghost btn-sm"
            style={{
              justifyContent: "flex-start",
              width: "100%",
              color: "var(--text-tertiary)",
            }}
            onClick={handleLogout}
          >
            <LogOut size={15} /> Sign Out
          </button>
        </div>
      </aside>

      {/* ── Main Chat Area ───────────────────────── */}
      <main
        style={{
          flex: 1,
          display: "flex",
          flexDirection: "column",
          overflow: "hidden",
        }}
      >
        {/* Chat Header */}
        <div
          style={{
            position: "relative",
            zIndex: 20,
            padding: "12px 20px",
            borderBottom: "1px solid var(--border-subtle)",
            display: "flex",
            alignItems: "center",
            gap: "12px",
            background: "rgba(10, 10, 15, 0.5)",
            backdropFilter: "blur(10px)",
          }}
        >
          <button
            className="btn-icon btn-ghost"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
          </button>

          {/* Title with Header Rename */}
          <div style={{ flex: 1, display: "flex", alignItems: "center", gap: "12px", minWidth: 0 }}>
            {activeConvId && editingConvId === activeConvId ? (
              <div style={{ display: "flex", alignItems: "center", gap: "6px", flex: 1, maxWidth: "340px" }}>
                <input
                  autoFocus
                  className="input"
                  value={editingTitle}
                  onChange={(e) => setEditingTitle(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleSaveRename(activeConvId);
                    if (e.key === "Escape") handleCancelRename();
                  }}
                  style={{ fontSize: "13px", padding: "4px 8px", height: "30px" }}
                />
                <button
                  className="btn-icon btn-ghost"
                  style={{ color: "var(--success)", padding: "5px" }}
                  onClick={() => handleSaveRename(activeConvId)}
                  title="Save title (Enter)"
                >
                  <Check size={14} />
                </button>
                <button
                  className="btn-icon btn-ghost"
                  style={{ color: "var(--text-muted)", padding: "5px" }}
                  onClick={handleCancelRename}
                  title="Cancel (Esc)"
                >
                  <X size={14} />
                </button>
              </div>
            ) : (
              <div style={{ display: "flex", alignItems: "center", gap: "6px", minWidth: 0 }}>
                <span
                  style={{
                    fontSize: "14px",
                    fontWeight: 600,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {activeConvId
                    ? conversations.find((c) => c.id === activeConvId)?.title || "Chat"
                    : "New Conversation"}
                </span>
                {activeConvId && (
                  <button
                    className="btn-icon btn-ghost"
                    style={{ padding: "4px", color: "var(--text-muted)" }}
                    onClick={() => {
                      const cur = conversations.find((c) => c.id === activeConvId);
                      if (cur) handleStartRename(activeConvId, cur.title);
                    }}
                    title="Rename conversation"
                  >
                    <Pencil size={12} />
                  </button>
                )}
              </div>
            )}

            {/* Document Scope Selector */}
            <div style={{ display: "flex", alignItems: "center", gap: "6px", flexShrink: 0 }}>
              <Filter size={13} style={{ color: selectedDocId ? "var(--accent-primary)" : "var(--text-muted)" }} />
              <select
                id="doc-scope-select"
                value={selectedDocId || ""}
                onChange={(e) => setSelectedDocId(e.target.value || null)}
                className="input"
                style={{
                  padding: "4px 8px",
                  fontSize: "12px",
                  borderRadius: "var(--radius-sm)",
                  background: selectedDocId ? "rgba(124, 92, 252, 0.12)" : "var(--bg-secondary)",
                  color: selectedDocId ? "var(--accent-primary)" : "var(--text-secondary)",
                  border: selectedDocId ? "1px solid var(--accent-primary)" : "1px solid var(--border-subtle)",
                  cursor: "pointer",
                  maxWidth: "200px",
                }}
                title="Filter answers strictly to this document, or search across all library documents"
              >
                <option value="">🌐 All Library Documents</option>
                {documents.map((d) => (
                  <option key={d.id} value={d.id}>
                    📄 {d.filename.length > 25 ? d.filename.slice(0, 22) + "..." : d.filename}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Action controls group at the top-right */}
          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexShrink: 0 }}>
            {/* Phase 4: Research Tools Button */}
            <button
              id="research-tools-btn"
              className="btn btn-secondary btn-sm"
              onClick={() => {
                setResearchModalOpen(true);
              }}
              style={{
                gap: "6px",
                fontSize: "12px",
                padding: "5px 12px",
                background: "linear-gradient(135deg, rgba(124, 92, 252, 0.15), rgba(6, 182, 212, 0.15))",
                border: "1px solid rgba(124, 92, 252, 0.3)",
                color: "var(--text-primary)",
              }}
              title="Open Multi-Source Document Comparison and Research Report Tools"
            >
              <Sparkles size={14} style={{ color: "var(--accent-primary)" }} />
              Research Tools
            </button>

            {/* Export Dropdown Button — next to Research Tools with PDF and Word options */}
            <div style={{ position: "relative" }} ref={exportDropdownRef}>
              <button
                id="export-btn"
                data-testid="export-btn"
                className="btn btn-ghost btn-sm"
                onClick={() => setExportOpen(!exportOpen)}
                disabled={exportingFormat !== null || !activeConvId || messages.length === 0}
                style={{
                  gap: "6px",
                  fontSize: "12px",
                  padding: "5px 10px",
                  color: (!activeConvId || messages.length === 0) ? "var(--text-muted)" : "var(--text-secondary)",
                  opacity: (!activeConvId || messages.length === 0) ? 0.6 : 1,
                  cursor: (!activeConvId || messages.length === 0) ? "not-allowed" : "pointer",
                }}
                title={
                  !activeConvId || messages.length === 0
                    ? "Select a conversation with messages to export"
                    : "Export conversation history as PDF or Word document"
                }
              >
                {exportingFormat ? (
                  <>
                    <Loader2 size={14} className="animate-spin" /> Exporting...
                  </>
                ) : (
                  <>
                    <Download size={14} /> Export
                  </>
                )}
              </button>

              {exportOpen && activeConvId && messages.length > 0 && (
                <div
                  className="glass-card animate-fade-in"
                  style={{
                    position: "absolute",
                    right: 0,
                    top: "calc(100% + 6px)",
                    zIndex: 100,
                    minWidth: "195px",
                    padding: "6px",
                    display: "flex",
                    flexDirection: "column",
                    gap: "2px",
                    boxShadow: "var(--shadow-md)",
                  }}
                >
                  <button
                    id="export-pdf-btn"
                    data-testid="export-pdf-btn"
                    className="btn btn-ghost btn-sm"
                    style={{
                      justifyContent: "flex-start",
                      width: "100%",
                      fontSize: "12px",
                      padding: "8px 10px",
                      gap: "8px",
                    }}
                    disabled={exportingFormat !== null}
                    onClick={() => handleExport("pdf")}
                  >
                    {exportingFormat === "pdf" ? (
                      <Loader2 size={13} className="animate-spin" />
                    ) : (
                      <span style={{ fontSize: "14px" }}>📕</span>
                    )}
                    Export as PDF (.pdf)
                  </button>
                  <button
                    id="export-docx-btn"
                    data-testid="export-docx-btn"
                    className="btn btn-ghost btn-sm"
                    style={{
                      justifyContent: "flex-start",
                      width: "100%",
                      fontSize: "12px",
                      padding: "8px 10px",
                      gap: "8px",
                    }}
                    disabled={exportingFormat !== null}
                    onClick={() => handleExport("docx")}
                  >
                    {exportingFormat === "docx" ? (
                      <Loader2 size={13} className="animate-spin" />
                    ) : (
                      <span style={{ fontSize: "14px" }}>📘</span>
                    )}
                    Export as Word (.docx)
                  </button>
                </div>
              )}
            </div>

            {/* Profile Avatar & Account Controls */}
            {user ? (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  fontSize: "13px",
                  color: "var(--text-secondary)",
                }}
              >
                <Link
                  href="/settings"
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "8px",
                    textDecoration: "none",
                    color: "inherit",
                    cursor: "pointer",
                  }}
                  title={`Signed in as ${user.username} (${user.email}) - Account Settings`}
                >
                  <div
                    style={{
                      width: "28px",
                      height: "28px",
                      borderRadius: "50%",
                      background: "var(--accent-gradient)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "12px",
                      fontWeight: 600,
                      color: "white",
                    }}
                  >
                    {user.username[0].toUpperCase()}
                  </div>
                  <span
                    style={{
                      fontSize: "13px",
                      fontWeight: 500,
                      maxWidth: "110px",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {user.username}
                  </span>
                </Link>
              </div>
            ) : (
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Link href="/login" className="btn btn-ghost btn-sm" style={{ fontSize: "12px" }}>
                  Sign In
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Messages */}
        <div
          style={{
            flex: 1,
            overflowY: "auto",
            padding: "24px",
          }}
        >
          {messages.length === 0 ? (
            <div
              style={{
                height: "100%",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                textAlign: "center",
                gap: "16px",
              }}
            >
              <div
                style={{
                  width: "72px",
                  height: "72px",
                  borderRadius: "var(--radius-xl)",
                  background: "rgba(124, 92, 252, 0.08)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Sparkles size={32} style={{ color: "var(--accent-primary)" }} />
              </div>
              <h2
                style={{
                  fontSize: "20px",
                  fontWeight: 600,
                }}
              >
                How can I help with your research?
              </h2>
              <p
                style={{
                  color: "var(--text-secondary)",
                  fontSize: "14px",
                  maxWidth: "400px",
                }}
              >
                Upload documents in the{" "}
                <Link href="/library" style={{ color: "var(--accent-primary)" }}>
                  library
                </Link>{" "}
                , then ask me questions. I&apos;ll find answers from your sources with
                citations.
              </p>
            </div>
          ) : (
            <div style={{ maxWidth: "800px", margin: "0 auto" }}>
              {messages.map((msg, idx) => {
                const isAssistant = msg.role === "assistant";
                const isLatestAssistant = idx === lastAssistantIndex;

                return (
                  <div
                    key={msg.id}
                    className="animate-fade-in"
                    data-role={msg.role}
                    data-testid={`message-${msg.role}`}
                    style={{
                      marginBottom: "24px",
                      display: "flex",
                      gap: "12px",
                      animationDelay: `${idx * 0.04}s`,
                    }}
                  >
                    {/* Avatar */}
                    <div
                      style={{
                        width: "32px",
                        height: "32px",
                        borderRadius: "var(--radius-md)",
                        background:
                          msg.role === "user"
                            ? "var(--accent-gradient)"
                            : "rgba(92, 225, 230, 0.12)",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        flexShrink: 0,
                        marginTop: "2px",
                      }}
                    >
                      {msg.role === "user" ? (
                        <span style={{ fontSize: "13px", fontWeight: 600, color: "white" }}>
                          {user?.username?.[0]?.toUpperCase() || "U"}
                        </span>
                      ) : (
                        <Brain size={16} style={{ color: "var(--accent-secondary)" }} />
                      )}
                    </div>

                    {/* Content */}
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          marginBottom: "6px",
                        }}
                      >
                        <span
                          style={{
                            fontSize: "12px",
                            fontWeight: 600,
                            color: "var(--text-tertiary)",
                            textTransform: "uppercase",
                            letterSpacing: "0.05em",
                          }}
                        >
                          {msg.role === "user" ? "You" : "Assistant"}
                        </span>

                        {/* Assistant Action Bar: Copy & Regenerate */}
                        {isAssistant && (
                          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                            <button
                              className="btn btn-ghost btn-sm"
                              onClick={() => handleCopyMessage(msg.id, msg.content)}
                              style={{
                                padding: "2px 8px",
                                fontSize: "11px",
                                height: "24px",
                                gap: "4px",
                                color: "var(--text-secondary)",
                              }}
                              title="Copy response text"
                            >
                              {copiedMessageId === msg.id ? (
                                <>
                                  <Check size={12} style={{ color: "var(--success)" }} /> Copied
                                </>
                              ) : (
                                <>
                                  <Copy size={12} /> Copy
                                </>
                              )}
                            </button>

                            {isLatestAssistant && (
                              <button
                                className="btn btn-ghost btn-sm"
                                onClick={handleRegenerate}
                                disabled={regenerating || sending}
                                style={{
                                  padding: "2px 8px",
                                  fontSize: "11px",
                                  height: "24px",
                                  gap: "4px",
                                  color: "var(--text-secondary)",
                                }}
                                title="Regenerate this response"
                              >
                                <RotateCw
                                  size={12}
                                  className={regenerating ? "animate-spin" : ""}
                                  style={
                                    regenerating
                                      ? { animation: "spin 1s linear infinite" }
                                      : undefined
                                  }
                                />
                                {regenerating ? "Regenerating..." : "Regenerate"}
                              </button>
                            )}
                          </div>
                        )}
                      </div>

                      <div
                        className="markdown-content"
                        style={{
                          fontSize: "14px",
                          lineHeight: 1.7,
                          color: "var(--text-primary)",
                        }}
                      >
                        {isAssistant ? (
                          <MarkdownRenderer
                            content={msg.content}
                            onCitationClick={handleCitationClick}
                          />
                        ) : (
                          <span style={{ whiteSpace: "pre-wrap" }}>{msg.content}</span>
                        )}
                      </div>

                      {/* Citations */}
                      {msg.citations && msg.citations.length > 0 && (
                        <div
                          style={{
                            marginTop: "14px",
                            display: "flex",
                            flexDirection: "column",
                            gap: "6px",
                          }}
                        >
                          <div
                            style={{
                              fontSize: "11px",
                              fontWeight: 600,
                              color: "var(--text-tertiary)",
                              textTransform: "uppercase",
                              letterSpacing: "0.05em",
                              marginBottom: "2px",
                            }}
                          >
                            <BookOpen size={12} style={{ display: "inline", marginRight: "4px" }} />
                            Verified Sources
                          </div>
                          {msg.citations.map((cit: Citation) => {
                            const isHighlighted = highlightedCitation === cit.citation_index;
                            return (
                              <div
                                key={cit.id}
                                id={`citation-${cit.citation_index}`}
                                className="glass-card"
                                style={{
                                  padding: "10px 14px",
                                  fontSize: "12px",
                                  borderRadius: "var(--radius-sm)",
                                  transition: "all 0.3s ease",
                                  border: isHighlighted
                                    ? "1px solid var(--accent-primary)"
                                    : "1px solid var(--border-subtle)",
                                  background: isHighlighted
                                    ? "rgba(124, 92, 252, 0.16)"
                                    : undefined,
                                  boxShadow: isHighlighted
                                    ? "0 0 14px rgba(124, 92, 252, 0.4)"
                                    : undefined,
                                }}
                              >
                                <div
                                  style={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: "6px",
                                    marginBottom: "4px",
                                  }}
                                >
                                  <span
                                    className={`badge ${isHighlighted ? "badge-primary" : "badge-accent"}`}
                                    style={{ fontSize: "10px", fontWeight: 700 }}
                                  >
                                    [{cit.citation_index}]
                                  </span>
                                  <span style={{ fontWeight: 500, color: "var(--text-primary)" }}>
                                    {cit.source_title}
                                  </span>
                                  {cit.page_number && (
                                    <span style={{ color: "var(--accent-secondary)", fontWeight: 500 }}>
                                      p.{cit.page_number}
                                    </span>
                                  )}
                                  {cit.source_url && (
                                    <a
                                      href={cit.source_url}
                                      target="_blank"
                                      rel="noopener noreferrer"
                                      style={{ color: "var(--accent-primary)" }}
                                    >
                                      <ExternalLink size={11} />
                                    </a>
                                  )}
                                </div>
                                <p
                                  style={{
                                    color: "var(--text-tertiary)",
                                    lineHeight: 1.4,
                                  }}
                                >
                                  {cit.snippet}
                                </p>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}

              {(sending || regenerating) && (
                <div
                  className="animate-fade-in"
                  style={{ display: "flex", gap: "12px", marginBottom: "24px" }}
                >
                  <div
                    style={{
                      width: "32px",
                      height: "32px",
                      borderRadius: "var(--radius-md)",
                      background: "rgba(92, 225, 230, 0.12)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                    }}
                  >
                    <Brain size={16} style={{ color: "var(--accent-secondary)" }} />
                  </div>
                  <div style={{ paddingTop: "8px" }}>
                    <div className="spinner" />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div
          style={{
            padding: "16px 24px 24px",
            borderTop: "1px solid var(--border-subtle)",
            background: "rgba(10, 10, 15, 0.5)",
            backdropFilter: "blur(10px)",
          }}
        >
          <div
            style={{
              maxWidth: "800px",
              margin: "0 auto",
              position: "relative",
            }}
          >
            <textarea
              ref={inputRef}
              id="chat-input"
              className="input input-lg"
              style={{
                paddingRight: "52px",
                resize: "none",
                minHeight: "52px",
                maxHeight: "200px",
              }}
              rows={1}
              placeholder="Ask a research question..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={sending || regenerating}
            />
            <button
              id="send-btn"
              className="btn btn-primary btn-icon"
              style={{
                position: "absolute",
                right: "6px",
                bottom: "6px",
                width: "40px",
                height: "40px",
              }}
              onClick={handleSend}
              disabled={sending || regenerating || !input.trim()}
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      </main>

      {/* ── Phase 4: Research Tools Modal ───────────────── */}
      {researchModalOpen && (
        <div
          id="research-modal"
          role="dialog"
          aria-modal="true"
          onClick={() => setResearchModalOpen(false)}
          style={{
            position: "fixed",
            inset: 0,
            zIndex: 999,
            backgroundColor: "rgba(0, 0, 0, 0.75)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            padding: "20px",
          }}
        >
          <div
            onClick={(e) => e.stopPropagation()}
            className="glass-card"
            style={{
              width: "100%",
              maxWidth: "880px",
              maxHeight: "90vh",
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
              border: "1px solid var(--border-accent)",
              boxShadow: "0 24px 48px rgba(0, 0, 0, 0.5), 0 0 24px rgba(124, 92, 252, 0.2)",
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
                background: "var(--bg-primary)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <div
                  style={{
                    width: "36px",
                    height: "36px",
                    borderRadius: "var(--radius-md)",
                    background: "linear-gradient(135deg, var(--accent-primary), var(--accent-secondary))",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "#fff",
                  }}
                >
                  <Sparkles size={18} />
                </div>
                <div>
                  <h2 style={{ fontSize: "16px", fontWeight: 700, margin: 0 }}>
                    AI Research Suite
                  </h2>
                  <p style={{ fontSize: "12px", color: "var(--text-muted)", margin: 0 }}>
                    Multi-source comparison, research report generation, and strict citation grounding
                  </p>
                </div>
              </div>
              <button
                id="close-research-modal-btn"
                className="btn-icon btn-ghost"
                onClick={() => setResearchModalOpen(false)}
                title="Close modal"
              >
                <X size={18} />
              </button>
            </div>

            {/* Navigation Tabs */}
            <div
              style={{
                display: "flex",
                borderBottom: "1px solid var(--border-subtle)",
                background: "rgba(10, 10, 15, 0.6)",
                padding: "4px 16px 0",
                gap: "8px",
              }}
            >
              <button
                id="research-tab-compare"
                onClick={() => {
                  setResearchTab("compare");
                  setResearchError("");
                }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "10px 16px",
                  fontSize: "13px",
                  fontWeight: 600,
                  border: "none",
                  background: "transparent",
                  color: researchTab === "compare" ? "var(--accent-primary)" : "var(--text-secondary)",
                  borderBottom: `2px solid ${researchTab === "compare" ? "var(--accent-primary)" : "transparent"
                    }`,
                  cursor: "pointer",
                  transition: "all var(--transition-fast)",
                }}
              >
                <GitCompare size={15} />
                Multi-Source Comparison
                {selectedResearchDocIds.length >= 2 && (
                  <span
                    style={{
                      background: "rgba(124, 92, 252, 0.2)",
                      color: "var(--accent-primary)",
                      borderRadius: "10px",
                      padding: "1px 6px",
                      fontSize: "11px",
                    }}
                  >
                    {selectedResearchDocIds.length}
                  </span>
                )}
              </button>

              <button
                id="research-tab-report"
                onClick={() => {
                  setResearchTab("report");
                  setResearchError("");
                }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "10px 16px",
                  fontSize: "13px",
                  fontWeight: 600,
                  border: "none",
                  background: "transparent",
                  color: researchTab === "report" ? "var(--accent-primary)" : "var(--text-secondary)",
                  borderBottom: `2px solid ${researchTab === "report" ? "var(--accent-primary)" : "transparent"
                    }`,
                  cursor: "pointer",
                  transition: "all var(--transition-fast)",
                }}
              >
                <FileText size={15} />
                Research Report Generator
              </button>
            </div>

            {/* Modal Body */}
            <div
              style={{
                flex: 1,
                overflowY: "auto",
                padding: "20px",
                display: "flex",
                flexDirection: "column",
                gap: "18px",
              }}
            >
              {researchError && (
                <div
                  style={{
                    padding: "10px 14px",
                    background: "rgba(248, 113, 113, 0.1)",
                    border: "1px solid rgba(248, 113, 113, 0.3)",
                    borderRadius: "var(--radius-sm)",
                    color: "var(--error)",
                    fontSize: "13px",
                  }}
                >
                  {researchError}
                </div>
              )}

              {/* ── TAB 1: COMPARE ───────────────────────────── */}
              {researchTab === "compare" && (
                <>
                  {compareResult ? (
                    /* Comparison Result View */
                    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "flex-start",
                          justifyContent: "space-between",
                          flexWrap: "wrap",
                          gap: "10px",
                          paddingBottom: "14px",
                          borderBottom: "1px solid var(--border-subtle)",
                        }}
                      >
                        <div>
                          <h3 style={{ fontSize: "18px", fontWeight: 700, margin: 0 }}>
                            {compareResult.title}
                          </h3>
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: "8px",
                              marginTop: "6px",
                              flexWrap: "wrap",
                            }}
                          >
                            <span style={{ fontSize: "12px", color: "var(--text-muted)" }}>
                              Compared Sources:
                            </span>
                            {compareResult.documents.map((d) => (
                              <span
                                key={d.id}
                                className="badge badge-accent"
                                style={{ fontSize: "11px" }}
                              >
                                📄 {d.filename}
                              </span>
                            ))}
                          </div>
                        </div>

                        {/* Export & New Comparison Action Buttons */}
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                          <button
                            id="download-compare-pdf-btn"
                            className="btn btn-secondary btn-sm"
                            disabled={researchExportingFormat !== null}
                            onClick={() => handleExportResearch(compareResult, "pdf")}
                            style={{ gap: "6px", fontSize: "12px" }}
                            title="Export comparative report as PDF"
                          >
                            {researchExportingFormat === "pdf" ? <Loader2 size={14} className="animate-spin" /> : <FileText size={14} />} PDF
                          </button>
                          <button
                            id="download-compare-docx-btn"
                            className="btn btn-secondary btn-sm"
                            disabled={researchExportingFormat !== null}
                            onClick={() => handleExportResearch(compareResult, "docx")}
                            style={{ gap: "6px", fontSize: "12px" }}
                            title="Export comparative report as Word (.docx)"
                          >
                            {researchExportingFormat === "docx" ? <Loader2 size={14} className="animate-spin" /> : <FileDown size={14} />} Word
                          </button>
                          <button
                            id="download-compare-md-btn"
                            className="btn btn-secondary btn-sm"
                            disabled={researchExportingFormat !== null}
                            onClick={() => handleExportResearch(compareResult, "markdown")}
                            style={{ gap: "6px", fontSize: "12px" }}
                            title="Export comparative report as Markdown"
                          >
                            {researchExportingFormat === "markdown" ? <Loader2 size={14} className="animate-spin" /> : <FileDown size={14} />} Markdown
                          </button>
                          <button
                            id="download-compare-json-btn"
                            className="btn btn-secondary btn-sm"
                            disabled={researchExportingFormat !== null}
                            onClick={() => handleExportResearch(compareResult, "json")}
                            style={{ gap: "6px", fontSize: "12px" }}
                            title="Export comparative report as JSON"
                          >
                            {researchExportingFormat === "json" ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />} JSON
                          </button>
                          <button
                            className="btn btn-ghost btn-sm"
                            onClick={() => setCompareResult(null)}
                            style={{ fontSize: "12px" }}
                          >
                            New Comparison
                          </button>
                        </div>
                      </div>

                      {/* Rendered Comparison Content */}
                      <div
                        className="markdown-content"
                        style={{
                          padding: "16px",
                          background: "var(--bg-secondary)",
                          borderRadius: "var(--radius-md)",
                          border: "1px solid var(--border-subtle)",
                          fontSize: "14px",
                          lineHeight: "1.7",
                        }}
                      >
                        <MarkdownRenderer
                          content={compareResult.content}
                          onCitationClick={handleCitationClick}
                        />
                      </div>

                      {/* Citations Footer */}
                      {compareResult.citations.length > 0 && (
                        <div
                          style={{
                            marginTop: "8px",
                            padding: "14px",
                            background: "rgba(10, 10, 15, 0.6)",
                            borderRadius: "var(--radius-sm)",
                            border: "1px solid var(--border-subtle)",
                          }}
                        >
                          <div
                            style={{
                              fontSize: "12px",
                              fontWeight: 600,
                              color: "var(--text-tertiary)",
                              textTransform: "uppercase",
                              marginBottom: "10px",
                              display: "flex",
                              alignItems: "center",
                              gap: "6px",
                            }}
                          >
                            <BookOpen size={13} />
                            Verified Citations ({compareResult.citations.length})
                          </div>
                          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                            {compareResult.citations.map((c) => (
                              <div
                                key={c.id || c.citation_index}
                                style={{
                                  fontSize: "12px",
                                  padding: "8px 10px",
                                  background: "var(--bg-primary)",
                                  border: "1px solid var(--border-subtle)",
                                  borderRadius: "var(--radius-sm)",
                                }}
                              >
                                <div style={{ fontWeight: 600, color: "var(--accent-primary)" }}>
                                  [{c.citation_index}] {c.source_title}
                                  {c.page_number ? ` (Page ${c.page_number})` : ""}
                                </div>
                                <div style={{ color: "var(--text-secondary)", marginTop: "3px" }}>
                                  &ldquo;{c.snippet}&rdquo;
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    /* Comparison Form */
                    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                      <p style={{ fontSize: "13px", color: "var(--text-secondary)", margin: 0 }}>
                        Select at least 2 indexed documents to evaluate their commonalities, core differences,
                        and missing information with verified source grounding.
                      </p>

                      {/* Document Picker */}
                      <div>
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            marginBottom: "8px",
                          }}
                        >
                          <label style={{ fontSize: "13px", fontWeight: 600 }}>
                            Select Documents to Compare ({selectedResearchDocIds.length} selected):
                          </label>
                          <button
                            type="button"
                            className="btn btn-ghost btn-sm"
                            onClick={handleSelectAllIndexedDocs}
                            style={{ fontSize: "11px", padding: "2px 8px" }}
                          >
                            {selectedResearchDocIds.length ===
                              documents.filter((d) => d.status === "indexed").length
                              ? "Deselect All"
                              : "Select All Indexed"}
                          </button>
                        </div>

                        <div
                          style={{
                            maxHeight: "180px",
                            overflowY: "auto",
                            border: "1px solid var(--border-subtle)",
                            borderRadius: "var(--radius-sm)",
                            padding: "6px",
                            display: "flex",
                            flexDirection: "column",
                            gap: "4px",
                            background: "var(--bg-primary)",
                          }}
                        >
                          {documents.length === 0 ? (
                            <div style={{ padding: "16px", textAlign: "center", color: "var(--text-muted)", fontSize: "12px" }}>
                              No documents available in library. Upload documents in the Library first.
                            </div>
                          ) : (
                            documents.map((doc) => {
                              const isChecked = selectedResearchDocIds.includes(doc.id);
                              const isIndexed = doc.status === "indexed";
                              return (
                                <label
                                  key={doc.id}
                                  style={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: "10px",
                                    padding: "6px 10px",
                                    borderRadius: "var(--radius-sm)",
                                    background: isChecked ? "rgba(124, 92, 252, 0.08)" : "transparent",
                                    cursor: isIndexed ? "pointer" : "not-allowed",
                                    opacity: isIndexed ? 1 : 0.45,
                                  }}
                                >
                                  <input
                                    type="checkbox"
                                    id={`compare-doc-${doc.id}`}
                                    checked={isChecked}
                                    onChange={() => toggleResearchDocSelection(doc.id)}
                                    disabled={!isIndexed}
                                    style={{ accentColor: "var(--accent-primary)" }}
                                  />
                                  <FileText size={14} style={{ color: "var(--accent-primary)" }} />
                                  <span style={{ fontSize: "13px", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                    {doc.filename}
                                  </span>
                                  <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                                    {isIndexed ? `${doc.chunk_count} chunks` : doc.status}
                                  </span>
                                </label>
                              );
                            })
                          )}
                        </div>
                      </div>

                      {/* Topic Input */}
                      <div>
                        <label
                          htmlFor="compare-topic-input"
                          style={{ display: "block", fontSize: "13px", fontWeight: 600, marginBottom: "6px" }}
                        >
                          Comparison Focus or Question (Optional):
                        </label>
                        <input
                          id="compare-topic-input"
                          type="text"
                          className="input"
                          placeholder="e.g. Compare architectural tradeoffs, accuracy benchmarks, and data pipelines"
                          value={researchTopic}
                          onChange={(e) => setResearchTopic(e.target.value)}
                        />
                      </div>

                      {/* Run Button */}
                      <button
                        id="run-compare-btn"
                        className="btn btn-primary"
                        onClick={handleRunCompare}
                        disabled={researchLoading || selectedResearchDocIds.length < 2}
                        style={{
                          marginTop: "8px",
                          gap: "8px",
                          justifyContent: "center",
                          height: "42px",
                        }}
                      >
                        {researchLoading ? (
                          <>
                            <RotateCw size={16} className="animate-spin" style={{ animation: "spin 1s linear infinite" }} />
                            Synthesizing Comparative Analysis...
                          </>
                        ) : (
                          <>
                            <GitCompare size={16} />
                            Run Multi-Source Comparison
                            {selectedResearchDocIds.length < 2 && " (Select at least 2)"}
                          </>
                        )}
                      </button>
                    </div>
                  )}
                </>
              )}

              {/* ── TAB 2: RESEARCH REPORT ───────────────────── */}
              {researchTab === "report" && (
                <>
                  {reportResult ? (
                    /* Report Result View */
                    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                      <div
                        style={{
                          display: "flex",
                          alignItems: "flex-start",
                          justifyContent: "space-between",
                          flexWrap: "wrap",
                          gap: "10px",
                          paddingBottom: "14px",
                          borderBottom: "1px solid var(--border-subtle)",
                        }}
                      >
                        <div>
                          <h3 style={{ fontSize: "18px", fontWeight: 700, margin: 0 }}>
                            {reportResult.title}
                          </h3>
                          <div style={{ marginTop: "6px", display: "flex", gap: "6px", flexWrap: "wrap" }}>
                            <span className="badge badge-accent" style={{ fontSize: "11px" }}>
                              Topic: {reportResult.topic}
                            </span>
                            {reportResult.documents.map((d) => (
                              <span key={d.id} className="badge badge-secondary" style={{ fontSize: "11px" }}>
                                📄 {d.filename}
                              </span>
                            ))}
                          </div>
                        </div>

                        {/* Export & Reset Actions */}
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                          <button
                            id="download-report-pdf-btn"
                            className="btn btn-secondary btn-sm"
                            disabled={researchExportingFormat !== null}
                            onClick={() => handleExportResearch(reportResult, "pdf")}
                            style={{ gap: "6px", fontSize: "12px" }}
                            title="Export research report as PDF"
                          >
                            {researchExportingFormat === "pdf" ? <Loader2 size={14} className="animate-spin" /> : <FileText size={14} />} PDF
                          </button>
                          <button
                            id="download-report-docx-btn"
                            className="btn btn-secondary btn-sm"
                            disabled={researchExportingFormat !== null}
                            onClick={() => handleExportResearch(reportResult, "docx")}
                            style={{ gap: "6px", fontSize: "12px" }}
                            title="Export research report as Word (.docx)"
                          >
                            {researchExportingFormat === "docx" ? <Loader2 size={14} className="animate-spin" /> : <FileDown size={14} />} Word
                          </button>
                          <button
                            id="download-report-md-btn"
                            className="btn btn-secondary btn-sm"
                            disabled={researchExportingFormat !== null}
                            onClick={() => handleExportResearch(reportResult, "markdown")}
                            style={{ gap: "6px", fontSize: "12px" }}
                            title="Export research report as Markdown"
                          >
                            {researchExportingFormat === "markdown" ? <Loader2 size={14} className="animate-spin" /> : <FileDown size={14} />} Markdown
                          </button>
                          <button
                            id="download-report-json-btn"
                            className="btn btn-secondary btn-sm"
                            disabled={researchExportingFormat !== null}
                            onClick={() => handleExportResearch(reportResult, "json")}
                            style={{ gap: "6px", fontSize: "12px" }}
                            title="Export research report as JSON"
                          >
                            {researchExportingFormat === "json" ? <Loader2 size={14} className="animate-spin" /> : <Download size={14} />} JSON
                          </button>
                          <button
                            className="btn btn-ghost btn-sm"
                            onClick={() => setReportResult(null)}
                            style={{ fontSize: "12px" }}
                          >
                            New Report
                          </button>
                        </div>
                      </div>

                      {/* Executive Summary Card */}
                      <div
                        style={{
                          padding: "16px",
                          background: "linear-gradient(135deg, rgba(124, 92, 252, 0.12), rgba(6, 182, 212, 0.08))",
                          border: "1px solid rgba(124, 92, 252, 0.3)",
                          borderRadius: "var(--radius-md)",
                        }}
                      >
                        <h4 style={{ fontSize: "13px", fontWeight: 700, color: "var(--accent-primary)", marginBottom: "6px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                          Executive Summary
                        </h4>
                        <p style={{ fontSize: "13px", lineHeight: "1.6", color: "var(--text-primary)", margin: 0 }}>
                          {reportResult.executive_summary}
                        </p>
                      </div>

                      {/* Key Findings */}
                      {reportResult.key_findings && reportResult.key_findings.length > 0 && (
                        <div
                          style={{
                            padding: "14px 16px",
                            background: "var(--bg-secondary)",
                            border: "1px solid var(--border-subtle)",
                            borderRadius: "var(--radius-md)",
                          }}
                        >
                          <h4 style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-tertiary)", marginBottom: "8px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
                            Key Findings
                          </h4>
                          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
                            {reportResult.key_findings.map((kf, i) => (
                              <div
                                key={i}
                                style={{
                                  display: "flex",
                                  alignItems: "flex-start",
                                  gap: "8px",
                                  fontSize: "13px",
                                  color: "var(--text-secondary)",
                                }}
                              >
                                <span style={{ color: "var(--accent-primary)", fontWeight: 700 }}>•</span>
                                <span>{kf}</span>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Main Report Body */}
                      <div
                        className="markdown-content"
                        style={{
                          padding: "16px",
                          background: "var(--bg-secondary)",
                          borderRadius: "var(--radius-md)",
                          border: "1px solid var(--border-subtle)",
                          fontSize: "14px",
                          lineHeight: "1.7",
                        }}
                      >
                        <MarkdownRenderer
                          content={reportResult.content}
                          onCitationClick={handleCitationClick}
                        />
                      </div>

                      {/* Conclusions & Limitations */}
                      <div
                        style={{
                          padding: "14px 16px",
                          background: "rgba(10, 10, 15, 0.6)",
                          border: "1px solid var(--border-subtle)",
                          borderRadius: "var(--radius-md)",
                          display: "flex",
                          flexDirection: "column",
                          gap: "8px",
                        }}
                      >
                        <h4 style={{ fontSize: "13px", fontWeight: 700, color: "var(--text-tertiary)", margin: 0, textTransform: "uppercase", letterSpacing: "0.05em" }}>
                          Conclusions & Missing Evidence
                        </h4>
                        <p style={{ fontSize: "13px", color: "var(--text-secondary)", margin: 0 }}>
                          {reportResult.conclusions}
                        </p>
                        {reportResult.limitations && (
                          <p style={{ fontSize: "12px", color: "var(--text-muted)", fontStyle: "italic", margin: 0 }}>
                            {reportResult.limitations}
                          </p>
                        )}
                      </div>

                      {/* Report Citations */}
                      {reportResult.citations && reportResult.citations.length > 0 && (
                        <div
                          style={{
                            padding: "14px",
                            background: "rgba(10, 10, 15, 0.6)",
                            borderRadius: "var(--radius-sm)",
                            border: "1px solid var(--border-subtle)",
                          }}
                        >
                          <div
                            style={{
                              fontSize: "12px",
                              fontWeight: 600,
                              color: "var(--text-tertiary)",
                              textTransform: "uppercase",
                              marginBottom: "10px",
                              display: "flex",
                              alignItems: "center",
                              gap: "6px",
                            }}
                          >
                            <BookOpen size={13} />
                            Verified Evidence Sources ({reportResult.citations.length})
                          </div>
                          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                            {reportResult.citations.map((c) => (
                              <div
                                key={c.id || c.citation_index}
                                style={{
                                  fontSize: "12px",
                                  padding: "8px 10px",
                                  background: "var(--bg-primary)",
                                  border: "1px solid var(--border-subtle)",
                                  borderRadius: "var(--radius-sm)",
                                }}
                              >
                                <div style={{ fontWeight: 600, color: "var(--accent-primary)" }}>
                                  [{c.citation_index}] {c.source_title}
                                  {c.page_number ? ` (Page ${c.page_number})` : ""}
                                </div>
                                <div style={{ color: "var(--text-secondary)", marginTop: "3px" }}>
                                  &ldquo;{c.snippet}&rdquo;
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ) : (
                    /* Report Generation Form */
                    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                      <p style={{ fontSize: "13px", color: "var(--text-secondary)", margin: 0 }}>
                        Generate a comprehensive, structured research report with executive summaries, key findings,
                        and rigorous citations from your indexed documents.
                      </p>

                      {/* Topic Input */}
                      <div>
                        <label
                          htmlFor="report-topic-input"
                          style={{ display: "block", fontSize: "13px", fontWeight: 600, marginBottom: "6px" }}
                        >
                          Research Topic or Central Question *
                        </label>
                        <textarea
                          id="report-topic-input"
                          className="input"
                          rows={2}
                          placeholder="e.g. Comprehensive synthesis of technical architecture, retrieval methods, and system performance"
                          value={researchTopic}
                          onChange={(e) => setResearchTopic(e.target.value)}
                          style={{ resize: "vertical" }}
                        />
                      </div>

                      {/* Document Scope (Optional) */}
                      <div>
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            marginBottom: "8px",
                          }}
                        >
                          <label style={{ fontSize: "13px", fontWeight: 600 }}>
                            Scope to Specific Documents (Optional — leave blank to search all indexed documents):
                          </label>
                          <button
                            type="button"
                            className="btn btn-ghost btn-sm"
                            onClick={handleSelectAllIndexedDocs}
                            style={{ fontSize: "11px", padding: "2px 8px" }}
                          >
                            {selectedResearchDocIds.length ===
                              documents.filter((d) => d.status === "indexed").length
                              ? "Deselect All"
                              : "Select All"}
                          </button>
                        </div>

                        <div
                          style={{
                            maxHeight: "150px",
                            overflowY: "auto",
                            border: "1px solid var(--border-subtle)",
                            borderRadius: "var(--radius-sm)",
                            padding: "6px",
                            display: "flex",
                            flexDirection: "column",
                            gap: "4px",
                            background: "var(--bg-primary)",
                          }}
                        >
                          {documents.map((doc) => {
                            const isChecked = selectedResearchDocIds.includes(doc.id);
                            const isIndexed = doc.status === "indexed";
                            return (
                              <label
                                key={doc.id}
                                style={{
                                  display: "flex",
                                  alignItems: "center",
                                  gap: "10px",
                                  padding: "6px 10px",
                                  borderRadius: "var(--radius-sm)",
                                  background: isChecked ? "rgba(124, 92, 252, 0.08)" : "transparent",
                                  cursor: isIndexed ? "pointer" : "not-allowed",
                                  opacity: isIndexed ? 1 : 0.45,
                                }}
                              >
                                <input
                                  type="checkbox"
                                  id={`report-doc-${doc.id}`}
                                  checked={isChecked}
                                  onChange={() => toggleResearchDocSelection(doc.id)}
                                  disabled={!isIndexed}
                                  style={{ accentColor: "var(--accent-primary)" }}
                                />
                                <FileText size={14} style={{ color: "var(--accent-primary)" }} />
                                <span style={{ fontSize: "13px", flex: 1, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                                  {doc.filename}
                                </span>
                                <span style={{ fontSize: "11px", color: "var(--text-muted)" }}>
                                  {isIndexed ? `${doc.chunk_count} chunks` : doc.status}
                                </span>
                              </label>
                            );
                          })}
                        </div>
                      </div>

                      {/* Generate Report Button */}
                      <button
                        id="run-report-btn"
                        className="btn btn-primary"
                        onClick={handleRunReport}
                        disabled={researchLoading || !researchTopic.trim()}
                        style={{
                          marginTop: "8px",
                          gap: "8px",
                          justifyContent: "center",
                          height: "42px",
                        }}
                      >
                        {researchLoading ? (
                          <>
                            <RotateCw size={16} className="animate-spin" style={{ animation: "spin 1s linear infinite" }} />
                            Generating Research Report...
                          </>
                        ) : (
                          <>
                            <Sparkles size={16} />
                            Generate Research Report
                          </>
                        )}
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Modal Footer */}
            <div
              style={{
                padding: "12px 20px",
                borderTop: "1px solid var(--border-subtle)",
                display: "flex",
                alignItems: "center",
                justifyContent: "flex-end",
                background: "var(--bg-primary)",
              }}
            >
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setResearchModalOpen(false)}
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
