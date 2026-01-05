"""
Persona Rewrite Dialog - Rewrite text using a writing persona
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QProgressDialog, QMessageBox, QTabWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from typing import Optional

from writing_persona import WritingPersona, PersonaManager


class PersonaRewriteWorker(QThread):
    """Worker thread for persona-based rewriting"""

    finished = pyqtSignal(str)  # rewritten_text
    error = pyqtSignal(str)

    def __init__(self, ai_manager, persona: WritingPersona, original_text: str, scope: str):
        super().__init__()
        self.ai_manager = ai_manager
        self.persona = persona
        self.original_text = original_text
        self.scope = scope

    def run(self):
        try:
            # Build prompt using persona
            prompt = self.persona.build_rewrite_prompt(self.original_text, self.scope)
            system_message = self.persona.get_system_message()

            print(f"Rewriting with persona: {self.persona.name}")
            print(f"Scope: {self.scope}")
            print(f"Original length: {len(self.original_text)} chars")

            # Call AI
            response = self.ai_manager.call_api(
                messages=[{"role": "user", "content": prompt}],
                system_message=system_message,
                temperature=0.7,  # Higher for creative rewriting
                max_tokens=8000  # Allow longer outputs
            )

            print(f"Rewritten length: {len(response)} chars")

            self.finished.emit(response.strip())

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))


class PersonaRewriteDialog(QDialog):
    """Dialog for rewriting text with a persona"""

    def __init__(self, parent, ai_manager, persona_manager: PersonaManager,
                 original_text: str, scope: str = "selection"):
        super().__init__(parent)
        self.ai_manager = ai_manager
        self.persona_manager = persona_manager
        self.original_text = original_text
        self.scope = scope
        self.rewritten_text = None

        self.setWindowTitle("Rewrite with Persona")
        self.setMinimumSize(1000, 700)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(f"✍️ Persona Rewrite - {self.scope.title()}")
        header.setStyleSheet("""
            font-size: 14pt;
            font-weight: bold;
            padding: 12px;
            background: #667eea;
            color: white;
            border-radius: 6px;
        """)
        layout.addWidget(header)

        # Persona selection
        persona_layout = QHBoxLayout()

        persona_label = QLabel("Writing Persona:")
        persona_label.setStyleSheet("font-weight: bold;")
        persona_layout.addWidget(persona_label)

        self.persona_combo = QComboBox()
        self.persona_combo.setMinimumWidth(300)
        self.load_personas()
        persona_layout.addWidget(self.persona_combo)

        persona_layout.addStretch()

        manage_btn = QPushButton("⚙️ Manage Personas")
        manage_btn.clicked.connect(self.manage_personas)
        persona_layout.addWidget(manage_btn)

        layout.addLayout(persona_layout)

        # Info
        word_count = len(self.original_text.split())
        info = QLabel(f"Original text: {word_count:,} words")
        info.setStyleSheet("color: #6c757d; padding: 5px; font-size: 9pt;")
        layout.addWidget(info)

        # Tabs for original vs rewritten
        self.tabs = QTabWidget()

        # Original
        self.original_text_edit = QTextEdit()
        self.original_text_edit.setReadOnly(True)
        self.original_text_edit.setPlainText(self.original_text)
        self.original_text_edit.setStyleSheet("""
            QTextEdit {
                background: #fff3cd;
                font-family: 'Georgia', serif;
                font-size: 11pt;
                line-height: 1.6;
                padding: 15px;
            }
        """)
        self.tabs.addTab(self.original_text_edit, "📝 Original")

        # Rewritten
        self.rewritten_text_edit = QTextEdit()
        self.rewritten_text_edit.setReadOnly(True)
        self.rewritten_text_edit.setPlaceholderText("Rewritten text will appear here...")
        self.rewritten_text_edit.setStyleSheet("""
            QTextEdit {
                background: #d4edda;
                font-family: 'Georgia', serif;
                font-size: 11pt;
                line-height: 1.6;
                padding: 15px;
            }
        """)
        self.tabs.addTab(self.rewritten_text_edit, "✨ Rewritten")

        layout.addWidget(self.tabs)

        # Buttons
        button_layout = QHBoxLayout()

        self.rewrite_btn = QPushButton("🎨 Rewrite")
        self.rewrite_btn.setStyleSheet("""
            QPushButton {
                background: #667eea;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover { background: #5a67d8; }
            QPushButton:disabled { background: #adb5bd; }
        """)
        self.rewrite_btn.clicked.connect(self.start_rewrite)
        button_layout.addWidget(self.rewrite_btn)

        button_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)

        self.apply_btn = QPushButton("✅ Apply Rewrite")
        self.apply_btn.setStyleSheet("""
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
        self.apply_btn.clicked.connect(self.apply_rewrite)
        self.apply_btn.setEnabled(False)
        button_layout.addWidget(self.apply_btn)

        layout.addLayout(button_layout)

    def load_personas(self):
        """Load personas into combo box"""
        self.persona_combo.clear()

        personas = self.persona_manager.list_personas()
        default_persona = self.persona_manager.get_default_persona()

        for persona in personas:
            label = persona.name
            if persona.is_default:
                label = f"⭐ {label} (Default)"

            self.persona_combo.addItem(label, persona.id)

        # Select default
        if default_persona:
            for i in range(self.persona_combo.count()):
                if self.persona_combo.itemData(i) == default_persona.id:
                    self.persona_combo.setCurrentIndex(i)
                    break

    def manage_personas(self):
        """Open persona manager"""
        from persona_manager_dialog import PersonaManagerDialog

        dialog = PersonaManagerDialog(self, self.persona_manager)
        if dialog.exec():
            # Reload personas
            self.load_personas()

    def start_rewrite(self):
        """Start the rewrite process"""
        # Get selected persona
        persona_id = self.persona_combo.currentData()
        persona = self.persona_manager.get_persona(persona_id)

        if not persona:
            QMessageBox.warning(self, "No Persona", "Please select a persona")
            return

        # Show progress
        progress = QProgressDialog("AI is rewriting with persona...", "Cancel", 0, 0, self)
        progress.setWindowTitle("Rewriting")
        progress.setMinimumDuration(0)
        progress.setValue(0)

        # Disable buttons
        self.rewrite_btn.setEnabled(False)
        self.persona_combo.setEnabled(False)

        # Start worker
        self.worker = PersonaRewriteWorker(
            self.ai_manager,
            persona,
            self.original_text,
            self.scope
        )

        def on_finished(rewritten):
            progress.close()
            self.rewrite_btn.setEnabled(True)
            self.persona_combo.setEnabled(True)

            self.rewritten_text = rewritten
            self.rewritten_text_edit.setPlainText(rewritten)
            self.apply_btn.setEnabled(True)

            # Switch to rewritten tab
            self.tabs.setCurrentIndex(1)

            # Show stats
            original_words = len(self.original_text.split())
            rewritten_words = len(rewritten.split())
            diff = rewritten_words - original_words
            diff_pct = (diff / original_words * 100) if original_words > 0 else 0

            QMessageBox.information(
                self,
                "Rewrite Complete",
                f"Original: {original_words:,} words\n"
                f"Rewritten: {rewritten_words:,} words\n"
                f"Difference: {diff:+,} words ({diff_pct:+.1f}%)"
            )

        def on_error(error):
            progress.close()
            self.rewrite_btn.setEnabled(True)
            self.persona_combo.setEnabled(True)

            QMessageBox.critical(
                self,
                "Rewrite Error",
                f"Failed to rewrite text:\n\n{error}"
            )

        self.worker.finished.connect(on_finished)
        self.worker.error.connect(on_error)
        progress.canceled.connect(self.worker.terminate)

        self.worker.start()

    def apply_rewrite(self):
        """Apply the rewrite and close"""
        if self.rewritten_text:
            self.accept()

    def get_rewritten_text(self) -> Optional[str]:
        """Get the rewritten text"""
        return self.rewritten_text