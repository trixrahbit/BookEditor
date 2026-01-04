"""
Story Insights Viewer - Shows all tracked issues by location
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QPushButton, QScrollArea, QFrame, QTextEdit, QToolButton, QSizePolicy
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class IssueCard(QFrame):
    """Visual card for displaying an issue"""

    def __init__(self, issue_data: dict):
        super().__init__()
        self.issue_data = issue_data or {}
        self.details_visible = False
        self.init_ui()

    def init_ui(self):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
                margin: 5px;
            }
            QFrame:hover {
                border-color: #667eea;
                background: #f8f9fa;
            }
        """)

        layout = QVBoxLayout(self)

        # Header with severity badge
        header = QHBoxLayout()

        severity = str(self.issue_data.get('severity', 'Minor'))
        severity_badge = QLabel(severity)
        severity_badge.setStyleSheet(self._get_severity_style(severity))

        # ✅ Fix clipping: let label size itself, but guarantee enough height
        fm = severity_badge.fontMetrics()
        severity_badge.setMinimumHeight(fm.height() + 14)  # font height + padding room
        severity_badge.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        severity_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)

        header.addWidget(severity_badge)
        header.addStretch()

        location_label = QLabel(f"📍 {self.issue_data.get('location', 'Unknown')}")
        location_label.setStyleSheet("color: #6c757d; font-size: 10pt;")
        header.addWidget(location_label)

        layout.addLayout(header)

        # Issue title
        title = QLabel(self.issue_data.get('issue', 'No description'))
        title.setWordWrap(True)
        title.setStyleSheet("font-size: 12pt; font-weight: bold; color: #212529; margin: 8px 0;")
        layout.addWidget(title)

        # Chapter info
        chapter = QLabel(f"Chapter: {self.issue_data.get('chapter', 'Unknown')}")
        chapter.setStyleSheet("color: #495057; font-size: 10pt; margin-bottom: 8px;")
        layout.addWidget(chapter)

        # Collapsible details (especially for Suggestions)
        detail_text = (self.issue_data.get('detail') or "").strip()
        suggestions = self.issue_data.get('suggestions')  # optional: list/str if you have it

        # Decide if this card should be collapsible
        collapsible = (
            severity in {"Suggestion", "Strength", "Observation"}
            or bool(suggestions)
            or len(detail_text) > 180
        )

        if collapsible and (detail_text or suggestions):
            # Toggle row
            self.toggle_btn = QToolButton()
            self.toggle_btn.setCheckable(True)
            self.toggle_btn.setChecked(False)
            self.toggle_btn.setArrowType(Qt.ArrowType.RightArrow)
            self.toggle_btn.setText(" Details")
            self.toggle_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            self.toggle_btn.setStyleSheet("""
                QToolButton {
                    border: none;
                    color: #667eea;
                    font-weight: bold;
                    padding: 4px 0;
                }
                QToolButton:hover { color: #4c63d2; }
            """)
            self.toggle_btn.toggled.connect(self._toggle_details)
            layout.addWidget(self.toggle_btn)

            # Details container (collapsed by default)
            self.details_container = QWidget()
            details_layout = QVBoxLayout(self.details_container)
            details_layout.setContentsMargins(0, 6, 0, 0)
            details_layout.setSpacing(6)

            if detail_text:
                detail = QLabel(detail_text)
                detail.setWordWrap(True)
                detail.setStyleSheet("color: #6c757d; font-size: 10pt;")
                details_layout.addWidget(detail)

            if suggestions:
                # Support list or string
                if isinstance(suggestions, list):
                    sug_text = "\n".join([f"• {str(s).strip()}" for s in suggestions if str(s).strip()])
                else:
                    sug_text = str(suggestions).strip()

                if sug_text:
                    sug_label = QLabel("💡 Suggestions")
                    sug_label.setStyleSheet("color: #495057; font-weight: bold; margin-top: 4px;")
                    details_layout.addWidget(sug_label)

                    sug_body = QLabel(sug_text)
                    sug_body.setWordWrap(True)
                    sug_body.setStyleSheet("color: #6c757d; font-size: 10pt;")
                    details_layout.addWidget(sug_body)

            self.details_container.setVisible(False)
            layout.addWidget(self.details_container)

        else:
            # Non-collapsible: keep old behavior (always show detail)
            if detail_text:
                detail = QLabel(detail_text)
                detail.setWordWrap(True)
                detail.setStyleSheet("color: #6c757d; font-size: 10pt;")
                layout.addWidget(detail)

    def _toggle_details(self, checked: bool):
        self.details_visible = checked
        self.details_container.setVisible(checked)
        self.toggle_btn.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)

    def _get_severity_style(self, severity: str) -> str:
        """Get CSS style for severity badge"""
        styles = {
            # ✅ Increase vertical padding so badge can grow naturally
            'Critical': "background: #dc3545; color: white; padding: 6px 14px; border-radius: 14px; font-weight: bold;",
            'Major': "background: #fd7e14; color: white; padding: 6px 14px; border-radius: 14px; font-weight: bold;",
            'Minor': "background: #ffc107; color: black; padding: 6px 14px; border-radius: 14px; font-weight: bold;",
            'Suggestion': "background: #0dcaf0; color: white; padding: 6px 14px; border-radius: 14px;",
            'Strength': "background: #198754; color: white; padding: 6px 14px; border-radius: 14px;",
            'Observation': "background: #6c757d; color: white; padding: 6px 14px; border-radius: 14px;"
        }
        return styles.get(severity, styles['Observation'])



