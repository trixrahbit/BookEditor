"""
AI Fix Chapter - Automatically fix timeline and consistency issues in a chapter
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QProgressBar, QListWidget, QListWidgetItem, QCheckBox,
    QGroupBox, QMessageBox, QTabWidget, QSplitter
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QTextCursor
from theme_manager import theme_manager
from typing import List, Dict, Any, Optional
import time
import difflib


def get_highlighted_diffs(old_text: str, new_text: str):
    """
    Returns (highlighted_old_html, highlighted_new_html)
    """
    # Character-based diffing for finer highlights
    s = difflib.SequenceMatcher(None, old_text, new_text)
    
    old_html = ""
    new_html = ""
    
    for tag, i1, i2, j1, j2 in s.get_opcodes():
        if tag == 'equal':
            chunk = old_text[i1:i2].replace('\n', '<br>')
            old_html += chunk
            new_html += chunk
        elif tag == 'delete':
            chunk = old_text[i1:i2].replace('\n', '<br>')
            old_html += f'<span style="background-color: #442222; color: #ff8888; text-decoration: line-through;">{chunk}</span>'
        elif tag == 'insert':
            chunk = new_text[j1:j2].replace('\n', '<br>')
            new_html += f'<span style="background-color: #224422; color: #88ff88;">{chunk}</span>'
        elif tag == 'replace':
            chunk_old = old_text[i1:i2].replace('\n', '<br>')
            chunk_new = new_text[j1:j2].replace('\n', '<br>')
            old_html += f'<span style="background-color: #442222; color: #ff8888; text-decoration: line-through;">{chunk_old}</span>'
            new_html += f'<span style="background-color: #224422; color: #88ff88;">{chunk_new}</span>'
            
    return old_html, new_html

from utils.memory_utils import cleanup_memory, log_memory, check_high_memory, TextSizeValidator
from utils.rate_limiter import RateLimiter
from utils.worker_utils import WorkerManager


class SceneFixWorker(QThread):
    """Worker thread for fixing a single scene"""

    finished = pyqtSignal(str, str)  # original_text, fixed_text
    error = pyqtSignal(str)

    def __init__(self, ai_manager, scene_name: str, scene_text: str, issues: List[Dict[str, Any]]):
        super().__init__()
        self.ai_manager = ai_manager
        self.scene_name = scene_name
        self.scene_text = scene_text
        self.issues = issues

    def run(self):
        try:
            # Build fix prompt
            prompt = self._build_fix_prompt()

            # Call AI
            fixed_text = self.ai_manager.call_api(
                messages=[{"role": "user", "content": prompt}],
                system_message="You are a professional fiction editor fixing continuity and timeline issues. Maintain the author's voice and style while correcting errors.",
                temperature=0.3,
                max_tokens=8000
            )

            self.finished.emit(self.scene_text, fixed_text.strip())

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))

    def _build_fix_prompt(self) -> str:
        """Build fix prompt for this scene"""
        # Group issues by severity
        critical = [i for i in self.issues if i.get('severity') == 'Critical']
        major = [i for i in self.issues if i.get('severity') == 'Major']
        minor = [i for i in self.issues if i.get('severity') == 'Minor']

        issues_text = []

        if critical:
            issues_text.append("**CRITICAL ISSUES (must fix):**")
            for i, issue in enumerate(critical, 1):
                issues_text.append(f"{i}. {issue.get('issue', 'Unknown issue')}")
                if issue.get('detail'):
                    issues_text.append(f"   Detail: {issue['detail']}")

        if major:
            issues_text.append("\n**MAJOR ISSUES (must fix):**")
            for i, issue in enumerate(major, 1):
                issues_text.append(f"{i}. {issue.get('issue', 'Unknown issue')}")
                if issue.get('detail'):
                    issues_text.append(f"   Detail: {issue['detail']}")

        if minor:
            issues_text.append("\n**MINOR ISSUES (should fix):**")
            for i, issue in enumerate(minor, 1):
                issues_text.append(f"{i}. {issue.get('issue', 'Unknown issue')}")
                if issue.get('detail'):
                    issues_text.append(f"   Detail: {issue['detail']}")

        issues_section = "\n".join(issues_text)

        prompt = f"""Fix the following issues in this scene while maintaining the author's voice and style.

SCENE: {self.scene_name}

ISSUES TO FIX:
{issues_section}

