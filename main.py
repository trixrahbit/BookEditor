#!/usr/bin/env python3
"""
Novelist AI - A novel writing application with AI-powered analysis
Main application entry point
"""
import json
import os
import sys
import threading
import logging
from logging.handlers import RotatingFileHandler
from typing import Dict, Any, Callable, Optional
from functools import wraps

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QMenuBar, QMenu, QToolBar, QStatusBar, QMessageBox, QFileDialog, QApplication
)
from PyQt6.QtCore import Qt, QSettings, pyqtSignal
from PyQt6.QtGui import QAction, QKeySequence, QIcon
from pathlib import Path

from ai_integration import AIFeatures
from ai_manager import ai_manager
from autosave_manager import AutoSaveManager
from db_manager import DatabaseManager, InsightDatabase
from editor_widget import EditorWidget
from insight_service import InsightService
from metadata_panel import MetadataPanel
from models.project import Project, ItemType
from project_dialog import ProjectDialog
from project_tree import ProjectTreeWidget
from settings_dialog import SettingsDialog
from story_insights_dialog import StoryInsightsDialog, AnalysisWorker
from docx_importer import DocxImporter
from analyzer import AIAnalyzer
from story_extractor import StoryExtractor
from chapter_insights_viewer import ChapterInsightsViewer

LOG_PATH: Optional[Path] = None


