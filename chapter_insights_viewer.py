"""
Chapter Insights Viewer - Shows analysis results when a chapter is selected
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QTabWidget, QTextEdit, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from typing import Dict, Any, List, Optional


class InsightIssueCard(QFrame):
    """Compact issue card for chapter view"""

    fix_requested = pyqtSignal(dict)  # issue_data

    def __init__(self, issue: Dict[str, Any]):
        super().__init__()
        self.issue = issue
        self.init_ui()

    def init_ui(self):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background: white;
                border-left: 3px solid #667eea;
                padding: 8px;
                margin: 3px 0;
            }
            QFrame:hover {
                background: #f8f9fa;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 6)

        # Severity badge
        severity = self.issue.get('severity', 'Minor')
        badge = QLabel(severity)
        badge.setStyleSheet(self._get_severity_style(severity))
        badge.setFixedWidth(70)
        layout.addWidget(badge)

        # Issue text
        issue_text = self.issue.get('issue', 'No description')
        label = QLabel(issue_text)
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 9pt; color: #212529;")
        layout.addWidget(label, stretch=1)

        # Fix button
        if self.issue.get('scene_id'):
            fix_btn = QPushButton("🔧")
            fix_btn.setFixedSize(30, 30)
            fix_btn.setStyleSheet("""
                QPushButton {
                    background: #667eea;
                    color: white;
                    border: none;
                    border-radius: 4px;
                }
                QPushButton:hover { background: #5a67d8; }
            """)
            fix_btn.setToolTip("AI Fix")
            fix_btn.clicked.connect(lambda: self.fix_requested.emit(self.issue))
            layout.addWidget(fix_btn)

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

    def __init__(self):
        super().__init__()
        self.chapter_id = None
        self.insight_service = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # Header with analyze button
        header_layout = QHBoxLayout()

        self.title_label = QLabel("Chapter Insights")
        self.title_label.setStyleSheet("font-size: 14pt; font-weight: bold; color: #212529;")
        header_layout.addWidget(self.title_label)

        header_layout.addStretch()

        self.analyze_btn = QPushButton("🤖 Run AI Analysis")
        self.analyze_btn.setStyleSheet("""
            QPushButton {
                background: #667eea;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background: #5a67d8; }
            QPushButton:disabled { background: #adb5bd; }
        """)
        self.analyze_btn.clicked.connect(self._on_analyze_clicked)
        self.analyze_btn.setEnabled(False)
        header_layout.addWidget(self.analyze_btn)

        layout.addLayout(header_layout)

        # Status label
        self.status_label = QLabel("No analysis yet")
        self.status_label.setStyleSheet("color: #6c757d; font-style: italic; margin: 5px 0;")
        layout.addWidget(self.status_label)

        # Tabs for different insight types
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                padding: 6px 12px;
                font-size: 9pt;
            }
            QTabBar::tab:selected {
                background: #667eea;
                color: white;
            }
        """)

        # Timeline tab
        self.timeline_widget = self._create_issues_widget()
        self.tabs.addTab(self.timeline_widget, "⏰ Timeline")

        # Consistency tab
        self.consistency_widget = self._create_issues_widget()
        self.tabs.addTab(self.consistency_widget, "🔍 Consistency")

        # Style tab
        self.style_widget = self._create_issues_widget()
        self.tabs.addTab(self.style_widget, "✍️ Style")

        # Reader tab
        self.reader_widget = QTextEdit()
        self.reader_widget.setReadOnly(True)
        self.reader_widget.setStyleSheet("background: white; border: 1px solid #dee2e6; font-size: 9pt;")
        self.tabs.addTab(self.reader_widget, "👁️ Reader")

        layout.addWidget(self.tabs)

        # Empty state
        self.empty_state = QLabel("Select a chapter to view insights")
        self.empty_state.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_state.setStyleSheet("color: #adb5bd; font-size: 12pt; padding: 40px;")
        layout.addWidget(self.empty_state)

        self.tabs.setVisible(False)

    def _create_issues_widget(self) -> QWidget:
        """Create a scrollable widget for issues"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #f8f9fa; }")

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(3)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        # Store reference
        widget.scroll_layout = scroll_layout

        return widget

    def load_chapter(self, chapter_id: str, chapter_name: str, project_id: str, insight_service):
        """Load chapter and its insights"""
        self.chapter_id = chapter_id
        self.project_id = project_id
        self.insight_service = insight_service

        self.title_label.setText(f"Insights: {chapter_name}")
        self.analyze_btn.setEnabled(True)
        self.empty_state.setVisible(False)
        self.tabs.setVisible(True)

        # Load existing insights
        self._load_insights()

    def _load_insights(self):
        """Load and display existing insights"""
        if not self.insight_service or not self.chapter_id:
            return

        db = self.insight_service.insight_db

        # Get project_id from db_manager
        # The insight_service has db_manager which has the project connection
        # We need to get project_id from somewhere - let's store it when loading chapter
        if not hasattr(self, 'project_id') or not self.project_id:
            print("No project_id available for loading insights")
            return

        # Load each type
        timeline = db.get_latest(self.project_id, 'chapter', self.chapter_id, 'timeline')
        consistency = db.get_latest(self.project_id, 'chapter', self.chapter_id, 'consistency')
        style = db.get_latest(self.project_id, 'chapter', self.chapter_id, 'style')
        reader = db.get_latest(self.project_id, 'chapter', self.chapter_id, 'reader_snapshot')

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
        critical = [i for i in issues if i.get('severity') == 'Critical']
        major = [i for i in issues if i.get('severity') == 'Major']
        minor = [i for i in issues if i.get('severity') == 'Minor']
        strengths = [i for i in issues if i.get('severity') == 'Strength']

        for issue_list, title in [(critical, f'Critical ({len(critical)})'),
                                   (major, f'Major ({len(major)})'),
                                   (minor, f'Minor ({len(minor)})'),
                                   (strengths, f'Strengths ({len(strengths)})')]:
            if issue_list:
                header = QLabel(title)
                header.setStyleSheet("font-size: 10pt; font-weight: bold; color: #495057; margin: 8px 0 4px 0;")
                layout.addWidget(header)

                for issue in issue_list[:10]:  # Limit to 10 per category
                    card = InsightIssueCard(issue)
                    card.fix_requested.connect(lambda i: self.fix_requested.emit(i, self.chapter_id))
                    layout.addWidget(card)

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
            self.analyze_requested.emit(self.chapter_id)

    def refresh(self):
        """Refresh the insights display"""
        self._load_insights()

    def clear(self):
        """Clear the display"""
        self.chapter_id = None
        self.insight_service = None
        self.title_label.setText("Chapter Insights")
        self.status_label.setText("No analysis yet")
        self.analyze_btn.setEnabled(False)
        self.empty_state.setVisible(True)
        self.tabs.setVisible(False)