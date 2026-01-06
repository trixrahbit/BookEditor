"""
AI Fix Dialog - Uses ai_fix_engine.py for proposing fixes
"""

import difflib
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget,
    QTextEdit, QMessageBox, QProgressDialog, QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QTextCursor
from typing import Dict, Any, List, Optional


def get_highlighted_diffs(old_text: str, new_text: str):
    """
    Returns (highlighted_old_html, highlighted_new_html)
    """
    # Character-based diffing for finer highlights
    s = difflib.SequenceMatcher(None, old_text, new_text)
    
    old_html = ""
    new_html = ""
    
    for tag, i1, i2, j1, j2 in s.get_opcodes():
        if tag == 'equal':
            chunk = old_text[i1:i2].replace('\n', '<br>')
            old_html += chunk
            new_html += chunk
        elif tag == 'delete':
            chunk = old_text[i1:i2].replace('\n', '<br>')
            old_html += f'<span style="background-color: #442222; color: #ff8888; text-decoration: line-through;">{chunk}</span>'
        elif tag == 'insert':
            chunk = new_text[j1:j2].replace('\n', '<br>')
            new_html += f'<span style="background-color: #224422; color: #88ff88;">{chunk}</span>'
        elif tag == 'replace':
            chunk_old = old_text[i1:i2].replace('\n', '<br>')
            chunk_new = new_text[j1:j2].replace('\n', '<br>')
            old_html += f'<span style="background-color: #442222; color: #ff8888; text-decoration: line-through;">{chunk_old}</span>'
            new_html += f'<span style="background-color: #224422; color: #88ff88;">{chunk_new}</span>'
            
    return old_html, new_html


class FixWorker(QThread):
    """Background worker for generating AI fix"""
    finished = pyqtSignal(dict)  # fix_result
    error = pyqtSignal(str)

    def __init__(self, ai_fix_engine, issue_data: Dict, scene_name: str, scene_html: str):
        super().__init__()
        self.ai_fix_engine = ai_fix_engine
        self.issue_data = issue_data
        self.scene_name = scene_name
        self.scene_html = scene_html

    def run(self):
        try:
            result = self.ai_fix_engine.propose_fix(
                self.issue_data,
                self.scene_name,
                self.scene_html
            )
            self.finished.emit(result)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))


