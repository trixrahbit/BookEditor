"""
Enhanced rich text editor widget with AI analysis button
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel, QToolBar, QPushButton,
    QFontComboBox, QComboBox, QColorDialog
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QAction, QTextCharFormat, QColor, QTextListFormat, QTextCursor

from models.project import Scene, ItemType
from db_manager import DatabaseManager

class EditorWidget(QWidget):
    content_changed = pyqtSignal()
    analyze_requested = pyqtSignal(str)  # Emits item_id for analysis

    def __init__(self):
        super().__init__()
        self.current_item: Scene = None
        self.db_manager: DatabaseManager = None
        self.project_id: str = None
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.setInterval(5000)  # 5 seconds

        self.init_ui()
        self.apply_modern_style()

    def init_ui(self):
        """Initialize the editor UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Title bar with AI button
        title_bar = QWidget()
        title_bar.setObjectName("titleBar")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(15, 10, 15, 10)

        self.title_label = QLabel("No scene selected")
        self.title_label.setObjectName("sceneTitle")
        title_layout.addWidget(self.title_label)

        title_layout.addStretch()

        # AI Analyze button
        self.ai_button = QPushButton("🤖 AI Analyze")
        self.ai_button.setObjectName("aiButton")
        self.ai_button.clicked.connect(self.on_ai_analyze)
        self.ai_button.setEnabled(False)
        title_layout.addWidget(self.ai_button)

        self.word_count_label = QLabel("0 words")
        self.word_count_label.setObjectName("wordCount")
        title_layout.addWidget(self.word_count_label)

        layout.addWidget(title_bar)

        # Text editor - CREATE THIS FIRST
        self.text_edit = QTextEdit()
        self.text_edit.setObjectName("mainEditor")
        self.text_edit.setAcceptRichText(True)

        # Set a nice writing font
        font = QFont("Georgia", 12)
        self.text_edit.setFont(font)

        # Connect signals
        self.text_edit.textChanged.connect(self.on_text_changed)

        # NOW create formatting toolbar (after text_edit exists)
        self.create_toolbar(layout)

        # Add text editor to layout
        layout.addWidget(self.text_edit)

        # Disable by default
        self.set_enabled(False)

    def create_toolbar(self, parent_layout):
        """Create comprehensive formatting toolbar"""
        toolbar = QToolBar()
        toolbar.setObjectName("editorToolbar")
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(18, 18))

        # Font Family
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont("Georgia"))
        self.font_combo.currentFontChanged.connect(self.change_font_family)
        toolbar.addWidget(self.font_combo)

        toolbar.addSeparator()

        # Font Size
        self.font_size_combo = QComboBox()
        self.font_size_combo.setEditable(True)
        sizes = ['8', '9', '10', '11', '12', '14', '16', '18', '20', '24', '28', '32', '36', '48', '72']
        self.font_size_combo.addItems(sizes)
        self.font_size_combo.setCurrentText('12')
        self.font_size_combo.activated.connect(self.change_font_size_combo)
        toolbar.addWidget(self.font_size_combo)

        toolbar.addSeparator()

        # Bold
        bold_action = QAction("B", self)
        bold_action.setCheckable(True)
        bold_action.setShortcut("Ctrl+B")
        bold_action.setToolTip("Bold (Ctrl+B)")
        bold_action.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        bold_action.triggered.connect(self.toggle_bold)
        toolbar.addAction(bold_action)
        self.bold_action = bold_action

        # Italic
        italic_action = QAction("I", self)
        italic_action.setCheckable(True)
        italic_action.setShortcut("Ctrl+I")
        italic_action.setToolTip("Italic (Ctrl+I)")
        italic_font = QFont("Arial", 10)
        italic_font.setItalic(True)
        italic_action.setFont(italic_font)
        italic_action.triggered.connect(self.toggle_italic)
        toolbar.addAction(italic_action)
        self.italic_action = italic_action

        # Underline
        underline_action = QAction("U", self)
        underline_action.setCheckable(True)
        underline_action.setShortcut("Ctrl+U")
        underline_action.setToolTip("Underline (Ctrl+U)")
        underline_font = QFont("Arial", 10)
        underline_font.setUnderline(True)
        underline_action.setFont(underline_font)
        underline_action.triggered.connect(self.toggle_underline)
        toolbar.addAction(underline_action)
        self.underline_action = underline_action

        # Strikethrough
        strike_action = QAction("S", self)
        strike_action.setCheckable(True)
        strike_action.setToolTip("Strikethrough")
        strike_font = QFont("Arial", 10)
        strike_font.setStrikeOut(True)
        strike_action.setFont(strike_font)
        strike_action.triggered.connect(self.toggle_strikethrough)
        toolbar.addAction(strike_action)
        self.strike_action = strike_action

        toolbar.addSeparator()

        # Text Color
        text_color_action = QAction("A", self)
        text_color_action.setToolTip("Text Color")
        text_color_action.triggered.connect(self.change_text_color)
        toolbar.addAction(text_color_action)

        # Highlight Color
        highlight_action = QAction("H", self)
        highlight_action.setToolTip("Highlight Color")
        highlight_action.triggered.connect(self.change_highlight_color)
        toolbar.addAction(highlight_action)

        toolbar.addSeparator()

        # Alignment
        align_left_action = QAction("⬅", self)
        align_left_action.setCheckable(True)
        align_left_action.setToolTip("Align Left")
        align_left_action.triggered.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignLeft))
        toolbar.addAction(align_left_action)
        self.align_left_action = align_left_action

        align_center_action = QAction("⬌", self)
        align_center_action.setCheckable(True)
        align_center_action.setToolTip("Align Center")
        align_center_action.triggered.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignCenter))
        toolbar.addAction(align_center_action)
        self.align_center_action = align_center_action

        align_right_action = QAction("➡", self)
        align_right_action.setCheckable(True)
        align_right_action.setToolTip("Align Right")
        align_right_action.triggered.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignRight))
        toolbar.addAction(align_right_action)
        self.align_right_action = align_right_action

        align_justify_action = QAction("⬍", self)
        align_justify_action.setCheckable(True)
        align_justify_action.setToolTip("Justify")
        align_justify_action.triggered.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignJustify))
        toolbar.addAction(align_justify_action)
        self.align_justify_action = align_justify_action

        toolbar.addSeparator()

        # Lists
        bullet_action = QAction("●", self)
        bullet_action.setToolTip("Bullet List")
        bullet_action.triggered.connect(self.toggle_bullet_list)
        toolbar.addAction(bullet_action)

        number_action = QAction("1.", self)
        number_action.setToolTip("Numbered List")
        number_action.triggered.connect(self.toggle_numbered_list)
        toolbar.addAction(number_action)

        toolbar.addSeparator()

        # Indentation
        indent_less_action = QAction("◁", self)
        indent_less_action.setToolTip("Decrease Indent")
        indent_less_action.triggered.connect(self.decrease_indent)
        toolbar.addAction(indent_less_action)

        indent_more_action = QAction("▷", self)
        indent_more_action.setToolTip("Increase Indent")
        indent_more_action.triggered.connect(self.increase_indent)
        toolbar.addAction(indent_more_action)

        toolbar.addSeparator()

        # Clear Formatting
        clear_format_action = QAction("✕", self)
        clear_format_action.setToolTip("Clear Formatting")
        clear_format_action.triggered.connect(self.clear_formatting)
        toolbar.addAction(clear_format_action)

        parent_layout.addWidget(toolbar)

        # Connect cursor position changed to update toolbar
        self.text_edit.cursorPositionChanged.connect(self.update_format_actions)

    def load_item(self, item, db_manager: DatabaseManager, project_id: str):
        """Load an item into the editor"""
        self.db_manager = db_manager
        self.project_id = project_id

        # Only scenes are editable in the main editor
        if item.item_type == ItemType.SCENE:
            self.current_item = item
            self.title_label.setText(item.name)

            # Block signals while loading
            self.text_edit.blockSignals(True)
            self.text_edit.setHtml(item.content)
            self.text_edit.blockSignals(False)

            self.update_word_count()
            self.set_enabled(True)
            self.ai_button.setEnabled(True)

            # Start auto-save timer
            self.auto_save_timer.start()
        else:
            self.current_item = None
            self.title_label.setText(f"{item.name} (not editable)")
            self.text_edit.clear()
            self.set_enabled(False)
            self.ai_button.setEnabled(False)
            self.auto_save_timer.stop()

    def on_text_changed(self):
        """Handle text changes"""
        self.update_word_count()
        self.content_changed.emit()

    def update_word_count(self):
        """Update word count display with detailed statistics"""
        text = self.text_edit.toPlainText()
        words = [w for w in text.split() if w]
        word_count = len(words)
        char_count = len(text)
        char_no_spaces = len(text.replace(' ', '').replace('\n', '').replace('\t', ''))

        # Count paragraphs
        paragraphs = len([p for p in text.split('\n\n') if p.strip()])

        # Build detailed tooltip
        stats_tooltip = (
            f"Words: {word_count:,}\n"
            f"Characters (with spaces): {char_count:,}\n"
            f"Characters (no spaces): {char_no_spaces:,}\n"
            f"Paragraphs: {paragraphs:,}"
        )

        # Display word count
        self.word_count_label.setText(f"📊 {word_count:,} words")
        self.word_count_label.setToolTip(stats_tooltip)

        if self.current_item:
            self.current_item.word_count = word_count

    def auto_save(self):
        """Auto-save the current scene"""
        if self.current_item and self.db_manager:
            self.current_item.content = self.text_edit.toHtml()
            self.db_manager.save_item(self.project_id, self.current_item)

    def on_ai_analyze(self):
        """Trigger AI analysis for current scene"""
        if self.current_item:
            self.analyze_requested.emit(self.current_item.id)

    def toggle_bold(self):
        """Toggle bold formatting"""
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Bold if self.bold_action.isChecked() else QFont.Weight.Normal)
        self.merge_format_on_word_or_selection(fmt)

    def toggle_italic(self):
        """Toggle italic formatting"""
        fmt = QTextCharFormat()
        fmt.setFontItalic(self.italic_action.isChecked())
        self.merge_format_on_word_or_selection(fmt)

    def toggle_underline(self):
        """Toggle underline formatting"""
        fmt = QTextCharFormat()
        fmt.setFontUnderline(self.underline_action.isChecked())
        self.merge_format_on_word_or_selection(fmt)

    def toggle_strikethrough(self):
        """Toggle strikethrough formatting"""
        fmt = QTextCharFormat()
        fmt.setFontStrikeOut(self.strike_action.isChecked())
        self.merge_format_on_word_or_selection(fmt)

    def change_font_family(self, font):
        """Change font family"""
        fmt = QTextCharFormat()
        fmt.setFontFamily(font.family())
        self.merge_format_on_word_or_selection(fmt)

    def change_font_size_combo(self):
        """Change font size from combo box"""
        size = self.font_size_combo.currentText()
        if size:
            fmt = QTextCharFormat()
            fmt.setFontPointSize(float(size))
            self.merge_format_on_word_or_selection(fmt)

    def change_text_color(self):
        """Change text color"""
        color = QColorDialog.getColor()
        if color.isValid():
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            self.merge_format_on_word_or_selection(fmt)

    def change_highlight_color(self):
        """Change highlight/background color"""
        color = QColorDialog.getColor()
        if color.isValid():
            fmt = QTextCharFormat()
            fmt.setBackground(color)
            self.merge_format_on_word_or_selection(fmt)

    def set_alignment(self, alignment):
        """Set text alignment"""
        self.text_edit.setAlignment(alignment)
        self.update_alignment_actions(alignment)

    def update_alignment_actions(self, alignment):
        """Update alignment button states"""
        self.align_left_action.setChecked(alignment == Qt.AlignmentFlag.AlignLeft)
        self.align_center_action.setChecked(alignment == Qt.AlignmentFlag.AlignCenter)
        self.align_right_action.setChecked(alignment == Qt.AlignmentFlag.AlignRight)
        self.align_justify_action.setChecked(alignment == Qt.AlignmentFlag.AlignJustify)

    def toggle_bullet_list(self):
        """Toggle bullet list"""
        cursor = self.text_edit.textCursor()
        cursor.beginEditBlock()

        # Check if already in a list
        current_list = cursor.currentList()

        if current_list:
            # Remove from list
            block_format = cursor.blockFormat()
            block_format.setIndent(0)
            cursor.setBlockFormat(block_format)

            # Remove from list
            for i in range(current_list.count()):
                current_list.removeItem(0)
        else:
            # Create bullet list
            list_format = QTextListFormat()
            list_format.setStyle(QTextListFormat.Style.ListDisc)
            cursor.createList(list_format)

        cursor.endEditBlock()

    def toggle_numbered_list(self):
        """Toggle numbered list"""
        cursor = self.text_edit.textCursor()
        cursor.beginEditBlock()

        current_list = cursor.currentList()

        if current_list:
            # Remove from list
            block_format = cursor.blockFormat()
            block_format.setIndent(0)
            cursor.setBlockFormat(block_format)

            for i in range(current_list.count()):
                current_list.removeItem(0)
        else:
            # Create numbered list
            list_format = QTextListFormat()
            list_format.setStyle(QTextListFormat.Style.ListDecimal)
            cursor.createList(list_format)

        cursor.endEditBlock()

    def increase_indent(self):
        """Increase paragraph indent"""
        cursor = self.text_edit.textCursor()
        block_format = cursor.blockFormat()
        block_format.setIndent(block_format.indent() + 1)
        cursor.setBlockFormat(block_format)

    def decrease_indent(self):
        """Decrease paragraph indent"""
        cursor = self.text_edit.textCursor()
        block_format = cursor.blockFormat()
        indent = block_format.indent()
        if indent > 0:
            block_format.setIndent(indent - 1)
            cursor.setBlockFormat(block_format)

    def clear_formatting(self):
        """Clear all formatting from selection"""
        cursor = self.text_edit.textCursor()
        if cursor.hasSelection():
            # Get plain text
            text = cursor.selectedText()
            # Remove and reinsert as plain text
            cursor.removeSelectedText()
            cursor.insertText(text)

    def merge_format_on_word_or_selection(self, fmt):
        """Apply format to selection or current word"""
        cursor = self.text_edit.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.mergeCharFormat(fmt)
        self.text_edit.mergeCurrentCharFormat(fmt)

    def update_format_actions(self):
        """Update toolbar button states based on current format"""
        cursor = self.text_edit.textCursor()
        fmt = cursor.charFormat()

        # Update format buttons
        self.bold_action.setChecked(fmt.fontWeight() == QFont.Weight.Bold)
        self.italic_action.setChecked(fmt.fontItalic())
        self.underline_action.setChecked(fmt.fontUnderline())
        self.strike_action.setChecked(fmt.fontStrikeOut())

        # Update font combo
        self.font_combo.setCurrentFont(fmt.font())

        # Update size combo
        size = fmt.fontPointSize()
        if size > 0:
            self.font_size_combo.setCurrentText(str(int(size)))

        # Update alignment
        self.update_alignment_actions(self.text_edit.alignment())

    def set_enabled(self, enabled: bool):
        """Enable or disable the editor"""
        self.text_edit.setEnabled(enabled)
        self.bold_action.setEnabled(enabled)
        self.italic_action.setEnabled(enabled)
        self.underline_action.setEnabled(enabled)

    def undo(self):
        """Undo last action"""
        self.text_edit.undo()

    def redo(self):
        """Redo last action"""
        self.text_edit.redo()

    def cut(self):
        """Cut selected text"""
        self.text_edit.cut()

    def copy(self):
        """Copy selected text"""
        self.text_edit.copy()

    def paste(self):
        """Paste text"""
        self.text_edit.paste()

    def apply_modern_style(self):
        """Apply modern styling to the editor"""
        self.setStyleSheet("""
            QWidget#titleBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #f8f9fa, stop:1 #e9ecef);
                border-bottom: 1px solid #dee2e6;
            }
            
            QLabel#sceneTitle {
                font-size: 16pt;
                font-weight: bold;
                color: #212529;
            }
            
            QLabel#wordCount {
                color: #6c757d;
                font-size: 10pt;
                padding: 5px 10px;
            }
            
            QPushButton#aiButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                font-size: 11pt;
            }
            
            QPushButton#aiButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #764ba2, stop:1 #667eea);
            }
            
            QPushButton#aiButton:pressed {
                background: #5a67d8;
            }
            
            QPushButton#aiButton:disabled {
                background: #e9ecef;
                color: #adb5bd;
            }
            
            QToolBar#editorToolbar {
                background: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
                spacing: 2px;
                padding: 8px;
            }
            
            QToolBar#editorToolbar QToolButton {
                background: white;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 6px;
                margin: 2px;
                min-width: 30px;
                min-height: 30px;
            }
            
            QToolBar#editorToolbar QToolButton:hover {
                background: #e9ecef;
                border-color: #adb5bd;
            }
            
            QToolBar#editorToolbar QToolButton:pressed {
                background: #dee2e6;
            }
            
            QToolBar#editorToolbar QToolButton:checked {
                background: #667eea;
                color: white;
                border-color: #667eea;
            }
            
            QFontComboBox, QComboBox {
                background: white;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 5px;
                margin: 2px;
                min-width: 120px;
            }
            
            QFontComboBox:hover, QComboBox:hover {
                border-color: #adb5bd;
            }
            
            QTextEdit#mainEditor {
                background: white;
                border: none;
                padding: 20px;
                selection-background-color: #667eea;
                selection-color: white;
            }
        """)