def setup_logging() -> Path:
    """Configure application logging."""
    global LOG_PATH
    log_dir = Path.home() / ".novelist_ai" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "novelist_ai.log"
    LOG_PATH = log_path

    logger = logging.getLogger("novelist_ai")
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        file_handler = RotatingFileHandler(
            log_path, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
        logger.addHandler(stream_handler)

    return log_path


def install_exception_hooks() -> None:
    """Install global exception hooks to log unexpected errors."""
    logger = logging.getLogger("novelist_ai")

    def handle_exception(exc_type, exc, tb):
        logger.error("Unhandled exception", exc_info=(exc_type, exc, tb))
        app = QApplication.instance()
        if app:
            log_hint = f"\n\nLog file: {LOG_PATH}" if LOG_PATH else ""
            QMessageBox.critical(
                None,
                "Unexpected Error",
                "An unexpected error occurred. Please check the logs for details."
                f"{log_hint}",
            )

    def handle_thread_exception(args):
        logger.error(
            "Unhandled exception in thread %s",
            args.thread.name,
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = handle_exception
    threading.excepthook = handle_thread_exception


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("Rabbit Consulting", "Novelist AI")
        self.db_manager: DatabaseManager = None
        self.ai_integration = None
        self.story_extractor = None
        self.current_project: Project = None
        self.autosave = AutoSaveManager(self, delay_ms=1000)  # 1 second delay
        self.autosave.save_triggered.connect(self._safe_slot(self.save_current_content))
        self.init_ui()
        self.restore_settings()
        self.insight_db = None
        self.insight_service = None
        self.persona_manager = None
        self.ai_manager = ai_manager

    def _safe_slot(self, func: Callable) -> Callable:
        logger = logging.getLogger("novelist_ai")

        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                # First try normal call (works for item_selected(item_id), etc.)
                return func(*args, **kwargs)
            except TypeError as te:
                # If it's a mismatch in args (common from QAction.triggered(bool)),
                # retry with no args.
                try:
                    return func()
                except Exception:
                    logger.exception("Error in slot after retry (no-args): %s", getattr(func, "__name__", repr(func)))
                    log_hint = f"\n\nLog file: {LOG_PATH}" if LOG_PATH else ""
                    QMessageBox.critical(
                        self,
                        "Unexpected Error",
                        "An unexpected error occurred. Please check the logs for details."
                        f"{log_hint}",
                    )
                # If the retry succeeded, we're done
                return None
            except Exception:
                logger.exception("Error in slot: %s", getattr(func, "__name__", repr(func)))
                log_hint = f"\n\nLog file: {LOG_PATH}" if LOG_PATH else ""
                QMessageBox.critical(
                    self,
                    "Unexpected Error",
                    "An unexpected error occurred. Please check the logs for details."
                    f"{log_hint}",
                )

        return wrapper

    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Novelist AI")
        self.setMinimumSize(1200, 800)

        # Create central widget with splitters FIRST
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Main splitter (horizontal)
        main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel - Project tree
        self.project_tree = ProjectTreeWidget()
        self.project_tree.setMinimumWidth(240)
        self.project_tree.item_selected.connect(self._safe_slot(self.on_item_selected))

        # Center panel - Editor
        self.editor = EditorWidget()
        self.editor.content_changed.connect(self._safe_slot(self.on_content_changed))
        self.editor.rewrite_requested.connect(self._safe_slot(self.rewrite_selection_with_persona))
        self.editor.rewrite_selection_action_requested.connect(self._safe_slot(self.rewrite_selection_with_persona))
        self.editor.rewrite_scene_action_requested.connect(self._safe_slot(self.rewrite_scene_with_persona))
        self.project_tree.ai_fill_requested.connect(self._safe_slot(self.on_ai_fill_scene))

        # Right panel - Metadata
        # Right panel - Smart panel (metadata OR chapter insights)
        self.metadata_panel = MetadataPanel()
        self.metadata_panel.setMinimumWidth(280)
        self.metadata_panel.metadata_changed.connect(self._safe_slot(self.on_metadata_changed))


        # Chapter insights viewer
        self.chapter_insights = ChapterInsightsViewer()
        self.chapter_insights.setMinimumWidth(280)
        self.chapter_insights.analyze_requested.connect(self._safe_slot(self.analyze_chapter_ai))
        self.chapter_insights.fix_requested.connect(self._safe_slot(self.on_insight_fix_requested))

        # Stack them (only one visible at a time)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.metadata_panel)
        right_layout.addWidget(self.chapter_insights)
        self.right_panel = right_panel
        self.right_panel = right_panel
        self.metadata_panel.collapse_toggled.connect(
            self._safe_slot(self.on_properties_panel_toggled)
        )

        # Hide chapter insights initially
        self.chapter_insights.setVisible(False)

        # NOW create menu bar and toolbar (after widgets exist)
        self.create_menu_bar()
        self.create_toolbar()
        self.project_tree.ai_analyze_requested.connect(self._safe_slot(self.analyze_chapter_ai))
        self.project_tree.ai_fix_requested.connect(self._safe_slot(self.fix_chapter_ai))

        # Add widgets to splitter
        main_splitter.addWidget(self.project_tree)
        main_splitter.addWidget(self.editor)
        main_splitter.addWidget(self.right_panel)

        # Set initial splitter sizes - give more space to tree and metadata
        main_splitter.setSizes([320, 600, 320])
        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 3)
        main_splitter.setStretchFactor(2, 1)

        main_layout.addWidget(main_splitter)

        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")
        self.autosave.saving_started.connect(lambda: self.statusBar.showMessage("Saving...", 0))
        self.autosave.saving_finished.connect(lambda: self.statusBar.showMessage("Saved ✓", 2000))
        # Store splitter for settings
        self.main_splitter = main_splitter
        self._right_panel_sizes = None
        self._right_panel_collapsed_width = 64

    def on_properties_panel_toggled(self, collapsed: bool):
        """Collapse or expand the properties panel within the splitter."""
        if collapsed:
            self._right_panel_sizes = self.main_splitter.sizes()
            self.right_panel.setMinimumWidth(self._right_panel_collapsed_width)
            self.right_panel.setMaximumWidth(self._right_panel_collapsed_width)
            sizes = self.main_splitter.sizes()
            if len(sizes) == 3:
                self.main_splitter.setSizes([
                    sizes[0],
                    sizes[1],
                    self._right_panel_collapsed_width
                ])
        else:
            self.right_panel.setMinimumWidth(0)
            self.right_panel.setMaximumWidth(16777215)
            if self._right_panel_sizes and len(self._right_panel_sizes) == 3:
                self.main_splitter.setSizes(self._right_panel_sizes)
            else:
                self.main_splitter.setSizes([320, 600, 320])


    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        new_action = QAction("&New Project...", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self._safe_slot(self.new_project))
        file_menu.addAction(new_action)

        open_action = QAction("&Open Project...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self._safe_slot(self.open_project))
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self._safe_slot(self.save_project))
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        import_docx_action = QAction("📥 Import from Word Document...", self)
        import_docx_action.triggered.connect(self._safe_slot(self.import_docx))
        file_menu.addAction(import_docx_action)

        file_menu.addSeparator()

        export_menu = file_menu.addMenu("&Export")

        export_md_action = QAction("Export as &Markdown...", self)
        export_md_action.triggered.connect(self._safe_slot(lambda: self.export_project("markdown")))
        export_menu.addAction(export_md_action)

        export_docx_action = QAction("Export as &Word Document...", self)
        export_docx_action.triggered.connect(self._safe_slot(lambda: self.export_project("docx")))
        export_menu.addAction(export_docx_action)

        file_menu.addSeparator()

        settings_action = QAction("&Settings...", self)
        settings_action.setShortcut(QKeySequence.StandardKey.Preferences)
        settings_action.triggered.connect(self._safe_slot(self.show_settings))
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # Edit menu
        edit_menu = menubar.addMenu("&Edit")

        undo_action = QAction("&Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self._safe_slot(self.editor.undo))
        edit_menu.addAction(undo_action)

        redo_action = QAction("&Redo", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self._safe_slot(self.editor.redo))
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        cut_action = QAction("Cu&t", self)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        cut_action.triggered.connect(self._safe_slot(self.editor.cut))
        edit_menu.addAction(cut_action)

        copy_action = QAction("&Copy", self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.triggered.connect(self._safe_slot(self.editor.copy))
        edit_menu.addAction(copy_action)

        paste_action = QAction("&Paste", self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.triggered.connect(self._safe_slot(self.editor.paste))
        edit_menu.addAction(paste_action)
        # Writing menu
        writing_menu = menubar.addMenu("&Writing")

        manage_personas_action = QAction("✍️ Manage Personas...", self)
        manage_personas_action.triggered.connect(self._safe_slot(self.manage_writing_personas))
        writing_menu.addAction(manage_personas_action)

        writing_menu.addSeparator()

        rewrite_selection_action = QAction("🎨 Rewrite Selection with Persona", self)
        rewrite_selection_action.setShortcut("Ctrl+Shift+R")
        rewrite_selection_action.triggered.connect(self._safe_slot(self.rewrite_selection_with_persona))
        writing_menu.addAction(rewrite_selection_action)

        rewrite_scene_action = QAction("📄 Rewrite Entire Scene", self)
        rewrite_scene_action.triggered.connect(self._safe_slot(self.rewrite_scene_with_persona))
        writing_menu.addAction(rewrite_scene_action)

        writing_menu.addSeparator()

        reformat_scenes_action = QAction("✨ Reformat Using AI...", self)
        reformat_scenes_action.triggered.connect(self._safe_slot(self.reformat_project_scenes_with_ai))
        writing_menu.addAction(reformat_scenes_action)
        # Project menu
        project_menu = menubar.addMenu("&Project")

        add_part_action = QAction("Add &Part", self)
        add_part_action.triggered.connect(self._safe_slot(lambda: self.project_tree.add_item("part")))
        project_menu.addAction(add_part_action)

        add_chapter_action = QAction("Add &Chapter", self)
        add_chapter_action.triggered.connect(self._safe_slot(lambda: self.project_tree.add_item("chapter")))
        project_menu.addAction(add_chapter_action)

        add_scene_action = QAction("Add &Scene", self)
        add_scene_action.setShortcut("Ctrl+N")
        add_scene_action.triggered.connect(self._safe_slot(lambda: self.project_tree.add_item("scene")))
        project_menu.addAction(add_scene_action)

        project_menu.addSeparator()

        add_character_action = QAction("Add Character...", self)
        add_character_action.triggered.connect(self._safe_slot(lambda: self.project_tree.add_item("character")))
        project_menu.addAction(add_character_action)

        add_location_action = QAction("Add Location...", self)
        add_location_action.triggered.connect(self._safe_slot(lambda: self.project_tree.add_item("location")))
        project_menu.addAction(add_location_action)

        add_plot_action = QAction("Add Plot Thread...", self)
        add_plot_action.triggered.connect(self._safe_slot(lambda: self.project_tree.add_item("plot")))
        project_menu.addAction(add_plot_action)

        # AI menu
        ai_menu = menubar.addMenu("&AI Analysis")

        analyze_character_action = QAction("📝 Extract &Characters from Text", self)
        analyze_character_action.triggered.connect(self._safe_slot(self.extract_characters))
        ai_menu.addAction(analyze_character_action)

        analyze_location_action = QAction("📍 Extract &Locations from Text", self)
        analyze_location_action.triggered.connect(self._safe_slot(self.extract_locations))
        ai_menu.addAction(analyze_location_action)

        analyze_plot_action = QAction("🎭 Analyze &Plot Structure", self)
        analyze_plot_action.triggered.connect(self._safe_slot(self.analyze_plot))
        ai_menu.addAction(analyze_plot_action)

        analyze_timeline_action = QAction("⏰ Analyze &Timeline", self)
        analyze_timeline_action.triggered.connect(self._safe_slot(self.analyze_timeline))
        ai_menu.addAction(analyze_timeline_action)

        analyze_style_action = QAction("✍️ Analyze Writing &Style", self)
        analyze_style_action.triggered.connect(self._safe_slot(self.analyze_writing_style))
        ai_menu.addAction(analyze_style_action)

        ai_menu.addSeparator()

        check_consistency_action = QAction("🔍 Check Story Consistency", self)
        check_consistency_action.triggered.connect(self._safe_slot(self.check_story_consistency))
        ai_menu.addAction(check_consistency_action)

        ai_menu.addSeparator()

        full_analysis_action = QAction("&Full Analysis Report", self)
        full_analysis_action.triggered.connect(self._safe_slot(lambda: self.run_full_ai_analysis("full")))
        ai_menu.addAction(full_analysis_action)

        ai_menu.addSeparator()

        story_insights_action = QAction("📊 Deep Insights (Comprehensive)", self)
        story_insights_action.triggered.connect(self._safe_slot(self.show_story_insights))
        ai_menu.addAction(story_insights_action)
        ai_menu.addSeparator()

        view_insights_action = QAction("📊 View Story Insights", self)
        view_insights_action.triggered.connect(self._safe_slot(self.view_story_insights))
        ai_menu.addAction(view_insights_action)
        ai_menu.addSeparator()

        batch_analyze_action = QAction("🚀 Analyze All Chapters", self)
        batch_analyze_action.triggered.connect(self._safe_slot(self.batch_analyze_chapters))
        ai_menu.addAction(batch_analyze_action)
        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self._safe_slot(self.show_about))
        help_menu.addAction(about_action)

    def create_toolbar(self):
        """Create the toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Add common actions
        new_scene_action = QAction("New Scene", self)
        new_scene_action.triggered.connect(self._safe_slot(lambda: self.project_tree.add_item("scene")))
        toolbar.addAction(new_scene_action)

        toolbar.addSeparator()

        save_action = QAction("Save", self)
        save_action.triggered.connect(self._safe_slot(self.save_project))
        toolbar.addAction(save_action)

    def new_project(self):
        """Create a new project"""
        dialog = ProjectDialog(self)
        if dialog.exec():
            project_data = dialog.get_project_data()

            # Ask for save location
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Create New Project",
                "",
                "Novelist AI Project (*.novelist)"
            )

            if file_path:
                if not file_path.endswith('.novelist'):
                    file_path += '.novelist'

                # Create new project
                self.current_project = Project(**project_data)

                # Initialize database
                if self.db_manager:
                    self.db_manager.close()

                self.db_manager = DatabaseManager(file_path)
                self.db_manager.save_project(self.current_project)

                # Initialize AI integration and story extractor
                self.ai_integration = AIFeatures(self, self.db_manager, self.current_project.id)
                self.story_extractor = StoryExtractor(self, self.db_manager, self.current_project.id)
                # Initialize insight service
                self.insight_db = InsightDatabase(self.db_manager)
                self.insight_service = InsightService(
                    ai_manager,
                    self.db_manager,
                    self.insight_db
                )
                # Initialize persona manager
                from writing_persona import PersonaManager
                self.persona_manager = PersonaManager(self.db_manager, self.current_project.id)
                self.editor_widget.set_project_context(self.db_manager, self.current_project.id, self.persona_manager)
                # Update UI
                self.project_tree.load_project(self.db_manager, self.current_project.id)
                self.setWindowTitle(f"Novelist AI - {self.current_project.name}")
                self.statusBar.showMessage(f"Created project: {self.current_project.name}")

    def open_project(self):
        """Open an existing project"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            "",
            "Novelist AI Project (*.novelist)"
        )

        if file_path:
            self.load_project(file_path)

    def load_project(self, file_path: str):
        """Load a project from file"""
        try:
            # Close existing database
            if self.db_manager:
                self.db_manager.close()

            # Open new database
            self.db_manager = DatabaseManager(file_path)
            projects = self.db_manager.list_projects()

            if projects:
                self.current_project = projects[0]  # SET PROJECT FIRST
                self.editor.set_project_context(self.db_manager, self.current_project.id, self.persona_manager)

                # NOW initialize AI integration (after current_project exists)
                self.ai_integration = AIFeatures(self, self.db_manager, self.current_project.id)
                # Initialize insight service
                self.insight_db = InsightDatabase(self.db_manager)
                self.insight_service = InsightService(
                    ai_manager,
                    self.db_manager,
                    self.insight_db
                )
                # Initialize story extractor
                self.story_extractor = StoryExtractor(self, self.db_manager, self.current_project.id)
                # Initialize persona manager
                from writing_persona import PersonaManager
                self.persona_manager = PersonaManager(self.db_manager, self.current_project.id)
                # Load UI
                self.project_tree.load_project(self.db_manager, self.current_project.id)
                self.setWindowTitle(f"Novelist AI - {self.current_project.name}")
                self.statusBar.showMessage(f"Opened project: {self.current_project.name}")
            else:
                QMessageBox.warning(self, "Error", "No project found in file")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open project: {str(e)}")

    def save_project(self):
        """Save the current project"""
        if not self.db_manager or not self.current_project:
            QMessageBox.warning(self, "No Project", "No project is currently open")
            return

        # Save is handled automatically by the tree and editor
        # Just update the status
        self.statusBar.showMessage("Project saved", 3000)


    def export_project(self, format_type: str):
        """Export project to various formats"""
        if not self.current_project:
            QMessageBox.warning(self, "No Project", "No project is currently open")
            return

        format_type = format_type.lower()

        if format_type == "docx":
            from PyQt6.QtWidgets import QFileDialog
            from docx_exporter import DocxExporter

            # Ask user where to save
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Export Project to Word",
                f"{self.current_project.name}.docx",
                "Word Documents (*.docx)"
            )

            if not file_path:
                return  # user cancelled

            try:
                exporter = DocxExporter()
                chapters, scenes = exporter.export_project(
                    db_manager=self.db_manager,
                    project_id=self.current_project.id,
                    output_path=file_path,
                    book_title=self.current_project.name,
                    include_scene_breaks=False  # flip to True if you want ***
                )

                QMessageBox.information(
                    self,
                    "Export Complete",
                    f"Exported successfully!\n\n"
                    f"Chapters: {chapters}\n"
                    f"Scenes: {scenes}\n\n"
                    f"File saved to:\n{file_path}"
                )

            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Export Failed",
                    f"An error occurred while exporting:\n\n{str(e)}"
                )
            return

        # ---- Future formats ----
        QMessageBox.information(
            self,
            "Export",
            f"Export to {format_type.upper()} coming soon!"
        )

    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self)
        dialog.exec()

    def _custom_dict_path(self):
        base = os.path.dirname(self.db_manager.db_path)
        return os.path.join(base, f".custom_dict_{self.current_project.id}.json")

    def load_custom_dict(self):
        path = self._custom_dict_path()
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            words = set(data.get("words", []))
        else:
            words = set()

        self.editor.live_checker.custom_words = set(w.lower() for w in words)

    def save_custom_dict(self):
        path = self._custom_dict_path()
        data = {"words": sorted(list(self.editor.live_checker.custom_words))}
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def on_item_selected(self, item_id: str):
        """Handle item selection in project tree"""
        if not self.db_manager:
            return

        # SAVE CURRENT ITEM IMMEDIATELY before switching
        self.autosave.save_immediately()

        # Now load new item
        item = self.db_manager.load_item(item_id)
        if not item:
            return

        from models.project import ItemType

        # Show appropriate panel based on item type
        if item.item_type == ItemType.CHAPTER:
            # Show chapter insights instead of metadata
            self.metadata_panel.setVisible(False)
            self.chapter_insights.setVisible(True)

            # Load chapter insights
            if self.insight_service:
                self.chapter_insights.load_chapter(
                    item_id,
                    item.name,
                    self.current_project.id,
                    self.insight_service
                )

            # Still load in editor (read-only chapter view)
            self.editor.load_item(item, self.db_manager, self.current_project.id)
            self.update_editor_toolbar_layout()
        else:
            # Show normal metadata for other items
            self.metadata_panel.setVisible(True)
            self.chapter_insights.setVisible(False)
            self.chapter_insights.clear()

            # Load normally
            self.editor.load_item(item, self.db_manager, self.current_project.id)
            self.metadata_panel.load_item(item, self.db_manager, self.current_project.id)
            self.update_editor_toolbar_layout()

    def on_content_changed(self):
        """Handle content changes in editor"""
        self.autosave.request_save()


    def on_metadata_changed(self):
        """Handle metadata changes"""
        # Auto-save could be implemented here
        pass

    def on_metadata_panel_collapsed(self, is_collapsed: bool):
        """Respond to properties panel collapse/expand."""
        self.update_editor_toolbar_layout(is_collapsed=is_collapsed)

    def update_editor_toolbar_layout(self, is_collapsed: Optional[bool] = None):
        """Update editor toolbar layout based on metadata panel visibility."""
        if not self.metadata_panel.isVisible():
            self.editor.set_toolbar_compact(False)
            return

        collapsed = self.metadata_panel.is_collapsed if is_collapsed is None else is_collapsed
        self.editor.set_toolbar_compact(not collapsed)

    def run_ai_analysis(self, analysis_type: str):
        """Run AI analysis on the project"""
        if not self.current_project:
            QMessageBox.warning(self, "No Project", "No project is currently open")
            return

        # TODO: Implement AI analysis
        QMessageBox.information(
            self,
            "AI Analysis",
            f"{analysis_type.title()} analysis coming soon!"
        )

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About Novelist AI",
            "Novelist AI v0.1\n\n"
            "A novel writing application with AI-powered analysis.\n\n"
            "Created by Rabbit Consulting"
        )

    def show_story_insights(self):
        """Show comprehensive story insights dialog"""
        if not self.current_project:
            QMessageBox.warning(self, "No Project", "No project is currently open")
            return

        # Gather all project data
        scenes = [s.to_dict() for s in self.db_manager.load_items(
            self.current_project.id, ItemType.SCENE)]
        characters = [c.to_dict() for c in self.db_manager.load_items(
            self.current_project.id, ItemType.CHARACTER)]
        plot_threads = [p.to_dict() for p in self.db_manager.load_items(
            self.current_project.id, ItemType.PLOT_THREAD)]
        chapters = [ch.to_dict() for ch in self.db_manager.load_items(
            self.current_project.id, ItemType.CHAPTER)]

        if not scenes:
            QMessageBox.warning(
                self,
                "No Content",
                "Please write some scenes before running Story Insights."
            )
            return

        # Create insights dialog
        dialog = StoryInsightsDialog(self)

        # Create and start analysis worker
        analyzer = AIAnalyzer()
        worker = AnalysisWorker(
            analyzer,
            self.current_project.to_dict(),
            scenes,
            characters,
            plot_threads,
            chapters
        )

        worker.progress.connect(self._safe_slot(dialog.update_progress))
        worker.finished.connect(self._safe_slot(dialog.show_analysis_results))
        worker.error.connect(self._safe_slot(dialog.show_error))

        worker.start()
        dialog.exec()

    def import_docx(self):
        """Import a Word document into the project"""
        if not self.current_project:
            QMessageBox.warning(self, "No Project", "Please create or open a project first")
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Word Document",
            "",
            "Word Documents (*.docx)"
        )

        if not file_path:
            return

        try:
            # Show preview
            importer = DocxImporter()
            preview = importer.estimate_structure(file_path)

            if 'error' in preview:
                QMessageBox.critical(
                    self,
                    "Import Error",
                    f"{preview['error']}\n\nPlease install python-docx:\npip install python-docx"
                )
                return

            # Confirm import
            msg = QMessageBox.question(
                self,
                "Confirm Import",
                f"This will import:\n\n"
                f"• {preview['parts']} Parts\n"
                f"• {preview['chapters']} Chapters\n"
                f"• {preview['scenes']} Scenes\n"
                f"• ~{preview['total_words']:,} words\n\n"
                f"Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if msg == QMessageBox.StandardButton.Yes:
                # Perform import
                parts, chapters, scenes = importer.import_docx(
                    file_path,
                    self.db_manager,
                    self.current_project.id
                )

                # Reload project tree
                self.project_tree.load_project(self.db_manager, self.current_project.id)

                QMessageBox.information(
                    self,
                    "Import Complete",
                    f"Successfully imported:\n\n"
                    f"• {parts} Parts\n"
                    f"• {chapters} Chapters\n"
                    f"• {scenes} Scenes"
                )

        except Exception as e:
            QMessageBox.critical(
                self,
                "Import Error",
                f"Failed to import document:\n\n{str(e)}"
            )


    def restore_settings(self):
        """Restore window settings"""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)

        splitter_state = self.settings.value("splitterState")
        if splitter_state:
            self.main_splitter.restoreState(splitter_state)

    def closeEvent(self, event):
        """Handle window close event"""
        # Shutdown insight service
        if self.insight_service:
            self.insight_service.shutdown()

        # Save settings
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        self.settings.setValue("splitterState", self.main_splitter.saveState())

        # Close database
        if self.db_manager:
            self.db_manager.close()

        event.accept()

    def on_ai_rewrite_requested(self, text: str):
        """Handle AI rewrite request from editor"""
        print(f"on_ai_rewrite_requested called with {len(text)} chars")

        if not self.current_project:
            QMessageBox.warning(self, "No Project", "Please open a project first")
            return

        if not self.ai_integration:
            QMessageBox.warning(self, "No AI", "AI integration not initialized")
            return

        def replace_text(new_text):
            """Callback to replace the selected text"""
            print(f"Replacing with {len(new_text)} chars")
            cursor = self.editor.text_edit.textCursor()
            if cursor.hasSelection():
                cursor.insertText(new_text)
                print("Text replaced")

        print("Calling ai_integration.rewrite_text...")
        self.ai_integration.rewrite_text(text, replace_text)

    def on_ai_analyze_requested(self, item_id: str):
        """AI Analyze button handler (scene => autofill properties)."""
        try:
            if not self.current_project:
                return

            item = self.db_manager.load_item(item_id)
            if not item:
                return

            # If a scene is currently open, save latest editor content before analyzing
            if self.editor_widget.current_item and self.editor_widget.current_item.id == item_id:
                self.editor_widget.auto_save()

            from models.project import ItemType

            if item.item_type == ItemType.SCENE:
                # Uses your existing AIIntegration pipeline to fill Summary/Goal/Conflict/Outcome
                def _refresh():
                    refreshed = self.db_manager.load_item(item_id)
                    if refreshed:
                        self.metadata_panel.load_item(refreshed, self.db_manager, self.current_project.id)

                self.ai_integration.fill_scene_properties(item_id, callback=_refresh)

            elif item.item_type == ItemType.CHAPTER:
                # You said you’ll handle the UI next — chapter analysis can be wired here later.
                QMessageBox.information(
                    self,
                    "Chapter Analysis",
                    "Chapter analysis wiring is ready for UI next.\n\n"
                    "Right now the chapter view shows all scenes combined (read-only)."
                )

        except Exception as e:
            QMessageBox.critical(self, "AI Analyze Error", str(e))

    def analyze_chapter_ai(self, chapter_id: str):
        """Run comprehensive AI analysis on a chapter"""
        if not self.current_project:
            QMessageBox.warning(self, "No Project", "Please open a project first")
            return

        if not self.insight_service:
            QMessageBox.warning(self, "No Analysis", "Insight service not initialized")
            return

        # Show analysis dialog
        from advanced_analysis_dialog import AdvancedAnalysisDialog
        dialog = AdvancedAnalysisDialog(
            self,
            self.db_manager,
            self.current_project.id,
            chapter_id,
            self.insight_service
        )

        # Refresh insights viewer when analysis completes
        if dialog.exec():
            self.chapter_insights.refresh()

    def check_story_consistency(self):
        """Check story for consistency issues"""
        if not self.ai_integration:
            QMessageBox.warning(self, "No Project", "Please open a project first")
            return

        self.ai_integration.check_consistency()

    def on_ai_fill_scene(self, scene_id: str):
        """Handle AI fill scene properties request"""
        if not self.ai_integration:
            QMessageBox.warning(self, "No Project", "Please open a project first")
            return

        def refresh():
            # Refresh the metadata panel if this scene is currently selected
            item = self.db_manager.load_item(scene_id)
            if item:
                self.metadata_panel.load_item(item, self.db_manager, self.current_project.id)

        self.ai_integration.fill_scene_properties(scene_id, refresh)

    def run_full_ai_analysis(self, analysis_type: str):
        """Run a full AI analysis of specified type"""
        if not self.current_project or not self.ai_integration:
            QMessageBox.warning(self, "No Project", "No project is currently open")
            return

        if not self.ai_integration.check_configured():
            return

        # Show that analysis is coming soon but configured
        QMessageBox.information(
            self,
            "AI Analysis",
            f"{analysis_type.title()} analysis is configured!\n\n"
            f"Full analysis features are being enhanced.\n"
            f"For now, try:\n"
            f"• Right-click on scenes to auto-fill properties\n"
            f"• Select text and right-click to rewrite with AI\n"
            f"• Use Check Story Consistency"
        )

    def extract_characters(self):
        """Extract characters from manuscript automatically"""
        if not self.story_extractor:
            QMessageBox.warning(self, "No Project", "Please open a project first")
            return

        if not ai_manager.is_configured():
            QMessageBox.warning(
                self,
                "AI Not Configured",
                "Please configure Azure OpenAI in Settings first"
            )
            return

        self.story_extractor.extract_characters()

    def extract_locations(self):
        """Extract locations from manuscript automatically"""
        if not self.story_extractor:
            QMessageBox.warning(self, "No Project", "Please open a project first")
            return

        if not ai_manager.is_configured():
            QMessageBox.warning(
                self,
                "AI Not Configured",
                "Please configure Azure OpenAI in Settings first"
            )
            return

        self.story_extractor.extract_locations()

    def analyze_plot(self):
        """Analyze plot structure chapter by chapter"""
        if not self.story_extractor:
            QMessageBox.warning(self, "No Project", "Please open a project first")
            return

        if not ai_manager.is_configured():
            QMessageBox.warning(
                self,
                "AI Not Configured",
                "Please configure Azure OpenAI in Settings first"
            )
            return

        self.story_extractor.analyze_plot()


    def analyze_timeline(self):
        """Analyze story timeline"""
        if not self.ai_integration:
            QMessageBox.warning(self, "No Project", "Please open a project first")
            return

        self.ai_integration.analyze_timeline()

    def analyze_writing_style(self):
        """Analyze writing style"""
        if not self.ai_integration:
            QMessageBox.warning(self, "No Project", "Please open a project first")
            return

        self.ai_integration.analyze_writing_style()

    def view_story_insights(self):
        """View Story Insights dashboard"""
        if not self.ai_integration:
            QMessageBox.warning(self, "No Project", "Please open a project first")
            return

        self.ai_integration.show_story_insights()

    def save_current_content(self):
        """Actually save the current content"""
        if not self.current_project or not self.db_manager:
            return

        # Get current item from editor
        current_item = self.editor.current_item
        if current_item:
            print(f"Saving: {current_item.name}")
            self.db_manager.save_item(self.current_project.id, current_item)
            self.statusBar.showMessage("Saved", 2000)

    def on_insight_fix_requested(self, issue: Dict[str, Any], chapter_id: str):
        """Handle AI fix request from chapter insights"""
        scene_id = issue.get('scene_id')
        if not scene_id:
            QMessageBox.warning(self, "No Scene", "This issue has no associated scene")
            return

        scene = self.db_manager.load_item(scene_id)
        if not scene:
            QMessageBox.warning(self, "Scene Not Found", "Could not find the scene")
            return

        # Open AI fix dialog
        from ai_fix_dialog import AIFixDialog
        dialog = AIFixDialog(
            self,
            issue,
            scene_id,
            getattr(scene, 'content', ''),
            self.db_manager,
            self.current_project.id
        )

        if dialog.exec():
            # Refresh insights after fix applied
            self.chapter_insights.refresh()

    def batch_analyze_chapters(self):
        """Analyze all chapters in batch"""
        if not self.current_project:
            QMessageBox.warning(self, "No Project", "Please open a project first")
            return

        if not self.insight_service:
            QMessageBox.warning(self, "No Analysis", "Insight service not initialized")
            return

        # Show batch analysis dialog
        from batch_analysis_dialog import BatchAnalysisDialog
        dialog = BatchAnalysisDialog(
            self,
            self.db_manager,
            self.current_project.id,
            self.insight_service
        )
        dialog.exec()

    def manage_writing_personas(self):
        """Open persona manager"""
        if not self.persona_manager:
            QMessageBox.warning(self, "No Project", "Please open a project first")
            return

        from persona_manager_dialog import PersonaManagerDialog
        dialog = PersonaManagerDialog(self, self.persona_manager)
        dialog.exec()

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

    def rewrite_scene_with_persona(self):
        """Rewrite entire current scene with persona"""
        if not self.persona_manager:
            QMessageBox.warning(self, "No Project", "Please open a project first")
            return

        # Get current scene
        current_item = self.editor.current_item
        if not current_item:
            QMessageBox.warning(self, "No Scene", "Please open a scene to rewrite")
            return

        from models.project import ItemType
        if current_item.item_type != ItemType.SCENE:
            QMessageBox.warning(self, "Not a Scene", "Please open a scene to rewrite")
            return

        # Get scene content
        from text_utils import html_to_plaintext
        scene_text = html_to_plaintext(current_item.content or "")

        if not scene_text.strip():
            QMessageBox.warning(self, "Empty Scene", "Scene has no content to rewrite")
            return

        # Confirm
        reply = QMessageBox.question(
            self,
            "Rewrite Scene",
            f"Rewrite entire scene '{current_item.name}'?\n\n"
            f"This will generate a new version based on your selected persona.\n"
            f"You can review before applying.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Open rewrite dialog
        from persona_rewrite_dialog import PersonaRewriteDialog
        from ai_manager import ai_manager

        dialog = PersonaRewriteDialog(
            self,
            ai_manager,
            self.persona_manager,
            scene_text,
            scope="scene"
        )

        if dialog.exec():
            # Apply rewritten text
            rewritten = dialog.get_rewritten_text()
            if rewritten:
                from text_utils import plaintext_to_html
                current_item.content = plaintext_to_html(rewritten)
                self.db_manager.save_item(self.current_project.id, current_item)

                # Reload in editor
                self.editor.load_item(current_item, self.db_manager, self.current_project.id)

                QMessageBox.information(self, "Applied", "Scene rewritten successfully!")

    def reformat_project_scenes_with_ai(self):
        """Open AI reformat dialog to select chapters/scenes and run formatting."""
        if not self.current_project:
            QMessageBox.warning(self, "No Project", "Please open a project first")
            return

        if not self.ai_manager.is_configured():
            QMessageBox.warning(
                self,
                "AI Not Configured",
                "Please configure Azure OpenAI in Settings before using this feature."
            )
            return

        # Open the selector dialog — nothing runs until the user clicks Start
        from ai_reformat_dialog import AIReformatDialog

        dialog = AIReformatDialog(
            parent=self,
            ai_manager=self.ai_manager,
            db_manager=self.db_manager,
            project_id=self.current_project.id,
            editor=self.editor
        )
        dialog.exec()

    def fix_chapter_ai(self, chapter_id: str):
        """Fix chapter issues with AI"""
        if not self.current_project or not self.insight_service:
            QMessageBox.warning(self, "Not Ready", "Please ensure project is loaded and AI is configured")
            return

        # Get chapter name
        chapter = self.db_manager.load_item(chapter_id)
        if not chapter:
            return

        # Open AI fix dialog
        from ai_fix_chapter_dialog import AIFixChapterDialog

        dialog = AIFixChapterDialog(
            self,
            self.ai_manager,
            self.db_manager,
            self.current_project.id,
            chapter_id,
            chapter.name,
            self.insight_service
        )

        if dialog.exec():
            # Refresh editor if currently viewing this chapter
            if self.editor.current_item and self.editor.current_item.id == chapter_id:
                self.editor.load_item(chapter, self.db_manager, self.current_project.id)

            QMessageBox.information(
                self,
                "Analysis Recommended",
                "Chapter has been fixed!\n\n"
                "Run 'AI Analyze Chapter' again to verify the fixes."
            )

def main():
    """Main entry point for the application"""
    print("Starting Novelist AI...")
    print(f"Python version: {sys.version}")
    setup_logging()
    install_exception_hooks()

    # Enable high DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    # Create application
    app = QApplication(sys.argv)
    app.setApplicationName("Novelist AI")
    app.setOrganizationName("Rabbit Consulting")
    app.setOrganizationDomain("rabbit-consulting.com")

    # Set application style
    app.setStyle('Fusion')

    # Create and show main window
    window = MainWindow()
    window.show()

    print("Window created and shown")
    print("Application running - use File menu to create/open projects")

    # Start event loop - this keeps the window open
    exit_code = app.exec()
    print(f"Application closed with exit code: {exit_code}")
    return exit_code


if __name__ == '__main__':
    sys.exit(main())
