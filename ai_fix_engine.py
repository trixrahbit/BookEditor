# ai_fix_engine.py
from typing import Dict, Any, Optional
from text_utils import format_scene_for_ai, sanitize_ai_output, plaintext_to_html


class AIFixEngine:
    def __init__(self, ai_manager):
        self.ai_manager = ai_manager

    def propose_fix(self, issue_data: Dict[str, Any], scene_name: str, scene_html: str) -> Dict[str, Any]:
        """
        Returns dict:
        {
          "fixed_plain": "...",
          "fixed_html": "<p>...</p>",
          "meta": {...}
        }
        """
        block = format_scene_for_ai(scene_name, scene_html, max_chars=14000)

        issue_type = issue_data.get("type", "general")
        issue = issue_data.get("issue", "")
        detail = issue_data.get("detail", "")
        anchors = issue_data.get("anchors", [])
        quote = issue_data.get("quote", "")

        anchor_hint = ""
        if anchors:
            anchor_hint = f"FOCUS PARAGRAPHS: {', '.join([str(a) for a in anchors])}\n"
        if quote:
            anchor_hint += f"QUOTE: {quote}\n"

        prompt = f"""
You are an expert editor. Fix this specific issue with minimal changes.

RULES:
- Return PLAIN TEXT ONLY (no HTML tags).
- Preserve paragraph breaks and line breaks.
- Do not collapse everything into one paragraph.
- Make minimal edits: only change what is needed to fix the issue.
- Keep the author’s voice.

ISSUE TYPE: {issue_type}
PROBLEM: {issue}
DETAILS: {detail}
{anchor_hint}

TEXT (paragraph anchors like [P3]):
{block["numbered_text"]}

Return ONLY the corrected plain text (no commentary).
""".strip()

        resp = self.ai_manager.call_api(
            messages=[{"role": "user", "content": prompt}],
            system_message="You are a professional editor. Return plain text only. Never return HTML.",
            temperature=0.25,
            max_tokens=5000
        )

        fixed_plain = sanitize_ai_output(resp)
        fixed_html = plaintext_to_html(fixed_plain)

        return {
            "fixed_plain": fixed_plain,
            "fixed_html": fixed_html,
            "meta": {"scene_name": scene_name, "issue_type": issue_type}
        }
