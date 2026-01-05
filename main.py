#!/usr/bin/env python3
"""
Novelist AI - A novel writing application with AI-powered analysis
Main application entry point
"""

import sys
from typing import Dict, Any

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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("Rabbit Consulting", "Novelist AI")
        self.db_manager: DatabaseManager = None
        self.ai_integration = None
        self.story_extractor = None
        self.current_project: Project = None
        self.autosave = AutoSaveManager(self, delay_ms=1000)  # 1 second delay
        self.autosave.save_triggered.connect(self.save_current_content)
        self.init_ui()
        self.restore_settings()
        self.insight_db = None
        self.insight_service = None

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
        self.project_tree.setMinimumWidth(280)
        self.project_tree.item_selected.connect(self.on_item_selected)

        # Center panel - Editor
        self.editor = EditorWidget()
        self.editor.content_changed.connect(self.on_content_changed)
        self.editor.rewrite_requested.connect(self.on_ai_rewrite_requested)
        self.project_tree.ai_fill_requested.connect(self.on_ai_fill_scene)

        # Right panel - Metadata
        # Right panel - Smart panel (metadata OR chapter insights)
        self.metadata_panel = MetadataPanel()
        self.metadata_panel.setMinimumWidth(280)
        self.metadata_panel.metadata_changed.connect(self.on_metadata_changed)

        # Chapter insights viewer
        self.chapter_insights = ChapterInsightsViewer()
        self.chapter_insights.setMinimumWidth(280)
        self.chapter_insights.analyze_requested.connect(self.analyze_chapter_ai)
        self.chapter_insights.fix_requested.connect(self.on_insight_fix_requested)

        # Stack them (only one visible at a time)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.metadata_panel)
        right_layout.addWidget(self.chapter_insights)

        # Hide chapter insights initially
        self.chapter_insights.setVisible(False)

        # NOW create menu bar and toolbar (after widgets exist)
        self.create_menu_bar()
        self.create_toolbar()
        self.project_tree.ai_analyze_requested.connect(self.analyze_chapter_ai)

        # Add widgets to splitter
        main_splitter.addWidget(self.project_tree)
        main_splitter.addWidget(self.editor)
        main_splitter.addWidget(right_panel)

        # Set initial splitter sizes - give more space to tree and metadata
        main_splitter.setSizes([320, 600, 320])

        main_layout.addWidget(main_splitter)

        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")
        self.autosave.saving_started.connect(lambda: self.statusBar.showMessage("Saving...", 0))
        self.autosave.saving_finished.connect(lambda: self.statusBar.showMessage("Saved ✓", 2000))
        # Store splitter for settings
        self.main_splitter = main_splitter

    def create_menu_bar(self):
        """Create the menu bar"""
        menubar = self.menuBar()

        # File menu
        file_menu = menubar.addMenu("&File")

        new_action = QAction("&New Project...", self)
        new_action.setShortcut(QKeySequence.StandardKey.New)
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)

        open_action = QAction("&Open Project...", self)
        open_action.setShortcut(QKeySequence.StandardKey.Open)
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)

        file_menu.addSeparator()

        import_docx_action = QAction("📥 Import from Word Document...", self)
        import_docx_action.triggered.connect(self.import_docx)
        file_menu.addAction(import_docx_action)

        file_menu.addSeparator()

        export_menu = file_menu.addMenu("&Export")

        export_md_action = QAction("Export as &Markdown...", self)
        export_md_action.triggered.connect(lambda: self.export_project("markdown"))
        export_menu.addAction(export_md_action)

        export_docx_action = QAction("Export as &Word Document...", self)
        export_docx_action.triggered.connect(lambda: self.export_project("docx"))
        export_menu.addAction(export_docx_action)

        file_menu.addSeparator()

        settings_action = QAction("&Settings...", self)
        settings_action.setShortcut(QKeySequence.StandardKey.Preferences)
        settings_action.triggered.connect(self.show_settings)
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
        undo_action.triggered.connect(self.editor.undo)
        edit_menu.addAction(undo_action)

        redo_action = QAction("&Redo", self)
        redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        redo_action.triggered.connect(self.editor.redo)
        edit_menu.addAction(redo_action)

        edit_menu.addSeparator()

        cut_action = QAction("Cu&t", self)
        cut_action.setShortcut(QKeySequence.StandardKey.Cut)
        cut_action.triggered.connect(self.editor.cut)
        edit_menu.addAction(cut_action)

        copy_action = QAction("&Copy", self)
        copy_action.setShortcut(QKeySequence.StandardKey.Copy)
        copy_action.triggered.connect(self.editor.copy)
        edit_menu.addAction(copy_action)

        paste_action = QAction("&Paste", self)
        paste_action.setShortcut(QKeySequence.StandardKey.Paste)
        paste_action.triggered.connect(self.editor.paste)
        edit_menu.addAction(paste_action)

        # Project menu
        project_menu = menubar.addMenu("&Project")

        add_part_action = QAction("Add &Part", self)
        add_part_action.triggered.connect(lambda: self.project_tree.add_item("part"))
        project_menu.addAction(add_part_action)

        add_chapter_action = QAction("Add &Chapter", self)
        add_chapter_action.triggered.connect(lambda: self.project_tree.add_item("chapter"))
        project_menu.addAction(add_chapter_action)

        add_scene_action = QAction("Add &Scene", self)
        add_scene_action.setShortcut("Ctrl+N")
        add_scene_action.triggered.connect(lambda: self.project_tree.add_item("scene"))
        project_menu.addAction(add_scene_action)

        project_menu.addSeparator()

        add_character_action = QAction("Add Character...", self)
        add_character_action.triggered.connect(lambda: self.project_tree.add_item("character"))
        project_menu.addAction(add_character_action)

        add_location_action = QAction("Add Location...", self)
        add_location_action.triggered.connect(lambda: self.project_tree.add_item("location"))
        project_menu.addAction(add_location_action)

        add_plot_action = QAction("Add Plot Thread...", self)
        add_plot_action.triggered.connect(lambda: self.project_tree.add_item("plot"))
        project_menu.addAction(add_plot_action)

        # AI menu
        ai_menu = menubar.addMenu("&AI Analysis")

        analyze_character_action = QAction("📝 Extract &Characters from Text", self)
        analyze_character_action.triggered.connect(self.extract_characters)
        ai_menu.addAction(analyze_character_action)

        analyze_location_action = QAction("📍 Extract &Locations from Text", self)
        analyze_location_action.triggered.connect(self.extract_locations)
        ai_menu.addAction(analyze_location_action)

        analyze_plot_action = QAction("🎭 Analyze &Plot Structure", self)
        analyze_plot_action.triggered.connect(self.analyze_plot)
        ai_menu.addAction(analyze_plot_action)

        analyze_timeline_action = QAction("⏰ Analyze &Timeline", self)
        analyze_timeline_action.triggered.connect(self.analyze_timeline)
        ai_menu.addAction(analyze_timeline_action)

        analyze_style_action = QAction("✍️ Analyze Writing &Style", self)
        analyze_style_action.triggered.connect(self.analyze_writing_style)
        ai_menu.addAction(analyze_style_action)

        ai_menu.addSeparator()

        check_consistency_action = QAction("🔍 Check Story Consistency", self)
        check_consistency_action.triggered.connect(self.check_story_consistency)
        ai_menu.addAction(check_consistency_action)

        ai_menu.addSeparator()

        full_analysis_action = QAction("&Full Analysis Report", self)
        full_analysis_action.triggered.connect(lambda: self.run_full_ai_analysis("full"))
        ai_menu.addAction(full_analysis_action)

        ai_menu.addSeparator()

        story_insights_action = QAction("📊 &Story Insights (Comprehensive)", self)
        story_insights_action.triggered.connect(self.show_story_insights)
        ai_menu.addAction(story_insights_action)
        ai_menu.addSeparator()

        view_insights_action = QAction("📊 View Story Insights", self)
        view_insights_action.triggered.connect(self.view_story_insights)
        ai_menu.addAction(view_insights_action)
        # Help menu
        help_menu = menubar.addMenu("&Help")

        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_toolbar(self):
        """Create the toolbar"""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Add common actions
        new_scene_action = QAction("New Scene", self)
        new_scene_action.triggered.connect(lambda: self.project_tree.add_item("scene"))
        toolbar.addAction(new_scene_action)

        toolbar.addSeparator()

        save_action = QAction("Save", self)
        save_action.triggered.connect(self.save_project)
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

        # TODO: Implement export functionality
        QMessageBox.information(
            self,
            "Export",
            f"Export to {format_type} coming soon!"
        )

    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self)
        dialog.exec()

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
        else:
            # Show normal metadata for other items
            self.metadata_panel.setVisible(True)
            self.chapter_insights.setVisible(False)
            self.chapter_insights.clear()

            # Load normally
            self.editor.load_item(item, self.db_manager, self.current_project.id)
            self.metadata_panel.load_item(item, self.db_manager, self.current_project.id)

    def on_content_changed(self):
        """Handle content changes in editor"""
        self.autosave.request_save()

    def on_metadata_changed(self):
        """Handle metadata changes"""
        # Auto-save could be implemented here
        pass

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

        worker.progress.connect(dialog.update_progress)
        worker.finished.connect(dialog.show_analysis_results)
        worker.error.connect(dialog.show_error)

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

def main():
    """Main entry point for the application"""
    print("Starting Novelist AI...")
    print(f"Python version: {sys.version}")

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