class StoryInsightsViewer(QDialog):
    """Main dialog for viewing all story insights"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.timeline_data = None
        self.consistency_data = None
        self.style_data = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Story Insights")
        self.setMinimumSize(900, 700)

        layout = QVBoxLayout(self)

        # Header
        header = QLabel("📊 Story Insights Dashboard")
        header.setStyleSheet("""
            font-size: 20pt;
            font-weight: bold;
            color: #212529;
            padding: 20px;
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #667eea, stop:1 #764ba2);
            color: white;
            border-radius: 8px;
        """)
        layout.addWidget(header)

        # Tabs for different analysis types
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                background: white;
            }
            QTabBar::tab {
                padding: 10px 20px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #667eea;
                color: white;
            }
        """)

        # Timeline tab
        self.timeline_tab = self.create_issues_tab()
        self.tabs.addTab(self.timeline_tab, "⏰ Timeline Issues")

        # Consistency tab
        self.consistency_tab = self.create_issues_tab()
        self.tabs.addTab(self.consistency_tab, "🔍 Consistency Issues")

        # Style tab
        self.style_tab = self.create_issues_tab()
        self.tabs.addTab(self.style_tab, "✍️ Writing Style")

        # Full Reports tab
        self.reports_tab = self.create_reports_tab()
        self.tabs.addTab(self.reports_tab, "📄 Full Reports")

        layout.addWidget(self.tabs)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                padding: 10px 30px;
                border-radius: 4px;
                font-size: 11pt;
            }
            QPushButton:hover {
                background: #5a6268;
            }
        """)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def create_issues_tab(self) -> QWidget:
        """Create a tab for displaying issues"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Scroll area for issues
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #f8f9fa; }")

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(10)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        # Store reference to scroll layout for adding issues
        widget.scroll_layout = scroll_layout
        widget.scroll_widget = scroll_widget

        return widget

    def create_reports_tab(self) -> QWidget:
        """Create tab for full text reports"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.reports_text = QTextEdit()
        self.reports_text.setReadOnly(True)
        self.reports_text.setStyleSheet("""
            QTextEdit {
                background: white;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 15px;
                font-family: 'Courier New', monospace;
                font-size: 10pt;
            }
        """)
        layout.addWidget(self.reports_text)

        return widget

    def load_timeline_data(self, data: dict):
        """Load timeline analysis data"""
        self.timeline_data = data
        self._populate_issues_tab(self.timeline_tab, data.get('issues', []))
        self._update_reports()

    def load_consistency_data(self, data: dict):
        """Load consistency analysis data"""
        self.consistency_data = data
        self._populate_issues_tab(self.consistency_tab, data.get('issues', []))
        self._update_reports()

    def load_style_data(self, data: dict):
        """Load style analysis data"""
        self.style_data = data
        self._populate_issues_tab(self.style_tab, data.get('issues', []))
        self._update_reports()

    def _populate_issues_tab(self, tab: QWidget, issues: list):
        """Populate a tab with issue cards"""
        # Clear existing
        layout = tab.scroll_layout
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not issues:
            no_issues = QLabel("✅ No issues found!")
            no_issues.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_issues.setStyleSheet("font-size: 14pt; color: #28a745; padding: 50px;")
            layout.addWidget(no_issues)
        else:
            # Group by severity
            critical = [i for i in issues if i.get('severity') == 'Critical']
            major = [i for i in issues if i.get('severity') == 'Major']
            minor = [i for i in issues if i.get('severity') == 'Minor']
            other = [i for i in issues if i.get('severity') not in ['Critical', 'Major', 'Minor']]

            for issue_list, title in [(critical, 'Critical Issues'), (major, 'Major Issues'),
                                      (minor, 'Minor Issues'), (other, 'Observations')]:
                if issue_list:
                    header = QLabel(f"── {title} ({len(issue_list)}) ──")
                    header.setStyleSheet("font-size: 12pt; font-weight: bold; color: #495057; margin: 15px 0 10px 0;")
                    layout.addWidget(header)

                    for issue in issue_list:
                        card = IssueCard(issue)
                        layout.addWidget(card)

        layout.addStretch()

    def _update_reports(self):
        """Update the full reports tab"""
        report_text = ""

        if self.timeline_data:
            report_text += "=" * 60 + "\n"
            report_text += "TIMELINE ANALYSIS\n"
            report_text += "=" * 60 + "\n\n"
            report_text += self.timeline_data.get('final_report', 'No report available')
            report_text += "\n\n"

        if self.consistency_data:
            report_text += "=" * 60 + "\n"
            report_text += "CONSISTENCY ANALYSIS\n"
            report_text += "=" * 60 + "\n\n"
            report_text += self.consistency_data.get('final_report', 'No report available')
            report_text += "\n\n"

        if self.style_data:
            report_text += "=" * 60 + "\n"
            report_text += "WRITING STYLE ANALYSIS\n"
            report_text += "=" * 60 + "\n\n"
            report_text += self.style_data.get('final_report', 'No report available')

        self.reports_text.setText(report_text)