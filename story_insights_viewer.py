"""
Story Insights Viewer - Shows all tracked issues by location with AI Fix
"""
import html
import re

import unicodedata
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QPushButton, QScrollArea, QFrame, QTextEdit, QToolButton,
    QSizePolicy, QMessageBox, QProgressDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QTextDocument
from ai_manager import ai_manager
from typing import Dict, List
import html as _html
from pacing_heatmap import PacingHeatmapWidget


from theme_manager import theme_manager

class CollapsibleSection(QWidget):
    """A widget that can collapse its contents"""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.toggle_btn = QToolButton()
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(True)
        self.toggle_btn.setText(title)
        self.toggle_btn.setArrowType(Qt.ArrowType.DownArrow)
        self.toggle_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_btn.setStyleSheet("""
            QToolButton {
                border: none;
                font-size: 12pt;
                font-weight: bold;
                color: #E0E0E0;
                padding: 10px;
                background: #2D2D2D;
                border-radius: 4px;
                text-align: left;
            }
            QToolButton:hover {
                background: #3D3D3D;
            }
        """)
        self.toggle_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.toggle_btn.toggled.connect(self._on_toggle)

        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(5, 5, 5, 5)
        self.content_layout.setSpacing(10)

        self.layout.addWidget(self.toggle_btn)
        self.layout.addWidget(self.content_area)

    def _on_toggle(self, checked: bool):
        self.content_area.setVisible(checked)
        self.toggle_btn.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)

    def add_widget(self, widget: QWidget):
        self.content_layout.addWidget(widget)

class AIFixWorker(QThread):
    """Worker thread for AI fix suggestions"""
    finished = pyqtSignal(str)  # Fixed text
    error = pyqtSignal(str)

    def __init__(self, issue_data: dict, scene_content: str):
        super().__init__()
        self.issue_data = issue_data or {}
        self.scene_content = scene_content or ""

    @staticmethod
    def html_to_plaintext(html: str) -> str:
        """
        Convert stored HTML to readable plain text for the AI prompt.
        Keeps paragraph breaks; does NOT collapse to a single line.
        """
        doc = QTextDocument()
        doc.setHtml(html or "")
        text = doc.toPlainText()

        # normalize NBSP + trim trailing whitespace
        text = text.replace("\u00a0", " ")
        text = "\n".join([ln.rstrip() for ln in text.splitlines()])

        # keep paragraph breaks but remove excessive blank lines
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        return text

    @staticmethod
    def sanitize_ai_output(text: str) -> str:
        """
        AI sometimes returns HTML or entities. This guarantees plain text with
        preserved paragraphs and no tags.
        """
        raw = (text or "").strip()
        if not raw:
            return ""

        # 1) Decode entities first (&nbsp; etc.)
        raw = html.unescape(raw).replace("\u00a0", " ")

        # 2) If it contains tags, let QTextDocument convert it safely to plain text
        if "<" in raw and ">" in raw:
            doc = QTextDocument()
            doc.setHtml(raw)
            raw = doc.toPlainText()

        # 3) Remove any remaining tags just in case
        raw = re.sub(r"<[^>]+>", "", raw)

        # 4) Normalize whitespace but keep paragraph breaks
        raw = "\n".join([ln.rstrip() for ln in raw.splitlines()])
        raw = re.sub(r"\n{3,}", "\n\n", raw).strip()

        return raw

    def run(self):
        try:
            issue_type = self.issue_data.get('type', 'general')
            issue = self.issue_data.get('issue', '')
            detail = self.issue_data.get('detail', '')
            chapter = self.issue_data.get('chapter', '')

            # ✅ Convert HTML -> plain text for prompt
            clean_content = self.html_to_plaintext(self.scene_content)

            prompt = f"""You are an expert editor. Fix this specific issue in the text.

ISSUE TYPE: {issue_type}
CHAPTER: {chapter}
PROBLEM: {issue}
DETAILS: {detail}

ORIGINAL TEXT:
{clean_content}

Return ONLY corrected PLAIN TEXT (no HTML). Keep the same paragraph structure and spacing as the original. Make minimal changes.

CORRECTED TEXT:"""

            response = ai_manager.call_api(
                messages=[{"role": "user", "content": prompt}],
                system_message=(
                    "You are a professional editor who makes precise, minimal corrections. "
                    "Return plain text only. No HTML, no markdown."
                ),
                temperature=0.3,
                max_tokens=4000
            )

            # Safety: strip any accidental tags the model returns
            fixed = (response or "").strip()
            fixed = re.sub(r"<[^>]+>", "", fixed).strip()

            self.finished.emit(fixed)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))



    def run(self):
        try:
            issue_type = self.issue_data.get("type", "general")
            issue = self.issue_data.get("issue", "")
            detail = self.issue_data.get("detail", "")
            chapter = self.issue_data.get("chapter", "")

            # Convert scene HTML -> plain text (preserve line breaks)
            clean_content = self.html_to_plaintext(self.scene_content)

            # Build AI prompt (explicitly preserve line breaks; forbid HTML/entities)
            prompt = f"""You are an expert editor. Fix this specific issue in the text.

ISSUE TYPE: {issue_type}
CHAPTER: {chapter}
PROBLEM: {issue}
DETAILS: {detail}

ORIGINAL TEXT (plain text, preserve line breaks exactly):
{clean_content}

Rules:
- Output MUST be plain text only (NO HTML tags, NO entities like &lt; &gt; &nbsp;)
- Preserve existing paragraph breaks and spacing
- Make minimal changes (only what's needed)

CORRECTED TEXT:"""

            response = ai_manager.call_api(
                messages=[{"role": "user", "content": prompt}],
                system_message=(
                    "You are a professional editor who makes precise, minimal corrections. "
                    "Return plain text only. Never output HTML or HTML entities."
                ),
                temperature=0.3,
                max_tokens=4000
            )

            fixed_plain = self.sanitize_ai_output(response)
            self.finished.emit(fixed_plain)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))

