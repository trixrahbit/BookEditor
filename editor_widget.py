"""
Enhanced rich text editor widget with AI analysis button
"""

import os
import re

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, QLabel, QToolBar, QPushButton,
    QFontComboBox, QComboBox, QColorDialog, QMessageBox, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QAction, QTextCharFormat, QColor, QTextListFormat, QTextCursor, QTextDocument
from models.project import Scene, ItemType
from db_manager import DatabaseManager
from live_text_check import LiveTextChecker, CheckResult, SpellIssue, GrammarIssue

class EditorWidget(QWidget):
    content_changed = pyqtSignal()
    rewrite_requested = pyqtSignal(str)  # Emits selected text for rewriting
    rewrite_selection_action_requested = pyqtSignal()
    rewrite_scene_action_requested = pyqtSignal()
    def __init__(self):
        super().__init__()
        self.current_item: Scene = None
        self.db_manager: DatabaseManager = None
        self.project_id: str = None
        self.auto_save_timer = QTimer()
        self.auto_save_timer.timeout.connect(self.auto_save)
        self.auto_save_timer.setInterval(5000)  # 5 seconds
        self.persona_manager = None
        self.current_text_color = QColor(Qt.GlobalColor.black)
        self.current_highlight_color = QColor(Qt.GlobalColor.transparent)
        self.init_ui()
        self.apply_modern_style()
        self.live_checks_enabled = True
        self._spell_issues: list[SpellIssue] = []
        self._grammar_issues: list[GrammarIssue] = []

        # Initialize live spell/grammar checker
        java_path = os.environ.get("JAVA_PATH")
        if java_path and not os.path.exists(java_path):
            java_path = None
        self.live_checker = LiveTextChecker(
            parent=self,
            language="en_US",
            debounce_ms=650,
            do_spell=True,
            do_grammar=True,
            java_path=java_path
        )
        self.live_checker.result_ready.connect(self._on_check_result)
        self.live_checker.debug.connect(lambda msg: print(f"[LiveCheck] {msg}"))

    def init_ui(self):
        """Initialize the editor UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Title bar
        title_bar = QWidget()
        title_bar.setObjectName("titleBar")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(15, 10, 15, 10)

        self.title_label = QLabel("No scene selected")
        self.title_label.setObjectName("sceneTitle")
        title_layout.addWidget(self.title_label)

        title_layout.addStretch()

        self.word_count_label = QLabel("0 words")
        self.word_count_label.setObjectName("wordCount")
        title_layout.addWidget(self.word_count_label)

        layout.addWidget(title_bar)

        # Text editor - CREATE THIS FIRST
        self.text_edit = QTextEdit()
        self.text_edit.setObjectName("mainEditor")
        self.text_edit.setAcceptRichText(True)
        self.text_edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.text_edit.customContextMenuRequested.connect(self.show_editor_context_menu)

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
        self.toolbar = toolbar
        self.toolbar_compact = False

        # Font Selection
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont("Georgia"))
        self.font_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.font_combo.setMinimumWidth(80)
        self.font_combo.setMaximumWidth(180)  # slightly reduced
        self.font_combo.currentFontChanged.connect(self.change_font_family)
        toolbar.addWidget(self.font_combo)

        self.toolbar_font_separator = toolbar.addSeparator()

        # Font Size
        self.font_size_combo = QComboBox()
        self.font_size_combo.setEditable(True)
        self.font_size_combo.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self.font_size_combo.setMinimumWidth(55)
        self.font_size_combo.setMaximumWidth(70)
        sizes = ['8', '9', '10', '11', '12', '14', '16', '18', '20', '24', '28', '32', '36', '48', '72']
        self.font_size_combo.addItems(sizes)
        self.font_size_combo.setCurrentText('12')
        self.font_size_combo.activated.connect(self.change_font_size_combo)
        toolbar.addWidget(self.font_size_combo)

        self.toolbar_size_separator = toolbar.addSeparator()

        # Group 1: Basic Formatting
        self.bold_action = QAction("𝐁", self)
        self.bold_action.setCheckable(True)
        self.bold_action.setShortcut("Ctrl+B")
        self.bold_action.setToolTip("Bold (Ctrl+B)")
        self.bold_action.triggered.connect(self.toggle_bold)
        toolbar.addAction(self.bold_action)

        self.italic_action = QAction("𝑰", self)
        self.italic_action.setCheckable(True)
        self.italic_action.setShortcut("Ctrl+I")
        self.italic_action.setToolTip("Italic (Ctrl+I)")
        self.italic_action.triggered.connect(self.toggle_italic)
        toolbar.addAction(self.italic_action)

        self.underline_action = QAction("U̲", self)
        self.underline_action.setCheckable(True)
        self.underline_action.setShortcut("Ctrl+U")
        self.underline_action.setToolTip("Underline (Ctrl+U)")
        self.underline_action.triggered.connect(self.toggle_underline)
        toolbar.addAction(self.underline_action)

        self.strike_action = QAction("S̶", self)
        self.strike_action.setCheckable(True)
        self.strike_action.setToolTip("Strikethrough")
        self.strike_action.triggered.connect(self.toggle_strikethrough)
        toolbar.addAction(self.strike_action)

        self.toolbar_format_separator = toolbar.addSeparator()

        # Group 2: Colors
        self.text_color_action = QAction("A", self)
        self.text_color_action.setToolTip("Text Color")
        self.text_color_action.triggered.connect(self.change_text_color)
        toolbar.addAction(self.text_color_action)

        self.highlight_action = QAction("H", self)
        self.highlight_action.setToolTip("Highlight Color")
        self.highlight_action.triggered.connect(self.change_highlight_color)
        toolbar.addAction(self.highlight_action)

        self.toolbar_color_separator = toolbar.addSeparator()

        # Group 3: Alignment
        self.align_left_action = QAction("⬅", self)
        self.align_left_action.setCheckable(True)
        self.align_left_action.setToolTip("Align Left")
        self.align_left_action.triggered.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignLeft))
        toolbar.addAction(self.align_left_action)

        self.align_center_action = QAction("⬌", self)
        self.align_center_action.setCheckable(True)
        self.align_center_action.setToolTip("Align Center")
        self.align_center_action.triggered.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignCenter))
        toolbar.addAction(self.align_center_action)

        self.align_right_action = QAction("➡", self)
        self.align_right_action.setCheckable(True)
        self.align_right_action.setToolTip("Align Right")
        self.align_right_action.triggered.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignRight))
        toolbar.addAction(self.align_right_action)

        self.align_justify_action = QAction("⬍", self)
        self.align_justify_action.setCheckable(True)
        self.align_justify_action.setToolTip("Justify")
        self.align_justify_action.triggered.connect(lambda: self.set_alignment(Qt.AlignmentFlag.AlignJustify))
        toolbar.addAction(self.align_justify_action)

        self.toolbar_align_separator = toolbar.addSeparator()

        # Group 4: Lists & Indentation
        self.bullet_action = QAction("●", self)
        self.bullet_action.setToolTip("Bullet List")
        self.bullet_action.triggered.connect(self.toggle_bullet_list)
        toolbar.addAction(self.bullet_action)

        self.number_action = QAction("1.", self)
        self.number_action.setToolTip("Numbered List")
        self.number_action.triggered.connect(self.toggle_numbered_list)
        toolbar.addAction(self.number_action)

        self.indent_less_action = QAction("◁", self)
        self.indent_less_action.setToolTip("Decrease Indent")
        self.indent_less_action.triggered.connect(self.decrease_indent)
        toolbar.addAction(self.indent_less_action)

        self.indent_more_action = QAction("▷", self)
        self.indent_more_action.setToolTip("Increase Indent")
        self.indent_more_action.triggered.connect(self.increase_indent)
        toolbar.addAction(self.indent_more_action)

        self.toolbar_list_separator = toolbar.addSeparator()

        # Group 5: Clear
        self.clear_format_action = QAction("✕", self)
        self.clear_format_action.setToolTip("Clear Formatting")
        self.clear_format_action.triggered.connect(self.clear_formatting)
        toolbar.addAction(self.clear_format_action)

        parent_layout.addWidget(toolbar)

        # Connect cursor position changed to update toolbar
        self.text_edit.cursorPositionChanged.connect(self.update_format_actions)

        # Initial color indicators
        self.update_color_indicators()

    def set_toolbar_compact(self, compact: bool):
        """Toggle compact mode for the toolbar.

        Note: Both modes now use similar spacing to maintain layout stability.
        """
        if self.toolbar_compact == compact:
            return
        self.toolbar_compact = compact

        icon_size = QSize(16, 16) if compact else QSize(18, 18)
        self.toolbar.setIconSize(icon_size)

        # Ensure consistent dark theme and minimal size changes
        # Padding and spacing are kept nearly identical to prevent jitter
        self.toolbar.setStyleSheet(f"""
            QToolBar#editorToolbar {{ 
                padding: 2px; 
                spacing: {2 if compact else 4}px; 
                background: #1A1A1A;
                border-bottom: 1px solid #2D2D2D;
            }}
            QToolButton {{
                padding: {2 if compact else 4}px;
            }}
        """)

    def html_to_plaintext(self, html: str) -> str:
        """Convert stored HTML to plain text while preserving paragraph breaks."""
        doc = QTextDocument()
        doc.setHtml(html or "")
        text = doc.toPlainText()

        # Normalize NBSP + line endings
        text = text.replace("\u00a0", " ")
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # Collapse excessive blank lines but keep paragraphs
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Trim trailing whitespace per line
        text = "\n".join([ln.rstrip() for ln in text.splitlines()])
        return text.strip()

    def load_item(self, item, db_manager: DatabaseManager, project_id: str):
        """Load an item into the editor.

        - SCENE: editable rich text (HTML)
        - CHAPTER: read-only combined plaintext view of all scenes in the chapter
        - Other: read-only/empty
        """
        self.current_item = item
        self.db_manager = db_manager
        self.project_id = project_id

        # Block signals while loading
        self.text_edit.blockSignals(True)
        self.text_edit.setExtraSelections([])

        if item.item_type == ItemType.SCENE:
            self.title_label.setText(item.name)
            self.text_edit.setAcceptRichText(True)
            self.text_edit.setHtml(item.content or "")

            self.set_enabled(True)
            self.auto_save_timer.start()

        elif item.item_type == ItemType.CHAPTER:
            self.title_label.setText(f"{item.name} (chapter view)")
            self.text_edit.setAcceptRichText(False)

            # Load scenes in this chapter and show as a single combined view
            try:
                chapter_scenes = self.db_manager.load_items(
                    self.project_id,
                    ItemType.SCENE,
                    parent_id=item.id
                )
            except Exception:
                chapter_scenes = []

            parts = []
            for s in chapter_scenes:
                parts.append(
                    f"=== {s.name} ===\n\n{self.html_to_plaintext(getattr(s, 'content', '') or '')}"
                )

            combined = "\n\n".join(parts).strip() if parts else "(No scenes in this chapter)"
            self.text_edit.setPlainText(combined)

            self.set_enabled(False)  # read-only
            self.auto_save_timer.stop()

        else:
            self.title_label.setText(f"{item.name} (not editable)")
            self.text_edit.setAcceptRichText(False)
            self.text_edit.setPlainText("")

            self.set_enabled(False)
            self.auto_save_timer.stop()

        self.text_edit.blockSignals(False)
        self.update_word_count()

        # ✅ Run checks immediately when a scene loads (not just after typing)
        if self.live_checks_enabled and item.item_type == ItemType.SCENE:
            self.live_checker.schedule(self.text_edit.toPlainText())
        else:
            # Clear underlines in non-scene views
            self._spell_issues = []
            self._grammar_issues = []
            self.text_edit.setExtraSelections([])

    def on_text_changed(self):
        """Handle text changes"""
        # print("DEBUG: on_text_changed")
        self.update_word_count()
        self.content_changed.emit()
        # schedule live checks (threaded + debounced)
        if self.live_checker:
            # print("DEBUG: Scheduling check")
            self.live_checker.schedule(self.text_edit.toPlainText())

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
        color = QColorDialog.getColor(self.current_text_color, self)
        if color.isValid():
            self.current_text_color = color
            fmt = QTextCharFormat()
            fmt.setForeground(color)
            self.merge_format_on_word_or_selection(fmt)
            self.update_color_indicators()

    def change_highlight_color(self):
        """Change highlight/background color"""
        color = QColorDialog.getColor(self.current_highlight_color, self)
        if color.isValid():
            self.current_highlight_color = color
            fmt = QTextCharFormat()
            fmt.setBackground(color)
            self.merge_format_on_word_or_selection(fmt)
            self.update_color_indicators()

    def update_color_indicators(self):
        """Update the visual color indicators on the toolbar buttons"""
        # We use a colored bottom border to indicate the color
        text_color_hex = self.current_text_color.name()

        # For highlight, if it's transparent, we use white/none
        if self.current_highlight_color.alpha() == 0:
            highlight_color_hex = "transparent"
            highlight_border = "#dee2e6" # default border
        else:
            highlight_color_hex = self.current_highlight_color.name()
            highlight_border = highlight_color_hex

        # Find the tool buttons in the toolbar
        for action in [self.text_color_action, self.highlight_action]:
            button = self.toolbar.widgetForAction(action)
            if button:
                if action == self.text_color_action:
                    button.setStyleSheet(f"""
                        QToolButton {{
                            border-bottom: 3px solid {text_color_hex};
                            padding-bottom: 1px;
                        }}
                    """)
                else:
                    button.setStyleSheet(f"""
                        QToolButton {{
                            border-bottom: 3px solid {highlight_border};
                            background-color: {highlight_color_hex};
                            padding-bottom: 1px;
                        }}
                    """)

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

        # Update colors
        self.current_text_color = fmt.foreground().color()
        self.current_highlight_color = fmt.background().color()
        self.update_color_indicators()

    def set_enabled(self, enabled: bool):
        """Enable/disable editing + formatting controls.

        We keep the editor widget enabled so users can still select/copy text
        in read-only views (e.g., chapter combined view). We toggle readOnly instead.
        """
        self.text_edit.setReadOnly(not enabled)

        # Formatting actions
        self.bold_action.setEnabled(enabled)
        self.italic_action.setEnabled(enabled)
        self.underline_action.setEnabled(enabled)
        self.strike_action.setEnabled(enabled)
        self.font_combo.setEnabled(enabled)
        self.font_size_combo.setEnabled(enabled)
        self.text_color_action.setEnabled(enabled)
        self.highlight_action.setEnabled(enabled)
        self.align_left_action.setEnabled(enabled)
        self.align_center_action.setEnabled(enabled)
        self.align_right_action.setEnabled(enabled)
        self.align_justify_action.setEnabled(enabled)

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

    def show_editor_context_menu(self, position):
        """Show context menu in editor (with spell + grammar suggestions)"""
        from PyQt6.QtWidgets import QMenu

        menu = self.text_edit.createStandardContextMenu()

        # Cursor at click position
        click_cursor = self.text_edit.cursorForPosition(position)
        pos = click_cursor.position()

        # Find issues at cursor
        spell_issue = self._find_spell_at_pos(pos)
        grammar_issue = self._find_grammar_at_pos(pos)

        # -------------------------
        # Spelling menu
        # -------------------------
        if spell_issue:
            menu.addSeparator()
            spelling_menu = menu.addMenu("🧠 Spelling")

            # Suggestions (if we have any)
            if spell_issue.suggestions:
                for sug in spell_issue.suggestions[:8]:
                    act = spelling_menu.addAction(sug)
                    act.triggered.connect(lambda _, s=sug, i=spell_issue: self._replace_range(i.start, i.length, s))
            else:
                spelling_menu.addAction("(No suggestions)").setEnabled(False)

            spelling_menu.addSeparator()

            ignore_act = spelling_menu.addAction("Ignore (this session)")
            ignore_act.triggered.connect(lambda _, w=spell_issue.word: self._ignore_word_session(w))

            add_act = spelling_menu.addAction("Add to dictionary")
            add_act.triggered.connect(lambda _, w=spell_issue.word: self._add_custom_word(w))

        # -------------------------
        # Grammar menu
        # -------------------------
        if grammar_issue:
            menu.addSeparator()
            grammar_menu = menu.addMenu("🧩 Grammar")

            if grammar_issue.suggestions:
                for sug in grammar_issue.suggestions[:8]:
                    act = grammar_menu.addAction(sug)
                    act.triggered.connect(lambda _, s=sug, i=grammar_issue: self._replace_range(i.start, i.length, s))
            else:
                grammar_menu.addAction(grammar_issue.message).setEnabled(False)

        # -------------------------
        # Persona rewrite
        # -------------------------
        cursor = self.text_edit.textCursor()
        if cursor.hasSelection():
            menu.addSeparator()

            rewrite_selection_action = QAction("🎨 Rewrite Selection with Persona", self)
            rewrite_selection_action.triggered.connect(lambda: self.rewrite_selection_action_requested.emit())
            menu.addAction(rewrite_selection_action)

        menu.exec(self.text_edit.viewport().mapToGlobal(position))

    def request_persona_rewrite(self):
        """Request persona rewrite (emit signal to main window)"""
        # Emit signal that main window will handle
        # Or call parent.rewrite_selection_with_persona() if parent is MainWindow

    def request_ai_rewrite(self):
        """Request AI rewrite of selected text"""
        cursor = self.text_edit.textCursor()
        if cursor.hasSelection():
            selected_text = cursor.selectedText()
            self.rewrite_requested.emit(selected_text)

    def apply_modern_style(self):
        """Apply modern futuristic styling to the editor"""
        self.setStyleSheet("""
            QWidget#titleBar {
                background: #1A1A1A;
                border-bottom: 1px solid #2D2D2D;
            }
            
            QLabel#sceneTitle {
                font-size: 16pt;
                font-weight: bold;
                color: #7C4DFF;
                padding: 2px 10px;
                background: transparent;
                border: none;
            }
            
            QLabel#wordCount {
                color: #A0A0A0;
                font-size: 10pt;
                padding: 5px 10px;
            }
            
            QToolBar#editorToolbar {
                background: #1A1A1A;
                border-bottom: 1px solid #2D2D2D;
                padding: 2px;
                spacing: 4px;
                color: #E0E0E0;
            }
            
            QToolBar#editorToolbar QToolButton {
                background: #252526;
                border: 1px solid #3D3D3D;
                border-radius: 4px;
                padding: 4px;
                margin: 1px;
            }
            
            QToolBar#editorToolbar QToolButton:hover {
                background: #3D3D3D;
                border-color: #7C4DFF;
            }
            
            QToolBar#editorToolbar QToolButton:checked {
                background: #7C4DFF;
                color: white;
            }
            
            QFontComboBox, QComboBox {
                background: #252526;
                border: 1px solid #3D3D3D;
                border-radius: 4px;
                padding: 2px 5px;
                margin: 1px;
                color: #E0E0E0;
            }
            
            QTextEdit#mainEditor {
                background-color: #1E1E1E;
                color: #E0E0E0;
                border: none;
                padding: 40px;
                selection-background-color: #7C4DFF;
                selection-color: white;
                font-family: 'Georgia', 'serif';
                font-size: 12pt;
                line-height: 1.6;
            }
        """)

    def rewrite_selection_with_persona(self):
        """Rewrite selected text with persona"""
        if not self.persona_manager:
            QMessageBox.warning(self, "No Project", "Please open a project first")
            return

        # Get selected text
        cursor = self.editor.text_edit.textCursor()
        selected_text = cursor.selectedText()

        if not selected_text:
            QMessageBox.warning(self, "No Selection", "Please select text to rewrite")
            return

        # Convert Qt paragraph separator to newline
        selected_text = selected_text.replace('\u2029', '\n')

        # Open rewrite dialog
        from persona_rewrite_dialog import PersonaRewriteDialog
        from ai_manager import ai_manager

        dialog = PersonaRewriteDialog(
            self,
            ai_manager,
            self.persona_manager,
            selected_text,
            scope="selection"
        )

        if dialog.exec():
            # Apply rewritten text
            rewritten = dialog.get_rewritten_text()
            if rewritten:
                cursor.insertText(rewritten)
                QMessageBox.information(self, "Applied", "Rewrite applied successfully!")

    def set_project_context(self, db_manager, project_id, persona_manager=None):
        self.db_manager = db_manager
        self.project_id = project_id
        if persona_manager is not None:
            self.persona_manager = persona_manager

    def _on_check_result(self, result: CheckResult):
        """Receive threaded results and underline issues."""
        self._spell_issues = list(result.spell)
        self._grammar_issues = list(result.grammar)
        self._apply_issue_underlines()

    def _apply_issue_underlines(self):
        """Apply red (spelling) + blue (grammar) wavy underlines via ExtraSelections."""
        doc = self.text_edit.document()
        text = self.text_edit.toPlainText()
        doc_len = len(text)

        # print(f"DEBUG: Applying underlines to text length {doc_len}. Spell={len(self._spell_issues)}, Grammar={len(self._grammar_issues)}")

        selections: list[QTextEdit.ExtraSelection] = []

        def add_underline(start: int, length: int, kind: str):
            if start < 0 or length <= 0:
                return
            if start >= doc_len:
                return

            end = min(start + length, doc_len)

            cursor = QTextCursor(doc)
            cursor.setPosition(start)
            cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

            fmt = QTextCharFormat()

            # Spellcheck underline is rendered most reliably by Qt
            if kind == "spell":
                fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
                fmt.setUnderlineColor(QColor("#FF0000")) # Brighter red
            else:
                fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.WaveUnderline)
                fmt.setUnderlineColor(QColor("#0000FF")) # Brighter blue

            sel = QTextEdit.ExtraSelection()
            sel.cursor = cursor
            sel.format = fmt
            selections.append(sel)

        for i in self._spell_issues:
            add_underline(i.start, i.length, "spell")

        for i in self._grammar_issues:
            add_underline(i.start, i.length, "grammar")

        self.text_edit.setExtraSelections(selections)

    def _find_spell_at_pos(self, pos: int):
        for i in self._spell_issues:
            if i.start <= pos < (i.start + i.length):
                return i
        return None

    def _find_grammar_at_pos(self, pos: int):
        for i in self._grammar_issues:
            if i.start <= pos < (i.start + i.length):
                return i
        return None

    def _replace_range(self, start: int, length: int, replacement: str):
        cursor = self.text_edit.textCursor()
        cursor.beginEditBlock()
        cursor.setPosition(start)
        cursor.setPosition(start + length, QTextCursor.MoveMode.KeepAnchor)
        cursor.insertText(replacement)
        cursor.endEditBlock()

        # Re-run checks after applying suggestion
        if self.live_checks_enabled:
            self.live_checker.schedule(self.text_edit.toPlainText())

    def _ignore_word_session(self, word: str):
        self.live_checker.ignore_word_session(word)
        # remove existing underlines for that word by re-checking
        if self.live_checks_enabled:
            self.live_checker.schedule(self.text_edit.toPlainText())

    def _add_custom_word(self, word: str):
        self.live_checker.add_custom_word(word)
        # TODO: persist to DB/file per project (see below)
        if self.live_checks_enabled:
            self.live_checker.schedule(self.text_edit.toPlainText())


    def resizeEvent(self, event):
        super().resizeEvent(event)

        # Heuristic thresholds — tweak these if you want
        w = self.width()

        # Compact when editor is narrow (usually because right panel is open)
        # 850 is a safer threshold for the new set of icons
        should_compact = w < 850

        self.set_toolbar_compact(should_compact)
