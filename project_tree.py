"""
Project tree widget for navigating the novel structure
"""

from PyQt6.QtWidgets import (
    QTreeWidget, QTreeWidgetItem, QMenu, QInputDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize
from PyQt6.QtGui import QAction, QIcon

from models.project import ItemType, Scene, Chapter, Part, Character, Location, PlotThread
from db_manager import DatabaseManager

class ProjectTreeWidget(QTreeWidget):
    item_selected = pyqtSignal(str)  # Emits item ID
    ai_fill_requested = pyqtSignal(str)  # Emits scene_id for AI analysis

    def __init__(self):
        super().__init__()
        self.db_manager: DatabaseManager = None
        self.project_id: str = None

        self.init_ui()

    def init_ui(self):
        """Initialize the tree widget"""
        self.setHeaderLabel("Project Structure")
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.itemClicked.connect(self.on_item_clicked)

        # Enable drag and drop for reordering
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)

        # Make items larger and more readable
        self.setIndentation(25)
        self.setIconSize(QSize(20, 20))

        # Apply modern styling
        self.setStyleSheet("""
            QTreeWidget {
                background: white;
                border: none;
                font-size: 11pt;
                outline: none;
            }
            
            QTreeWidget::item {
                padding: 8px 5px;
                border-bottom: 1px solid #f0f0f0;
            }
            
            QTreeWidget::item:hover {
                background: #f8f9fa;
            }
            
            QTreeWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #667eea, stop:1 #764ba2);
                color: white;
                border-radius: 4px;
            }
            
            QTreeWidget::branch {
                background: white;
            }
        """)

    def load_project(self, db_manager: DatabaseManager, project_id: str):
        """Load project structure into tree"""
        self.db_manager = db_manager
        self.project_id = project_id
        self.clear()

        # Create root sections with icons
        manuscript_root = QTreeWidgetItem(self)
        manuscript_root.setText(0, "📚 Manuscript")
        manuscript_root.setData(0, Qt.ItemDataRole.UserRole, "manuscript_root")
        manuscript_root.setExpanded(True)

        characters_root = QTreeWidgetItem(self)
        characters_root.setText(0, "👥 Characters")
        characters_root.setData(0, Qt.ItemDataRole.UserRole, "characters_root")
        characters_root.setExpanded(True)

        locations_root = QTreeWidgetItem(self)
        locations_root.setText(0, "🌍 Locations")
        locations_root.setData(0, Qt.ItemDataRole.UserRole, "locations_root")

        plots_root = QTreeWidgetItem(self)
        plots_root.setText(0, "🎭 Plot Threads")
        plots_root.setData(0, Qt.ItemDataRole.UserRole, "plots_root")

        # Load manuscript items (parts, chapters, scenes)
        self._load_manuscript_items(manuscript_root)

        # Load characters
        self._load_items(characters_root, ItemType.CHARACTER, "👤")

        # Load locations
        self._load_items(locations_root, ItemType.LOCATION, "📍")

        # Load plot threads
        self._load_items(plots_root, ItemType.PLOT_THREAD, "🧵")

    def _load_manuscript_items(self, parent_widget: QTreeWidgetItem):
        """Load manuscript structure (parts > chapters > scenes)"""
        # Load top-level parts
        parts = self.db_manager.load_items(self.project_id, ItemType.PART, parent_id=None)

        for part in parts:
            part_item = QTreeWidgetItem(parent_widget)
            part_item.setText(0, f"📚 {part.name}")
            part_item.setData(0, Qt.ItemDataRole.UserRole, part.id)
            part_item.setExpanded(True)

            # Load chapters in this part
            chapters = self.db_manager.load_items(self.project_id, ItemType.CHAPTER, parent_id=part.id)
            for chapter in chapters:
                chapter_item = QTreeWidgetItem(part_item)
                chapter_item.setText(0, f"📖 {chapter.name}")
                chapter_item.setData(0, Qt.ItemDataRole.UserRole, chapter.id)
                chapter_item.setExpanded(True)

                # Load scenes in this chapter
                self._load_scenes(chapter_item, chapter.id)

        # Load top-level chapters (no part)
        chapters = self.db_manager.load_items(self.project_id, ItemType.CHAPTER, parent_id=None)
        for chapter in chapters:
            chapter_item = QTreeWidgetItem(parent_widget)
            chapter_item.setText(0, f"📖 {chapter.name}")
            chapter_item.setData(0, Qt.ItemDataRole.UserRole, chapter.id)
            chapter_item.setExpanded(True)

            # Load scenes in this chapter
            self._load_scenes(chapter_item, chapter.id)

        # NOTE: We do NOT load orphan scenes (parent_id=None) at root level
        # All scenes should be under a chapter

    def _load_scenes(self, parent_widget: QTreeWidgetItem, parent_id: str):
        """Load scenes under a parent"""
        scenes = self.db_manager.load_items(self.project_id, ItemType.SCENE, parent_id=parent_id)
        for scene in scenes:
            scene_item = QTreeWidgetItem(parent_widget)

            # Format with word count
            if scene.word_count > 0:
                scene_item.setText(0, f"📝 {scene.name}")
                scene_item.setToolTip(0, f"{scene.name}\n{scene.word_count:,} words")
            else:
                scene_item.setText(0, f"📝 {scene.name}")
                scene_item.setToolTip(0, f"{scene.name}\nNo content yet")

            scene_item.setData(0, Qt.ItemDataRole.UserRole, scene.id)

    def _load_items(self, parent_widget: QTreeWidgetItem, item_type: ItemType, icon: str = ""):
        """Load items of a specific type"""
        items = self.db_manager.load_items(self.project_id, item_type)
        for item in items:
            tree_item = QTreeWidgetItem(parent_widget)
            tree_item.setText(0, f"{icon} {item.name}" if icon else item.name)
            tree_item.setData(0, Qt.ItemDataRole.UserRole, item.id)

    def on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle item click"""
        item_id = item.data(0, Qt.ItemDataRole.UserRole)

        # Don't emit for root items
        if item_id and not item_id.endswith("_root"):
            self.item_selected.emit(item_id)

    def show_context_menu(self, position):
        """Show context menu for tree items"""
        item = self.itemAt(position)
        if not item:
            return

        item_id = item.data(0, Qt.ItemDataRole.UserRole)

        menu = QMenu(self)

        # Different menus based on item type
        if item_id == "manuscript_root":
            add_part_action = QAction("Add Part", self)
            add_part_action.triggered.connect(lambda: self.add_item("part"))
            menu.addAction(add_part_action)

            add_chapter_action = QAction("Add Chapter", self)
            add_chapter_action.triggered.connect(lambda: self.add_item("chapter"))
            menu.addAction(add_chapter_action)

            add_scene_action = QAction("Add Scene", self)
            add_scene_action.triggered.connect(lambda: self.add_item("scene"))
            menu.addAction(add_scene_action)

        elif item_id == "characters_root":
            add_character_action = QAction("Add Character", self)
            add_character_action.triggered.connect(lambda: self.add_item("character"))
            menu.addAction(add_character_action)

        elif item_id == "locations_root":
            add_location_action = QAction("Add Location", self)
            add_location_action.triggered.connect(lambda: self.add_item("location"))
            menu.addAction(add_location_action)

        elif item_id == "plots_root":
            add_plot_action = QAction("Add Plot Thread", self)
            add_plot_action.triggered.connect(lambda: self.add_item("plot"))
            menu.addAction(add_plot_action)

        else:
            # Regular item - check what type it is
            db_item = self.db_manager.load_item(item_id)

            if db_item:
                # AI features for scenes
                if db_item.item_type == ItemType.SCENE:
                    ai_fill_action = QAction("🤖 AI: Auto-fill Scene Properties", self)
                    ai_fill_action.triggered.connect(lambda: self.ai_fill_requested.emit(item_id))
                    menu.addAction(ai_fill_action)
                    menu.addSeparator()

            # Regular edit/delete actions
            rename_action = QAction("Rename", self)
            rename_action.triggered.connect(lambda: self.rename_item(item))
            menu.addAction(rename_action)

            menu.addSeparator()

            delete_action = QAction("Delete", self)
            delete_action.triggered.connect(lambda: self.delete_item(item))
            menu.addAction(delete_action)

        menu.exec(self.viewport().mapToGlobal(position))

    def add_item(self, item_type: str):
        """Add a new item to the project"""
        if not self.db_manager or not self.project_id:
            return

        # Get name from user
        name, ok = QInputDialog.getText(
            self,
            f"Add {item_type.title()}",
            f"Enter {item_type} name:"
        )

        if not ok or not name:
            return

        # Create appropriate item type
        if item_type == "part":
            item = Part(name=name)
        elif item_type == "chapter":
            item = Chapter(name=name)
        elif item_type == "scene":
            item = Scene(name=name)
        elif item_type == "character":
            item = Character(name=name)
        elif item_type == "location":
            item = Location(name=name)
        elif item_type == "plot":
            item = PlotThread(name=name)
        else:
            return

        # Get parent if applicable
        current_item = self.currentItem()
        if current_item:
            parent_id = current_item.data(0, Qt.ItemDataRole.UserRole)
            if parent_id and not parent_id.endswith("_root"):
                # Check if parent is appropriate
                parent = self.db_manager.load_item(parent_id)
                if parent and self._can_add_child(parent.item_type, item.item_type):
                    item.parent_id = parent_id

        # Save to database
        self.db_manager.save_item(self.project_id, item)

        # Reload tree
        self.load_project(self.db_manager, self.project_id)

    def _can_add_child(self, parent_type: ItemType, child_type: ItemType) -> bool:
        """Check if a child can be added to a parent"""
        valid_combinations = {
            ItemType.PART: [ItemType.CHAPTER],
            ItemType.CHAPTER: [ItemType.SCENE],
        }

        return child_type in valid_combinations.get(parent_type, [])

    def rename_item(self, tree_item: QTreeWidgetItem):
        """Rename an item"""
        item_id = tree_item.data(0, Qt.ItemDataRole.UserRole)
        if not item_id or item_id.endswith("_root"):
            return

        item = self.db_manager.load_item(item_id)
        if not item:
            return

        new_name, ok = QInputDialog.getText(
            self,
            "Rename Item",
            "Enter new name:",
            text=item.name
        )

        if ok and new_name and new_name != item.name:
            item.name = new_name
            self.db_manager.save_item(self.project_id, item)
            tree_item.setText(0, new_name)

    def delete_item(self, tree_item: QTreeWidgetItem):
        """Delete an item"""
        item_id = tree_item.data(0, Qt.ItemDataRole.UserRole)
        if not item_id or item_id.endswith("_root"):
            return

        item = self.db_manager.load_item(item_id)
        if not item:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{item.name}'?\n\n"
            "This will also delete all child items.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.db_manager.delete_item(item_id)
            self.load_project(self.db_manager, self.project_id)