"""
AI Fix Dialog - Uses ai_fix_engine.py for proposing fixes
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QTabWidget, QMessageBox, QProgressDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from typing import Dict, Any


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
        self.setMinimumSize(900, 700)
        self.init_ui()
        self.generate_fix()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Header
        scene = self.db_manager.load_item(self.scene_id)
        scene_name = scene.name if scene else "Unknown Scene"

        header = QLabel(f"AI Fix: {self.issue.get('issue', 'Unknown Issue')}")
        header.setStyleSheet("""
            font-size: 14pt;
            font-weight: bold;
            padding: 12px;
            background: #667eea;
            color: white;
            border-radius: 6px;
        """)
        layout.addWidget(header)

        # Issue info
        info_text = f"""
<b>Scene:</b> {scene_name}<br>
<b>Problem:</b> {self.issue.get('detail', 'No details')}<br>
<b>Type:</b> {self.issue.get('type', 'general')}
        """
        info = QLabel(info_text)
        info.setWordWrap(True)
        info.setStyleSheet("""
            background: #f8f9fa;
            padding: 10px;
            border-radius: 4px;
            margin: 8px 0;
        """)
        layout.addWidget(info)

        # Tabs for original vs fixed
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                padding: 8px 16px;
            }
            QTabBar::tab:selected {
                background: #667eea;
                color: white;
            }
        """)

        # Original
        self.original_text = QTextEdit()
        self.original_text.setReadOnly(True)
        self.original_text.setStyleSheet("""
            QTextEdit {
                background: #fff3cd;
                font-family: 'Courier New', monospace;
                font-size: 10pt;
                padding: 10px;
            }
        """)
        self.tabs.addTab(self.original_text, "📝 Original")

        # Fixed
        self.fixed_text = QTextEdit()
        self.fixed_text.setReadOnly(True)
        self.fixed_text.setStyleSheet("""
            QTextEdit {
                background: #d4edda;
                font-family: 'Courier New', monospace;
                font-size: 10pt;
                padding: 10px;
            }
        """)
        self.tabs.addTab(self.fixed_text, "✨ AI Fixed")

        layout.addWidget(self.tabs)

        # Status label
        self.status_label = QLabel("Generating fix...")
        self.status_label.setStyleSheet("color: #667eea; font-style: italic; margin: 8px;")
        layout.addWidget(self.status_label)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.deny_btn = QPushButton("❌ Deny")
        self.deny_btn.setEnabled(False)
        self.deny_btn.setStyleSheet("""
            QPushButton {
                background: #dc3545;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background: #c82333; }
            QPushButton:disabled { background: #adb5bd; }
        """)
        self.deny_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.deny_btn)

        self.approve_btn = QPushButton("✅ Approve & Apply")
        self.approve_btn.setEnabled(False)
        self.approve_btn.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background: #218838; }
            QPushButton:disabled { background: #adb5bd; }
        """)
        self.approve_btn.clicked.connect(self.apply_fix)
        button_layout.addWidget(self.approve_btn)

        layout.addLayout(button_layout)

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

        # Show fixed text
        fixed_plain = result.get('fixed_plain', '')
        self.fixed_text.setPlainText(fixed_plain)

        # Enable buttons
        self.approve_btn.setEnabled(True)
        self.deny_btn.setEnabled(True)
        self.status_label.setText("✓ Fix generated! Review the changes.")
        self.status_label.setStyleSheet("color: #28a745; font-weight: bold; margin: 8px;")

        # Switch to fixed tab
        self.tabs.setCurrentIndex(1)

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