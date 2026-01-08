"""
Chapter Insights Viewer - Shows analysis results when a chapter is selected
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTabWidget, QTextEdit, QGroupBox, QToolButton,
    QSpacerItem, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QFont, QIcon
from typing import Dict, Any, List, Optional


class CollapsibleSectionInsight(QWidget):
    """A widget that can collapse its contents"""
    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        self.toggle_btn = QPushButton(title)
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.setChecked(True)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                border: none;
                font-size: 10pt;
                font-weight: bold;
                color: #A0A0A0;
                padding: 6px;
                background: #1A1A1A;
                text-align: left;
                border-bottom: 1px solid #2D2D2D;
            }
            QPushButton:hover {
                background: #252526;
            }
            QPushButton:checked {
                color: #7C4DFF;
            }
        """)
        self.toggle_btn.toggled.connect(self._on_toggle)

        self.content_area = QWidget()
        self.content_layout = QVBoxLayout(self.content_area)
        self.content_layout.setContentsMargins(5, 5, 5, 5)
        self.content_layout.setSpacing(8)

        self.layout.addWidget(self.toggle_btn)
        self.layout.addWidget(self.content_area)

    def _on_toggle(self, checked: bool):
        self.content_area.setVisible(checked)

    def add_widget(self, widget: QWidget):
        self.content_layout.addWidget(widget)


