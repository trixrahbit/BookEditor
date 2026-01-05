"""
Advanced Analysis Dialog - Shows comprehensive chapter analysis
with microservices-style results and meta-layer reasoning
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTabWidget, QWidget,
    QLabel, QPushButton, QScrollArea, QFrame, QProgressBar,
    QTextEdit, QGroupBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont
from typing import Dict, Any, List, Optional


class AnalysisWorker(QThread):
    """Background worker for running chapter analysis"""
    progress = pyqtSignal(str, int)  # message, percentage
    finished = pyqtSignal(dict)  # All results
    error = pyqtSignal(str)

    def __init__(self, insight_service, project_id: str, chapter_id: str):
        super().__init__()
        self.insight_service = insight_service
        self.project_id = project_id
        self.chapter_id = chapter_id

    def run(self):
        try:
            self.progress.emit("Starting analysis...", 10)

            # Enqueue all chapter analyses
            self.insight_service.enqueue_chapter_analyses(
                self.project_id,
                self.chapter_id,
                include_style=True,
                include_reader_snapshot=True
            )

            self.progress.emit("Analysis queued, waiting for results...", 30)

            # Wait for results (simplified - in production use proper job completion tracking)
            import time
            time.sleep(2)  # Give worker time to process

            self.progress.emit("Retrieving results...", 80)

            # Load results from database
            results = self._load_results()

            self.progress.emit("Complete!", 100)
            self.finished.emit(results)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))

    def _load_results(self) -> Dict[str, Any]:
        """Load all analysis results for this chapter"""
        db = self.insight_service.insight_db

        return {
            'timeline': db.get_latest(self.project_id, 'chapter', self.chapter_id, 'timeline'),
            'consistency': db.get_latest(self.project_id, 'chapter', self.chapter_id, 'consistency'),
            'style': db.get_latest(self.project_id, 'chapter', self.chapter_id, 'style'),
            'reader_snapshot': db.get_latest(self.project_id, 'chapter', self.chapter_id, 'reader_snapshot'),
        }


class IssueCardAdvanced(QFrame):
    """Issue card with AI Fix integration"""

    fix_requested = pyqtSignal(dict, str, str)  # issue_data, scene_id, scene_content

    def __init__(self, issue: Dict[str, Any], db_manager, project_id: str):
        super().__init__()
        self.issue = issue
        self.db_manager = db_manager
        self.project_id = project_id
        self.init_ui()

    def init_ui(self):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background: white;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 12px;
                margin: 5px;
            }
            QFrame:hover {
                border-color: #667eea;
                background: #f8f9fa;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Header: Severity + Fix button
        header = QHBoxLayout()

        severity = self.issue.get('severity', 'Minor')
        badge = QLabel(severity)
        badge.setStyleSheet(self._get_severity_style(severity))
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.addWidget(badge)

        header.addStretch()

        # AI Fix button if we have scene_id
        if self.issue.get('scene_id'):
            fix_btn = QPushButton("🔧 AI Fix")
            fix_btn.setStyleSheet("""
                QPushButton {
                    background: #667eea;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 4px 10px;
                    font-weight: bold;
                }
                QPushButton:hover { background: #5a67d8; }
            """)
            fix_btn.clicked.connect(self._request_fix)
            header.addWidget(fix_btn)

        # Location
        location = QLabel(f"📍 {self.issue.get('location', 'Unknown')}")
        location.setStyleSheet("color: #6c757d; font-size: 9pt;")
        header.addWidget(location)

        layout.addLayout(header)

        # Issue title
        title = QLabel(self.issue.get('issue', 'No description'))
        title.setWordWrap(True)
        title.setStyleSheet("font-size: 11pt; font-weight: bold; color: #212529;")
        layout.addWidget(title)

        # Detail
        detail = self.issue.get('detail', '')
        if detail:
            detail_label = QLabel(detail)
            detail_label.setWordWrap(True)
            detail_label.setStyleSheet("color: #6c757d; font-size: 9pt;")
            layout.addWidget(detail_label)

        # Suggestions
        suggestions = self.issue.get('suggestions', [])
        if suggestions:
            sug_text = "\n".join([f"• {s}" for s in suggestions if s])
            sug_label = QLabel(f"💡 {sug_text}")
            sug_label.setWordWrap(True)
            sug_label.setStyleSheet(
                "color: #495057; font-size: 9pt; background: #e7f3ff; padding: 6px; border-radius: 4px;")
            layout.addWidget(sug_label)

    def _request_fix(self):
        """Request AI fix for this issue"""
        scene_id = self.issue.get('scene_id')
        if not scene_id:
            return

        scene = self.db_manager.load_item(scene_id)
        if not scene:
            return

        self.fix_requested.emit(self.issue, scene_id, getattr(scene, 'content', ''))

    def _get_severity_style(self, severity: str) -> str:
        styles = {
            'Critical': "background: #dc3545; color: white; padding: 4px 10px; border-radius: 12px; font-weight: bold; font-size: 9pt;",
            'Major': "background: #fd7e14; color: white; padding: 4px 10px; border-radius: 12px; font-weight: bold; font-size: 9pt;",
            'Minor': "background: #ffc107; color: black; padding: 4px 10px; border-radius: 12px; font-weight: bold; font-size: 9pt;",
            'Strength': "background: #198754; color: white; padding: 4px 10px; border-radius: 12px; font-size: 9pt;",
        }
        return styles.get(severity, styles['Minor'])


class AdvancedAnalysisDialog(QDialog):
    """Main dialog for advanced chapter analysis"""

    def __init__(self, parent, db_manager, project_id: str, chapter_id: str, insight_service):
        super().__init__(parent)
        self.db_manager = db_manager
        self.project_id = project_id
        self.chapter_id = chapter_id
        self.insight_service = insight_service
        self.results = {}

        self.setWindowTitle("AI Analysis")
        self.setMinimumSize(1000, 800)
        self.init_ui()

        # Auto-run analysis on open
        self.run_analysis()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Header
        chapter = self.db_manager.load_item(self.chapter_id)
        chapter_name = chapter.name if chapter else "Unknown Chapter"

        header = QLabel(f"🤖 AI Analysis: {chapter_name}")
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

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #dee2e6;
                border-radius: 4px;
                text-align: center;
                height: 24px;
            }
            QProgressBar::chunk {
                background: #667eea;
                border-radius: 3px;
            }
        """)
        self.progress_label = QLabel("Ready")
        self.progress_label.setStyleSheet("color: #6c757d; font-size: 9pt; margin: 4px;")
        layout.addWidget(self.progress_label)
        layout.addWidget(self.progress_bar)

        # Tabs for different analysis types
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                padding: 10px 20px;
                margin-right: 2px;
                font-size: 10pt;
            }
            QTabBar::tab:selected {
                background: #667eea;
                color: white;
            }
        """)

        # Create tabs
        self.timeline_tab = self.create_issues_tab()
        self.tabs.addTab(self.timeline_tab, "⏰ Timeline")

        self.consistency_tab = self.create_issues_tab()
        self.tabs.addTab(self.consistency_tab, "🔍 Consistency")

        self.style_tab = self.create_issues_tab()
        self.tabs.addTab(self.style_tab, "✍️ Style")

        self.reader_tab = self.create_reader_tab()
        self.tabs.addTab(self.reader_tab, "👁️ Reader Simulation")

        layout.addWidget(self.tabs)

        # Buttons
        button_layout = QHBoxLayout()

        reanalyze_btn = QPushButton("🔄 Re-Analyze")
        reanalyze_btn.setStyleSheet("""
            QPushButton {
                background: #667eea;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background: #5a67d8; }
        """)
        reanalyze_btn.clicked.connect(self.run_analysis)
        button_layout.addWidget(reanalyze_btn)

        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover { background: #5a6268; }
        """)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def create_issues_tab(self) -> QWidget:
        """Create tab for displaying issues"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: #f8f9fa; }")

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(8)

        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)

        widget.scroll_layout = scroll_layout
        return widget

    def create_reader_tab(self) -> QWidget:
        """Create tab for reader simulation results"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        self.reader_text = QTextEdit()
        self.reader_text.setReadOnly(True)
        self.reader_text.setStyleSheet("""
            QTextEdit {
                background: white;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 12px;
                font-size: 10pt;
            }
        """)
        layout.addWidget(self.reader_text)

        return widget

    def run_analysis(self):
        """Start background analysis"""
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.progress_label.setVisible(True)

        # Start worker
        self.worker = AnalysisWorker(self.insight_service, self.project_id, self.chapter_id)
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_progress(self, message: str, percentage: int):
        self.progress_label.setText(message)
        self.progress_bar.setValue(percentage)

    def on_finished(self, results: Dict[str, Any]):
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.results = results
        self.display_results()

    def on_error(self, error: str):
        self.progress_bar.setVisible(False)
        self.progress_label.setText(f"Error: {error}")
        self.progress_label.setStyleSheet("color: #dc3545; font-weight: bold;")

    def display_results(self):
        """Display all analysis results"""
        # Timeline
        if self.results.get('timeline'):
            timeline_data = self.results['timeline'].payload
            issues = timeline_data.get('issues', [])
            self.populate_issues_tab(self.timeline_tab, issues)

        # Consistency
        if self.results.get('consistency'):
            cons_data = self.results['consistency'].payload
            issues = cons_data.get('issues', [])
            self.populate_issues_tab(self.consistency_tab, issues)

        # Style
        if self.results.get('style'):
            style_data = self.results['style'].payload
            issues = style_data.get('issues', [])
            self.populate_issues_tab(self.style_tab, issues)

        # Reader simulation
        if self.results.get('reader_snapshot'):
            reader_data = self.results['reader_snapshot'].payload
            self.display_reader_snapshot(reader_data)

    def populate_issues_tab(self, tab: QWidget, issues: List[Dict]):
        """Populate tab with issue cards"""
        layout = tab.scroll_layout

        # Clear existing
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if not issues:
            no_issues = QLabel("✅ No issues found!")
            no_issues.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_issues.setStyleSheet("font-size: 13pt; color: #28a745; padding: 40px;")
            layout.addWidget(no_issues)
        else:
            # Group by severity
            critical = [i for i in issues if i.get('severity') == 'Critical']
            major = [i for i in issues if i.get('severity') == 'Major']
            minor = [i for i in issues if i.get('severity') == 'Minor']
            strengths = [i for i in issues if i.get('severity') == 'Strength']

            for issue_list, title in [(critical, 'Critical'), (major, 'Major'),
                                      (minor, 'Minor'), (strengths, 'Strengths')]:
                if issue_list:
                    header = QLabel(f"── {title} ({len(issue_list)}) ──")
                    header.setStyleSheet("font-size: 11pt; font-weight: bold; color: #495057; margin: 10px 0 6px 0;")
                    layout.addWidget(header)

                    for issue in issue_list:
                        card = IssueCardAdvanced(issue, self.db_manager, self.project_id)
                        card.fix_requested.connect(self.on_fix_requested)
                        layout.addWidget(card)

        layout.addStretch()

    def display_reader_snapshot(self, data: Dict[str, Any]):
        """Display reader simulation results"""
        text = "READER SIMULATION\n"
        text += "=" * 60 + "\n\n"

        for reader_type in ['careful_reader', 'skimmer', 'distracted_reader']:
            reader_data = data.get(reader_type, {})
            title = reader_type.replace('_', ' ').title()

            text += f"{title}:\n"
            text += f"  Understanding: {reader_data.get('understanding', 'N/A')}\n"
            text += f"  Confusion: {reader_data.get('confusion', 'None')}\n"
            text += f"  Missed: {reader_data.get('missed', 'Nothing')}\n"
            text += "\n"

        self.reader_text.setPlainText(text)

    def on_fix_requested(self, issue: Dict, scene_id: str, scene_content: str):
        """Handle AI fix request"""
        from ai_fix_dialog import AIFixDialog
        dialog = AIFixDialog(self, issue, scene_id, scene_content, self.db_manager, self.project_id)
        dialog.exec()