# text_utils.py
import re
from typing import List, Dict, Any, Optional

try:
    # Available in PyQt6
    from PyQt6.QtGui import QTextDocument
except Exception:
    QTextDocument = None


HTML_TAG_RE = re.compile(r"<[^>]+>")
MULTISPACE_RE = re.compile(r"[ \t]+")


def html_to_plaintext(html: str) -> str:
    """
    Converts HTML stored in your scenes to plain text while preserving paragraph breaks.
    Uses QTextDocument when available; falls back to regex stripping.
    """
    html = html or ""

    if QTextDocument is not None:
        doc = QTextDocument()
        doc.setHtml(html)
        text = doc.toPlainText()
    else:
        # fallback: remove tags but preserve <p>/<br> somewhat
        tmp = html
        tmp = re.sub(r"</p\s*>", "\n\n", tmp, flags=re.IGNORECASE)
        tmp = re.sub(r"<br\s*/?>", "\n", tmp, flags=re.IGNORECASE)
        text = HTML_TAG_RE.sub("", tmp)

    # normalize entities-ish
    text = (text
            .replace("\u00a0", " ")
            .replace("&nbsp;", " ")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&amp;", "&")
            .replace("&quot;", "\""))

    # normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # preserve blank lines; trim trailing spaces per line
    lines = [ln.rstrip() for ln in text.split("\n")]
    text = "\n".join(lines)

    # collapse huge vertical gaps a bit (optional)
    text = re.sub(r"\n{4,}", "\n\n\n", text).strip()
    return text


def plaintext_to_html(text: str) -> str:
    """
    Converts plain text back into simple HTML suitable for rich text display.
    Preserves paragraph breaks and single line breaks.
    """
    text = (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return ""

    # Escape minimal HTML chars
    esc = (text.replace("&", "&amp;")
               .replace("<", "&lt;")
               .replace(">", "&gt;"))

    # Paragraphs: split on blank lines
    paras = re.split(r"\n\s*\n", esc)
    html_paras = []
    for p in paras:
        # within paragraph, keep single newlines as <br>
        p = p.strip("\n")
        p = p.replace("\n", "<br>")
        html_paras.append(f"<p>{p}</p>")

    return "\n".join(html_paras)


def sanitize_ai_output(text: str) -> str:
    """
    The AI sometimes returns HTML or collapses whitespace.
    We force it into clean plain text that preserves paragraph breaks.
    """
    raw = text or ""
    # If it contains tags, convert through html_to_plaintext
    if "<" in raw and ">" in raw and re.search(r"</?\w+", raw):
        raw = html_to_plaintext(raw)
    else:
        raw = raw.replace("\u00a0", " ").replace("&nbsp;", " ")

    raw = raw.replace("\r\n", "\n").replace("\r", "\n")

    # Trim trailing spaces per line, but DO NOT collapse newlines into one line
    raw = "\n".join([ln.rstrip() for ln in raw.split("\n")])

    # normalize excessive spaces
    raw = MULTISPACE_RE.sub(" ", raw)

    # keep at most 3 blank lines
    raw = re.sub(r"\n{4,}", "\n\n\n", raw).strip()
    return raw


def build_anchored_paragraphs(text: str) -> List[Dict[str, Any]]:
    """
    Splits plain text into paragraphs and assigns stable ids/indexes for anchoring.
    Returns [{idx, text, start_char, end_char}...]
    """
    t = (text or "").replace("\r\n", "\n").replace("\r", "\n")
    # paragraphs separated by blank lines
    parts = re.split(r"\n\s*\n", t.strip())
    paragraphs = []
    pos = 0
    for idx, p in enumerate(parts, start=1):
        p_norm = p.strip("\n")
        start = pos
        end = pos + len(p_norm)
        paragraphs.append({"idx": idx, "text": p_norm, "start_char": start, "end_char": end})
        pos = end + 2  # approx for separator
    return paragraphs


def format_scene_for_ai(scene_name: str, html_content: str, max_chars: int = 12000) -> Dict[str, Any]:
    """
    Produces AI-friendly plain text + paragraph anchors.
    """
    plain = html_to_plaintext(html_content or "")
    plain = plain[:max_chars]
    paras = build_anchored_paragraphs(plain)
    # Provide numbered paragraphs to AI for precise references.
    numbered = []
    for p in paras:
        numbered.append(f"[P{p['idx']}] {p['text']}")
    return {
        "scene_name": scene_name or "Untitled",
        "plain": plain,
        "paragraphs": paras,
        "numbered_text": "\n\n".join(numbered),
    }