class InsightIssueCard(QFrame):
    """Compact issue card for chapter view"""

    fix_requested = pyqtSignal(dict)  # issue_data
    jump_requested = pyqtSignal(dict) # issue_data

    def __init__(self, issue: Dict[str, Any]):
        super().__init__()
        self.issue = issue
        self.init_ui()

    def init_ui(self):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background: #252526;
                border-left: 3px solid #7C4DFF;
                padding: 10px;
                margin: 5px 0;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
            }
            QFrame:hover {
                background: #2D2D2D;
                border-left-color: #00D2FF;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)

        # Severity badge
        severity = self.issue.get('severity', 'Minor')
        badge = QLabel(severity)
        badge.setStyleSheet(self._get_severity_style(severity))
        badge.setFixedWidth(70)
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(badge)

        # Scene location hint
        loc = self.issue.get('location', '')
        if loc:
            loc_label = QLabel(f"📍 {loc}")
            loc_label.setStyleSheet("color: #888; font-size: 8pt;")
            loc_label.setWordWrap(True)
            header_layout.addWidget(loc_label)

        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Issue text
        issue_text = self.issue.get('issue', 'No description')
        label = QLabel(issue_text)
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 9pt; color: #E0E0E0; font-weight: bold;")
        layout.addWidget(label)

        # Detail text (optional)
        detail = self.issue.get('detail', '')
        if detail:
            detail_label = QLabel(detail)
            detail_label.setWordWrap(True)
            detail_label.setStyleSheet("font-size: 8pt; color: #A0A0A0;")
            layout.addWidget(detail_label)

        # Buttons layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        btn_layout.setContentsMargins(0, 4, 0, 0)

        # Jump button
        self.jump_btn = QPushButton("👁️ Jump to Scene")
        self.jump_btn.setFixedHeight(24)
        self.jump_btn.setStyleSheet("""
            QPushButton {
                background: #3E3E42;
                color: #E0E0E0;
                border: none;
                border-radius: 4px;
                font-size: 8pt;
                padding: 0 8px;
            }
            QPushButton:hover { background: #4E4E52; }
        """)
        self.jump_btn.clicked.connect(lambda: self.jump_requested.emit(self.issue))
        btn_layout.addWidget(self.jump_btn)

        # Fix button
        if self.issue.get('scene_id') and severity != "Strength":
            self.fix_btn = QPushButton("✨ AI Fix")
            self.fix_btn.setFixedHeight(24)
            self.fix_btn.setStyleSheet("""
                QPushButton {
                    background: #7C4DFF;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-weight: bold;
                    font-size: 8pt;
                    padding: 0 8px;
                }
                QPushButton:hover { background: #9E7CFF; }
            """)
            self.fix_btn.clicked.connect(lambda: self.fix_requested.emit(self.issue))
            btn_layout.addWidget(self.fix_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _get_severity_style(self, severity: str) -> str:
        styles = {
            'Critical': "background: #dc3545; color: white; padding: 3px 6px; border-radius: 8px; font-size: 8pt; font-weight: bold;",
            'Major': "background: #fd7e14; color: white; padding: 3px 6px; border-radius: 8px; font-size: 8pt; font-weight: bold;",
            'Minor': "background: #ffc107; color: black; padding: 3px 6px; border-radius: 8px; font-size: 8pt; font-weight: bold;",
            'Strength': "background: #198754; color: white; padding: 3px 6px; border-radius: 8px; font-size: 8pt;",
        }
        return styles.get(severity, styles['Minor'])


class ChapterInsightsViewer(QWidget):
    """Widget that displays chapter analysis insights"""

    analyze_requested = pyqtSignal(str)  # chapter_id
    fix_requested = pyqtSignal(dict, str)  # issue_data, chapter_id
    jump_requested = pyqtSignal(dict) # issue_data
    collapse_toggled = pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.chapter_id = None
        self.insight_service = None
        self.is_collapsed = False
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Header - consistent with MetadataPanel
        header = QFrame()
        header.setObjectName("insightHeader")
        header.setFixedHeight(50)
        header.setStyleSheet("""
            QFrame#insightHeader {
                background: #1A1A1A;
                border-bottom: 1px solid #2D2D2D;
            }
        """)
        self.header_layout = QHBoxLayout(header)
        self.header_layout.setContentsMargins(15, 0, 15, 0)
        self.header_layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.title_label = QLabel("Chapter Insights")
        self.title_label.setObjectName("titleLabel")
        self.title_label.setStyleSheet("""
            font-size: 14pt;
            font-weight: bold;
            color: #FFFFFF;
            background: transparent;
        """)
        self.header_layout.addWidget(self.title_label)

        self.header_spacer = QSpacerItem(0, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        self.header_layout.addSpacerItem(self.header_spacer)

        self.toggle_button = QToolButton()
        self.toggle_button.setObjectName("insightToggle")
        self.toggle_button.setText("−")
        self.toggle_button.setToolTip("Collapse insights panel")
        self.toggle_button.setCheckable(True)
        self.toggle_button.setStyleSheet("""
            QToolButton#insightToggle {
                border: 1px solid #3D3D3D;
                border-radius: 6px;
                padding: 4px 8px;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2D2D2D, stop:1 #252526);
                color: #E0E0E0;
                font-weight: bold;
            }
            QToolButton#insightToggle:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3D3D3D, stop:1 #333333);
                border-color: #7C4DFF;
            }
        """)
        self.toggle_button.clicked.connect(self.toggle_collapsed)
        self.header_layout.addWidget(self.toggle_button)

        layout.addWidget(header)
        self.header_widget = header

        # Main content area
        self.content_widget = QWidget()
        content_layout = QVBoxLayout(self.content_widget)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(15)

        # Status & Action Area
        status_action_layout = QHBoxLayout()
        
        # Status label
        self.status_label = QLabel("No analysis yet")
        self.status_label.setStyleSheet("color: #A0A0A0; font-style: italic;")
        status_action_layout.addWidget(self.status_label)
        
        status_action_layout.addStretch()

        self.analyze_btn = QPushButton("🤖 Run AI Analysis")
        self.analyze_btn.setFixedWidth(120)
        self.analyze_btn.setFixedHeight(26)
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #7C4DFF, stop:1 #6A3DE8);
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
                font-size: 8pt;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #8F66FF, stop:1 #7C4DFF);
            }
            QPushButton:disabled {
                background-color: #2D2D2D;
                color: #4D4D4D;
            }
        """)
        self.analyze_btn.clicked.connect(self._on_analyze_clicked)
        self.analyze_btn.setEnabled(False)
        status_action_layout.addWidget(self.analyze_btn)
        
        content_layout.addLayout(status_action_layout)

        # Tabs for different insight types
        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #2D2D2D;
                background: #121212;
                top: -1px;
            }
            QTabBar {
                qproperty-drawBase: 0;
                left: 0px;
            }
            QTabBar::tab {
                padding: 8px 12px;
                background: #1A1A1A;
                color: #A0A0A0;
                border: 1px solid #2D2D2D;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
                font-size: 8pt;
                min-width: 60px;
            }
            QTabBar::tab:selected {
                background: #252526;
                color: #FFFFFF;
                border-bottom: 2px solid #7C4DFF;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background: #2D2D2D;
                color: #FFFFFF;
            }
            QTabBar::scroller {
                width: 20px;
            }
        """)

        # Timeline tab
        self.timeline_widget = self._create_issues_widget()
        self.tabs.addTab(self.timeline_widget, "⏰ Timeline")

        # Consistency tab
        self.consistency_widget = self._create_issues_widget()
        self.tabs.addTab(self.consistency_widget, "🔍 Consistency")

        # World Rules tab
        self.world_rules_widget = self._create_issues_widget()
        self.tabs.addTab(self.world_rules_widget, "🌌 World Rules")

        # Style tab
        self.style_widget = self._create_issues_widget()
        self.tabs.addTab(self.style_widget, "✍️ Style")

        # Reader tab
        self.reader_widget = QTextEdit()
        self.reader_widget.setReadOnly(True)
        self.reader_widget.setStyleSheet("""
            background: #1E1E1E; 
            border: none; 
            color: #E0E0E0; 
            font-size: 10pt;
            padding: 10px;
        """)
        self.tabs.addTab(self.reader_widget, "👁️ Reader")

        content_layout.addWidget(self.tabs)

        # Empty state
        self.empty_state = QLabel("Select a chapter to view insights")
        self.empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state.setStyleSheet("color: #4D4D4D; font-size: 12pt; padding: 40px;")
        content_layout.addWidget(self.empty_state)

        layout.addWidget(self.content_widget)
        self.tabs.setVisible(False)

    def toggle_collapsed(self):
        """Collapse or expand the insights panel body."""
        self.is_collapsed = not self.is_collapsed
        if self.is_collapsed:
            self.content_widget.setVisible(False)
            self.title_label.setVisible(False)
            if self.header_spacer is not None:
                self.header_layout.removeItem(self.header_spacer)
            self.toggle_button.setText("+")
            self.toggle_button.setToolTip("Expand insights panel")
            self.header_layout.setContentsMargins(6, 6, 6, 6)
            self.header_layout.setAlignment(self.toggle_button, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        else:
            self.content_widget.setVisible(True)
            self.title_label.setVisible(True)
            if self.header_spacer is not None:
                self.header_layout.addItem(self.header_spacer)
            self.toggle_button.setText("−")
            self.toggle_button.setToolTip("Collapse insights panel")
            self.header_layout.setContentsMargins(15, 0, 15, 0)
            self.header_layout.setAlignment(self.toggle_button, Qt.AlignmentFlag.AlignRight)
        self.collapse_toggled.emit(self.is_collapsed)

    def _create_issues_widget(self) -> QWidget:
        """Create a scrollable widget for issues"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { 
                border: none; 
                background: transparent; 
            }
            QWidget {
                background: transparent;
            }
        """)

        scroll_content = QWidget()
        scroll_content.setObjectName("scrollContent")
        scroll_content.setStyleSheet("QWidget#scrollContent { background: transparent; }")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(10)
        scroll_layout.setContentsMargins(5, 5, 5, 5)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Store reference
        widget.scroll_layout = scroll_layout

        return widget

    def load_chapter(self, chapter_id: str, chapter_name: str, project_id: str, insight_service):
        """Load chapter and its insights"""
        try:
            print(f"[ChapterInsights] Loading chapter: {chapter_name}")
            print(f"  chapter_id: {chapter_id}")
            print(f"  project_id: {project_id}")
            print(f"  insight_service: {insight_service}")

            self.chapter_id = chapter_id
            self.project_id = project_id
            self.insight_service = insight_service

            self.title_label.setText(f"Insights: {chapter_name}")
            self.analyze_btn.setEnabled(True)
            self.empty_state.setVisible(False)
            self.tabs.setVisible(True)

            print("[ChapterInsights] Loading insights...")
            # Load existing insights
            self._load_insights()
            print("[ChapterInsights] Load complete")

        except Exception as e:
            print(f"[ChapterInsights] ERROR in load_chapter: {e}")
            import traceback
            traceback.print_exc()

            # Show error in UI
            self.status_label.setText(f"Error loading insights: {str(e)}")
            self.status_label.setStyleSheet("color: #dc3545; font-weight: bold;")

    def _load_insights(self):
        """Load and display existing insights"""
        try:
            print("[ChapterInsights] _load_insights called")

            if not self.insight_service or not self.chapter_id:
                print(f"  Missing: insight_service={self.insight_service}, chapter_id={self.chapter_id}")
                return

            print(f"  Getting insight_db...")
            db = self.insight_service.insight_db
            print(f"  db={db}")

            # Get project_id from db_manager
            # The insight_service has db_manager which has the project connection
            # We need to get project_id from somewhere - let's store it when loading chapter
            if not hasattr(self, 'project_id') or not self.project_id:
                print("  No project_id available for loading insights")
                self.status_label.setText("No project ID")
                return

            print(f"  Loading insights for project={self.project_id}, chapter={self.chapter_id}")

            # Load each type
            print("  Loading timeline...")
            timeline = db.get_latest(self.project_id, 'chapter', self.chapter_id, 'timeline')
            print(f"    timeline={timeline is not None}")

            print("  Loading consistency...")
            consistency = db.get_latest(self.project_id, 'chapter', self.chapter_id, 'consistency')
            print(f"    consistency={consistency is not None}")

            print("  Loading style...")
            style = db.get_latest(self.project_id, 'chapter', self.chapter_id, 'style')
            print(f"    style={style is not None}")

            print("  Loading reader...")
            reader = db.get_latest(self.project_id, 'chapter', self.chapter_id, 'reader_snapshot')
            print(f"    reader={reader is not None}")

            print("  Loading world rules...")
            world_rules = db.get_latest(self.project_id, 'chapter', self.chapter_id, 'world_rules')
            print(f"    world_rules={world_rules is not None}")

        except Exception as e:
            print(f"[ChapterInsights] ERROR in _load_insights: {e}")
            import traceback
            traceback.print_exc()
            self.status_label.setText(f"Error: {str(e)}")
            return

        # Check if we have any insights
        has_insights = any([timeline, consistency, style, reader])

        if has_insights:
            self.status_label.setText("✓ Analysis available")
            self.status_label.setStyleSheet("color: #28a745; font-weight: bold; margin: 5px 0;")
        else:
            self.status_label.setText("No analysis yet - click 'Run AI Analysis'")
            self.status_label.setStyleSheet("color: #6c757d; font-style: italic; margin: 5px 0;")

        # Populate tabs
        if timeline:
            issues = timeline.payload.get('issues', [])
            self._populate_issues(self.timeline_widget, issues)
        else:
            self._show_empty(self.timeline_widget)

        if consistency:
            issues = consistency.payload.get('issues', [])
            self._populate_issues(self.consistency_widget, issues)
        else:
            self._show_empty(self.consistency_widget)

        if world_rules:
            issues = world_rules.payload.get('issues', [])
            self._populate_issues(self.world_rules_widget, issues)
        else:
            self._show_empty(self.world_rules_widget)

        if style:
            issues = style.payload.get('issues', [])
            self._populate_issues(self.style_widget, issues)
        else:
            self._show_empty(self.style_widget)

        if reader:
            self._display_reader_snapshot(reader.payload)
        else:
            self.reader_widget.setPlainText("No reader simulation available")

    def _populate_issues(self, widget: QWidget, issues: List[Dict]):
        """Populate widget with issue cards"""
        layout = widget.scroll_layout

        # Clear existing
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not issues:
            self._show_empty(widget)
            return

        # Group by severity
        groups = [
            ('Critical Issues', [i for i in issues if i.get('severity') == 'Critical']),
            ('Major Issues', [i for i in issues if i.get('severity') == 'Major']),
            ('Minor Issues', [i for i in issues if i.get('severity') == 'Minor']),
            ('Suggestions', [i for i in issues if i.get('severity') == 'Suggestion']),
            ('Strengths', [i for i in issues if i.get('severity') == 'Strength']),
            ('Observations', [i for i in issues if i.get('severity') not in ['Critical', 'Major', 'Minor', 'Suggestion', 'Strength']])
        ]

        for title, issue_list in groups:
            if issue_list:
                section = CollapsibleSectionInsight(f"{title} ({len(issue_list)})")
                layout.addWidget(section)

                for issue in issue_list:
                    card = InsightIssueCard(issue)
                    card.fix_requested.connect(lambda i: self.fix_requested.emit(i, self.chapter_id))
                    card.jump_requested.connect(self.jump_requested.emit)
                    section.add_widget(card)

        layout.addStretch()

    def _show_empty(self, widget: QWidget):
        """Show empty state in widget"""
        layout = widget.scroll_layout

        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        empty = QLabel("No issues found ✓")
        empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty.setStyleSheet("color: #28a745; font-size: 11pt; padding: 30px;")
        layout.addWidget(empty)

    def _display_reader_snapshot(self, data: Dict):
        """Display reader simulation"""
        # Unwrap nested payload if it exists (from _store_generic)
        if 'payload' in data and isinstance(data['payload'], dict):
            data = data['payload']

        text = "READER SIMULATION\n\n"

        for reader_type in ['careful_reader', 'skimmer', 'distracted_reader']:
            reader_data = data.get(reader_type, {})
            title = reader_type.replace('_', ' ').title()

            text += f"{title}:\n"
            text += f"  Understanding: {reader_data.get('understanding', 'N/A')}\n"
            text += f"  Confusion: {reader_data.get('confusion', 'None')}\n"
            text += f"  Missed: {reader_data.get('missed', 'Nothing')}\n"
            text += "\n"

        self.reader_widget.setPlainText(text)

    def _on_analyze_clicked(self):
        """Handle analyze button click"""
        if self.chapter_id:
            self.analyze_btn.setEnabled(False)
            self.analyze_btn.setText("⏳ Analyzing...")
            self.analyze_requested.emit(self.chapter_id)

    def refresh(self):
        """Refresh the insights display"""
        if self.chapter_id:
            self.analyze_btn.setText("🤖 Run AI Analysis")
            self.analyze_btn.setEnabled(True)
        self._load_insights()

    def clear(self):
        """Clear the display"""
        self.chapter_id = None
        self.insight_service = None
        self.title_label.setText("Chapter Insights")
        self.status_label.setText("No analysis yet")
        self.status_label.setStyleSheet("color: #A0A0A0; font-style: italic; margin-bottom: 5px;")
        self.analyze_btn.setEnabled(False)
        self.empty_state.setVisible(True)
        self.tabs.setVisible(False)