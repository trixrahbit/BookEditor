"""
Metadata panel for displaying and editing item properties
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFormLayout,
    QLineEdit, QTextEdit, QComboBox, QPushButton, QFrame, QToolButton,
    QSizePolicy, QSpacerItem)
from PyQt6.QtCore import Qt, pyqtSignal

from models.project import (
    Scene, Character, Location, PlotThread, Chapter, Part, ItemType
)

from db_manager import DatabaseManager


class MetadataPanel(QWidget):
    metadata_changed = pyqtSignal()
    collapse_toggled = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.current_item = None
        self.db_manager: DatabaseManager = None
        self.project_id: str = None

        self.init_ui()
        self.apply_modern_style()

    def init_ui(self):
        """Initialize the metadata panel UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Title
        title_widget = QWidget()
        title_widget.setObjectName("metadataTitle")
        self.title_layout = QHBoxLayout(title_widget)
        self.title_layout.setContentsMargins(15, 15, 15, 15)

        self.title_label = QLabel("Properties")
        self.title_label.setObjectName("titleLabel")
        self.title_layout.addWidget(self.title_label)
        self.title_spacer = QSpacerItem(
            0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum
        )
        self.title_layout.addItem(self.title_spacer)

        self.toggle_button = QToolButton()
        self.toggle_button.setObjectName("metadataToggle")
        self.toggle_button.setText("−")
        self.toggle_button.setToolTip("Collapse properties panel")
        self.toggle_button.setCheckable(True)
        self.toggle_button.clicked.connect(self.toggle_collapsed)
        self.title_layout.addWidget(self.toggle_button)

        layout.addWidget(title_widget)
        self.title_widget = title_widget
        # Scrollable form area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll.setObjectName("metadataScroll")

        self.form_widget = QWidget()
        self.form_layout = QFormLayout(self.form_widget)
        self.form_layout.setSpacing(10)
        self.form_layout.setContentsMargins(15, 10, 15, 10)

        self.scroll.setWidget(self.form_widget)
        layout.addWidget(self.scroll)

        # Save button
        self.save_button = QPushButton("💾 Save Properties")
        self.save_button.setObjectName("saveButton")
        self.save_button.clicked.connect(self.save_metadata)
        self.save_button.setEnabled(False)
        layout.addWidget(self.save_button)

        # Storage for form fields
        self.fields = {}
        self.is_collapsed = False

    def toggle_collapsed(self):
        """Collapse or expand the metadata panel body."""
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.scroll.setVisible(False)
            self.save_button.setVisible(False)
            self.title_label.setVisible(False)
            if self.title_spacer is not None:
                self.title_layout.removeItem(self.title_spacer)
            self.toggle_button.setText("+")
            self.toggle_button.setToolTip("Expand properties panel")
            self.title_layout.setContentsMargins(6, 6, 6, 6)
            self.title_layout.setAlignment(self.toggle_button, Qt.AlignmentFlag.AlignLeft)
        else:
            self.scroll.setVisible(True)
            self.save_button.setVisible(True)
            self.title_label.setVisible(True)
            if self.title_spacer is not None:
                self.title_layout.addItem(self.title_spacer)
            self.toggle_button.setText("−")
            self.toggle_button.setToolTip("Collapse properties panel")
            self.title_layout.setContentsMargins(15, 15, 15, 15)
            self.title_layout.setAlignment(self.toggle_button, Qt.AlignmentFlag.AlignRight)
        self.collapse_toggled.emit(self.is_collapsed)

    def load_item(self, item, db_manager: DatabaseManager, project_id: str):
        """Load an item's metadata"""
        self.current_item = item
        self.db_manager = db_manager
        self.project_id = project_id

        # Clear existing fields
        self.clear_form()

        # Build form based on item type
        if item.item_type == ItemType.SCENE:
            self.build_scene_form(item)
        elif item.item_type == ItemType.CHARACTER:
            self.build_character_form(item)
        elif item.item_type == ItemType.LOCATION:
            self.build_location_form(item)
        elif item.item_type == ItemType.PLOT_THREAD:
            self.build_plot_form(item)
        elif item.item_type == ItemType.CHAPTER:
            self.build_chapter_form(item)
        elif item.item_type == ItemType.PART:
            self.build_part_form(item)

        self.save_button.setEnabled(True)

    def clear_form(self):
        """Clear all form fields"""
        while self.form_layout.rowCount() > 0:
            self.form_layout.removeRow(0)
        self.fields.clear()

    def add_text_field(self, label: str, field_name: str, value: str = "", multiline: bool = False):
        """Add a text field to the form"""
        if multiline:
            widget = QTextEdit()
            widget.setPlainText(value)
            widget.setMaximumHeight(100)
            widget.setObjectName("metadataTextEdit")
        else:
            widget = QLineEdit()
            widget.setText(value)
            widget.setObjectName("metadataLineEdit")

        self.fields[field_name] = widget
        self.form_layout.addRow(label, widget)

    def add_combo_field(self, label: str, field_name: str, options: list, current: str = ""):
        """Add a combo box to the form"""
        widget = QComboBox()
        widget.setObjectName("metadataCombo")
        widget.addItems(options)
        if current:
            index = widget.findText(current)
            if index >= 0:
                widget.setCurrentIndex(index)

        self.fields[field_name] = widget
        self.form_layout.addRow(label, widget)

    def build_scene_form(self, scene: Scene):
        """Build form for scene metadata"""
        self.add_text_field("Summary", "summary", scene.summary, multiline=True)
        self.add_text_field("Goal", "goal", scene.goal, multiline=True)
        self.add_text_field("Conflict", "conflict", scene.conflict, multiline=True)
        self.add_text_field("Outcome", "outcome", scene.outcome, multiline=True)
        self.add_combo_field("Status", "status",
                             ["draft", "revision", "final"], scene.status)

    def build_character_form(self, character: Character):
        """Build form for character metadata"""
        self.add_combo_field("Role", "role",
                             ["protagonist", "antagonist", "major", "minor"],
                             character.role)
        self.add_text_field("Age", "age", character.age)
        self.add_text_field("Appearance", "appearance", character.appearance, multiline=True)
        self.add_text_field("Personality", "personality", character.personality, multiline=True)
        self.add_text_field("Motivation", "motivation", character.motivation, multiline=True)
        self.add_text_field("Conflict", "conflict", character.conflict, multiline=True)
        self.add_text_field("Character Arc", "arc", character.arc, multiline=True)
        self.add_text_field("Strengths", "strengths", character.strengths, multiline=True)
        self.add_text_field("Weaknesses", "weaknesses", character.weaknesses, multiline=True)
        self.add_text_field("Notes", "notes", character.notes, multiline=True)

    def build_location_form(self, location: Location):
        """Build form for location metadata"""
        self.add_text_field("Description", "description", location.description, multiline=True)
        self.add_text_field("Significance", "significance", location.significance, multiline=True)
        self.add_text_field("Notes", "notes", location.notes, multiline=True)

    def build_plot_form(self, plot: PlotThread):
        """Build form for plot thread metadata"""
        self.add_combo_field("Importance", "importance",
                             ["main", "major", "minor"],
                             plot.importance)
        self.add_text_field("Description", "description", plot.description, multiline=True)
        self.add_text_field("Resolution", "resolution", plot.resolution, multiline=True)
        self.add_text_field("Notes", "notes", plot.notes, multiline=True)

    def build_chapter_form(self, chapter: Chapter):
        """Build form for chapter metadata"""
        self.add_text_field("Summary", "summary", chapter.summary, multiline=True)
        self.add_text_field("Description", "description", chapter.description, multiline=True)

    def build_part_form(self, part: Part):
        """Build form for part metadata"""
        self.add_text_field("Description", "description", part.description, multiline=True)

    def save_metadata(self):
        """Save metadata changes to the item"""
        if not self.current_item or not self.db_manager:
            return

        for field_name, widget in self.fields.items():
            if isinstance(widget, QLineEdit):
                value = widget.text()
            elif isinstance(widget, QTextEdit):
                value = widget.toPlainText()
            elif isinstance(widget, QComboBox):
                value = widget.currentText()
            else:
                continue

            if hasattr(self.current_item, field_name):
                setattr(self.current_item, field_name, value)

        self.db_manager.save_item(self.project_id, self.current_item)
        self.metadata_changed.emit()

    def apply_modern_style(self):
        """Apply modern futuristic styling"""
        self.setStyleSheet("""
            QWidget#metadataTitle {
                background: #1A1A1A;
                border-bottom: 1px solid #2D2D2D;
            }

            QLabel#titleLabel {
                font-size: 14pt;
                font-weight: bold;
                color: #7C4DFF;
                background: transparent;
            }

            QToolButton#metadataToggle {
                border: 1px solid #3D3D3D;
                border-radius: 4px;
                padding: 2px 6px;
                background: #252526;
                color: #E0E0E0;
                font-weight: bold;
            }

            QToolButton#metadataToggle:hover {
                background: #3D3D3D;
                border-color: #7C4DFF;
            }

            QScrollArea#metadataScroll {
                background: #1E1E1E;
                border: none;
            }

            QLineEdit#metadataLineEdit,
            QTextEdit#metadataTextEdit,
            QComboBox#metadataCombo {
                border: 1px solid #3D3D3D;
                border-radius: 4px;
                padding: 6px;
                background: #252526;
                color: #E0E0E0;
            }

            QLineEdit#metadataLineEdit:focus,
            QTextEdit#metadataTextEdit:focus {
                border-color: #7C4DFF;
            }

            QPushButton#saveButton {
                background-color: #00E676;
                color: #121212;
                border: none;
                border-radius: 6px;
                padding: 10px;
                font-weight: bold;
                margin: 10px;
            }

            QPushButton#saveButton:hover {
                background-color: #69F0AE;
            }

            QPushButton#saveButton:disabled {
                background-color: #2D2D2D;
                color: #4D4D4D;
            }
        """)
