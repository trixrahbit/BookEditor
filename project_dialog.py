"""
Project creation/editing dialog with modern styling
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QTextEdit, QSpinBox, QDialogButtonBox, QLabel
)
from PyQt6.QtCore import Qt


class ProjectDialog(QDialog):
    def __init__(self, parent=None, project=None):
        super().__init__(parent)
        self.project = project
        self.init_ui()
        self.apply_modern_style()

    def init_ui(self):
        """Initialize the dialog UI"""
        self.setWindowTitle("New Project" if not self.project else "Edit Project")
        self.setMinimumWidth(550)

        layout = QVBoxLayout(self)
        layout.setSpacing(20)

        # Header
        header = QLabel("Create Your Novel Project")
        header.setObjectName("dialogHeader")
        layout.addWidget(header)

        # Form layout
        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        # Project name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g., My Sci-Fi Adventure")
        if self.project:
            self.name_edit.setText(self.project.name)
        form_layout.addRow("Project Name:", self.name_edit)

        # Author
        self.author_edit = QLineEdit()
        self.author_edit.setPlaceholderText("Your name")
        if self.project:
            self.author_edit.setText(self.project.author)
        form_layout.addRow("Author:", self.author_edit)

        # Genre
        self.genre_edit = QLineEdit()
        self.genre_edit.setPlaceholderText("e.g., Science Fiction, Romance")
        if self.project:
            self.genre_edit.setText(self.project.genre)
        form_layout.addRow("Genre:", self.genre_edit)

        # Target word count
        self.word_count_spin = QSpinBox()
        self.word_count_spin.setRange(0, 1000000)
        self.word_count_spin.setSingleStep(1000)
        self.word_count_spin.setValue(80000 if not self.project else self.project.target_word_count)
        self.word_count_spin.setSuffix(" words")
        form_layout.addRow("Target Word Count:", self.word_count_spin)

        # Description
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Brief description of your novel...")
        self.description_edit.setMaximumHeight(100)
        if self.project:
            self.description_edit.setPlainText(self.project.description)
        form_layout.addRow("Description:", self.description_edit)

        layout.addLayout(form_layout)

        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_project_data(self):
        """Get project data from form"""
        return {
            'name': self.name_edit.text(),
            'author': self.author_edit.text(),
            'genre': self.genre_edit.text(),
            'target_word_count': self.word_count_spin.value(),
            'description': self.description_edit.toPlainText()
        }

    def apply_modern_style(self):
        """Apply modern styling"""
        self.setStyleSheet("""
            QDialog {
                background-color: #121212;
            }

            QLabel#dialogHeader {
                font-size: 18pt;
                font-weight: bold;
                color: white;
                padding: 15px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #7C4DFF, stop:1 #5E35B1);
                border-radius: 6px;
                margin-bottom: 10px;
            }
            
            QLabel {
                color: #E0E0E0;
                font-size: 10pt;
            }

            QLineEdit, QTextEdit, QSpinBox {
                border: 1px solid #3D3D3D;
                border-radius: 6px;
                padding: 8px;
                background: #1E1E1E;
                color: #E0E0E0;
                font-size: 11pt;
            }

            QLineEdit:focus, QTextEdit:focus, QSpinBox:focus {
                border-color: #7C4DFF;
                outline: none;
            }

            QPushButton {
                background-color: #252526;
                border: 1px solid #3D3D3D;
                border-radius: 6px;
                padding: 8px 16px;
                color: #E0E0E0;
                font-weight: 500;
            }
            
            QPushButton:hover {
                background-color: #3D3D3D;
                border-color: #7C4DFF;
            }
            
            QDialogButtonBox QPushButton {
                min-width: 80px;
            }
        """)