ORIGINAL TEXT:
{self.scene_text}

INSTRUCTIONS:
1. Fix ALL critical and major issues completely
2. Fix minor issues where possible
3. Maintain the author's writing style and voice
4. Keep all plot points and character actions
5. Preserve dialogue intent and character voice
6. Make MINIMAL changes - only fix what's broken
7. If fixing requires adding/removing content, do so naturally
8. Ensure timeline consistency
9. Fix any character behavior inconsistencies
10. Resolve any continuity errors

Return ONLY the corrected scene text with NO explanations, preamble, or commentary."""

        return prompt

class SceneReviewDialog(QDialog):
    """Dialog for reviewing a single scene fix"""

    def __init__(self, parent, scene_name: str, original_text: str, fixed_text: str, issues: List[Dict[str, Any]]):
        super().__init__(parent)
        self.scene_name = scene_name
        self.original_text = original_text
        self.fixed_text = fixed_text
        self.issues = issues
        self.approved = False

        self.setWindowTitle(f"Review Fix: {scene_name}")
        self.setMinimumSize(1200, 800)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Header
        header = QLabel(f"📝 Review Fix: {self.scene_name}")
        header.setStyleSheet("""
            font-size: 14pt;
            font-weight: bold;
            padding: 12px;
            background: #667eea;
            color: white;
            border-radius: 6px;
        """)
        layout.addWidget(header)

        # Issues summary
        issues_summary = QLabel(f"Fixing {len(self.issues)} issues")
        issues_summary.setStyleSheet("color: #6c757d; padding: 10px; font-size: 10pt;")
        layout.addWidget(issues_summary)

        # Issues list (compact)
        issues_text = []
        for issue in self.issues:
            severity = issue.get('severity', 'Minor')
            issue_txt = issue.get('issue', 'Unknown')
            if severity == 'Critical':
                issues_text.append(f"🔴 {issue_txt}")
            elif severity == 'Major':
                issues_text.append(f"🟠 {issue_txt}")
            else:
                issues_text.append(f"🟡 {issue_txt}")

        issues_label = QLabel("\n".join(issues_text[:5]))  # Show first 5
        if len(self.issues) > 5:
            issues_label.setText(issues_label.text() + f"\n... and {len(self.issues) - 5} more")
        issues_label.setStyleSheet("color: #495057; padding: 10px; font-size: 9pt;")
        layout.addWidget(issues_label)

        # Tabs for original vs fixed
        tabs = QTabWidget()
        
        orig_highlighted, fixed_highlighted = get_highlighted_diffs(self.original_text, self.fixed_text)

        # Original text
        original_widget = QTextEdit()
        original_widget.setReadOnly(True)
        original_widget.setHtml(f"<div style='white-space: pre-wrap;'>{orig_highlighted}</div>")
        original_widget.setStyleSheet("""
            QTextEdit {
                background: #1E1E1E;
                color: #A0A0A0;
                font-family: 'Georgia', serif;
                font-size: 11pt;
                line-height: 1.6;
                padding: 15px;
            }
        """)
        tabs.addTab(original_widget, "📄 Original")

        # Fixed text
        fixed_widget = QTextEdit()
        fixed_widget.setReadOnly(True)
        fixed_widget.setHtml(f"<div style='white-space: pre-wrap;'>{fixed_highlighted}</div>")
        fixed_widget.setStyleSheet("""
            QTextEdit {
                background: #1A1A1A;
                color: #E0E0E0;
                font-family: 'Georgia', serif;
                font-size: 11pt;
                line-height: 1.6;
                padding: 15px;
            }
        """)
        tabs.addTab(fixed_widget, "✨ AI Fixed")

        # Side-by-side splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        original_side = QTextEdit()
        original_side.setReadOnly(True)
        original_side.setHtml(f"<div style='white-space: pre-wrap;'>{orig_highlighted}</div>")
        original_side.setStyleSheet("""
            QTextEdit {
                background: #1E1E1E;
                color: #A0A0A0;
                font-family: 'Georgia', serif;
                font-size: 10pt;
                padding: 10px;
            }
        """)

        fixed_side = QTextEdit()
        fixed_side.setReadOnly(True)
        fixed_side.setHtml(f"<div style='white-space: pre-wrap;'>{fixed_highlighted}</div>")
        fixed_side.setStyleSheet("""
            QTextEdit {
                background: #1A1A1A;
                color: #E0E0E0;
                font-family: 'Georgia', serif;
                font-size: 10pt;
                padding: 10px;
            }
        """)

        # Synchronize scrolling for side-by-side
        original_side.verticalScrollBar().valueChanged.connect(
            fixed_side.verticalScrollBar().setValue
        )
        fixed_side.verticalScrollBar().valueChanged.connect(
            original_side.verticalScrollBar().setValue
        )

        splitter.addWidget(original_side)
        splitter.addWidget(fixed_side)
        splitter.setSizes([600, 600])

        tabs.addTab(splitter, "📊 Side-by-Side")
        tabs.setCurrentIndex(2) # Default to side-by-side

        layout.addWidget(tabs)

        # Stats
        original_words = len(self.original_text.split())
        fixed_words = len(self.fixed_text.split())
        diff = fixed_words - original_words

        stats_text = f"Original: {original_words:,} words  |  Fixed: {fixed_words:,} words  |  Change: {diff:+,} words"
        stats_label = QLabel(stats_text)
        stats_label.setStyleSheet("color: #6c757d; padding: 5px; font-size: 9pt;")
        layout.addWidget(stats_label)

        # Buttons
        button_layout = QHBoxLayout()

        deny_btn = QPushButton("❌ Deny - Keep Original")
        deny_btn.setStyleSheet("""
            QPushButton {
                background: #dc3545;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover { background: #c82333; }
        """)
        deny_btn.clicked.connect(self.reject)
        button_layout.addWidget(deny_btn)

        button_layout.addStretch()

        approve_btn = QPushButton("✅ Approve - Apply Fix")
        approve_btn.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover { background: #218838; }
        """)
        approve_btn.clicked.connect(self.approve)
        button_layout.addWidget(approve_btn)

        layout.addLayout(button_layout)

    def approve(self):
        """Approve the fix"""
        self.approved = True
        self.accept()

    def is_approved(self) -> bool:
        """Check if fix was approved"""
        return self.approved

