"""
Persona Manager Dialog - Create, edit, and manage writing personas
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QLineEdit,
    QComboBox, QGroupBox, QFormLayout, QMessageBox, QSplitter,
    QCheckBox, QPlainTextEdit, QScrollArea, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal
from typing import Optional

from writing_persona import WritingPersona, PersonaManager, PERSONA_TEMPLATES


class PersonaEditorWidget(QGroupBox):
    """Widget for editing a persona"""

    persona_changed = pyqtSignal()

    def __init__(self):
        super().__init__("Persona Editor")
        self.current_persona: Optional[WritingPersona] = None
        self.init_ui()

    def init_ui(self):
        # Main layout with scroll area
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 15, 10, 10)

        # Scroll area for all content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        scroll_widget = QWidget()
        layout = QVBoxLayout(scroll_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(5, 5, 5, 5)

        # Basic info
        basic_group = QGroupBox("Basic Information")
        basic_layout = QFormLayout()
        basic_layout.setSpacing(10)
        basic_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.name_edit = QLineEdit()
        self.name_edit.textChanged.connect(self.persona_changed.emit)
        basic_layout.addRow("Name:", self.name_edit)

        self.description_edit = QLineEdit()
        self.description_edit.textChanged.connect(self.persona_changed.emit)
        basic_layout.addRow("Description:", self.description_edit)

        basic_group.setLayout(basic_layout)
        layout.addWidget(basic_group)

        # Voice & Style
        voice_group = QGroupBox("Voice & Perspective")
        voice_layout = QFormLayout()
        voice_layout.setSpacing(10)
        voice_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.voice_tone_edit = QLineEdit()
        self.voice_tone_edit.setPlaceholderText("e.g., Professional, engaging, introspective")
        voice_layout.addRow("Voice Tone:", self.voice_tone_edit)

        self.pov_combo = QComboBox()
        self.pov_combo.addItems(["First person", "Third person limited", "Third person omniscient", "Second person"])
        voice_layout.addRow("POV:", self.pov_combo)

        self.tense_combo = QComboBox()
        self.tense_combo.addItems(["Past tense", "Present tense"])
        voice_layout.addRow("Tense:", self.tense_combo)

        voice_group.setLayout(voice_layout)
        layout.addWidget(voice_group)

        # Prose Style
        prose_group = QGroupBox("Prose Characteristics")
        prose_layout = QFormLayout()
        prose_layout.setSpacing(10)
        prose_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.sentence_variety_edit = QLineEdit()
        self.sentence_variety_edit.setPlaceholderText("e.g., Mix of short and long for rhythm")
        prose_layout.addRow("Sentence Variety:", self.sentence_variety_edit)

        self.vocabulary_combo = QComboBox()
        self.vocabulary_combo.addItems(["Simple", "Accessible but literary", "Literary", "Academic"])
        prose_layout.addRow("Vocabulary:", self.vocabulary_combo)

        prose_group.setLayout(prose_layout)
        layout.addWidget(prose_group)

        # Techniques
        tech_group = QGroupBox("Narrative Techniques")
        tech_layout = QFormLayout()
        tech_layout.setSpacing(10)
        tech_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.show_tell_edit = QLineEdit()
        self.show_tell_edit.setPlaceholderText("e.g., Heavily favor showing through action")
        tech_layout.addRow("Show vs Tell:", self.show_tell_edit)

        self.dialogue_edit = QLineEdit()
        self.dialogue_edit.setPlaceholderText("e.g., Natural, character-driven, with subtext")
        tech_layout.addRow("Dialogue:", self.dialogue_edit)

        self.description_edit_style = QLineEdit()
        self.description_edit_style.setPlaceholderText("e.g., Vivid sensory details")
        tech_layout.addRow("Description:", self.description_edit_style)

        tech_group.setLayout(tech_layout)
        layout.addWidget(tech_group)

        # Genre & Audience
        genre_group = QGroupBox("Genre & Audience")
        genre_layout = QFormLayout()
        genre_layout.setSpacing(10)
        genre_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.genre_edit = QLineEdit()
        self.genre_edit.setPlaceholderText("e.g., Literary fiction with thriller pacing")
        genre_layout.addRow("Genre:", self.genre_edit)

        self.authors_edit = QLineEdit()
        self.authors_edit.setPlaceholderText("e.g., Gillian Flynn, Celeste Ng")
        genre_layout.addRow("Comparable Authors:", self.authors_edit)

        genre_group.setLayout(genre_layout)
        layout.addWidget(genre_group)

        # Avoid/Prefer
        rules_group = QGroupBox("Writing Rules")
        rules_layout = QFormLayout()
        rules_layout.setSpacing(10)
        rules_layout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.avoid_words_edit = QLineEdit()
        self.avoid_words_edit.setPlaceholderText("Comma-separated: suddenly, very, just")
        rules_layout.addRow("Avoid Words:", self.avoid_words_edit)

        self.prefer_tech_edit = QLineEdit()
        self.prefer_tech_edit.setPlaceholderText("Comma-separated: active voice, concrete details")
        rules_layout.addRow("Prefer Techniques:", self.prefer_tech_edit)

        rules_group.setLayout(rules_layout)
        layout.addWidget(rules_group)

        # Custom instructions
        custom_group = QGroupBox("Custom Instructions")
        custom_layout = QVBoxLayout()
        custom_layout.setSpacing(5)

        self.custom_edit = QPlainTextEdit()
        self.custom_edit.setPlaceholderText("Additional instructions for the AI...\n\nExample: Focus on character psychology. Show emotional states through physical reactions.")
        self.custom_edit.setMaximumHeight(120)
        custom_layout.addWidget(self.custom_edit)

        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)

        layout.addStretch()

        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

    def load_persona(self, persona: WritingPersona):
        """Load persona into editor"""
        self.current_persona = persona

        self.name_edit.setText(persona.name)
        self.description_edit.setText(persona.description)
        self.voice_tone_edit.setText(persona.voice_tone)

        # Set comboboxes
        self.pov_combo.setCurrentText(persona.pov_style)
        self.tense_combo.setCurrentText(persona.tense)
        self.vocabulary_combo.setCurrentText(persona.vocabulary_level)

        self.sentence_variety_edit.setText(persona.sentence_variety)
        self.show_tell_edit.setText(persona.show_vs_tell)
        self.dialogue_edit.setText(persona.dialogue_style)
        self.description_edit_style.setText(persona.description_style)
        self.genre_edit.setText(persona.genre_conventions)
        self.authors_edit.setText(persona.comparative_authors)

        self.avoid_words_edit.setText(", ".join(persona.avoid_words))
        self.prefer_tech_edit.setText(", ".join(persona.prefer_techniques))
        self.custom_edit.setPlainText(persona.custom_instructions)

    def save_to_persona(self) -> WritingPersona:
        """Save current values to persona"""
        if not self.current_persona:
            self.current_persona = WritingPersona()

        self.current_persona.name = self.name_edit.text()
        self.current_persona.description = self.description_edit.text()
        self.current_persona.voice_tone = self.voice_tone_edit.text()
        self.current_persona.pov_style = self.pov_combo.currentText()
        self.current_persona.tense = self.tense_combo.currentText()
        self.current_persona.vocabulary_level = self.vocabulary_combo.currentText()
        self.current_persona.sentence_variety = self.sentence_variety_edit.text()
        self.current_persona.show_vs_tell = self.show_tell_edit.text()
        self.current_persona.dialogue_style = self.dialogue_edit.text()
        self.current_persona.description_style = self.description_edit_style.text()
        self.current_persona.genre_conventions = self.genre_edit.text()
        self.current_persona.comparative_authors = self.authors_edit.text()

        # Parse lists
        avoid_text = self.avoid_words_edit.text().strip()
        self.current_persona.avoid_words = [w.strip() for w in avoid_text.split(',') if w.strip()]

        prefer_text = self.prefer_tech_edit.text().strip()
        self.current_persona.prefer_techniques = [t.strip() for t in prefer_text.split(',') if t.strip()]

        self.current_persona.custom_instructions = self.custom_edit.toPlainText()

        return self.current_persona

    def clear(self):
        """Clear all fields"""
        self.current_persona = None
        self.name_edit.clear()
        self.description_edit.clear()
        self.voice_tone_edit.clear()
        self.sentence_variety_edit.clear()
        self.show_tell_edit.clear()
        self.dialogue_edit.clear()
        self.description_edit_style.clear()
        self.genre_edit.clear()
        self.authors_edit.clear()
        self.avoid_words_edit.clear()
        self.prefer_tech_edit.clear()
        self.custom_edit.clear()


class PersonaManagerDialog(QDialog):
    """Dialog for managing writing personas"""

    def __init__(self, parent, persona_manager: PersonaManager):
        super().__init__(parent)
        self.persona_manager = persona_manager
        self.setWindowTitle("Writing Personas")
        self.setMinimumSize(1000, 700)
        self.init_ui()
        self.load_personas()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("✍️ Writing Personas")
        header.setStyleSheet("""
            font-size: 16pt;
            font-weight: bold;
            padding: 15px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #667eea, stop:1 #764ba2);
            color: white;
            border-radius: 6px;
        """)
        layout.addWidget(header)

        info = QLabel("Define writing styles to maintain consistent voice across your manuscript")
        info.setStyleSheet("color: #6c757d; padding: 10px; font-size: 10pt;")
        layout.addWidget(info)

        # Main splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: List of personas
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)

        list_header = QLabel("Personas:")
        list_header.setStyleSheet("font-weight: bold; font-size: 11pt;")
        left_layout.addWidget(list_header)

        self.persona_list = QListWidget()
        self.persona_list.itemClicked.connect(self.on_persona_selected)
        left_layout.addWidget(self.persona_list)

        # List buttons
        list_btn_layout = QHBoxLayout()

        new_btn = QPushButton("➕ New")
        new_btn.clicked.connect(self.create_new_persona)
        list_btn_layout.addWidget(new_btn)

        template_btn = QPushButton("📋 From Template")
        template_btn.clicked.connect(self.create_from_template)
        list_btn_layout.addWidget(template_btn)

        delete_btn = QPushButton("🗑️ Delete")
        delete_btn.clicked.connect(self.delete_persona)
        list_btn_layout.addWidget(delete_btn)

        left_layout.addLayout(list_btn_layout)

        splitter.addWidget(left_widget)

        # Right: Editor
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        self.editor = PersonaEditorWidget()
        self.editor.persona_changed.connect(self.on_editor_changed)
        right_layout.addWidget(self.editor)

        # Editor buttons
        editor_btn_layout = QHBoxLayout()
        editor_btn_layout.addStretch()

        self.save_btn = QPushButton("💾 Save Changes")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background: #218838; }
            QPushButton:disabled { background: #adb5bd; }
        """)
        self.save_btn.clicked.connect(self.save_current_persona)
        self.save_btn.setEnabled(False)
        editor_btn_layout.addWidget(self.save_btn)

        self.default_btn = QPushButton("⭐ Set as Default")
        self.default_btn.clicked.connect(self.set_as_default)
        self.default_btn.setEnabled(False)
        editor_btn_layout.addWidget(self.default_btn)

        right_layout.addLayout(editor_btn_layout)

        splitter.addWidget(right_widget)
        splitter.setSizes([300, 700])

        layout.addWidget(splitter)

        # Dialog buttons
        dialog_btn_layout = QHBoxLayout()
        dialog_btn_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        dialog_btn_layout.addWidget(close_btn)

        layout.addLayout(dialog_btn_layout)

    def load_personas(self):
        """Load personas into list"""
        self.persona_list.clear()

        for persona in self.persona_manager.list_personas():
            item = QListWidgetItem(persona.name)
            item.setData(Qt.ItemDataRole.UserRole, persona.id)

            if persona.is_default:
                item.setText(f"⭐ {persona.name}")
                item.setForeground(Qt.GlobalColor.darkBlue)

            self.persona_list.addItem(item)

    def on_persona_selected(self, item: QListWidgetItem):
        """Handle persona selection"""
        persona_id = item.data(Qt.ItemDataRole.UserRole)
        persona = self.persona_manager.get_persona(persona_id)

        if persona:
            self.editor.load_persona(persona)
            self.save_btn.setEnabled(False)
            self.default_btn.setEnabled(True)

    def on_editor_changed(self):
        """Handle editor changes"""
        self.save_btn.setEnabled(True)

    def create_new_persona(self):
        """Create new blank persona"""
        persona = WritingPersona(name="New Persona")
        persona_id = self.persona_manager.create_persona(persona)

        self.load_personas()

        # Select the new persona
        for i in range(self.persona_list.count()):
            item = self.persona_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == persona_id:
                self.persona_list.setCurrentItem(item)
                self.on_persona_selected(item)
                break

    def create_from_template(self):
        """Create persona from template"""
        from PyQt6.QtWidgets import QInputDialog

        templates = list(PERSONA_TEMPLATES.keys())
        template_names = [t.replace('_', ' ').title() for t in templates]

        choice, ok = QInputDialog.getItem(
            self,
            "Choose Template",
            "Select a persona template:",
            template_names,
            0,
            False
        )

        if ok:
            idx = template_names.index(choice)
            template_key = templates[idx]
            persona = PERSONA_TEMPLATES[template_key]

            # Create new instance
            import copy
            new_persona = copy.deepcopy(persona)

            persona_id = self.persona_manager.create_persona(new_persona)
            self.load_personas()

            # Select it
            for i in range(self.persona_list.count()):
                item = self.persona_list.item(i)
                if item.data(Qt.ItemDataRole.UserRole) == persona_id:
                    self.persona_list.setCurrentItem(item)
                    self.on_persona_selected(item)
                    break

    def save_current_persona(self):
        """Save current persona"""
        if not self.editor.current_persona:
            return

        persona = self.editor.save_to_persona()
        self.persona_manager.update_persona(persona)

        self.load_personas()
        self.save_btn.setEnabled(False)

        QMessageBox.information(self, "Saved", f"Persona '{persona.name}' saved!")

    def set_as_default(self):
        """Set current persona as default"""
        if not self.editor.current_persona:
            return

        self.persona_manager.set_default(self.editor.current_persona.id)
        self.load_personas()

        QMessageBox.information(self, "Default Set", f"'{self.editor.current_persona.name}' is now the default persona")

    def delete_persona(self):
        """Delete selected persona"""
        current_item = self.persona_list.currentItem()
        if not current_item:
            return

        persona_id = current_item.data(Qt.ItemDataRole.UserRole)
        persona = self.persona_manager.get_persona(persona_id)

        if persona and persona.is_default:
            QMessageBox.warning(self, "Cannot Delete", "Cannot delete the default persona")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Delete persona '{persona.name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.persona_manager.delete_persona(persona_id)
            self.load_personas()
            self.editor.clear()
            self.save_btn.setEnabled(False)
            self.default_btn.setEnabled(False)