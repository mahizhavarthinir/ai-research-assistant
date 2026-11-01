"""
AI Research Assistant — Document Parser

Extracts raw text from uploaded files (PDF, TXT, Markdown, DOCX, CSV)
and fetched web pages.
"""

from __future__ import annotations

import csv
import io
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx
from loguru import logger

from app.core.config import settings


# YouTube URL patterns
YOUTUBE_PATTERN = re.compile(
    r'(?:https?:\/\/)?(?:www\.|m\.)?(?:youtube\.com\/(?:watch\?v=|embed\/|shorts\/|v\/)|youtu\.be\/)([a-zA-Z0-9_-]{11})',
    re.IGNORECASE,
)


def extract_youtube_video_id(url: str) -> str | None:
    """Extract an 11-character YouTube video ID from a URL."""
    match = YOUTUBE_PATTERN.search(url)
    if match:
        return match.group(1)
    return None


async def parse_file_sections(file_path: str, file_type: str) -> list[dict]:
    """
    Extract structured sections from a file with accurate page number tracking.
    Returns a list of dicts: [{"page_number": int | None, "content": str}]
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if file_type == "pdf":
        return _parse_pdf_sections(path)
    else:
        # Non-PDF documents don't have distinct physical page numbers
        full_text = await parse_file(file_path, file_type)
        return [{"page_number": None, "content": full_text}]


def _parse_pdf_sections(path: Path) -> list[dict]:
    """Extract text from a PDF page-by-page to accurately preserve page numbers."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("pypdf is required for PDF parsing. Install with: pip install pypdf")

    reader = PdfReader(str(path))
    sections: list[dict] = []

    for i, page in enumerate(reader.pages):
        page_num = i + 1
        page_text = ""
        try:
            page_text = page.extract_text() or ""
        except Exception as e:
            logger.warning(f"Failed standard extraction for page {page_num}: {e}")

        if not page_text.strip():
            try:
                page_text = page.extract_text(extraction_mode="layout") or ""
            except Exception:
                pass

        if page_text and page_text.strip():
            sections.append({
                "page_number": page_num,
                "content": page_text.strip(),
            })

    logger.info(f"Parsed PDF sections: {path.name} — {len(sections)} pages extracted")
    return sections


