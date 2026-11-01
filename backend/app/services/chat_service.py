"""
AI Research Assistant — Chat Service

Orchestrates the full chat flow:
  1. Classify user intent (general / document / URL / MCP tool)
  2. Retrieve context from the appropriate source(s)
  3. Build a dynamic prompt tailored to the source type
  4. Call the LLM with only relevant context
  5. Return the response with citations
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.llm import get_llm_provider, LLMMessage
from app.models.citation import Citation
from app.models.conversation import Conversation, Message
from app.rag.retriever import get_retriever, RetrievedChunk


# ── Intent Classification ───────────────────────────────────

class QueryIntent(str, Enum):
    GENERAL = "general"          # General knowledge / conversational
    DOCUMENT = "document"        # User expects answer from uploaded docs
    URL = "url"                  # User pasted a URL to process
    MCP_TOOL = "mcp_tool"       # User wants to use an MCP tool
    FOLLOW_UP = "follow_up"     # Continuation of previous topic


# URL pattern for detecting pasted URLs
URL_PATTERN = re.compile(
    r'https?://[^\s<>"\']+|www\.[^\s<>"\']+',
    re.IGNORECASE,
)

# Keywords that indicate user wants to query their documents
DOCUMENT_KEYWORDS = [
    "in the document", "in the pdf", "in my document", "in my file",
    "in the file", "uploaded", "from the document", "from my document",
    "from the pdf", "from my pdf", "according to the document",
    "in the paper", "in the article", "from the article",
    "what does the document say", "in my library", "from my library",
    "in my uploaded", "from my uploaded", "in my files", "summarize document",
    "summarize paper", "summarize pdf", "based on document", "based on my file",
]

# Keywords that indicate user wants to use a tool/integration
MCP_KEYWORDS = [
    "search github", "search repo", "search repositories", "github",
    "search code", "run tool", "use tool", "execute tool",
    "create issue", "list issues", "pull request", "create branch",
    "calculator", "calculate", "python_calculator", "evaluate",
]

# Follow-up / vague queries
FOLLOW_UP_INDICATORS = [
    "tell me more", "more about", "explain that", "what about",
    "elaborate", "continue", "go on", "and then", "what else",
    "can you explain", "why is that", "how does that",
    "what do you mean", "give me more", "details",
    "yes", "sure", "ok",
]


def classify_intent(
    user_message: str,
    history: list[Message],
    has_documents: bool = False,
) -> QueryIntent:
    """
    Classify the user's intent to route the query to the right source.
    """
    msg_lower = user_message.lower().strip()

    # 1. URL detected in the message
    if URL_PATTERN.search(user_message):
        return QueryIntent.URL

    # 2. MCP tool keywords
    if any(kw in msg_lower for kw in MCP_KEYWORDS):
        return QueryIntent.MCP_TOOL

    # 3. Explicit document reference
    if any(kw in msg_lower for kw in DOCUMENT_KEYWORDS):
        return QueryIntent.DOCUMENT

    # 4. Short/vague follow-up
    word_count = len(user_message.split())
    is_vague = word_count <= 5 and any(v in msg_lower for v in FOLLOW_UP_INDICATORS)
    if is_vague and history:
        return QueryIntent.FOLLOW_UP

    # 5. If user has documents and query might be document-related, route to DOCUMENT
    if has_documents and any(w in msg_lower for w in ["summarize", "find", "what is", "who", "when", "how", "explain", "why"]):
        return QueryIntent.DOCUMENT

    # 6. Default to GENERAL
    return QueryIntent.GENERAL


# ── System Prompts ──────────────────────────────────────────

SYSTEM_PROMPT_GENERAL = """You are an AI Research Assistant — a knowledgeable, helpful, and articulate chatbot.