class ChapterFixWorker(QThread):
    """Worker thread for fixing chapter issues with AI"""

    progress = pyqtSignal(str)  # status message
    scene_fixed = pyqtSignal(str, str)  # scene_name, fixed_html
    finished = pyqtSignal(dict)  # summary stats
    error = pyqtSignal(str)

    def __init__(self, ai_manager, db_manager, project_id: str, chapter_id: str,
                 insight_service, issues_to_fix: List[Dict[str, Any]]):
        super().__init__()
        self.ai_manager = ai_manager
        self.db_manager = db_manager
        self.project_id = project_id
        self.chapter_id = chapter_id
        self.insight_service = insight_service
        self.issues_to_fix = issues_to_fix
        self.should_stop = False

    def run(self):
        try:
            from models.project import ItemType
            from text_utils import html_to_plaintext, plaintext_to_html

            stats = {
                'scenes_fixed': 0,
                'issues_addressed': len(self.issues_to_fix),
                'failed': 0
            }

            # Group issues by scene
            issues_by_scene = {}
            for issue in self.issues_to_fix:
                scene_id = issue.get('scene_id')
                scene_name = issue.get('location', 'Unknown Scene')

                if scene_id not in issues_by_scene:
                    issues_by_scene[scene_id] = {
                        'scene_name': scene_name,
                        'scene_id': scene_id,
                        'issues': []
                    }
                issues_by_scene[scene_id]['issues'].append(issue)

            self.progress.emit(f"Found issues in {len(issues_by_scene)} scenes")

            # Fix each scene
            for scene_data in issues_by_scene.values():
                if self.should_stop:
                    break

                scene_id = scene_data['scene_id']
                scene_name = scene_data['scene_name']
                issues = scene_data['issues']

                if not scene_id:
                    continue

                self.progress.emit(f"Fixing {scene_name}...")

                try:
                    # Load scene
                    scene = self.db_manager.load_item(scene_id)
                    if not scene:
                        stats['failed'] += 1
                        continue

                    # Get scene content
                    scene_html = scene.content or ""
                    scene_text = html_to_plaintext(scene_html)

                    if not scene_text.strip():
                        continue

                    # Build fix prompt
                    prompt = self._build_fix_prompt(scene_name, scene_text, issues)

                    # Call AI
                    self.progress.emit(f"AI processing {scene_name}...")

                    fixed_text = self.ai_manager.call_api(
                        messages=[{"role": "user", "content": prompt}],
                        system_message="You are a professional fiction editor fixing continuity and timeline issues. Maintain the author's voice and style while correcting errors.",
                        temperature=0.3,  # Lower for accuracy
                        max_tokens=8000
                    )

                    # Convert back to HTML
                    fixed_html = plaintext_to_html(fixed_text.strip())

                    # Save fixed scene
                    scene.content = fixed_html
                    self.db_manager.save_item(self.project_id, scene)

                    stats['scenes_fixed'] += 1
                    self.scene_fixed.emit(scene_name, fixed_html)
                    self.progress.emit(f"✓ Fixed {scene_name}")

                    # Small delay between scenes
                    time.sleep(0.5)

                except Exception as e:
                    stats['failed'] += 1
                    self.progress.emit(f"✗ Error fixing {scene_name}: {str(e)[:50]}")

            self.finished.emit(stats)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))

    def _build_fix_prompt(self, scene_name: str, scene_text: str, issues: List[Dict[str, Any]]) -> str:
        """Build comprehensive fix prompt"""

        # Group issues by severity
        critical = [i for i in issues if i.get('severity') == 'Critical']
        major = [i for i in issues if i.get('severity') == 'Major']
        minor = [i for i in issues if i.get('severity') == 'Minor']

        issues_text = []

        if critical:
            issues_text.append("**CRITICAL ISSUES (must fix):**")
            for i, issue in enumerate(critical, 1):
                issues_text.append(f"{i}. {issue.get('issue', 'Unknown issue')}")
                if issue.get('detail'):
                    issues_text.append(f"   Detail: {issue['detail']}")

        if major:
            issues_text.append("\n**MAJOR ISSUES (must fix):**")
            for i, issue in enumerate(major, 1):
                issues_text.append(f"{i}. {issue.get('issue', 'Unknown issue')}")
                if issue.get('detail'):
                    issues_text.append(f"   Detail: {issue['detail']}")

        if minor:
            issues_text.append("\n**MINOR ISSUES (should fix):**")
            for i, issue in enumerate(minor, 1):
                issues_text.append(f"{i}. {issue.get('issue', 'Unknown issue')}")
                if issue.get('detail'):
                    issues_text.append(f"   Detail: {issue['detail']}")

        issues_section = "\n".join(issues_text)

        prompt = f"""Fix the following issues in this scene while maintaining the author's voice and style.

SCENE: {scene_name}

ISSUES TO FIX:
{issues_section}

ORIGINAL TEXT:
{scene_text}

INSTRUCTIONS:
1. Fix ALL critical and major issues completely
2. Fix minor issues where possible
3. Maintain the author's writing style and voice
4. Keep all plot points and character actions
5. Preserve dialogue intent and character voice
6. Make MINIMAL changes - only fix what's broken
7. If fixing requires adding/removing content, do so naturally
8. Ensure timeline consistency
9. Fix any character behavior inconsistencies
10. Resolve any continuity errors

Return ONLY the corrected scene text with NO explanations, preamble, or commentary."""

        return prompt

    def stop(self):
        """Request worker to stop"""
        self.should_stop = True


