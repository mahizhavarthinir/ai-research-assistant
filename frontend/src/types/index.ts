/* ── API Types ────────────────────────────────────────── */

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface UserProfile {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

export interface RegisterPayload {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

export interface LoginPayload {
  email: string;
  password: string;
}

/* ── Chat Types ──────────────────────────────────────── */

export interface Citation {
  id: string;
  source_title: string;
  source_url: string | null;
  page_number: number | null;
  snippet: string;
  relevance_score: number | null;
  citation_index: number;
}

export interface ChatRequest {
  message: string;
  conversation_id?: string;
  document_id?: string;
  document_ids?: string[];
}

export interface ChatResponse {
  conversation_id: string;
  message_id: string;
  content: string;
  citations: Citation[];
  model_used: string | null;
}

export interface Message {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  sequence_number: number;
  citations: Citation[];
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

/* ── Document Types ──────────────────────────────────── */

export interface Document {
  id: string;
  filename: string;
  file_type: string;
  file_size: number | null;
  source_url: string | null;
  status: "pending" | "processing" | "indexed" | "error";
  error_message: string | null;
  chunk_count: number;
  created_at: string;
}

export interface DocumentListResponse {
  items: Document[];
  total: number;
}

export interface DocumentChunk {
  id: string;
  chunk_index: number;
  content: string;
  page_number: number | null;
  token_count: number;
}

/* ── Integration Types ───────────────────────────────── */

export interface Integration {
  id: string;
  name: string;
  description: string;
  tool_type: string;
  is_enabled: boolean;
  requires_auth: boolean;
  icon: string | null;
}

export interface IntegrationHealthItem {
  name: string;
  server: string;
  enabled: boolean;
}

export interface IntegrationsHealthResponse {
  status: string;
  total_tools?: number;
  enabled_tools?: number;
  error?: string;
  integrations?: IntegrationHealthItem[];
}

/* ── Research Types (Phase 4) ────────────────────────── */

export interface DocumentSummary {
  id: string;
  filename: string;
  file_type: string;
}

export interface DocumentCompareRequest {
  document_ids: string[];
  topic?: string;
  conversation_id?: string;
}

export interface DocumentCompareResponse {
  title: string;
  topic: string;
  content: string;
  documents: DocumentSummary[];
  citations: Citation[];
  conversation_id?: string | null;
  message_id?: string | null;
}

export interface ResearchReportRequest {
  document_ids?: string[];
  topic: string;
  conversation_id?: string;
}

export interface ResearchReportResponse {
  title: string;
  topic: string;
  executive_summary: string;
  key_findings: string[];
  conclusions: string;
  limitations: string;
  content: string;
  documents: DocumentSummary[];
  citations: Citation[];
  conversation_id?: string | null;
  message_id?: string | null;
}
