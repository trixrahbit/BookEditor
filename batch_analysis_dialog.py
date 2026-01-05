"""
Batch Analysis Manager - Handles analyzing all chapters with progress tracking
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QCheckBox, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from typing import List, Dict, Any
import time


class BatchAnalysisWorker(QThread):
    """Worker thread for analyzing multiple chapters"""

    progress = pyqtSignal(int, int, str)  # current, total, message
    chapter_complete = pyqtSignal(str, bool, str)  # chapter_name, success, message
    finished = pyqtSignal(dict)  # summary stats
    error = pyqtSignal(str)

    def __init__(self, insight_service, project_id: str, chapters: List[Dict[str, Any]],
                 analyze_timeline: bool, analyze_consistency: bool, analyze_style: bool, analyze_reader: bool):
        super().__init__()
        self.insight_service = insight_service
        self.project_id = project_id
        self.chapters = chapters
        self.analyze_timeline = analyze_timeline
        self.analyze_consistency = analyze_consistency
        self.analyze_style = analyze_style
        self.analyze_reader = analyze_reader
        self.should_stop = False

    def run(self):
        try:
            stats = {
                'total': len(self.chapters),
                'completed': 0,
                'failed': 0,
                'skipped': 0
            }

            for i, chapter in enumerate(self.chapters):
                if self.should_stop:
                    self.progress.emit(i, len(self.chapters), "Cancelled by user")
                    break

                chapter_id = chapter['id']
                chapter_name = chapter['name']

                self.progress.emit(i + 1, len(self.chapters), f"Analyzing: {chapter_name}")

                try:
                    # Enqueue analyses
                    self.insight_service.enqueue_chapter_analyses(
                        self.project_id,
                        chapter_id,
                        include_style=self.analyze_style,
                        include_reader_snapshot=self.analyze_reader
                    )

                    # Wait for job queue to process (with longer timeout)
                    # AI analysis can take 2-5 minutes per chapter depending on size
                    timeout = 300  # 5 minutes max per chapter
                    start_time = time.time()
                    last_check_time = start_time

                    while time.time() - start_time < timeout:
                        if self.should_stop:
                            break

                        # Check if analyses exist
                        db = self.insight_service.insight_db

                        has_timeline = True
                        has_consistency = True
                        has_style = True
                        has_reader = True

                        if self.analyze_timeline:
                            has_timeline = db.get_latest(self.project_id, 'chapter', chapter_id, 'timeline') is not None
                        if self.analyze_consistency:
                            has_consistency = db.get_latest(self.project_id, 'chapter', chapter_id, 'consistency') is not None
                        if self.analyze_style:
                            has_style = db.get_latest(self.project_id, 'chapter', chapter_id, 'style') is not None
                        if self.analyze_reader:
                            has_reader = db.get_latest(self.project_id, 'chapter', chapter_id, 'reader_snapshot') is not None

                        all_complete = (
                            (has_timeline or not self.analyze_timeline) and
                            (has_consistency or not self.analyze_consistency) and
                            (has_style or not self.analyze_style) and
                            (has_reader or not self.analyze_reader)
                        )

                        if all_complete:
                            stats['completed'] += 1
                            elapsed = time.time() - start_time
                            self.chapter_complete.emit(chapter_name, True, f"✓ Complete ({elapsed:.1f}s)")
                            break

                        # Show progress every 5 seconds
                        current_time = time.time()
                        if current_time - last_check_time >= 5:
                            elapsed = current_time - start_time
                            self.progress.emit(i + 1, len(self.chapters), f"Analyzing: {chapter_name} ({elapsed:.0f}s)")
                            last_check_time = current_time

                        time.sleep(1)  # Check every second
                    else:
                        # Timeout - but check one more time
                        db = self.insight_service.insight_db
                        has_any = (
                            db.get_latest(self.project_id, 'chapter', chapter_id, 'timeline') is not None or
                            db.get_latest(self.project_id, 'chapter', chapter_id, 'consistency') is not None or
                            db.get_latest(self.project_id, 'chapter', chapter_id, 'style') is not None or
                            db.get_latest(self.project_id, 'chapter', chapter_id, 'reader_snapshot') is not None
                        )

                        if has_any:
                            # Partial completion
                            stats['completed'] += 1
                            self.chapter_complete.emit(chapter_name, True, "⚠ Partial (timeout)")
                        else:
                            # Complete timeout
                            stats['failed'] += 1
                            self.chapter_complete.emit(chapter_name, False, "✗ Timeout (no results)")

                    # Small delay between chapters to prevent overwhelming the system
                    time.sleep(1)

                except Exception as e:
                    stats['failed'] += 1
                    error_msg = str(e)[:100]
                    self.chapter_complete.emit(chapter_name, False, f"✗ Error: {error_msg}")

            self.finished.emit(stats)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))

    def stop(self):
        """Request worker to stop"""
        self.should_stop = True


class BatchAnalysisDialog(QDialog):
    """Dialog for batch analyzing all chapters"""

    def __init__(self, parent, db_manager, project_id: str, insight_service):
        super().__init__(parent)
        self.db_manager = db_manager
        self.project_id = project_id
        self.insight_service = insight_service
        self.worker = None

        self.setWindowTitle("Analyze All Chapters")
        self.setMinimumSize(700, 600)
        self.init_ui()
        self.load_chapters()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QLabel("📊 Batch Chapter Analysis")
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

        # Info label
        self.info_label = QLabel("Select analysis types and click 'Start Analysis'")
        self.info_label.setStyleSheet("color: #6c757d; padding: 10px; font-size: 10pt;")
        layout.addWidget(self.info_label)

        # Analysis type selection
        options_group = QGroupBox("Analysis Types")
        options_layout = QVBoxLayout()

        self.timeline_check = QCheckBox("⏰ Timeline Analysis")
        self.timeline_check.setChecked(True)
        options_layout.addWidget(self.timeline_check)

        self.consistency_check = QCheckBox("🔍 Consistency Analysis")
        self.consistency_check.setChecked(True)
        options_layout.addWidget(self.consistency_check)

        self.style_check = QCheckBox("✍️ Writing Style Analysis")
        self.style_check.setChecked(True)
        options_layout.addWidget(self.style_check)

        self.reader_check = QCheckBox("👁️ Reader Simulation")
        self.reader_check.setChecked(False)
        options_layout.addWidget(self.reader_check)

        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Progress
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()

        self.progress_label = QLabel("Ready to start")
        self.progress_label.setStyleSheet("font-size: 10pt; color: #495057;")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #dee2e6;
                border-radius: 5px;
                text-align: center;
                height: 25px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)

        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        # Log
        log_group = QGroupBox("Analysis Log")
        log_layout = QVBoxLayout()

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                font-family: 'Courier New', monospace;
                font-size: 9pt;
            }
        """)
        log_layout.addWidget(self.log_text)

        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        # Buttons
        button_layout = QHBoxLayout()

        self.start_btn = QPushButton("▶ Start Analysis")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover { background: #218838; }
            QPushButton:disabled { background: #adb5bd; }
        """)
        self.start_btn.clicked.connect(self.start_analysis)
        button_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background: #dc3545;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background: #c82333; }
        """)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_analysis)
        button_layout.addWidget(self.stop_btn)

        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
            }
            QPushButton:hover { background: #5a6268; }
        """)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def load_chapters(self):
        """Load all chapters from project"""
        from models.project import ItemType
        chapters = self.db_manager.load_items(self.project_id, ItemType.CHAPTER)

        self.chapters = [{'id': ch.id, 'name': ch.name} for ch in chapters]

        self.info_label.setText(f"Found {len(self.chapters)} chapters to analyze")
        self.log_text.append(f"📚 Loaded {len(self.chapters)} chapters")

    def start_analysis(self):
        """Start batch analysis"""
        if not self.chapters:
            self.log_text.append("❌ No chapters found")
            return

        # Check at least one analysis type selected
        if not any([
            self.timeline_check.isChecked(),
            self.consistency_check.isChecked(),
            self.style_check.isChecked(),
            self.reader_check.isChecked()
        ]):
            self.log_text.append("❌ Please select at least one analysis type")
            return

        # Disable controls
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.timeline_check.setEnabled(False)
        self.consistency_check.setEnabled(False)
        self.style_check.setEnabled(False)
        self.reader_check.setEnabled(False)

        # Clear log
        self.log_text.clear()
        self.log_text.append("🚀 Starting batch analysis...")
        self.log_text.append(f"📊 Chapters: {len(self.chapters)}")

        types = []
        if self.timeline_check.isChecked():
            types.append("Timeline")
        if self.consistency_check.isChecked():
            types.append("Consistency")
        if self.style_check.isChecked():
            types.append("Style")
        if self.reader_check.isChecked():
            types.append("Reader")

        self.log_text.append(f"📋 Types: {', '.join(types)}")
        self.log_text.append("")

        # Start worker
        self.worker = BatchAnalysisWorker(
            self.insight_service,
            self.project_id,
            self.chapters,
            self.timeline_check.isChecked(),
            self.consistency_check.isChecked(),
            self.style_check.isChecked(),
            self.reader_check.isChecked()
        )

        self.worker.progress.connect(self.on_progress)
        self.worker.chapter_complete.connect(self.on_chapter_complete)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)

        self.worker.start()

    def stop_analysis(self):
        """Stop the analysis"""
        if self.worker:
            self.log_text.append("\n⏹ Stopping analysis...")
            self.worker.stop()
            self.stop_btn.setEnabled(False)

    def on_progress(self, current: int, total: int, message: str):
        """Update progress"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"{message} ({current}/{total})")

    def on_chapter_complete(self, chapter_name: str, success: bool, message: str):
        """Chapter analysis complete"""
        self.log_text.append(f"{message} {chapter_name}")

    def on_finished(self, stats: Dict[str, Any]):
        """All analyses complete"""
        self.progress_label.setText("Complete!")
        self.progress_bar.setValue(self.progress_bar.maximum())

        self.log_text.append("")
        self.log_text.append("=" * 50)
        self.log_text.append("✅ Batch Analysis Complete!")
        self.log_text.append(f"   Total: {stats['total']}")
        self.log_text.append(f"   ✓ Completed: {stats['completed']}")
        self.log_text.append(f"   ✗ Failed: {stats['failed']}")

        # Re-enable controls
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.timeline_check.setEnabled(True)
        self.consistency_check.setEnabled(True)
        self.style_check.setEnabled(True)
        self.reader_check.setEnabled(True)

    def on_error(self, error: str):
        """Error occurred"""
        self.log_text.append(f"\n❌ ERROR: {error}")
        self.progress_label.setText("Error occurred")

        # Re-enable controls
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.timeline_check.setEnabled(True)
        self.consistency_check.setEnabled(True)
        self.style_check.setEnabled(True)
        self.reader_check.setEnabled(True)