INSTRUCTIONS:
- Answer the user's question directly and accurately using your general knowledge.
- Be natural, conversational, and thorough.
- Use clear structure: headings (##), bullet points, bold for key terms.
- Provide examples, explanations, and code snippets when relevant.
- If you don't know something, say so honestly.
- Never fabricate citations or sources.
- Give complete, useful answers — not just summaries.
"""

SYSTEM_PROMPT_DOCUMENT = """You are an AI Research Assistant. Answer questions using the document context provided below.

INSTRUCTIONS:
1. Answer based strictly on the provided document context passages.
2. Cite facts using [1], [2], etc. matching the passage numbers.
3. STRICT GROUNDING & UNAVAILABLE INFORMATION: If the provided document context does not contain the answer or lacks information on a requested topic or detail, you MUST explicitly state: "The provided document(s) do not contain information regarding [topic]." Do NOT speculate, extrapolate, or fabricate citations or facts not explicitly supported by the passages.
4. For PDF sources, mention the page number when available.
5. For URL sources, mention the source URL.
6. Be thorough and well-structured.

RESPONSE FORMAT:
- Use ## and ### headings for longer answers
- Use bullet points and numbered lists
- Use **bold** for key terms
- Cite sources: [1], [2], etc.
"""

SYSTEM_PROMPT_URL = """You are an AI Research Assistant. The user has provided a URL. Answer based on the extracted webpage content below.

INSTRUCTIONS:
1. Answer using the content extracted from the URL.
2. Mention the source URL in your response.
3. If the extracted content doesn't answer the question, say so clearly.
4. Summarize key information clearly and concisely.
"""

SYSTEM_PROMPT_MCP = """You are an AI Research Assistant with access to external tools.

INSTRUCTIONS:
1. Use the tool results provided to answer the user's question.
2. Present the results clearly and explain what was found.
3. If the tool returned an error, explain what happened.
4. Mention which tool was used and what it returned.
"""


# ── Context Building ────────────────────────────────────────

def _build_document_context(chunks: list[RetrievedChunk]) -> str:
    """Format retrieved document chunks into a context block."""
    if not chunks:
        return ""

    lines = ["DOCUMENT CONTEXT:\n"]
    for i, chunk in enumerate(chunks, 1):
        chunk.citation_index = i
        source_info = chunk.document_title
        if chunk.page_number:
            source_info += f" (Page {chunk.page_number})"
        if chunk.source_url:
            source_info += f" — {chunk.source_url}"

        lines.append(f"[{i}] Source: {source_info}")
        lines.append(f"    {chunk.content}")
        lines.append("")

    return "\n".join(lines)


def _build_retrieval_query(user_message: str, history: list[Message]) -> str:
    """
    Build an effective retrieval query using the user's message and conversation history.
    Expands follow-up questions by combining with prior context.
    """
    msg_lower = user_message.lower().strip()
    word_count = len(user_message.split())
    
    is_followup = (
        word_count <= 8
        and any(v in msg_lower for v in FOLLOW_UP_INDICATORS)
    )

    if not is_followup or not history:
        return user_message

    # Get the last user message for context
    for msg in reversed(history[-6:]):
        if msg.role == "user" and msg.content != user_message:
            combined = f"{msg.content} {user_message}"
            logger.info(f"Follow-up query expanded: '{user_message}' → '{combined[:100]}...'")
            return combined

    return user_message


def _extract_urls(text: str) -> list[str]:
    """Extract all URLs from a text string."""
    return URL_PATTERN.findall(text)


# ── Main Chat Flow ──────────────────────────────────────────

async def generate_chat_response(
    db: AsyncSession,
    conversation: Conversation,
    user_message: str,
    user_id: str,
    document_id: str | None = None,
    document_ids: list[str] | None = None,
) -> tuple[str, list[RetrievedChunk], str]:
    """
    Generate an AI response for a chat message.

    Unified workflow:
      1. Load conversation history
      2. Classify intent (or document-scoped if document_id/document_ids provided)
      3. Retrieve context from the appropriate source
      4. Build prompt with the right system instruction
      5. Call the LLM
      6. Filter citations strictly to genuinely cited sources
      7. Return response, chunks, and model name

    Returns:
        A tuple of (response_text, retrieved_chunks, model_name).
    """
    from sqlalchemy import select

    is_doc_scoped = bool(document_id or (document_ids and len(document_ids) > 0))
    logger.info(
        f"generate_chat_response called — user_message: '{user_message[:100]}...', "
        f"document_id: {document_id}, document_ids: {document_ids}"
    )

    # ── Step 1: Get conversation history ─────────
    history_result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation.id)
        .order_by(Message.sequence_number.desc())
        .limit(12)
    )
    all_history = list(reversed(history_result.scalars().all()))

    # Exclude the current user message from history
    history = [m for m in all_history if not (m.role == "user" and m.content == user_message)]
    if len(history) == len(all_history) and all_history:
        history = all_history[:-1]

    # ── Step 2: Classify intent ──────────────────
    if is_doc_scoped:
        intent = QueryIntent.DOCUMENT
    else:
        intent = classify_intent(user_message, history)
    logger.info(f"Query intent classified as: {intent.value} (scoped_docs={is_doc_scoped})")

    # ── Step 3: Retrieve context based on intent ─
    chunks: list[RetrievedChunk] = []
    extra_context = ""
    system_prompt = SYSTEM_PROMPT_GENERAL

    if intent == QueryIntent.URL:
        # Extract and fetch URL content (web page or YouTube transcript)
        urls = _extract_urls(user_message)
        if urls:
            system_prompt = SYSTEM_PROMPT_URL
            url_contents = []
            for url in urls[:3]:  # Limit to 3 URLs
                try:
                    from app.rag.parser import fetch_url_content
                    content = await fetch_url_content(url)
                    # Trim to avoid token overflow
                    trimmed = content[:8000] if len(content) > 8000 else content
                    url_contents.append(f"Content from {url}:\n{trimmed}")

                    # Generate citation chunk for the UI
                    snippet_preview = trimmed[:350].replace("\n", " ")
                    chunks.append(
                        RetrievedChunk(
                            chunk_id=f"url-{len(chunks)+1}",
                            content=trimmed[:3000],
                            document_id="",
                            document_title=f"Source: {url[:50]}",
                            source_url=url,
                            page_number=None,
                            chunk_index=len(chunks) + 1,
                            relevance_score=1.0,
                        )
                    )
                    logger.info(f"Fetched URL content: {url} ({len(content)} chars)")
                except Exception as e:
                    url_contents.append(f"Failed to fetch {url}: {str(e)}")
                    logger.warning(f"URL fetch failed for {url}: {e}")
            extra_context = "\n\n---\n\n".join(url_contents)

    elif intent == QueryIntent.MCP_TOOL:
        # Execute relevant MCP tool
        system_prompt = SYSTEM_PROMPT_MCP
        try:
            from app.mcp.registry import get_tool_registry
            from app.mcp.executor import execute_mcp_tool

            registry = await get_tool_registry()
            available_tools = registry.list_enabled_tools()

            if available_tools:
                tool = _match_mcp_tool(user_message, available_tools)
                if tool:
                    arguments = _extract_tool_arguments(user_message, tool)
                    logger.info(f"Matched MCP tool: {tool.name} with arguments: {arguments}")
                    result = await execute_mcp_tool(
                        tool_name=tool.name,
                        arguments=arguments,
                        user_id=user_id,
                        conversation_id=conversation.id,
                        db=db,
                    )
                    if result["status"] == "success":
                        tool_output = str(result["result"])
                        if len(tool_output) > 6000:
                            tool_output = tool_output[:6000] + "\n... (truncated)"
                        extra_context = (
                            f"Tool Executed: {tool.name}\n"
                            f"Tool Description: {tool.description}\n"
                            f"Actual Result from Tool:\n{tool_output}"
                        )
                    else:
                        extra_context = (
                            f"Tool '{tool.name}' returned an error: {result['error']}\n"
                            "Please provide a helpful and honest response explaining this failure."
                        )
                else:
                    tool_list = "\n".join(
                        f"- {t.name}: {t.description}" for t in available_tools
                    )
                    extra_context = (
                        f"No exact matching tool for query. Available tools:\n{tool_list}"
                    )
                    system_prompt = SYSTEM_PROMPT_GENERAL
            else:
                extra_context = "No MCP tools are currently available."
                system_prompt = SYSTEM_PROMPT_GENERAL
        except Exception as e:
            logger.warning(f"MCP tool execution failed: {e}")
            extra_context = f"MCP tool integration encountered an error: {str(e)}"
            system_prompt = SYSTEM_PROMPT_GENERAL

    else:
        # Document retrieval for DOCUMENT, FOLLOW_UP, or GENERAL when documents exist
        retrieval_query = _build_retrieval_query(user_message, history)
        retriever = get_retriever()
        retrieved_chunks = retriever.retrieve(
            query=retrieval_query,
            user_id=user_id,
            document_id=document_id,
            document_ids=document_ids,
        )

        # Scoped document queries use 0.40; explicit document queries use 0.50; unprompted general use 0.68
        if is_doc_scoped:
            min_threshold = 0.40
        elif intent == QueryIntent.DOCUMENT:
            min_threshold = 0.50
        else:
            min_threshold = 0.68

        if retrieved_chunks and retrieved_chunks[0].relevance_score >= min_threshold:
            # Filter chunks to those above the threshold
            chunks = [c for c in retrieved_chunks if c.relevance_score >= min_threshold]
            extra_context = _build_document_context(chunks)
            system_prompt = SYSTEM_PROMPT_DOCUMENT
            logger.info(f"Using {len(chunks)} document chunks (top score: {chunks[0].relevance_score})")
        elif intent == QueryIntent.DOCUMENT or is_doc_scoped:
            # User specifically asked for document context, but no documents match
            extra_context = (
                f"DOCUMENT CONTEXT NOTICE: The user explicitly requested information from specific document(s), "
                f"but no matching passages were found for '{user_message}'. "
                f"State clearly: 'The provided document(s) do not contain information regarding this topic.' "
                f"Do not guess or fabricate information."
            )
            system_prompt = SYSTEM_PROMPT_DOCUMENT
        else:
            chunks = []
            system_prompt = SYSTEM_PROMPT_GENERAL

    logger.info(f"Retrieved {len(chunks)} context chunks for chat (intent: {intent.value})")

    # ── Step 4: Build LLM messages ───────────────
    messages: list[LLMMessage] = []

    # Add recent conversation history for continuity (last 6 messages)
    for msg in history[-6:]:
        messages.append(LLMMessage(role=msg.role, content=msg.content))

    # Build the user message with context if available
    if extra_context:
        user_prompt = f"{extra_context}\n\n---\n\nUser Question: {user_message}"
    else:
        user_prompt = user_message

    messages.append(LLMMessage(role="user", content=user_prompt))

    # ── Step 5: Call the LLM ─────────────────────
    llm = get_llm_provider()
    model_name = llm.get_model_name()

    logger.info(
        f"Calling LLM ({model_name}) with {len(messages)} messages, "
        f"intent={intent.value}, has_context={bool(extra_context)}"
    )

    # Use lower temperature for document grounding, higher for general chat
    temperature = 0.2 if intent == QueryIntent.DOCUMENT else 0.5

    response = await llm.generate(
        messages=messages,
        system_prompt=system_prompt,
        temperature=temperature,
    )

    logger.info(
        f"LLM response generated — model: {response.model}, "
        f"tokens: {response.total_tokens}, intent: {intent.value}, "
        f"response_length: {len(response.content)}"
    )

    # ── Step 6: Filter citations strictly to genuinely cited sources ──
    # Find all citation numbers [1], [2], etc. referenced in the LLM response text
    cited_nums = set(int(m) for m in re.findall(r'\[(\d+)\]', response.content))
    if cited_nums and chunks:
        # Keep only the chunks whose passage index was genuinely cited
        cited_chunks = [c for c in chunks if getattr(c, "citation_index", None) in cited_nums]
        if cited_chunks:
            logger.info(
                f"Filtered {len(chunks)} candidate chunks to {len(cited_chunks)} cited chunks: {cited_nums}"
            )
            chunks = cited_chunks
    elif intent == QueryIntent.GENERAL and not document_id:
        # General query with no cited references should not display ungrounded citations
        chunks = []
    elif chunks and not cited_nums:
        # Document query where LLM answered without explicit bracket numbers; retain only top grounded chunk
        chunks = [chunks[0]] if chunks[0].relevance_score >= 0.70 else []

    return response.content, chunks, response.model


# ── MCP Helper Functions ────────────────────────────────────

def _match_mcp_tool(user_message: str, tools: list) -> Optional[object]:
    """Find the best matching MCP tool for the user's message."""
    msg_lower = user_message.lower()

    # Prioritize specific tool matches based on intent keywords
    if any(k in msg_lower for k in ["github", "repository", "repositories", "repo"]):
        if "code" in msg_lower:
            for t in tools:
                if "github_search_code" in t.name:
                    return t
        for t in tools:
            if "github_search_repositories" in t.name or "repository" in t.name:
                return t

    if any(k in msg_lower for k in ["calculate", "calculator", "math", "compute", "eval"]):
        for t in tools:
            if "calculator" in t.name:
                return t

    if any(k in msg_lower for k in ["fetch", "webpage", "web content"]) and URL_PATTERN.search(user_message):
        for t in tools:
            if "fetch_web_content" in t.name:
                return t

    # Score-based fallback
    best_tool = None
    best_score = 0
    for tool in tools:
        score = 0
        tool_name_lower = tool.name.lower().replace("_", " ").replace("-", " ")
        tool_desc_lower = (tool.description or "").lower()

        for word in tool_name_lower.split():
            if word in msg_lower and len(word) > 2:
                score += 3
        for word in tool_desc_lower.split():
            if word in msg_lower and len(word) > 3:
                score += 1

        if score > best_score:
            best_score = score
            best_tool = tool

    return best_tool if best_score >= 3 else (tools[0] if tools else None)


def _extract_tool_arguments(user_message: str, tool) -> dict:
    """Extract tool arguments from the user's message accurately."""
    arguments = {}
    schema = tool.input_schema or {}
    properties = schema.get("properties", {})
    if not properties:
        return arguments

    # 1. Try quoted strings first
    quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', user_message)
    if quoted:
        val = quoted[0][0] or quoted[0][1]
        first_prop = list(properties.keys())[0]
        arguments[first_prop] = val.strip()
        return arguments

    # 2. Extract based on tool pattern
    msg_clean = user_message.strip()
    if tool.name in ("github_search_repositories", "github_search_code"):
        # Strip common search trigger prefixes
        cleaned = re.sub(
            r'^(?:please\s+)?(?:search\s+github\s+(?:for\s+)?|github\s+search\s+|search\s+repositories\s+(?:for\s+)?|search\s+repos\s+(?:for\s+)?|search\s+code\s+(?:for\s+)?|find\s+repos\s+(?:for\s+)?)',
            '',
            msg_clean,
            flags=re.IGNORECASE,
        ).strip()
        arguments["query"] = cleaned if cleaned else msg_clean
    elif tool.name == "fetch_web_content":
        urls = URL_PATTERN.findall(user_message)
        if urls:
            arguments["url"] = urls[0]
        else:
            arguments["url"] = msg_clean
    elif tool.name == "python_calculator":
        cleaned = re.sub(r'^(?:calculate|compute|eval|what is)\s+', '', msg_clean, flags=re.IGNORECASE).strip()
        arguments["expression"] = cleaned if cleaned else msg_clean
    else:
        first_prop = list(properties.keys())[0]
        arguments[first_prop] = msg_clean

    return arguments


# ── Citation Saving ─────────────────────────────────────────

async def save_citations(
    db: AsyncSession,
    message_id: str,
    chunks: list[RetrievedChunk],
) -> list[Citation]:
    """Save citation records linking an assistant message to its source chunks."""
    citations = []
    for i, chunk in enumerate(chunks, 1):
        doc_id = chunk.document_id.strip() if chunk.document_id and chunk.document_id.strip() else None
        citation = Citation(
            message_id=message_id,
            document_id=doc_id,
            chunk_id=chunk.chunk_id,
            source_title=chunk.document_title,
            source_url=chunk.source_url,
            page_number=chunk.page_number,
            snippet=chunk.content[:300],
            relevance_score=chunk.relevance_score,
            citation_index=getattr(chunk, "citation_index", i) or i,
        )
        db.add(citation)
        citations.append(citation)

    await db.flush()
    logger.debug(f"Saved {len(citations)} citations for message {message_id}")
    return citations