class AIFixChapterDialog(QDialog):
    """Dialog for fixing chapter issues with AI - WITH APPROVE/DENY + UTILS"""

    def __init__(self, parent, ai_manager, db_manager, project_id: str, chapter_id: str,
                 chapter_name: str, insight_service):
        super().__init__(parent)
        self.ai_manager = ai_manager
        self.db_manager = db_manager
        self.project_id = project_id
        self.chapter_id = chapter_id
        self.chapter_name = chapter_name
        self.insight_service = insight_service
        self.worker = None

        # Initialize utils
        self.worker_manager = WorkerManager()
        self.rate_limiter = RateLimiter(
            requests_per_minute=15,
            min_delay_seconds=2.0
        )

        # Track fixes
        self.pending_fixes = []  # List of {scene, issues}
        self.current_fix_index = 0

        self.setWindowTitle(f"AI Fix: {chapter_name}")
        self.setMinimumSize(800, 600)
        self.init_ui()
        self.load_issues()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Header
        self.header = QLabel(f"🪄 AI Smart Fix: {self.chapter_name}")
        self.header.setObjectName("dialogHeader")
        layout.addWidget(self.header)

        # Info
        self.info_label = QLabel("AI will fix timeline and consistency issues found in analysis")
        self.info_label.setObjectName("infoLabel")
        layout.addWidget(self.info_label)

        # Issues list
        issues_group = QGroupBox("Issues to Fix")
        issues_layout = QVBoxLayout()

        self.issues_list = QListWidget()
        issues_layout.addWidget(self.issues_list)

        # Severity filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Include:"))

        self.critical_check = QCheckBox("Critical")
        self.critical_check.setChecked(True)
        self.critical_check.setObjectName("criticalCheck")
        self.critical_check.stateChanged.connect(self.update_issues_list)
        filter_layout.addWidget(self.critical_check)

        self.major_check = QCheckBox("Major")
        self.major_check.setChecked(True)
        self.major_check.setObjectName("majorCheck")
        self.major_check.stateChanged.connect(self.update_issues_list)
        filter_layout.addWidget(self.major_check)

        self.minor_check = QCheckBox("Minor")
        self.minor_check.setChecked(False)
        self.minor_check.setObjectName("minorCheck")
        self.minor_check.stateChanged.connect(self.update_issues_list)
        filter_layout.addWidget(self.minor_check)

        filter_layout.addStretch()
        issues_layout.addLayout(filter_layout)

        issues_group.setLayout(issues_layout)
        layout.addWidget(issues_group)

        # Progress
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()

        self.status_label = QLabel("Ready to start")
        self.status_label.setObjectName("statusLabel")
        progress_layout.addWidget(self.status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)

        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        # Buttons
        button_layout = QHBoxLayout()

        self.fix_btn = QPushButton("🔧 Start Review Process")
        self.fix_btn.setObjectName("primaryButton")
        self.fix_btn.clicked.connect(self.start_fixing)
        button_layout.addWidget(self.fix_btn)

        button_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)
        self.apply_modern_style()

    def apply_modern_style(self):
        """Apply modern styling"""
        self.setStyleSheet(theme_manager.get_dialog_stylesheet())
        self.header.setObjectName("settingsHeader")

    def load_issues(self):
        """Load timeline and consistency issues for chapter"""
        self.all_issues = []

        try:
            if not self.insight_service or not hasattr(self.insight_service, 'insight_db'):
                QMessageBox.warning(self, "Error", "Insight service not initialized")
                self.fix_btn.setEnabled(False)
                return

            db = self.insight_service.insight_db

            # Load timeline issues
            timeline_record = db.get_latest(self.project_id, 'chapter', self.chapter_id, 'timeline')
            if timeline_record:
                for issue in timeline_record.payload.get('issues', []):
                    issue['type'] = 'timeline'
                    self.all_issues.append(issue)

            # Load consistency issues
            consistency_record = db.get_latest(self.project_id, 'chapter', self.chapter_id, 'consistency')
            if consistency_record:
                for issue in consistency_record.payload.get('issues', []):
                    issue['type'] = 'consistency'
                    self.all_issues.append(issue)

            self.update_issues_list()

            if not self.all_issues:
                self.fix_btn.setEnabled(False)
                QMessageBox.information(
                    self,
                    "No Issues Found",
                    f"No timeline or consistency issues found.\n\n"
                    "Run 'AI Analyze Chapter' first."
                )

        except Exception as e:
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, "Error", f"Failed to load issues:\n\n{e}")
            self.fix_btn.setEnabled(False)

    def update_issues_list(self):
        """Update issues list based on filters"""
        try:
            self.issues_list.clear()

            severities = []
            if self.critical_check.isChecked():
                severities.append('Critical')
            if self.major_check.isChecked():
                severities.append('Major')
            if self.minor_check.isChecked():
                severities.append('Minor')

            count = 0
            for issue in self.all_issues:
                if issue.get('severity') not in severities:
                    continue

                severity = issue.get('severity', 'Minor')
                issue_type = issue.get('type', 'unknown')
                location = issue.get('location', 'Unknown')
                issue_text = issue.get('issue', 'No description')

                icon = "🔴" if severity == 'Critical' else "🟠" if severity == 'Major' else "🟡"
                item_text = f"{icon} [{severity}] {issue_type.title()}: {issue_text}\n    Scene: {location}"

                self.issues_list.addItem(QListWidgetItem(item_text))
                count += 1

            self.fix_btn.setText(f"🔧 Start Review Process ({count} issues)")
            self.fix_btn.setEnabled(count > 0)

        except Exception as e:
            import traceback
            traceback.print_exc()

    def start_fixing(self):
        """Start the review and fix process"""
        # Log starting memory
        log_memory("[AIFix] Starting:")

        # Get filtered issues
        severities = []
        if self.critical_check.isChecked():
            severities.append('Critical')
        if self.major_check.isChecked():
            severities.append('Major')
        if self.minor_check.isChecked():
            severities.append('Minor')

        issues_to_fix = [i for i in self.all_issues if i.get('severity') in severities]

        if not issues_to_fix:
            QMessageBox.warning(self, "No Issues", "No issues selected to fix")
            return

        # Group by scene
        issues_by_scene = {}
        for issue in issues_to_fix:
            scene_id = issue.get('scene_id')
            scene_name = issue.get('location', 'Unknown Scene')

            if scene_id not in issues_by_scene:
                issues_by_scene[scene_id] = {
                    'scene_id': scene_id,
                    'scene_name': scene_name,
                    'issues': []
                }
            issues_by_scene[scene_id]['issues'].append(issue)

        self.pending_fixes = list(issues_by_scene.values())
        self.current_fix_index = 0

        QMessageBox.information(
            self,
            "Review Process",
            f"Will process {len(self.pending_fixes)} scenes.\n\n"
            f"For each scene:\n"
            f"1. AI will generate a fix\n"
            f"2. You'll review original vs fixed\n"
            f"3. Approve or deny the changes\n\n"
            f"Scenes are processed ONE AT A TIME with 2-second delays\n"
            f"to prevent memory/API overload.\n\n"
            f"Ready to begin?"
        )

        # Start processing first scene
        self.process_next_scene()

    def process_next_scene(self):
        """Process the next scene in the queue"""
        if self.current_fix_index >= len(self.pending_fixes):
            # All done!
            print("[AIFix] All scenes processed")

            # Cleanup worker
            if self.worker:
                self.worker_manager.cleanup_worker(self.worker)
                self.worker = None

            # Final cleanup
            cleanup_memory()
            log_memory("[AIFix] Final:")

            # Reload issues to show what's left
            self.load_issues()

            QMessageBox.information(
                self,
                "Complete",
                "All scenes have been reviewed!\n\n"
                "The issue list has been updated.\n"
                "Remaining issues (if any) are shown above.\n\n"
                "You can:\n"
                "• Run 'AI Analyze Chapter' to find new issues\n"
                "• Fix remaining issues if any\n"
                "• Close this dialog"
            )
            return

        scene_data = self.pending_fixes[self.current_fix_index]
        scene_id = scene_data['scene_id']
        scene_name = scene_data['scene_name']
        issues = scene_data['issues']

        if not scene_id:
            print("[AIFix] No scene_id, skipping")
            self.current_fix_index += 1
            QTimer.singleShot(100, self.process_next_scene)
            return

        print(f"[AIFix] Processing scene {self.current_fix_index + 1}/{len(self.pending_fixes)}: {scene_name}")

        self.status_label.setText(
            f"Processing scene {self.current_fix_index + 1}/{len(self.pending_fixes)}: {scene_name}"
        )
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate

        # Load scene
        from text_utils import html_to_plaintext

        scene = self.db_manager.load_item(scene_id)
        if not scene:
            print("[AIFix] Could not load scene, skipping")
            self.current_fix_index += 1
            QTimer.singleShot(100, self.process_next_scene)
            return

        scene_text = html_to_plaintext(scene.content or "")

        if not scene_text.strip():
            print("[AIFix] Scene is empty, skipping")
            self.current_fix_index += 1
            QTimer.singleShot(100, self.process_next_scene)
            return

        # Check text size
        size_category = TextSizeValidator.get_size_category(scene_text)
        print(f"[AIFix] Scene size: {size_category} ({len(scene_text)} chars)")

        if size_category in ['xlarge', 'huge']:
            QMessageBox.warning(
                self,
                "Large Scene",
                f"Scene '{scene_name}' is {size_category} ({len(scene_text):,} characters).\n\n"
                f"This might cause memory issues.\n\n"
                f"Consider breaking it into smaller scenes first."
            )
            # Ask if they want to skip
            reply = QMessageBox.question(
                self,
                "Skip Large Scene?",
                f"Skip this scene and continue with others?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply == QMessageBox.StandardButton.Yes:
                self.current_fix_index += 1
                QTimer.singleShot(100, self.process_next_scene)
                return

        # Truncate if needed (safety)
        scene_text, was_truncated = TextSizeValidator.truncate_safe(scene_text, 50000)
        if was_truncated:
            print(f"[AIFix] WARNING: Scene truncated to 50000 chars")

        # Rate limiting - wait if needed
        print("[AIFix] Checking rate limit...")
        self.rate_limiter.wait_if_needed()

        # Cleanup previous worker if exists
        if self.worker:
            print("[AIFix] Cleaning up previous worker")
            self.worker_manager.cleanup_worker(self.worker)
            self.worker = None
            cleanup_memory()

        # Start AI worker
        print(f"[AIFix] Creating worker for: {scene_name}")
        from ai_fix_chapter_dialog import SceneFixWorker  # Import here to avoid circular

        self.worker = SceneFixWorker(self.ai_manager, scene_name, scene_text, issues)
        self.worker_manager.create_worker(self.worker)
        self.worker.finished.connect(lambda orig, fixed: self.on_fix_ready(scene, orig, fixed, issues))
        self.worker.error.connect(self.on_fix_error)
        self.worker.start()

        # Record request
        self.rate_limiter.record_request()
        print("[AIFix] Worker started, request recorded")

    def on_fix_ready(self, scene, original_text: str, fixed_text: str, issues: List[Dict[str, Any]]):
        """AI fix is ready - show review dialog"""
        try:
            print(f"[AIFix] Fix ready for: {scene.name}")
            log_memory(f"[AIFix] Before review dialog ({scene.name}):")

            self.progress_bar.setVisible(False)

            # Show review dialog
            from ai_fix_chapter_dialog import SceneReviewDialog  # Import here to avoid circular
            review_dialog = SceneReviewDialog(self, scene.name, original_text, fixed_text, issues)
            result = review_dialog.exec()

            if result and review_dialog.is_approved():
                print(f"[AIFix] User approved fix for: {scene.name}")

                # Save the fix
                from text_utils import plaintext_to_html
                scene.content = plaintext_to_html(fixed_text)
                self.db_manager.save_item(self.project_id, scene)
                print(f"[AIFix] Scene saved: {scene.name}")

                # Remove fixed issues
                try:
                    self.remove_fixed_issues(issues)
                    print(f"[AIFix] Issues removed for: {scene.name}")
                except Exception as e:
                    print(f"[AIFix] Error removing issues: {e}")
                    import traceback
                    traceback.print_exc()

                self.status_label.setText(f"✅ Applied fix to: {scene.name}")
            else:
                print(f"[AIFix] User denied fix for: {scene.name}")
                self.status_label.setText(f"❌ Kept original: {scene.name}")

            # Clean up dialog
            review_dialog.deleteLater()
            del review_dialog
            del original_text
            del fixed_text

            # Memory cleanup
            cleanup_memory()
            log_memory(f"[AIFix] After {scene.name}:")

            # Check if memory is high
            if check_high_memory(threshold_mb=500):
                print("[AIFix] High memory detected - cleaned up")

            # Move to next scene with longer delay
            self.current_fix_index += 1

            # 2 second delay between scenes
            QTimer.singleShot(2000, self.process_next_scene)

        except Exception as e:
            print(f"[AIFix] FATAL ERROR in on_fix_ready: {e}")
            import traceback
            traceback.print_exc()

            # Always cleanup on error
            cleanup_memory()

            QMessageBox.critical(
                self,
                "Fatal Error",
                f"Error processing scene:\n\n{e}\n\n"
                f"Skipping to next scene..."
            )

            # Skip this scene
            self.current_fix_index += 1
            QTimer.singleShot(2000, self.process_next_scene)

    def on_fix_error(self, error: str):
        """Error generating fix"""
        print(f"[AIFix] Worker error: {error}")

        self.progress_bar.setVisible(False)

        # Clean up worker
        if self.worker:
            self.worker_manager.cleanup_worker(self.worker)
            self.worker = None

        cleanup_memory()

        QMessageBox.warning(
            self,
            "Fix Error",
            f"Failed to generate fix:\n\n{error}\n\nSkipping this scene."
        )

        # Skip this scene
        self.current_fix_index += 1
        QTimer.singleShot(2000, self.process_next_scene)

    def remove_fixed_issues(self, fixed_issues: List[Dict[str, Any]]):
        """
        Remove fixed issues from insights database
        Uses multiple criteria for matching to ensure accuracy
        """
        try:
            db = self.insight_service.insight_db
            total_removed = 0

            # Process timeline issues
            timeline_record = db.get_latest(self.project_id, 'chapter', self.chapter_id, 'timeline')
            if timeline_record:
                original_count = len(timeline_record.payload.get('issues', []))
                remaining = self._filter_fixed_issues(
                    timeline_record.payload.get('issues', []),
                    fixed_issues,
                    'timeline'
                )

                if len(remaining) < original_count:
                    timeline_record.payload['issues'] = remaining
                    self._save_updated_record(db, timeline_record, self.project_id, self.chapter_id, 'timeline')
                    removed = original_count - len(remaining)
                    total_removed += removed
                    print(f"[AIFix] Removed {removed} timeline issues")

            # Process consistency issues
            consistency_record = db.get_latest(self.project_id, 'chapter', self.chapter_id, 'consistency')
            if consistency_record:
                original_count = len(consistency_record.payload.get('issues', []))
                remaining = self._filter_fixed_issues(
                    consistency_record.payload.get('issues', []),
                    fixed_issues,
                    'consistency'
                )

                if len(remaining) < original_count:
                    consistency_record.payload['issues'] = remaining
                    self._save_updated_record(db, consistency_record, self.project_id, self.chapter_id, 'consistency')
                    removed = original_count - len(remaining)
                    total_removed += removed
                    print(f"[AIFix] Removed {removed} consistency issues")

            if total_removed > 0:
                print(f"[AIFix] Total issues removed: {total_removed}")
                self.info_label.setText(f"✅ Removed {total_removed} fixed issues from insights")

        except Exception as e:
            print(f"[AIFix] Error removing fixed issues: {e}")
            import traceback
            traceback.print_exc()

    def _filter_fixed_issues(self, all_issues: List[Dict], fixed_issues: List[Dict], issue_type: str) -> List[Dict]:
        """
        Filter out fixed issues from the full list
        Returns only the issues that were NOT fixed
        """
        remaining = []

        for issue in all_issues:
            is_fixed = False

            for fixed in fixed_issues:
                # Must match type
                if fixed.get('type') != issue_type:
                    continue

                # Match on multiple criteria for accuracy
                matches = 0

                # Check issue text
                if fixed.get('issue') == issue.get('issue'):
                    matches += 1

                # Check location (scene name)
                if fixed.get('location') == issue.get('location'):
                    matches += 1

                # Check severity
                if fixed.get('severity') == issue.get('severity'):
                    matches += 1

                # Check detail if available
                if fixed.get('detail') and issue.get('detail'):
                    if fixed.get('detail') == issue.get('detail'):
                        matches += 1

                # If at least 2 criteria match, consider it the same issue
                if matches >= 2:
                    is_fixed = True
                    break

            if not is_fixed:
                remaining.append(issue)

        return remaining

    def _save_updated_record(self, db, record, project_id: str, chapter_id: str, insight_type: str):
        """Save updated insight record with new hash"""
        import hashlib
        import json

        # Create deterministic hash of the payload
        payload_str = json.dumps(record.payload, sort_keys=True)
        new_hash = hashlib.sha256(payload_str.encode()).hexdigest()

        db.upsert(
            record.id,
            project_id,
            'chapter',
            chapter_id,
            insight_type,
            record.payload,
            new_hash
        )

    def closeEvent(self, event):
        """Clean up when dialog is closed"""
        print("\n[AIFix] Dialog closing, cleaning up...")

        # Stop and clean up worker
        if self.worker:
            self.worker_manager.cleanup_worker(self.worker)
            self.worker = None

        # Cleanup all workers
        self.worker_manager.cleanup_all()
        self.worker_manager.print_stats()

        # Print rate limit stats
        self.rate_limiter.print_stats()

        # Clean up large data structures
        self.all_issues = []
        self.pending_fixes = []

        # Final memory cleanup
        cleanup_memory()
        log_memory("[AIFix] After cleanup:")

        print("[AIFix] Cleanup complete")
        event.accept()


