class IssueCard(QFrame):
    """Visual card for displaying an issue with AI fix capability"""

    def __init__(self, issue_data: dict, db_manager=None, project_id=None):
        super().__init__()
        self.issue_data = issue_data or {}
        self.db_manager = db_manager
        self.project_id = project_id
        self.details_visible = False
        self.fix_worker = None
        self.suggested_fix = None
        self.init_ui()

    def init_ui(self):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background: #252526;
                border: 1px solid #3D3D3D;
                border-radius: 8px;
                padding: 15px;
                margin: 5px;
            }
            QFrame:hover {
                border-color: #7C4DFF;
                background: #2D2D30;
            }
        """)

        layout = QVBoxLayout(self)

        # Header with severity badge and Fix button
        header = QHBoxLayout()

        severity = str(self.issue_data.get('severity', 'Minor'))
        severity_badge = QLabel(severity)
        severity_badge.setStyleSheet(self._get_severity_style(severity))

        fm = severity_badge.fontMetrics()
        severity_badge.setMinimumHeight(fm.height() + 14)
        severity_badge.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        severity_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        header.addWidget(severity_badge)
        header.addStretch()

        # Add Fix button if we have db_manager
        if self.db_manager and self.project_id:
            self.fix_btn = QPushButton("🔧 AI Fix")
            self.fix_btn.setStyleSheet("""
                QPushButton {
                    background: #667eea;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #5a67d8;
                }
                QPushButton:disabled {
                    background: #adb5bd;
                }
            """)
            self.fix_btn.clicked.connect(self._request_fix)
            header.addWidget(self.fix_btn)

            # Strengths don't need a fix button
            if severity == "Strength":
                self.fix_btn.hide()

        location_label = QLabel(f"📍 {self.issue_data.get('location', 'Unknown')}")
        location_label.setStyleSheet("color: #A0A0A0; font-size: 10pt; margin-left: 10px;")
        location_label.setWordWrap(True)
        header.addWidget(location_label)

        layout.addLayout(header)

        # Issue title
        title = QLabel(self.issue_data.get('issue', 'No description'))
        title.setWordWrap(True)
        title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #E0E0E0; margin: 8px 0;")
        layout.addWidget(title)

        # Chapter info
        chapter = QLabel(f"Chapter: {self.issue_data.get('chapter', 'Unknown')}")
        chapter.setWordWrap(True)
        chapter.setStyleSheet("color: #A0A0A0; font-size: 10pt; margin-bottom: 8px;")
        layout.addWidget(chapter)

        # Collapsible details
        detail_text = (self.issue_data.get('detail') or "").strip()
        suggestions = self.issue_data.get('suggestions')

        collapsible = (
            severity in {"Suggestion", "Strength", "Observation"}
            or bool(suggestions)
            or len(detail_text) > 180
        )

        if collapsible and (detail_text or suggestions):
            self.toggle_btn = QToolButton()
            self.toggle_btn.setCheckable(True)
            self.toggle_btn.setChecked(False)
            self.toggle_btn.setArrowType(Qt.ArrowType.RightArrow)
            self.toggle_btn.setText(" Details")
            self.toggle_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            self.toggle_btn.setStyleSheet("""
                QToolButton {
                    border: none;
                    color: #7C4DFF;
                    font-weight: bold;
                    padding: 4px 0;
                }
                QToolButton:hover { color: #9E7BFF; }
            """)
            self.toggle_btn.toggled.connect(self._toggle_details)
            layout.addWidget(self.toggle_btn)

            self.details_container = QWidget()
            details_layout = QVBoxLayout(self.details_container)
            details_layout.setContentsMargins(0, 6, 0, 0)
            details_layout.setSpacing(6)

            if detail_text:
                detail = QLabel(detail_text)
                detail.setWordWrap(True)
                detail.setStyleSheet("color: #A0A0A0; font-size: 10pt;")
                details_layout.addWidget(detail)

            if suggestions:
                if isinstance(suggestions, list):
                    sug_text = "\n".join([f"• {str(s).strip()}" for s in suggestions if str(s).strip()])
                else:
                    sug_text = str(suggestions).strip()

                if sug_text:
                    sug_label = QLabel("💡 Suggestions")
                    sug_label.setStyleSheet("color: #E0E0E0; font-weight: bold; margin-top: 4px;")
                    details_layout.addWidget(sug_label)

                    sug_body = QLabel(sug_text)
                    sug_body.setWordWrap(True)
                    sug_body.setStyleSheet("color: #A0A0A0; font-size: 10pt;")
                    details_layout.addWidget(sug_body)

            self.details_container.setVisible(False)
            layout.addWidget(self.details_container)
        else:
            if detail_text:
                detail = QLabel(detail_text)
                detail.setWordWrap(True)
                detail.setStyleSheet("color: #A0A0A0; font-size: 10pt;")
                layout.addWidget(detail)

    def _norm_scene_key(s: str) -> str:
        s = (s or "").strip()
        if not s:
            return ""

        # decode entities (&quot; etc) and normalize unicode
        s = _html.unescape(s)
        s = unicodedata.normalize("NFKC", s)

        # normalize common punctuation differences
        s = (s.replace("\u201c", '"').replace("\u201d", '"')  # “ ”
             .replace("\u2018", "'").replace("\u2019", "'")  # ‘ ’
             .replace("\u2013", "-").replace("\u2014", "-")  # – —
             .replace("\u00a0", " "))  # NBSP

        # collapse whitespace, case-insensitive compare
        s = re.sub(r"\s+", " ", s).strip().casefold()
        return s

    def _request_fix(self):
        """Request AI fix for this issue"""
        from PyQt6.QtWidgets import QMessageBox, QProgressDialog
        from models.project import ItemType
        import re
        import unicodedata
        import html as _html

        def _norm_scene_key(s: str) -> str:
            """Normalize strings so 'smart quotes', dashes, nbsp, and whitespace don't break matching."""
            s = (s or "").strip()
            if not s:
                return ""

            # decode entities (&quot; etc) and normalize unicode forms
            s = _html.unescape(s)
            s = unicodedata.normalize("NFKC", s)

            # normalize punctuation differences
            s = (s.replace("\u201c", '"').replace("\u201d", '"')  # “ ”
                 .replace("\u2018", "'").replace("\u2019", "'")  # ‘ ’
                 .replace("\u2013", "-").replace("\u2014", "-")  # – —
                 .replace("\u00a0", " "))  # NBSP

            # collapse whitespace & casefold
            s = re.sub(r"\s+", " ", s).strip().casefold()
            return s

        # Find the scene with this issue
        location = self.issue_data.get('location', '') or ''
        chapter_name = self.issue_data.get('chapter', '') or ''
        issue_type = (self.issue_data.get("type") or "").lower()
        strict_single_scene = issue_type in {"timeline", "consistency"}

        print(f"Looking for scene: '{location}' in chapter: '{chapter_name}'")

        # Load the scene content
        scenes = self.db_manager.load_items(self.project_id, ItemType.SCENE)
        chapters = self.db_manager.load_items(self.project_id, ItemType.CHAPTER)

        # Find the chapter first
        target_chapter = None
        chap_key = _norm_scene_key(chapter_name)
        for ch in chapters:
            # Normalize both sides so "Chapter 9: X" matches even if punctuation varies
            if _norm_scene_key(getattr(ch, "name", "")) == chap_key or (
                    chap_key and chap_key in _norm_scene_key(getattr(ch, "name", ""))):
                target_chapter = ch
                break

        # Determine scene_names
        scene_names = []

        if strict_single_scene:
            # timeline/consistency must be single-scene; never expand to many
            scene_names = [(location or "").strip()] if (location or "").strip() else []
        else:
            if location in ["Multiple scenes", "Throughout chapter", "Unknown"]:
                if target_chapter:
                    scene_names = [
                        s.name for s in scenes
                        if getattr(s, 'parent_id', None) == target_chapter.id
                    ]
            else:
                # keep your existing exact-match + split logic
                exact_match = False
                for s in scenes:
                    if (s.name or "") == location:
                        scene_names = [location]
                        exact_match = True
                        break

                if not exact_match:
                    if ' / ' in location or ' -> ' in location or ' → ' in location or ', ' in location or ' and ' in location:
                        location_normalized = re.sub(r'\s*(?:/|->|→|,)\s+', '|', location)
                        location_normalized = re.sub(r'\s+and\s+', '|', location_normalized)
                        scene_names = [name.strip() for name in location_normalized.split('|') if name.strip()]
                    else:
                        scene_names = [location]

        print(f"Parsed scene names: {scene_names}")

        # Find matching scenes
        target_scenes = []

        # Best case: use stable identifier
        scene_id = self.issue_data.get("scene_id")
        if scene_id:
            scene = self.db_manager.load_item(scene_id)
            if scene:
                target_scenes = [scene]
        else:
            expected_name = (scene_names[0] if scene_names else (location or "")).strip()
            expected_key = _norm_scene_key(expected_name)

            if expected_key:
                # 1) exact match after normalization (fixes smart quotes/dashes/nbsp/spacing issues)
                exact = [s for s in scenes if _norm_scene_key(getattr(s, "name", "")) == expected_key]

                if len(exact) == 1:
                    target_scenes = exact
                elif len(exact) > 1:
                    # duplicate names -> prefer within chapter if possible
                    if target_chapter:
                        exact_in_chapter = [
                            s for s in exact
                            if getattr(s, "parent_id", None) == target_chapter.id
                        ]
                        if len(exact_in_chapter) == 1:
                            target_scenes = exact_in_chapter
                        else:
                            target_scenes = exact
                    else:
                        target_scenes = exact
                else:
                    # 2) strict fallback: only allow exact match WITHIN chapter after normalization
                    if target_chapter:
                        in_chapter = [
                            s for s in scenes
                            if getattr(s, "parent_id", None) == target_chapter.id
                        ]
                        exact_in_chapter = [
                            s for s in in_chapter
                            if _norm_scene_key(getattr(s, "name", "")) == expected_key
                        ]
                        if len(exact_in_chapter) == 1:
                            target_scenes = exact_in_chapter

        # Remove duplicates while preserving order
        seen = set()
        unique_scenes = []
        for s in target_scenes:
            sid = getattr(s, "id", None)
            if sid and sid not in seen:
                seen.add(sid)
                unique_scenes.append(s)
        target_scenes = unique_scenes

        print(f"Found {len(target_scenes)} matching scene(s)")

        if not target_scenes:
            # Helpful debug: show a few candidates in the same chapter (normalized contains)
            candidates = []
            expected_key = _norm_scene_key((scene_names[0] if scene_names else location) or "")
            if expected_key:
                for s in scenes:
                    if target_chapter and getattr(s, "parent_id", None) != target_chapter.id:
                        continue
                    name_key = _norm_scene_key(getattr(s, "name", ""))
                    if expected_key in name_key or name_key in expected_key:
                        candidates.append(getattr(s, "name", ""))
                    if len(candidates) >= 6:
                        break

            extra = ""
            if candidates:
                extra = "\n\nClosest scene name(s) in this chapter:\n- " + "\n- ".join(candidates)

            QMessageBox.warning(
                self,
                "Scene Not Found",
                f"Could not find scene(s) for location '{location}' in chapter '{chapter_name}'.\n\n"
                f"Parsed scene names: {', '.join(scene_names) if scene_names else 'None'}"
                f"{extra}\n\n"
                "Tip: storing issue['scene_id'] during analysis makes this 100% reliable."
            )
            return

        # If multiple scenes were found
        if len(target_scenes) > 1:
            if strict_single_scene:
                QMessageBox.warning(
                    self,
                    "Ambiguous Scene Match",
                    "This timeline/consistency issue should map to exactly ONE scene, "
                    "but multiple scenes matched.\n\n"
                    f"Location: {location}\nChapter: {chapter_name}\n\n"
                    "Fix: store a 'scene_id' in each issue so matching is exact."
                )
                return

            from PyQt6.QtWidgets import QInputDialog
            scene_choices = [f"{s.name} ({len(s.content or '')} chars)" for s in target_scenes]
            scene_choices.insert(0, f"All {len(target_scenes)} scenes (combined)")

            choice, ok = QInputDialog.getItem(
                self,
                "Multiple Scenes Found",
                "This issue affects multiple scenes:\n\nWhich would you like to fix?",
                scene_choices,
                0,
                False
            )
            if not ok:
                return

            if choice.startswith("All"):
                combined_content = "\n\n---SCENE BREAK---\n\n".join([
                    f"SCENE: {s.name}\n{s.content or ''}" for s in target_scenes
                ])

                class CombinedScene:
                    def __init__(self, scenes_):
                        self.scenes = scenes_
                        self.name = f"{len(scenes_)} scenes"
                        self.content = combined_content

                target_scene = CombinedScene(target_scenes)
            else:
                idx = scene_choices.index(choice)
                target_scene = target_scenes[idx - 1] if idx > 0 else target_scenes[0]
        else:
            target_scene = target_scenes[0]

        print(f"Fixing scene: {target_scene.name}")

        # Show progress
        progress = QProgressDialog("AI is analyzing and fixing the issue...", "Cancel", 0, 0, self)
        progress.setWindowTitle("AI Fix")
        progress.setMinimumDuration(0)
        progress.setValue(0)

        # Disable fix button
        self.fix_btn.setEnabled(False)
        self.fix_btn.setText("⏳ Fixing...")

        # Start AI fix worker
        self.fix_worker = AIFixWorker(self.issue_data, target_scene.content)

        def on_finished(fixed_text):
            progress.close()
            self.fix_btn.setEnabled(True)
            self.fix_btn.setText("🔧 AI Fix")
            self._show_fix_approval(target_scene, fixed_text, target_scenes if len(target_scenes) > 1 else None)

        def on_error(error):
            progress.close()
            self.fix_btn.setEnabled(True)
            self.fix_btn.setText("🔧 AI Fix")
            QMessageBox.critical(self, "Fix Error", f"Failed to generate fix:\n\n{error}")

        self.fix_worker.finished.connect(on_finished)
        self.fix_worker.error.connect(on_error)
        progress.canceled.connect(self.fix_worker.terminate)
        self.fix_worker.start()

    def _show_fix_approval(self, scene, fixed_text, all_scenes=None):
        """Show dialog to approve or deny the fix (preview as plain text; save back as HTML for the editor)."""
        dialog = QDialog(self)
        dialog.setWindowTitle("Approve AI Fix")
        dialog.setMinimumSize(800, 600)

        layout = QVBoxLayout(dialog)

        # --- helpers -------------------------------------------------------------

        def html_to_plaintext(html_text: str) -> str:
            """Convert editor HTML -> plain text while preserving paragraph breaks."""
            doc = QTextDocument()
            doc.setHtml(html_text or "")
            text = doc.toPlainText()
            text = text.replace("\u00a0", " ")
            text = "\n".join(ln.rstrip() for ln in text.splitlines())
            return text.strip()

        def sanitize_ai_output(text: str) -> str:
            """Ensure AI output is plain text (no HTML, no entities), preserving line breaks."""
            t = (text or "").strip()

            # If it looks like HTML, render it to plain text
            if "<" in t and ">" in t:
                doc = QTextDocument()
                doc.setHtml(t)
                t = doc.toPlainText()

            # Decode entities (&lt; &nbsp; etc.)
            t = _html.unescape(t)

            # Normalize newlines
            t = t.replace("\r\n", "\n").replace("\r", "\n")

            # Trim trailing spaces per line, keep paragraph breaks
            t = "\n".join(ln.rstrip() for ln in t.splitlines())

            return t.strip()

        def plaintext_to_editor_html(text: str) -> str:
            """
            Convert plain text -> HTML that your QTextEdit can render with preserved line breaks.
            (Use <br> for line breaks; escape HTML.)
            """
            t = (text or "")
            t = t.replace("\u00a0", " ")
            t = t.replace("\r\n", "\n").replace("\r", "\n")
            # Escape, then convert newlines to <br>
            t = _html.escape(t)
            t = t.replace("\n", "<br>\n")
            return t

        # --- header --------------------------------------------------------------

        header = QLabel(f"AI Fix for: {self.issue_data.get('issue', 'Unknown Issue')}")
        header.setStyleSheet("font-size: 14pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(header)

        scene_info = f"<b>Scene:</b> {scene.name}<br>" if hasattr(scene, "name") else ""
        if all_scenes:
            scene_info = f"<b>Scenes:</b> {len(all_scenes)} scenes combined<br>"

        issue_info = QLabel(
            f"<b>Chapter:</b> {self.issue_data.get('chapter', 'Unknown')}<br>"
            f"{scene_info}"
            f"<b>Problem:</b> {self.issue_data.get('detail', 'No details')}"
        )
        issue_info.setWordWrap(True)
        issue_info.setStyleSheet("background: #f8f9fa; padding: 10px; border-radius: 4px; margin-bottom: 10px;")
        layout.addWidget(issue_info)

        # --- tabs ---------------------------------------------------------------

        tabs = QTabWidget()

        # Original preview (plain text)
        original_text = QTextEdit()
        original_text.setReadOnly(True)
        original_plain = html_to_plaintext(getattr(scene, "content", "") or "")
        original_text.setPlainText(original_plain)
        original_text.setStyleSheet("font-family: 'Courier New', monospace; font-size: 10pt; background: #fff3cd;")
        tabs.addTab(original_text, "📝 Original")

        # Fixed preview (plain text, sanitized)
        fixed_text_widget = QTextEdit()
        fixed_text_widget.setReadOnly(True)
        clean_fixed = sanitize_ai_output(fixed_text)
        fixed_text_widget.setPlainText(clean_fixed)
        fixed_text_widget.setStyleSheet("font-family: 'Courier New', monospace; font-size: 10pt; background: #d4edda;")
        tabs.addTab(fixed_text_widget, "✨ AI Fixed")

        layout.addWidget(tabs)

        # --- buttons ------------------------------------------------------------

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        deny_btn = QPushButton("❌ Deny")
        deny_btn.setStyleSheet("""
            QPushButton {
                background: #dc3545;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background: #c82333; }
        """)
        deny_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(deny_btn)

        approve_btn = QPushButton("✅ Approve & Apply")
        approve_btn.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background: #218838; }
        """)
        approve_btn.clicked.connect(dialog.accept)
        button_layout.addWidget(approve_btn)

        layout.addLayout(button_layout)

        # --- apply --------------------------------------------------------------

        if dialog.exec() == QDialog.DialogCode.Accepted:
            # IMPORTANT:
            # - clean_fixed is plain text (no HTML)
            # - your editor stores HTML in scene.content, so convert back to safe HTML
            fixed_html = plaintext_to_editor_html(clean_fixed)

            if all_scenes:
                QMessageBox.information(
                    self,
                    "Multiple Scenes",
                    f"Fix approved for {len(all_scenes)} scenes.\n\n"
                    f"Note: The AI generated a combined fix. You may need to manually "
                    f"distribute the changes across the individual scenes."
                )
                all_scenes[0].content = fixed_html
                self.db_manager.save_item(self.project_id, all_scenes[0])
            else:
                scene.content = fixed_html
                self.db_manager.save_item(self.project_id, scene)

            self.fix_btn.setText("✓ Fixed")
            self.fix_btn.setStyleSheet("""
                QPushButton {
                    background: #28a745;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                }
            """)
            self.fix_btn.setEnabled(False)

            scene_name = scene.name if hasattr(scene, "name") else "selected scenes"
            QMessageBox.information(self, "Fix Applied", f"The fix has been applied to '{scene_name}'!")

    def _toggle_details(self, checked: bool):
        self.details_visible = checked
        self.details_container.setVisible(checked)
        self.toggle_btn.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)

    def _get_severity_style(self, severity: str) -> str:
        """Get CSS style for severity badge"""
        styles = {
            'Critical': "background: #dc3545; color: white; padding: 6px 14px; border-radius: 14px; font-weight: bold;",
            'Major': "background: #fd7e14; color: white; padding: 6px 14px; border-radius: 14px; font-weight: bold;",
            'Minor': "background: #ffc107; color: black; padding: 6px 14px; border-radius: 14px; font-weight: bold;",
            'Suggestion': "background: #0dcaf0; color: white; padding: 6px 14px; border-radius: 14px;",
            'Strength': "background: #198754; color: white; padding: 6px 14px; border-radius: 14px;",
            'Observation': "background: #6c757d; color: white; padding: 6px 14px; border-radius: 14px;"
        }
        return styles.get(severity, styles['Observation'])


class StoryInsightsViewer(QDialog):
    """Main dialog for viewing all story insights"""
    rerun_pacing_requested = pyqtSignal()
    jump_requested = pyqtSignal(dict)

    def __init__(self, parent=None, db_manager=None, project_id=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.project_id = project_id
        self.timeline_data = None
        self.consistency_data = None
        self.style_data = None
        self.pacing_data = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Story Insights")
        self.setMinimumSize(1000, 800)

        layout = QVBoxLayout(self)

        # Header
        self.header = QLabel("🔮 Story Intelligence Report")
        self.header.setObjectName("dialogHeader")
        layout.addWidget(self.header)

        # Tabs for different analysis types
        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)

        # Pacing Heatmap tab
        self.pacing_tab = self.create_pacing_tab()
        self.tabs.addTab(self.pacing_tab, "📉 Pacing Heatmap")

        # Timeline tab
        self.timeline_tab = self.create_issues_tab()
        self.tabs.addTab(self.timeline_tab, "⏰ Timeline Issues")

        # Consistency tab
        self.consistency_tab = self.create_issues_tab()
        self.tabs.addTab(self.consistency_tab, "🔍 Consistency Issues")

        # Style tab
        self.style_tab = self.create_issues_tab()
        self.tabs.addTab(self.style_tab, "✍️ Writing Style")

        # Full Reports tab
        self.reports_tab = self.create_reports_tab()
        self.tabs.addTab(self.reports_tab, "📄 Full Reports")

        layout.addWidget(self.tabs)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
        self.apply_modern_style()

    def apply_modern_style(self):
        """Apply modern styling"""
        self.setStyleSheet(theme_manager.get_dialog_stylesheet())
        self.header.setObjectName("settingsHeader")

    def create_issues_tab(self) -> QWidget:
        """Create a tab for displaying issues"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Scroll area for issues
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(10)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Store reference to scroll layout for adding issues
        widget.scroll_layout = scroll_layout
        widget.scroll_widget = scroll_widget

        return widget

    def create_pacing_tab(self) -> QWidget:
        """Create tab for pacing heatmap"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Pacing heatmap
        self.heatmap = PacingHeatmapWidget()
        self.heatmap.scene_selected.connect(self._on_pacing_scene_selected)
        layout.addWidget(self.heatmap)
        
        # Legend or info
        info_layout = QHBoxLayout()
        info = QLabel("The heatmap shows intensity (🔵 calm → 🔴 intense). "
                      "The dashed line shows the tension curve. "
                      "The bottom bar shows dialogue (gold) vs exposition (grey).")
        info.setWordWrap(True)
        info.setStyleSheet("color: #A0A0A0; padding: 10px;")
        info_layout.addWidget(info, 1)
        
        # Re-run button
        rerun_btn = QPushButton("🔄 Re-Run Pace Analysis")
        rerun_btn.clicked.connect(self.rerun_pacing_requested.emit)
        info_layout.addWidget(rerun_btn)
        
        layout.addLayout(info_layout)
        
        layout.addStretch()
        return widget

    def create_reports_tab(self) -> QWidget:
        """Create tab for full text reports"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.reports_text = QTextEdit()
        self.reports_text.setReadOnly(True)
        # Inherits the modern style from apply_modern_style
        layout.addWidget(self.reports_text)

        return widget

    def load_timeline_data(self, data: dict):
        """Load timeline analysis data"""
        self.timeline_data = data
        self._populate_issues_tab(self.timeline_tab, data.get('issues', []))
        self._update_reports()

    def load_consistency_data(self, data: dict):
        """Load consistency analysis data"""
        self.consistency_data = data
        self._populate_issues_tab(self.consistency_tab, data.get('issues', []))
        self._update_reports()

    def load_style_data(self, data: dict):
        """Load style analysis data"""
        self.style_data = data
        self._populate_issues_tab(self.style_tab, data.get('issues', []))
        self._update_reports()

    def load_pacing_data(self, data: dict):
        """Load pacing analysis data"""
        self.pacing_data = data
        payload = data.get('payload', {})
        pacing_list = payload.get('pacing_data', [])
        self.heatmap.set_data(pacing_list)
        self._update_reports()

    def _populate_issues_tab(self, tab: QWidget, issues: list):
        """Populate a tab with issue cards"""
        # Clear existing
        layout = tab.scroll_layout
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not issues:
            no_issues = QLabel("✅ No issues found!")
            no_issues.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_issues.setStyleSheet("font-size: 14pt; color: #28a745; padding: 50px;")
            layout.addWidget(no_issues)
        else:
            # Group by severity
            critical = [i for i in issues if i.get('severity') == 'Critical']
            major = [i for i in issues if i.get('severity') == 'Major']
            minor = [i for i in issues if i.get('severity') == 'Minor']
            suggestions = [i for i in issues if i.get('severity') == 'Suggestion']
            strengths = [i for i in issues if i.get('severity') == 'Strength']
            other = [i for i in issues if i.get('severity') not in ['Critical', 'Major', 'Minor', 'Suggestion', 'Strength']]

            groups = [
                (critical, 'Critical Issues'),
                (major, 'Major Issues'),
                (minor, 'Minor Issues'),
                (suggestions, 'Suggestions'),
                (strengths, 'Strengths'),
                (other, 'Observations')
            ]

            for issue_list, title in groups:
                if issue_list:
                    section = CollapsibleSection(f"{title} ({len(issue_list)})")
                    layout.addWidget(section)

                    for issue in issue_list:
                        card = IssueCard(issue, self.db_manager, self.project_id)
                        section.add_widget(card)

        layout.addStretch()

    def _on_pacing_scene_selected(self, scene_name: str):
        """Handle scene selection from pacing heatmap"""
        if not scene_name:
            return
            
        # Try to find the scene_id in any of the analysis data
        scene_id = None
        
        # Check timeline issues
        if self.timeline_data:
            for issue in self.timeline_data.get('issues', []):
                if issue.get('location') == scene_name:
                    scene_id = issue.get('scene_id')
                    break
                    
        # If not found, check consistency issues
        if not scene_id and self.consistency_data:
            for issue in self.consistency_data.get('issues', []):
                if issue.get('location') == scene_name:
                    scene_id = issue.get('scene_id')
                    break
        
        # If still not found, we just have the name. 
        # The main window on_insight_jump_requested usually expects a dict with scene_id
        if scene_id:
            self.jump_requested.emit({"scene_id": scene_id})
        else:
            # Fallback: some systems might handle just the name or we need to look it up in DB
            # For now, emit what we have
            self.jump_requested.emit({"scene_name": scene_name})

    def _update_reports(self):
        """Update the full reports tab"""
        report_text = ""

        if self.timeline_data:
            report_text += "=" * 60 + "\n"
            report_text += "TIMELINE ANALYSIS\n"
            report_text += "=" * 60 + "\n\n"
            report_text += self.timeline_data.get('final_report', 'No report available')
            report_text += "\n\n"

        if self.consistency_data:
            report_text += "=" * 60 + "\n"
            report_text += "CONSISTENCY ANALYSIS\n"
            report_text += "=" * 60 + "\n\n"
            report_text += self.consistency_data.get('final_report', 'No report available')
            report_text += "\n\n"

        if self.style_data:
            report_text += "=" * 60 + "\n"
            report_text += "WRITING STYLE ANALYSIS\n"
            report_text += "=" * 60 + "\n\n"
            report_text += self.style_data.get('final_report', 'No report available')

        self.reports_text.setText(report_text)