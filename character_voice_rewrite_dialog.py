"""
Character Voice Rewrite Dialog - Rewrite text in a specific character's voice
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QComboBox, QProgressDialog, QMessageBox, QTabWidget,
    QScrollArea
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from theme_manager import theme_manager
from typing import Optional, List, Dict, Any

from models.project import Character
from ai_prompts import AIPrompts


class CharacterVoiceRewriteWorker(QThread):
    """Worker thread for character voice rewriting"""

    finished = pyqtSignal(str)  # rewritten_text
    error = pyqtSignal(str)

    def __init__(self, ai_manager, character: Character, original_text: str):
        super().__init__()
        self.ai_manager = ai_manager
        self.character = character
        self.original_text = original_text

    def run(self):
        try:
            # Build prompt using character profile
            prompt_data = AIPrompts.rewrite_in_character_voice(
                self.original_text,
                self.character.name,
                self.character.to_dict()
            )

            # Call AI
            response = self.ai_manager.call_api(
                messages=[{"role": "user", "content": prompt_data["user"]}],
                system_message=prompt_data["system"],
                temperature=0.7,
                max_tokens=8000
            )

            self.finished.emit(response.strip())

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))


class CharacterVoiceRewriteDialog(QDialog):
    """Dialog for rewriting text in a character's voice"""

    def __init__(self, parent, ai_manager, characters: List[Character], original_text: str):
        super().__init__(parent)
        self.ai_manager = ai_manager
        self.characters = characters
        self.original_text = original_text
        self.rewritten_text = None

        self.setWindowTitle("Rewrite in Character Voice")
        self.setMinimumSize(800, 600)
        self.init_ui()
        self.apply_modern_style()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("🎭 Character Voice Lock - Rewrite")
        header.setObjectName("dialogHeader")
        header.setStyleSheet("font-size: 16pt; font-weight: bold; color: #7C4DFF; margin-bottom: 10px;")
        layout.addWidget(header)

        # Character selection
        char_layout = QHBoxLayout()
        char_label = QLabel("Select Character:")
        char_label.setStyleSheet("font-weight: bold;")
        char_layout.addWidget(char_label)

        self.char_combo = QComboBox()
        for char in self.characters:
            self.char_combo.addItem(char.name, char)
        char_layout.addWidget(self.char_combo)
        char_layout.addStretch()
        layout.addLayout(char_layout)

        # Comparison
        content_layout = QHBoxLayout()
        
        # Original
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("Original Text:"))
        self.original_edit = QTextEdit()
        self.original_edit.setPlainText(self.original_text)
        self.original_edit.setReadOnly(True)
        left_layout.addWidget(self.original_edit)
        content_layout.addLayout(left_layout)

        # Rewritten
        right_layout = QVBoxLayout()
        right_layout.addWidget(QLabel("Character Voice:"))
        self.rewritten_edit = QTextEdit()
        self.rewritten_edit.setReadOnly(True)
        self.rewritten_edit.setPlaceholderText("Rewritten text will appear here...")
        right_layout.addWidget(self.rewritten_edit)
        content_layout.addLayout(right_layout)

        layout.addLayout(content_layout)

        # Buttons
        btn_layout = QHBoxLayout()
        
        self.rewrite_btn = QPushButton("🚀 Rewrite in Voice")
        self.rewrite_btn.clicked.connect(self.start_rewrite)
        self.rewrite_btn.setMinimumHeight(40)
        self.rewrite_btn.setStyleSheet("background-color: #7C4DFF; color: white; font-weight: bold;")
        
        self.apply_btn = QPushButton("✅ Apply Changes")
        self.apply_btn.clicked.connect(self.accept)
        self.apply_btn.setEnabled(False)
        self.apply_btn.setMinimumHeight(40)
        self.apply_btn.setStyleSheet("background-color: #00E676; color: black; font-weight: bold;")
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        self.cancel_btn.setMinimumHeight(40)
        
        btn_layout.addWidget(self.cancel_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.rewrite_btn)
        btn_layout.addWidget(self.apply_btn)
        
        layout.addLayout(btn_layout)

    def start_rewrite(self):
        char = self.char_combo.currentData()
        if not char:
            return

        self.rewrite_btn.setEnabled(False)
        self.rewrite_btn.setText("Rewriting...")
        
        self.worker = CharacterVoiceRewriteWorker(self.ai_manager, char, self.original_text)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_finished(self, rewritten_text):
        self.rewritten_text = rewritten_text
        self.rewritten_edit.setPlainText(rewritten_text)
        self.rewrite_btn.setEnabled(True)
        self.rewrite_btn.setText("🚀 Rewrite Again")
        self.apply_btn.setEnabled(True)

    def on_error(self, error_msg):
        self.rewrite_btn.setEnabled(True)
        self.rewrite_btn.setText("🚀 Retry Rewrite")
        QMessageBox.critical(self, "AI Error", f"Failed to rewrite: {error_msg}")

    def get_rewritten_text(self):
        return self.rewritten_text

    def apply_modern_style(self):
        """Apply modern styling"""
        self.setStyleSheet(theme_manager.get_dialog_stylesheet())
        self.header.setObjectName("settingsHeader")
