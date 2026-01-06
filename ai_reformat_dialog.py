"""
AI Reformat Dialog - Reformat all scenes with AI without changing words.
"""

from typing import Dict, List
import re

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTextEdit, QGroupBox, QMessageBox
)

from models.project import ItemType
from text_utils import html_to_plaintext, plaintext_to_html, sanitize_ai_output


class SceneReformatWorker(QThread):
    """Worker thread for reformatting scenes with AI"""

    progress = pyqtSignal(int, int, str)
    scene_complete = pyqtSignal(str, bool, str)
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, ai_manager, db_manager, project_id: str, scenes: List[Dict[str, str]]):
        super().__init__()
        self.ai_manager = ai_manager
        self.db_manager = db_manager
        self.project_id = project_id
        self.scenes = scenes
        self.should_stop = False

    def stop(self):
        """Request worker to stop"""
        self.should_stop = True

    def run(self):
        try:
            stats = {
                "total": len(self.scenes),
                "updated": 0,
                "skipped": 0,
                "failed": 0,
                "mismatched": 0,
            }

            for i, scene_info in enumerate(self.scenes):
                if self.should_stop:
                    self.progress.emit(i, len(self.scenes), "Cancelled by user")
                    break

                scene_id = scene_info["id"]
                scene_name = scene_info["name"]
                chapter_name = scene_info["chapter"]

                self.progress.emit(
                    i + 1,
                    len(self.scenes),
                    f"Formatting: {chapter_name} → {scene_name}"
                )

                try:
                    scene = self.db_manager.load_item(scene_id)
                    if not scene:
                        stats["failed"] += 1
                        self.scene_complete.emit(scene_id, False, "✗ Scene not found")
                        continue

                    plain_text = html_to_plaintext(scene.content or "")
                    if not plain_text.strip():
                        stats["skipped"] += 1
                        self.scene_complete.emit(scene_id, True, "Skipped (empty scene)")
                        continue

                    prompt = self._build_prompt(scene_name, plain_text)
                    response = self.ai_manager.call_api(
                        messages=[{"role": "user", "content": prompt}],
                        system_message=(
                            "You are a professional formatter. Return plain text only. "
                            "Never change or replace any words or punctuation."
                        ),
                        temperature=0.0,
                        max_tokens=8000
                    )

                    formatted_text = sanitize_ai_output(response)
                    if not self._matches_original(plain_text, formatted_text):
                        stats["mismatched"] += 1
                        self.scene_complete.emit(
                            scene_id,
                            False,
                            "⚠ Word/punctuation mismatch - skipped"
                        )
                        continue

                    if formatted_text.strip() == plain_text.strip():
                        stats["skipped"] += 1
                        self.scene_complete.emit(scene_id, True, "No formatting changes")
                        continue

                    scene.content = plaintext_to_html(formatted_text)
                    scene.word_count = len([w for w in formatted_text.split() if w])
                    saved = self.db_manager.save_item(self.project_id, scene)

                    if saved:
                        stats["updated"] += 1
                        self.scene_complete.emit(scene_id, True, "✓ Updated")
                    else:
                        stats["failed"] += 1
                        self.scene_complete.emit(scene_id, False, "✗ Failed to save")

                except Exception as e:
                    stats["failed"] += 1
                    self.scene_complete.emit(scene_id, False, f"✗ Error: {str(e)[:120]}")

            self.finished.emit(stats)

        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))

    def _build_prompt(self, scene_name: str, text: str) -> str:
        return (
            "Reformat the following scene for clean paragraphing and line breaks.\n\n"
            "STRICT RULES:\n"
            "- Do NOT change, remove, or add any words.\n"
            "- Do NOT alter punctuation or capitalization.\n"
            "- Keep the exact words in the exact order.\n"
            "- Only adjust whitespace, line breaks, and paragraph breaks.\n"
            "- Return PLAIN TEXT ONLY.\n\n"
            f"SCENE: {scene_name}\n\n"
            f"TEXT:\n{text}\n\n"
            "Return ONLY the reformatted plain text."
        )

    def _matches_original(self, original: str, formatted: str) -> bool:
        normalize = lambda value: re.sub(r"\\s+", "", value or "")
        return normalize(original) == normalize(formatted)