async def parse_file(file_path: str, file_type: str) -> str:
    """
    Extract text content from a file on disk.

    Supported types: pdf, txt, md, markdown, docx, csv.
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if file_type == "pdf":
        return _parse_pdf(path)
    elif file_type in ("txt", "md", "markdown"):
        return _parse_text(path)
    elif file_type == "docx":
        return _parse_docx(path)
    elif file_type == "csv":
        return _parse_csv(path)
    else:
        # Fallback: try reading as plain text
        logger.warning(f"Unknown file type '{file_type}', attempting plain text read")
        try:
            return _parse_text(path)
        except Exception:
            raise ValueError(f"Unsupported file type: {file_type}")


def _parse_pdf(path: Path) -> str:
    """Extract text from a PDF using pypdf."""
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError(
            "pypdf is required for PDF parsing. Install with: pip install pypdf"
        )

    reader = PdfReader(str(path))
    pages: list[str] = []
    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text()
            if text and text.strip():
                pages.append(f"[Page {i + 1}]\n{text.strip()}")
        except Exception as e:
            logger.warning(f"Failed to extract text from page {i + 1}: {e}")
            continue

    if not pages:
        # Fallback: try extracting with different parameters
        logger.warning(f"Standard text extraction failed for {path.name}, trying fallback")
        for i, page in enumerate(reader.pages):
            try:
                text = page.extract_text(extraction_mode="layout")
                if text and text.strip():
                    pages.append(f"[Page {i + 1}]\n{text.strip()}")
            except Exception:
                continue

    full_text = "\n\n".join(pages)
    logger.info(f"Parsed PDF: {path.name} — {len(reader.pages)} pages, {len(full_text)} chars")
    return full_text


def _parse_text(path: Path) -> str:
    """Read a plain text or Markdown file with multiple encoding fallbacks."""
    # Try multiple encodings
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252", "ascii"):
        try:
            text = path.read_text(encoding=encoding)
            logger.info(f"Parsed text file: {path.name} ({encoding}) — {len(text)} chars")
            return text
        except (UnicodeDecodeError, UnicodeError):
            continue

    # Last resort: read with errors replaced
    text = path.read_text(encoding="utf-8", errors="replace")
    logger.info(f"Parsed text file: {path.name} (utf-8 with replacements) — {len(text)} chars")
    return text


def _parse_docx(path: Path) -> str:
    """Extract text from a Word (.docx) file."""
    try:
        from docx import Document as DocxDocument
    except ImportError:
        raise ImportError(
            "python-docx is required for DOCX parsing. Install with: pip install python-docx"
        )

    doc = DocxDocument(str(path))
    paragraphs: list[str] = []

    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            # Preserve heading structure
            if para.style and para.style.name.startswith("Heading"):
                level = para.style.name.replace("Heading", "").strip()
                prefix = "#" * (int(level) if level.isdigit() else 1)
                paragraphs.append(f"{prefix} {text}")
            else:
                paragraphs.append(text)

    # Also extract text from tables
    for table in doc.tables:
        table_rows: list[str] = []
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                table_rows.append(" | ".join(cells))
        if table_rows:
            paragraphs.append("\n".join(table_rows))

    full_text = "\n\n".join(paragraphs)
    logger.info(f"Parsed DOCX: {path.name} — {len(paragraphs)} sections, {len(full_text)} chars")
    return full_text


def _parse_csv(path: Path) -> str:
    """Extract text from a CSV file, converting to a readable format."""
    text_parts: list[str] = []

    # Try to detect the encoding
    raw_bytes = path.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            content = raw_bytes.decode(encoding)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    else:
        content = raw_bytes.decode("utf-8", errors="replace")

    reader = csv.reader(io.StringIO(content))
    rows = list(reader)

    if not rows:
        return ""

    # First row as headers
    headers = rows[0] if rows else []
    text_parts.append(f"CSV Data with {len(rows) - 1} records and {len(headers)} columns")
    text_parts.append(f"Columns: {', '.join(headers)}")
    text_parts.append("")

    # Convert each row to a readable format
    for i, row in enumerate(rows[1:], 1):
        row_text_parts = []
        for j, cell in enumerate(row):
            if cell.strip():
                header = headers[j] if j < len(headers) else f"Column {j + 1}"
                row_text_parts.append(f"{header}: {cell.strip()}")
        if row_text_parts:
            text_parts.append(f"Record {i}: " + " | ".join(row_text_parts))

    full_text = "\n".join(text_parts)
    logger.info(f"Parsed CSV: {path.name} — {len(rows) - 1} records, {len(full_text)} chars")
    return full_text


async def fetch_youtube_transcript(url_or_video_id: str) -> str:
    """
    Extract video transcript with timestamps from a YouTube URL or video ID.
    Handles various YouTube URL formats and reports failures honestly.
    """
    video_id = extract_youtube_video_id(url_or_video_id) or url_or_video_id
    logger.info(f"Fetching YouTube transcript for video ID: {video_id}")

    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()
        transcript = api.fetch(video_id)

        lines = [
            f"Title: YouTube Video ({video_id})",
            f"Source: https://www.youtube.com/watch?v={video_id}",
            "",
            "TRANSCRIPT (with timestamps):",
        ]

        for item in transcript:
            m_int = int(item.start // 60)
            s_int = int(item.start % 60)
            timestamp = f"[{m_int:02d}:{s_int:02d}]"
            clean_text = item.text.replace("\n", " ").strip()
            if clean_text:
                lines.append(f"{timestamp} {clean_text}")

        full_text = "\n".join(lines)
        logger.info(f"YouTube transcript fetched: {video_id} — {len(lines)} lines, {len(full_text)} chars")
        return full_text

    except Exception as e:
        err_msg = str(e)
        logger.warning(f"Could not extract YouTube transcript for {video_id}: {err_msg}")
        return (
            f"Source: https://www.youtube.com/watch?v={video_id}\n\n"
            f"⚠️ **YouTube Transcript Notice**: Could not retrieve transcript for video `{video_id}`.\n"
            f"Reason: {err_msg}\n\n"
            f"Note: Captions/subtitles may be disabled by the video owner or not yet generated."
        )


def _is_wikimedia_url(url: str) -> bool:
    """Check if the target URL belongs to Wikipedia or the Wikimedia foundation network."""
    try:
        domain = urlparse(url).netloc.lower().split(":")[0]
        wiki_domains = (
            "wikipedia.org", "wikimedia.org", "wiktionary.org", 
            "wikidata.org", "wikibooks.org", "wikinews.org",
            "wikiquote.org", "wikisource.org", "wikiversity.org",
            "wikivoyage.org", "mediawiki.org"
        )
        return any(domain == d or domain.endswith("." + d) for d in wiki_domains)
    except Exception:
        return False


def _get_headers_for_url(url: str, prefer_bot_policy: bool | None = None) -> dict[str, str]:
    """
    Get HTTP headers tailored for the target domain.
    Wikimedia requires compliance with its official User-Agent Robot Policy.
    General websites typically prefer standard modern browser headers.
    """
    use_bot_policy = prefer_bot_policy if prefer_bot_policy is not None else _is_wikimedia_url(url)
    
    if use_bot_policy:
        return {
            "User-Agent": "AIResearchAssistant/1.0 (https://github.com/ai-research-assistant; contact@research-assistant.local) httpx/0.28.1",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
    return {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }


async def fetch_url_content(url: str, fetch_linked_pages: bool = True) -> str:
    """
    Fetch a public web page or YouTube transcript and extract its text content.
    Includes accessible linked-page content when available.
    Features domain-specific headers, automatic 403 bot-block fallbacks, and graceful error messages.
    """
    # Check for YouTube URL first
    if extract_youtube_video_id(url):
        return await fetch_youtube_transcript(url)

    logger.info(f"Fetching URL: {url}")
    is_wiki = _is_wikimedia_url(url)
    primary_headers = _get_headers_for_url(url, prefer_bot_policy=is_wiki)
    fallback_headers = _get_headers_for_url(url, prefer_bot_policy=not is_wiki)

    try:
        async with httpx.AsyncClient(
            timeout=settings.URL_FETCH_TIMEOUT_SECONDS,
            follow_redirects=True,
            headers=primary_headers,
        ) as client:
            try:
                response = await client.get(url)
                # If blocked by strict bot/WAF protections (403, 401, or 429), attempt fallback headers
                if response.status_code in (401, 403, 429):
                    logger.warning(
                        f"Initial fetch for '{url}' returned HTTP {response.status_code}. "
                        "Retrying with alternative user-agent signature..."
                    )
                    resp_alt = await client.get(url, headers=fallback_headers)
                    if resp_alt.is_success:
                        response = resp_alt

                response.raise_for_status()

            except httpx.HTTPStatusError as hse:
                # If still 403 Forbidden, attempt standard urllib fallback in executor thread
                if hse.response.status_code == 403:
                    logger.warning(f"HTTP 403 on '{url}' with httpx. Attempting urllib fallback...")
                    try:
                        import urllib.request

                        req = urllib.request.Request(url, headers=fallback_headers)
                        loop = asyncio.get_event_loop()

                        def _urllib_fetch():
                            with urllib.request.urlopen(req, timeout=settings.URL_FETCH_TIMEOUT_SECONDS) as u_resp:
                                return u_resp.read().decode("utf-8", errors="replace")

                        html_text = await loop.run_in_executor(None, _urllib_fetch)
                        text, _ = _extract_html_content_and_links(html_text, url)
                        logger.info(f"Fetched URL via urllib fallback: {url} — {len(text)} chars extracted")
                        return text
                    except Exception as ue:
                        logger.warning(f"urllib fallback also failed for '{url}': {ue}")
                        raise hse
                else:
                    raise hse

            # Check content size
            content_bytes = len(response.content)
            max_bytes = settings.MAX_URL_FETCH_SIZE_MB * 1024 * 1024
            if content_bytes > max_bytes:
                raise ValueError(
                    f"Page content ({content_bytes / 1024 / 1024:.1f} MB) "
                    f"exceeds the {settings.MAX_URL_FETCH_SIZE_MB} MB limit."
                )

            content_type = response.headers.get("content-type", "")

            if "text/html" in content_type:
                text, internal_links = _extract_html_content_and_links(response.text, url)

                # Optionally fetch up to 2 accessible linked pages on the same domain
                if fetch_linked_pages and internal_links:
                    linked_sections = []
                    for link in internal_links[:2]:
                        try:
                            logger.info(f"Fetching linked page: {link}")
                            link_headers = _get_headers_for_url(link)
                            link_resp = await client.get(link, timeout=8.0, headers=link_headers)
                            if link_resp.is_success and "text/html" in link_resp.headers.get("content-type", ""):
                                sub_text, _ = _extract_html_content_and_links(link_resp.text, link)
                                if sub_text and len(sub_text.strip()) > 100:
                                    linked_sections.append(
                                        f"\n\n--- Linked Page: {link} ---\n{sub_text[:3000]}"
                                    )
                        except Exception as le:
                            logger.debug(f"Could not fetch linked page {link}: {le}")

                    if linked_sections:
                        text += "".join(linked_sections)

            elif "application/json" in content_type:
                # For JSON responses, format them as readable text
                import json

                try:
                    data = json.loads(response.text)
                    text = f"JSON data from {url}:\n\n{json.dumps(data, indent=2)}"
                except json.JSONDecodeError:
                    text = response.text
            elif "text/plain" in content_type:
                text = response.text
            else:
                # Try HTML extraction as fallback, then plain text
                try:
                    text, _ = _extract_html_content_and_links(response.text, url)
                except Exception:
                    text = response.text

    except httpx.HTTPStatusError as hse:
        status_code = hse.response.status_code
        domain_name = urlparse(url).netloc or url
        if status_code == 403:
            raise ValueError(
                f"Access forbidden (HTTP 403): The website '{domain_name}' blocked automated access. "
                "Try saving the webpage as a PDF or copying the text into a .txt file, then upload it directly."
            ) from hse
        elif status_code == 404:
            raise ValueError(
                f"Page not found (HTTP 404): The URL '{url}' does not exist or has been moved."
            ) from hse
        elif status_code == 401:
            raise ValueError(
                f"Authentication required (HTTP 401): The webpage '{url}' requires a login to view."
            ) from hse
        elif status_code == 429:
            raise ValueError(
                f"Rate limit exceeded (HTTP 429): The website '{domain_name}' is limiting automated requests. "
                "Please wait a few minutes before retrying."
            ) from hse
        else:
            raise ValueError(
                f"HTTP {status_code} Error: Could not retrieve webpage from '{url}'."
            ) from hse
    except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout) as te:
        domain_name = urlparse(url).netloc or url
        raise ValueError(
            f"Connection timed out: The website '{domain_name}' took too long to respond. "
            "Please check if the URL is accessible and try again."
        ) from te
    except httpx.ConnectError as ce:
        domain_name = urlparse(url).netloc or url
        raise ValueError(
            f"Could not connect to '{domain_name}': Please verify the URL is correct and online."
        ) from ce
    except Exception as e:
        if isinstance(e, ValueError):
            raise
        raise ValueError(f"Failed to fetch webpage '{url}': {str(e)[:300]}") from e

    logger.info(f"Fetched URL: {url} — {len(text)} chars extracted")
    return text


def _extract_html_content_and_links(html: str, url: str) -> tuple[str, list[str]]:
    """
    Thoroughly extract text content and internal links from HTML.
    Gets main content, headings, lists, paragraphs, metadata, and internal links.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        raise ImportError(
            "beautifulsoup4 is required for HTML parsing. Install with: pip install beautifulsoup4 lxml"
        )

    soup = BeautifulSoup(html, "lxml")

    # Discover accessible internal links on the same domain
    internal_links: list[str] = []
    base_domain = urlparse(url).netloc
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        full_url = urljoin(url, href)
        parsed = urlparse(full_url)
        if (
            parsed.netloc == base_domain
            and full_url != url
            and not any(full_url.endswith(ext) for ext in (".png", ".jpg", ".jpeg", ".gif", ".svg", ".css", ".js", ".pdf", ".zip"))
        ):
            if full_url not in internal_links:
                internal_links.append(full_url)

    # Extract page title and meta description
    parts: list[str] = []

    title_tag = soup.find("title")
    if title_tag and title_tag.string:
        parts.append(f"Title: {title_tag.string.strip()}")

    meta_desc = soup.find("meta", attrs={"name": "description"})
    if meta_desc and meta_desc.get("content"):
        parts.append(f"Description: {meta_desc['content'].strip()}")

    if parts:
        parts.append(f"Source: {url}")
        parts.append("")

    # Remove scripts, styles, nav, footer, ads, and other non-content
    for tag in soup(
        [
            "script", "style", "nav", "footer", "header", "aside",
            "noscript", "iframe", "svg", "form", "button",
            "meta", "link",
        ]
    ):
        tag.decompose()

    # Also remove common ad/tracking divs
    for div in soup.find_all(["div", "section"], class_=lambda x: x and any(
        kw in str(x).lower() for kw in ["cookie", "popup", "modal", "banner", "ad-", "sidebar"]
    )):
        div.decompose()

    # Try to find the main content area (ordered by priority)
    main = (
        soup.find("article")
        or soup.find("main")
        or soup.find("div", {"role": "main"})
        or soup.find("div", {"id": "content"})
        or soup.find("div", {"id": "main-content"})
        or soup.find("div", {"class": "content"})
        or soup.find("body")
    )

    if main:
        text = main.get_text(separator="\n", strip=True)
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)
    else:
        text = ""

    full_extracted = ("\n".join(parts) + "\n" + text) if parts else text
    return full_extracted, internal_links


def _extract_html_content(html: str, url: str) -> str:
    """Backwards-compatible wrapper returning only extracted text."""
    text, _ = _extract_html_content_and_links(html, url)
    return text
