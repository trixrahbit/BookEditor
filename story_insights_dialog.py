"""
Story Insights Dialog - Comprehensive analysis display
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QScrollArea, QWidget,
    QLabel, QPushButton, QFrame, QProgressBar, QTextBrowser
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont
from typing import Dict, List, Any


class InsightCard(QFrame):
    """Individual insight card widget"""

    def __init__(self, title: str, severity: str, points: List[str], parent=None):
        super().__init__(parent)
        self.setObjectName("insightCard")
        self.init_ui(title, severity, points)

    def init_ui(self, title: str, severity: str, points: List[str]):
        """Initialize the card UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Header
        header_layout = QHBoxLayout()

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        title_label.setWordWrap(True)
        header_layout.addWidget(title_label, 1)

        # Severity badge
        severity_label = QLabel(severity)
        severity_label.setObjectName(f"severity_{severity}")
        severity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        severity_label.setFixedWidth(90)
        header_layout.addWidget(severity_label)

        layout.addLayout(header_layout)

        # Points
        for point in points:
            point_label = QLabel(f"• {point}")
            point_label.setWordWrap(True)
            point_label.setObjectName("cardPoint")
            layout.addWidget(point_label)

        self.apply_card_style(severity)

    def apply_card_style(self, severity: str):
        """Apply styling based on severity"""
        border_colors = {
            "critical": "#dc3545",
            "important": "#ffc107",
            "minor": "#17a2b8"
        }

        bg_colors = {
            "critical": "#f8d7da",
            "important": "#fff3cd",
            "minor": "#d1ecf1"
        }

        border_color = border_colors.get(severity, "#6c757d")
        bg_color = bg_colors.get(severity, "#e9ecef")

        self.setStyleSheet(f"""
            QFrame#insightCard {{
                background: white;
                border-left: 4px solid {border_color};
                border-radius: 8px;
                padding: 15px;
                margin: 10px 0;
            }}

            QLabel#cardTitle {{
                font-size: 13pt;
                font-weight: bold;
                color: #212529;
                margin-bottom: 5px;
            }}

            QLabel#severity_critical {{
                background: #dc3545;
                color: white;
                border-radius: 12px;
                padding: 4px 12px;
                font-weight: bold;
                font-size: 9pt;
            }}

            QLabel#severity_important {{
                background: #ffc107;
                color: #212529;
                border-radius: 12px;
                padding: 4px 12px;
                font-weight: bold;
                font-size: 9pt;
            }}

            QLabel#severity_minor {{
                background: #17a2b8;
                color: white;
                border-radius: 12px;
                padding: 4px 12px;
                font-weight: bold;
                font-size: 9pt;
            }}

            QLabel#cardPoint {{
                color: #495057;
                font-size: 11pt;
                padding-left: 10px;
                margin: 3px 0;
            }}
        """)


class AnalysisWorker(QThread):
    """Background worker for running AI analysis"""
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, analyzer, project_data, scenes, characters, plot_threads, chapters):
        super().__init__()
        self.analyzer = analyzer
        self.project_data = project_data
        self.scenes = scenes
        self.characters = characters
        self.plot_threads = plot_threads
        self.chapters = chapters

    def run(self):
        """Run all analyses"""
        try:
            results = {}
            total_steps = 9

            # Character analysis
            self.progress.emit(1, "Analyzing character arcs and development...")
            results['characters'] = self.analyzer.analyze_characters(self.scenes, self.characters)

            # Plot analysis
            self.progress.emit(2, "Analyzing plot structure and coherence...")
            results['plot'] = self.analyzer.analyze_plot(self.scenes, self.plot_threads)

            # Conflicts
            self.progress.emit(3, "Identifying key conflicts...")
            results['conflicts'] = self.analyzer.analyze_conflicts(self.scenes, self.chapters)

            # Themes
            self.progress.emit(4, "Discovering themes and motifs...")
            results['themes'] = self.analyzer.analyze_themes(self.scenes)

            # Tone
            self.progress.emit(5, "Analyzing tone and voice...")
            results['tone'] = self.analyzer.analyze_tone(self.scenes)

            # Market
            self.progress.emit(6, "Evaluating market potential...")
            results['market'] = self.analyzer.analyze_market(self.project_data, self.scenes)

            # Flow
            self.progress.emit(7, "Assessing narrative flow and pacing...")
            results['flow'] = self.analyzer.analyze_flow(self.scenes, self.chapters)

            # Style
            self.progress.emit(8, "Analyzing writing style patterns...")
            results['style'] = self.analyzer.analyze_style(self.scenes)

            # Comprehensive insights
            self.progress.emit(9, "Generating comprehensive insights...")
            results['insights'] = self.analyzer.analyze_insights(self.scenes, self.characters, self.plot_threads)

            self.finished.emit(results)

        except Exception as e:
            self.error.emit(str(e))