class AIFixDialog(QDialog):
    """Dialog for reviewing and approving AI-proposed fixes"""

    def __init__(self, parent, issue: Dict[str, Any], scene_id: str,
                 scene_content: str, db_manager, project_id: str):
        super().__init__(parent)
        self.issue = issue
        self.scene_id = scene_id
        self.scene_content = scene_content
        self.db_manager = db_manager
        self.project_id = project_id
        self.fix_result = None

        self.setWindowTitle("AI Fix Proposal")
        self.setMinimumSize(1200, 800)
        self.init_ui()
        self.generate_fix()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Header
        scene = self.db_manager.load_item(self.scene_id)
        scene_name = scene.name if scene else "Unknown Scene"

        header = QLabel(f"AI Fix: {self.issue.get('issue', 'Unknown Issue')}")
        header.setObjectName("dialogHeader")
        layout.addWidget(header)

        # Issue info
        info_text = f"""
<b>Scene:</b> {scene_name}<br>
<b>Problem:</b> {self.issue.get('detail', 'No details')}<br>
<b>Type:</b> {self.issue.get('type', 'general')}
        """
        info = QLabel(info_text)
        info.setWordWrap(True)
        info.setObjectName("infoLabel")
        layout.addWidget(info)

        # Side-by-side comparison
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setObjectName("comparisonSplitter")

        # Left: Original
        original_container = QWidget()
        original_layout = QVBoxLayout(original_container)
        original_layout.setContentsMargins(0, 0, 0, 0)
        orig_header = QLabel("📝 ORIGINAL")
        orig_header.setStyleSheet("color: #fd7e14; font-weight: bold; padding: 5px;")
        original_layout.addWidget(orig_header)
        
        self.original_text = QTextEdit()
        self.original_text.setReadOnly(True)
        self.original_text.setObjectName("originalText")
        original_layout.addWidget(self.original_text)

        # Right: Fixed
        fixed_container = QWidget()
        fixed_layout = QVBoxLayout(fixed_container)
        fixed_layout.setContentsMargins(0, 0, 0, 0)
        fix_header = QLabel("✨ AI FIXED")
        fix_header.setStyleSheet("color: #28a745; font-weight: bold; padding: 5px;")
        fixed_layout.addWidget(fix_header)

        self.fixed_text = QTextEdit()
        self.fixed_text.setReadOnly(True)
        self.fixed_text.setObjectName("fixedText")
        fixed_layout.addWidget(self.fixed_text)

        self.splitter.addWidget(original_container)
        self.splitter.addWidget(fixed_container)
        self.splitter.setSizes([450, 450])

        layout.addWidget(self.splitter)

        # Synchronize scrolling
        self.original_text.verticalScrollBar().valueChanged.connect(
            self.fixed_text.verticalScrollBar().setValue
        )
        self.fixed_text.verticalScrollBar().valueChanged.connect(
            self.original_text.verticalScrollBar().setValue
        )

        # Stats
        orig_words = len(self.scene_content.split())
        self.stats_label = QLabel(f"Original: {orig_words} words")
        self.stats_label.setStyleSheet("color: #6c757d; font-size: 9pt; margin-left: 10px;")
        layout.addWidget(self.stats_label)

        # Status label
        self.status_label = QLabel("Generating fix...")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.deny_btn = QPushButton("❌ Deny")
        self.deny_btn.setEnabled(False)
        self.deny_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.deny_btn)

        self.approve_btn = QPushButton("✅ Approve & Apply")
        self.approve_btn.setEnabled(False)
        self.approve_btn.setObjectName("primaryButton")
        self.approve_btn.clicked.connect(self.apply_fix)
        button_layout.addWidget(self.approve_btn)

        layout.addLayout(button_layout)
        self.apply_modern_style()

    def apply_modern_style(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #121212;
            }
            
            QLabel#dialogHeader {
                font-size: 14pt;
                font-weight: bold;
                padding: 12px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #7C4DFF, stop:1 #5E35B1);
                color: white;
                border-radius: 6px;
                margin-bottom: 5px;
            }
            
            QLabel#infoLabel {
                background: #1E1E1E;
                color: #E0E0E0;
                padding: 12px;
                border: 1px solid #2D2D2D;
                border-radius: 6px;
                margin: 8px 0;
            }
            
            QLabel#statusLabel {
                color: #7C4DFF;
                font-style: italic;
                margin: 8px;
            }
            
            QSplitter::handle {
                background: #2D2D2D;
                width: 2px;
            }
            
            QTextEdit#originalText {
                background: #1E1E1E;
                color: #A0A0A0;
                font-family: 'Georgia', serif;
                font-size: 11pt;
                padding: 15px;
                border: 1px solid #333333;
            }
            
            QTextEdit#fixedText {
                background: #1A1A1A;
                color: #E0E0E0;
                font-family: 'Georgia', serif;
                font-size: 11pt;
                padding: 15px;
                border: 1px solid #333333;
            }
            
            QPushButton {
                background-color: #252526;
                border: 1px solid #3D3D3D;
                border-radius: 6px;
                padding: 10px 20px;
                color: #E0E0E0;
                font-weight: 500;
            }
            
            QPushButton:hover {
                background-color: #3D3D3D;
                border-color: #7C4DFF;
            }
            
            QPushButton#primaryButton {
                background-color: #00C853;
                border: none;
                color: white;
            }
            
            QPushButton#primaryButton:hover {
                background-color: #69F0AE;
                color: black;
            }
            
            QPushButton:disabled {
                background-color: #1A1A1A;
                color: #555555;
                border-color: #2D2D2D;
            }
        """)

    def generate_fix(self):
        """Start generating AI fix"""
        from ai_fix_engine import AIFixEngine
        from ai_manager import ai_manager

        scene = self.db_manager.load_item(self.scene_id)
        scene_name = scene.name if scene else "Untitled"

        # Show original
        from text_utils import html_to_plaintext
        original_plain = html_to_plaintext(self.scene_content)
        self.original_text.setPlainText(original_plain)

        # Start worker
        engine = AIFixEngine(ai_manager)
        self.worker = FixWorker(engine, self.issue, scene_name, self.scene_content)
        self.worker.finished.connect(self.on_fix_generated)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_fix_generated(self, result: Dict[str, Any]):
        """Handle fix generation completion"""
        self.fix_result = result

        # Show highlighted text
        from text_utils import html_to_plaintext
        original_plain = html_to_plaintext(self.scene_content)
        fixed_plain = result.get('fixed_plain', '')
        
        orig_highlighted, fixed_highlighted = get_highlighted_diffs(original_plain, fixed_plain)
        
        self.original_text.setHtml(f"<div style='white-space: pre-wrap;'>{orig_highlighted}</div>")
        self.fixed_text.setHtml(f"<div style='white-space: pre-wrap;'>{fixed_highlighted}</div>")

        # Enable buttons
        self.approve_btn.setEnabled(True)
        self.deny_btn.setEnabled(True)
        
        # Update stats
        orig_words = len(self.original_text.toPlainText().split())
        fixed_words = len(fixed_plain.split())
        diff = fixed_words - orig_words
        self.stats_label.setText(f"Original: {orig_words:,} words | Fixed: {fixed_words:,} words | Change: {diff:+,} words")
        
        self.status_label.setText("✓ Fix generated! Review the changes.")
        self.status_label.setStyleSheet("color: #28a745; font-weight: bold; margin: 8px;")

    def on_error(self, error: str):
        """Handle fix generation error"""
        self.status_label.setText(f"❌ Error: {error}")
        self.status_label.setStyleSheet("color: #dc3545; font-weight: bold; margin: 8px;")
        self.deny_btn.setEnabled(True)

    def apply_fix(self):
        """Apply the fix to the scene"""
        if not self.fix_result:
            return

        # Get the scene
        scene = self.db_manager.load_item(self.scene_id)
        if not scene:
            QMessageBox.critical(self, "Error", "Scene not found")
            return

        # Apply the fixed HTML
        fixed_html = self.fix_result.get('fixed_html', '')
        scene.content = fixed_html

        # Save
        self.db_manager.save_item(self.project_id, scene)

        QMessageBox.information(
            self,
            "Fix Applied",
            f"The AI fix has been applied to '{scene.name}'!"
        )

        self.accept()