class AIReformatDialog(QDialog):
    """Dialog for batch reformatting all scenes with AI"""

    def __init__(self, parent, ai_manager, db_manager, project_id: str, editor):
        super().__init__(parent)
        self.ai_manager = ai_manager
        self.db_manager = db_manager
        self.project_id = project_id
        self.editor = editor
        self.worker = None
        self.scenes = []
        self.scene_lookup = {}

        self.setWindowTitle("Reformat All Scenes (AI)")
        self.setMinimumSize(720, 520)
        self.init_ui()
        self.load_scenes()

    def init_ui(self):
        layout = QVBoxLayout(self)

        header = QLabel("✨ Reformat All Scenes with AI")
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

        self.info_label = QLabel("This will reformat every scene without changing any words.")
        self.info_label.setStyleSheet("color: #6c757d; padding: 8px; font-size: 10pt;")
        layout.addWidget(self.info_label)

        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout()

        self.progress_label = QLabel("Ready to start")
        self.progress_label.setStyleSheet("font-size: 10pt; color: #495057;")
        progress_layout.addWidget(self.progress_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #dee2e6;
                border-radius: 5px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #667eea, stop:1 #764ba2);
                border-radius: 5px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        progress_group.setLayout(progress_layout)
        layout.addWidget(progress_group)

        log_group = QGroupBox("Log")
        log_layout = QVBoxLayout()
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("""
            QTextEdit {
                background: #f8f9fa;
                font-family: 'Courier New', monospace;
                font-size: 9pt;
                padding: 8px;
            }
        """)
        log_layout.addWidget(self.log_output)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.start_btn = QPushButton("▶ Start")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: #28a745;
                color: white;
                padding: 8px 18px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background: #218838; }
        """)
        self.start_btn.clicked.connect(self.start_reformat)
        button_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹ Stop")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background: #ffc107;
                color: #212529;
                padding: 8px 18px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background: #e0a800; }
            QPushButton:disabled { background: #e9ecef; color: #6c757d; }
        """)
        self.stop_btn.clicked.connect(self.stop_reformat)
        button_layout.addWidget(self.stop_btn)

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

    def load_scenes(self):
        self.scenes = []
        self.scene_lookup = {}

        parts = self.db_manager.load_items(self.project_id, ItemType.PART, parent_id=None)
        for part in parts:
            chapters = self.db_manager.load_items(self.project_id, ItemType.CHAPTER, parent_id=part.id)
            self._collect_chapter_scenes(chapters, part_name=part.name)

        chapters = self.db_manager.load_items(self.project_id, ItemType.CHAPTER, parent_id=None)
        self._collect_chapter_scenes(chapters, part_name=None)

        total_scenes = len(self.scenes)
        total_chapters = len({scene["chapter_id"] for scene in self.scenes})

        self.info_label.setText(
            f"Found {total_scenes} scenes across {total_chapters} chapters. "
            "Click Start to reformat."
        )

    def _collect_chapter_scenes(self, chapters, part_name=None):
        for chapter in chapters:
            scenes = self.db_manager.load_items(self.project_id, ItemType.SCENE, parent_id=chapter.id)
            for scene in scenes:
                chapter_label = f"{part_name} / {chapter.name}" if part_name else chapter.name
                scene_info = {
                    "id": scene.id,
                    "name": scene.name,
                    "chapter": chapter_label,
                    "chapter_id": chapter.id,
                }
                self.scenes.append(scene_info)
                self.scene_lookup[scene.id] = scene_info

    def start_reformat(self):
        if not self.scenes:
            QMessageBox.information(self, "No Scenes", "No scenes found to reformat.")
            return

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log_output.clear()
        self.progress_bar.setValue(0)
        self.progress_label.setText("Starting...")

        self.worker = SceneReformatWorker(
            self.ai_manager,
            self.db_manager,
            self.project_id,
            self.scenes
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.scene_complete.connect(self.on_scene_complete)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def stop_reformat(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.progress_label.setText("Stopping...")
            self.stop_btn.setEnabled(False)

    def on_progress(self, current: int, total: int, message: str):
        self.progress_label.setText(message)
        if total > 0:
            self.progress_bar.setValue(int((current / total) * 100))

    def on_scene_complete(self, scene_id: str, success: bool, message: str):
        scene_info = self.scene_lookup.get(scene_id, {"name": "Unknown", "chapter": "Unknown"})
        status = "OK" if success else "WARN"
        self.log_output.append(f"[{status}] {scene_info['chapter']} → {scene_info['name']}: {message}")

        if success and message == "✓ Updated":
            current_item = getattr(self.editor, "current_item", None)
            if current_item and current_item.id == scene_id:
                scene = self.db_manager.load_item(scene_id)
                if scene:
                    self.editor.load_item(scene, self.db_manager, self.project_id)

    def on_finished(self, stats: dict):
        self.progress_label.setText("Complete")
        self.progress_bar.setValue(100)
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)

        summary = (
            f"Updated: {stats.get('updated', 0)} | "
            f"Skipped: {stats.get('skipped', 0)} | "
            f"Mismatched: {stats.get('mismatched', 0)} | "
            f"Failed: {stats.get('failed', 0)}"
        )
        self.log_output.append("\n" + summary)
        QMessageBox.information(self, "Reformat Complete", summary)

    def on_error(self, message: str):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        QMessageBox.critical(self, "Reformat Error", message)

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Stop Reformatting?",
                "Reformatting is still running. Stop and close?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.worker.stop()
                self.worker.wait(2000)
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