class StoryInsightsDialog(QDialog):
    """Dialog for displaying comprehensive story insights"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("📊 Story Insights")
        self.setMinimumSize(900, 700)
        self.init_ui()
        self.apply_modern_style()

    def init_ui(self):
        """Initialize the dialog UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(0)

        # Header
        header = QWidget()
        header.setObjectName("insightsHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(30, 20, 30, 20)

        title = QLabel("Story Insights")
        title.setObjectName("mainTitle")
        header_layout.addWidget(title)

        subtitle = QLabel(
            "This page offers reflections on your story's development potential and your unique writing style. "
            "These insights are designed to illuminate possibilities rather than prescribe changes. "
            "Consider them as thoughtful observations to inspire your creative process."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)
        header_layout.addWidget(subtitle)

        layout.addWidget(header)

        # Progress bar (hidden when complete)
        self.progress_widget = QWidget()
        progress_layout = QVBoxLayout(self.progress_widget)
        progress_layout.setContentsMargins(30, 20, 30, 20)

        self.progress_label = QLabel("Initializing analysis...")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        progress_layout.addWidget(self.progress_bar)

        layout.addWidget(self.progress_widget)

        # Scroll area for insights
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setObjectName("insightsScroll")

        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(30, 20, 30, 20)
        self.content_layout.setSpacing(20)

        scroll.setWidget(self.content_widget)
        layout.addWidget(scroll)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.setObjectName("closeButton")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def show_analysis_results(self, results: Dict[str, Any]):
        """Display analysis results"""
        self.progress_widget.hide()

        # Story Development Opportunities
        dev_section = self.create_section_header(
            "Story Development Opportunities",
            "These insights highlight thematic and structural elements with potential for enhancement."
        )
        self.content_layout.addWidget(dev_section)

        # Add development insights from results
        if results.get('plot') and results['plot'].success:
            self.parse_and_add_insights(results['plot'].content, "Story Development")

        if results.get('conflicts') and results['conflicts'].success:
            self.parse_and_add_insights(results['conflicts'].content, "Conflicts")

        if results.get('flow') and results['flow'].success:
            self.parse_and_add_insights(results['flow'].content, "Pacing")

        # Writing Style Reflections
        style_section = self.create_section_header(
            "Writing Style Reflections",
            "These observations focus on patterns in your writing style and voice."
        )
        self.content_layout.addWidget(style_section)

        if results.get('style') and results['style'].success:
            self.parse_and_add_insights(results['style'].content, "Writing Style")

        if results.get('tone') and results['tone'].success:
            self.parse_and_add_insights(results['tone'].content, "Tone")

        # Additional sections
        if results.get('themes') and results['themes'].success:
            themes_section = self.create_section_header("Themes & Motifs", "")
            self.content_layout.addWidget(themes_section)
            self.add_text_content(results['themes'].content)

        if results.get('market') and results['market'].success:
            market_section = self.create_section_header("Market Analysis", "")
            self.content_layout.addWidget(market_section)
            self.add_text_content(results['market'].content)

        self.content_layout.addStretch()

    def create_section_header(self, title: str, description: str) -> QWidget:
        """Create a section header"""
        widget = QWidget()
        widget.setObjectName("sectionHeader")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 20, 0, 10)

        title_label = QLabel(title)
        title_label.setObjectName("sectionTitle")
        layout.addWidget(title_label)

        if description:
            desc_label = QLabel(description)
            desc_label.setObjectName("sectionDesc")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)

        return widget

    def parse_and_add_insights(self, content: str, category: str):
        """Parse AI response and create insight cards"""
        # Simple parsing - split by numbered points or headers
        lines = content.split('\n')
        current_insight = None
        current_points = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if it's a numbered item or header
            if line[0].isdigit() and ('.' in line[:3] or ':' in line[:3]):
                # Save previous insight
                if current_insight:
                    severity = self.determine_severity(current_insight, current_points)
                    card = InsightCard(current_insight, severity, current_points)
                    self.content_layout.addWidget(card)

                # Start new insight
                current_insight = line.split('.', 1)[-1].split(':', 1)[-1].strip()
                current_points = []

            elif line.startswith('-') or line.startswith('•'):
                # Add point to current insight
                current_points.append(line[1:].strip())

        # Add last insight
        if current_insight:
            severity = self.determine_severity(current_insight, current_points)
            card = InsightCard(current_insight, severity, current_points)
            self.content_layout.addWidget(card)

    def determine_severity(self, title: str, points: List[str]) -> str:
        """Determine severity based on content"""
        title_lower = title.lower()
        content_lower = ' '.join(points).lower()

        critical_keywords = ['critical', 'major', 'essential', 'fundamental', 'crucial']
        important_keywords = ['important', 'significant', 'notable', 'considerable']

        if any(word in title_lower or word in content_lower for word in critical_keywords):
            return "critical"
        elif any(word in title_lower or word in content_lower for word in important_keywords):
            return "important"
        else:
            return "minor"

    def add_text_content(self, content: str):
        """Add formatted text content"""
        browser = QTextBrowser()
        browser.setObjectName("textContent")
        browser.setMarkdown(content)
        browser.setMaximumHeight(300)
        self.content_layout.addWidget(browser)

    def update_progress(self, step: int, message: str):
        """Update progress bar"""
        self.progress_bar.setValue(int(step / 9 * 100))
        self.progress_label.setText(message)

    def show_error(self, error: str):
        """Show error message"""
        self.progress_widget.hide()
        error_label = QLabel(f"❌ Analysis Error\n\n{error}")
        error_label.setObjectName("errorLabel")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_label.setWordWrap(True)
        self.content_layout.addWidget(error_label)

    def apply_modern_style(self):
        """Apply modern styling"""
        self.setStyleSheet("""
            QDialog {
                background: #121212;
            }

            QWidget#insightsHeader {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #7C4DFF, stop:1 #5E35B1);
                border-radius: 6px;
            }

            QLabel#mainTitle {
                font-size: 24pt;
                font-weight: bold;
                color: white;
            }

            QLabel#subtitle {
                font-size: 11pt;
                color: rgba(255, 255, 255, 0.95);
                margin-top: 10px;
            }

            QLabel#sectionTitle {
                font-size: 18pt;
                font-weight: bold;
                color: #7C4DFF;
                border-bottom: 3px solid #7C4DFF;
                padding-bottom: 5px;
            }

            QLabel#sectionDesc {
                font-size: 10pt;
                color: #A0A0A0;
                margin-top: 5px;
            }

            QProgressBar {
                border: 1px solid #2D2D2D;
                border-radius: 5px;
                text-align: center;
                height: 25px;
                background: #1A1A1A;
                color: white;
            }

            QProgressBar::chunk {
                background: #7C4DFF;
            }

            QTextBrowser#textContent {
                background: #1E1E1E;
                border: 1px solid #2D2D2D;
                border-radius: 8px;
                padding: 15px;
                color: #E0E0E0;
            }

            QLabel#errorLabel {
                font-size: 14pt;
                color: #FF5252;
                padding: 40px;
            }

            QPushButton#closeButton {
                background: #252526;
                color: #E0E0E0;
                border: 1px solid #3D3D3D;
                border-radius: 6px;
                padding: 12px 30px;
                font-weight: bold;
                font-size: 11pt;
                margin: 15px;
            }

            QPushButton#closeButton:hover {
                background: #3D3D3D;
                border-color: #7C4DFF;
            }
            
            QScrollArea {
                border: none;
                background: transparent;
            }
            
            QScrollArea QWidget {
                background: transparent;
            }
        """)