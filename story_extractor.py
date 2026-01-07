"""
Story Extraction and Analysis - Auto-populate characters, locations, and plot from text
"""

from PyQt6.QtWidgets import (
    QMessageBox, QProgressDialog, QDialog, QVBoxLayout, 
    QScrollArea, QWidget, QCheckBox, QPushButton, QHBoxLayout, QLabel
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from ai_manager import ai_manager
from typing import List, Dict, Any
import re

class SelectionDialog(QDialog):
    """Dialog with checkboxes to select items for import"""
    def __init__(self, items: List[Dict], title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumSize(400, 500)
        self.selected_items = []
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("Select items to import into your project:"))
        
        # Scroll area for items
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.content_layout = QVBoxLayout(content)
        
        self.checkboxes = []
        for item in items:
            cb = QCheckBox(f"{item['display_name']}")
            cb.setToolTip(item.get('description', ''))
            cb.setChecked(True)
            cb.setProperty("item_data", item['original_data'])
            cb.setProperty("item_id", item['id'])
            self.content_layout.addWidget(cb)
            self.checkboxes.append(cb)
            
        self.content_layout.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll)
        
        # Buttons
        btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_none_btn = QPushButton("Select None")
        ok_btn = QPushButton("Import Selected")
        cancel_btn = QPushButton("Cancel")
        
        select_all_btn.clicked.connect(self.select_all)
        select_none_btn.clicked.connect(self.select_none)
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(select_none_btn)
        btn_layout.addStretch()
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

    def select_all(self):
        for cb in self.checkboxes:
            cb.setChecked(True)

    def select_none(self):
        for cb in self.checkboxes:
            cb.setChecked(False)

    def get_selected(self) -> Dict:
        selected = {}
        for cb in self.checkboxes:
            if cb.isChecked():
                item_id = cb.property("item_id")
                selected[item_id] = cb.property("item_data")
        return selected

class ExtractionWorker(QThread):
    """Worker thread for extracting story elements"""
    progress = pyqtSignal(str, int)  # message, percentage
    finished = pyqtSignal(dict)  # extracted data
    error = pyqtSignal(str)

    def __init__(self, operation_type: str, chapters: List[Dict], scenes: List[Dict]):
        super().__init__()
        self.operation_type = operation_type
        self.chapters = chapters
        self.scenes = scenes

    def run(self):
        try:
            if self.operation_type == "characters":
                result = self._extract_characters()
            elif self.operation_type == "locations":
                result = self._extract_locations()
            elif self.operation_type == "plot":
                result = self._analyze_plot()
            else:
                result = {}

            self.finished.emit(result)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))

    def _extract_characters(self):
        """Extract characters from all scenes chapter by chapter"""
        all_characters = {}
        total_chapters = len(self.chapters)

        for idx, chapter in enumerate(self.chapters):
            chapter_name = chapter.get('name', f'Chapter {idx + 1}')
            self.progress.emit(f"Analyzing {chapter_name}...", int((idx / total_chapters) * 100))

            # Get scenes for this chapter
            chapter_scenes = [s for s in self.scenes if s.get('parent_id') == chapter.get('id')]

            if not chapter_scenes:
                continue

            # Combine scene content
            chapter_text = "\n\n".join([
                self._strip_html(s.get('content', '')) for s in chapter_scenes
            ])[:3000]  # Limit to prevent token overflow

            # Ask AI to extract characters
            prompt = f"""Extract all character names from this chapter text. For each character:
1. Identify their full name (first and last if available)
2. Estimate their significance (major, supporting, or minor)
3. Brief one-line description of their role

Chapter: {chapter_name}

TEXT:
{chapter_text}

Respond in this EXACT format:
CHARACTER: [Name]
SIGNIFICANCE: [major/supporting/minor]
ROLE: [one-line role description]

(Repeat for each character found)"""

            try:
                response = ai_manager.call_api(
                    messages=[{"role": "user", "content": prompt}],
                    system_message="You are a literary analyst extracting character information from novels.",
                    temperature=0.3,
                    max_tokens=16000
                )

                # Parse response
                characters = self._parse_character_response(response, chapter_name)

                # Merge with existing characters
                for char_name, char_data in characters.items():
                    # Find if this is a duplicate (first/last name match)
                    matched_name = self._find_matching_character(char_name, all_characters)

                    if matched_name:
                        # Matched an existing character - merge
                        all_characters[matched_name]['mentions'] += 1
                        all_characters[matched_name]['chapters'].append(chapter_name)
                        # Upgrade significance if needed
                        if char_data['significance'] == 'major':
                            all_characters[matched_name]['significance'] = 'major'
                        elif char_data['significance'] == 'supporting' and all_characters[matched_name][
                            'significance'] == 'minor':
                            all_characters[matched_name]['significance'] = 'supporting'
                        # Use the longer/more complete name
                        if len(char_name) > len(matched_name):
                            all_characters[char_name] = all_characters.pop(matched_name)
                            all_characters[char_name]['name'] = char_name
                    else:
                        # New character
                        all_characters[char_name] = {
                            **char_data,
                            'mentions': 1,
                            'chapters': [chapter_name]
                        }

            except Exception as e:
                print(f"Error analyzing chapter {chapter_name}: {e}")
                continue

        return {'characters': all_characters}

    def _extract_locations(self):
        """Extract locations from all scenes chapter by chapter"""
        all_locations = {}
        total_chapters = len(self.chapters)

        for idx, chapter in enumerate(self.chapters):
            chapter_name = chapter.get('name', f'Chapter {idx + 1}')
            self.progress.emit(f"Finding locations in {chapter_name}...", int((idx / total_chapters) * 100))

            # Get scenes for this chapter
            chapter_scenes = [s for s in self.scenes if s.get('parent_id') == chapter.get('id')]

            if not chapter_scenes:
                continue

            # Combine scene content
            chapter_text = "\n\n".join([
                self._strip_html(s.get('content', '')) for s in chapter_scenes
            ])[:3000]

            # Ask AI to extract locations
            prompt = f"""Extract all significant locations mentioned in this chapter text. For each location:
1. The location name
2. Type (city, building, room, outdoor, etc.)
3. Brief description

Chapter: {chapter_name}

TEXT:
{chapter_text}

Respond in this EXACT format:
LOCATION: [Name]
TYPE: [type]
DESCRIPTION: [one-line description]

(Repeat for each location)"""

            try:
                response = ai_manager.call_api(
                    messages=[{"role": "user", "content": prompt}],
                    system_message="You are a literary analyst extracting location information from novels.",
                    temperature=0.3,
                    max_tokens=16000
                )

                # Parse response
                locations = self._parse_location_response(response, chapter_name)

                # Merge with existing locations
                for loc_name, loc_data in locations.items():
                    if loc_name in all_locations:
                        all_locations[loc_name]['appearances'] += 1
                        all_locations[loc_name]['chapters'].append(chapter_name)
                    else:
                        all_locations[loc_name] = {
                            **loc_data,
                            'appearances': 1,
                            'chapters': [chapter_name]
                        }

            except Exception as e:
                print(f"Error analyzing chapter {chapter_name}: {e}")
                continue

        return {'locations': all_locations}

    def _analyze_plot(self):
        """Analyze plot structure chapter by chapter"""
        plot_analysis = []
        plot_threads = {}  # Track unique plot threads
        total_chapters = len(self.chapters)

        for idx, chapter in enumerate(self.chapters):
            chapter_name = chapter.get('name', f'Chapter {idx + 1}')
            self.progress.emit(f"Analyzing plot in {chapter_name}...", int((idx / total_chapters) * 100))

            # Get scenes for this chapter
            chapter_scenes = [s for s in self.scenes if s.get('parent_id') == chapter.get('id')]

            if not chapter_scenes:
                continue

            # Get scene summaries or content
            scene_info = []
            for scene in chapter_scenes:
                summary = scene.get('summary', '')
                if not summary:
                    content = self._strip_html(scene.get('content', ''))[:500]
                    summary = content
                scene_info.append(f"Scene: {scene.get('name', 'Untitled')}\n{summary}")

            chapter_content = "\n\n".join(scene_info)

            # Ask AI to analyze plot
            prompt = f"""Analyze the plot elements in this chapter:

Chapter: {chapter_name}

SCENES:
{chapter_content}

Provide:
1. PLOT THREADS: What ongoing storylines are present? (Give each a short name)
2. KEY EVENTS: What major events happen?
3. CONFLICTS: What conflicts arise or continue?
4. TURNING POINTS: Any major turning points or revelations?

Format as:
PLOT THREADS: [Thread Name 1], [Thread Name 2], ...
KEY EVENTS: [list]
CONFLICTS: [list]
TURNING POINTS: [list or "None"]"""

            try:
                response = ai_manager.call_api(
                    messages=[{"role": "user", "content": prompt}],
                    system_message="You are a plot analyst examining story structure.",
                    temperature=0.4,
                    max_tokens=800
                )

                plot_analysis.append({
                    'chapter': chapter_name,
                    'analysis': response
                })

                # Extract plot threads from response
                threads = self._extract_plot_threads(response, chapter_name)
                for thread_name, thread_data in threads.items():
                    if thread_name in plot_threads:
                        plot_threads[thread_name]['chapters'].append(chapter_name)
                    else:
                        plot_threads[thread_name] = thread_data
                        plot_threads[thread_name]['chapters'] = [chapter_name]

            except Exception as e:
                print(f"Error analyzing plot for {chapter_name}: {e}")
                continue

        return {
            'plot_analysis': plot_analysis,
            'plot_threads': plot_threads
        }

    def _parse_character_response(self, response: str, chapter_name: str) -> Dict:
        """Parse AI response for character extraction"""
        characters = {}
        lines = response.strip().split('\n')

        current_char = None
        current_data = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith('CHARACTER:'):
                # Save previous character
                if current_char:
                    characters[current_char] = current_data
                # Start new character
                current_char = line.split(':', 1)[1].strip()
                current_data = {
                    'name': current_char,
                    'significance': 'minor',
                    'role': '',
                    'first_appearance': chapter_name
                }
            elif line.startswith('SIGNIFICANCE:') and current_char:
                sig = line.split(':', 1)[1].strip().lower()
                if sig in ['major', 'supporting', 'minor']:
                    current_data['significance'] = sig
            elif line.startswith('ROLE:') and current_char:
                current_data['role'] = line.split(':', 1)[1].strip()

        # Don't forget last character
        if current_char:
            characters[current_char] = current_data

        return characters

    def _parse_location_response(self, response: str, chapter_name: str) -> Dict:
        """Parse AI response for location extraction"""
        locations = {}
        lines = response.strip().split('\n')

        current_loc = None
        current_data = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            if line.startswith('LOCATION:'):
                # Save previous location
                if current_loc:
                    locations[current_loc] = current_data
                # Start new location
                current_loc = line.split(':', 1)[1].strip()
                current_data = {
                    'name': current_loc,
                    'type': 'unknown',
                    'description': '',
                    'first_mention': chapter_name
                }
            elif line.startswith('TYPE:') and current_loc:
                current_data['type'] = line.split(':', 1)[1].strip()
            elif line.startswith('DESCRIPTION:') and current_loc:
                current_data['description'] = line.split(':', 1)[1].strip()

        # Don't forget last location
        if current_loc:
            locations[current_loc] = current_data

        return locations

    def _extract_plot_threads(self, response: str, chapter_name: str) -> Dict:
        """Extract plot thread names from AI response"""
        plot_threads = {}
        lines = response.strip().split('\n')

        for line in lines:
            line = line.strip()
            if line.startswith('PLOT THREADS:'):
                # Extract thread names
                threads_text = line.split(':', 1)[1].strip()
                # Split by commas
                thread_names = [t.strip() for t in threads_text.split(',')]

                for thread_name in thread_names:
                    if thread_name and thread_name.lower() not in ['none', 'n/a', '']:
                        plot_threads[thread_name] = {
                            'name': thread_name,
                            'description': f'Plot thread identified in {chapter_name}'
                        }
                break

        return plot_threads

    def _strip_html(self, html: str) -> str:
        """Strip HTML tags from content"""
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _find_matching_character(self, new_name: str, existing_characters: Dict) -> str:
        """
        Find if a character name matches an existing one
        Returns the existing character name if match found, None otherwise

        Handles cases like:
        - "John Smith" matches "Smith" or "John"
        - "Sarah" matches "Sarah Johnson"
        - "Dr. Watson" matches "Watson"
        """
        new_name_clean = new_name.strip().lower()
        new_parts = new_name_clean.split()

        for existing_name in existing_characters.keys():
            existing_clean = existing_name.strip().lower()
            existing_parts = existing_clean.split()

            # Exact match
            if new_name_clean == existing_clean:
                return existing_name

            # Check if one is a subset of the other
            # e.g., "Smith" vs "John Smith"
            if new_name_clean in existing_clean or existing_clean in new_name_clean:
                return existing_name

            # Check if they share both first AND last name
            # e.g., "John Smith" vs "John A. Smith"
            if len(new_parts) >= 2 and len(existing_parts) >= 2:
                # First name match
                first_match = new_parts[0] == existing_parts[0]
                # Last name match
                last_match = new_parts[-1] == existing_parts[-1]

                if first_match and last_match:
                    return existing_name

            # Check if single name matches first or last of a full name
            # e.g., "John" matches "John Smith" or "Smith" matches "John Smith"
            if len(new_parts) == 1:
                for part in existing_parts:
                    if new_parts[0] == part:
                        return existing_name

            if len(existing_parts) == 1:
                for part in new_parts:
                    if existing_parts[0] == part:
                        return existing_name

        return None


class StoryExtractor:
    """Main class for extracting and analyzing story elements"""

    def __init__(self, parent, db_manager, project_id):
        self.parent = parent
        self.db_manager = db_manager
        self.project_id = project_id
        self.worker = None

    def extract_characters(self):
        """Extract characters from manuscript"""
        from models.project import ItemType

        # Get all chapters and scenes
        chapters = [c.to_dict() for c in self.db_manager.load_items(self.project_id, ItemType.CHAPTER)]
        scenes = [s.to_dict() for s in self.db_manager.load_items(self.project_id, ItemType.SCENE)]

        if not scenes:
            QMessageBox.warning(self.parent, "No Content", "Please write some scenes first.")
            return

        # Show progress dialog
        progress = QProgressDialog("Extracting characters...", "Cancel", 0, 100, self.parent)
        progress.setWindowTitle("Character Analysis")
        progress.setMinimumDuration(0)
        progress.setValue(0)

        # Start worker
        self.worker = ExtractionWorker("characters", chapters, scenes)

        def on_finished(data):
            progress.close()
            characters = data.get('characters', {})

            if not characters:
                QMessageBox.information(self.parent, "No Characters", "No characters were found.")
                return

            # Prepare items for selection dialog
            items = []
            for name, char_data in sorted(characters.items(), key=lambda x: -x[1]['mentions']):
                items.append({
                    'id': name,
                    'display_name': f"{name} ({char_data['significance']}) - {char_data['mentions']} chapters",
                    'description': char_data.get('role', ''),
                    'original_data': char_data
                })

            dialog = SelectionDialog(items, "Select Characters to Import", self.parent)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_characters = dialog.get_selected()
                if selected_characters:
                    # Clear existing characters first
                    self._clear_existing_items('character')
                    # Save new characters
                    self._save_characters(selected_characters)

        def on_error(error):
            progress.close()
            QMessageBox.critical(self.parent, "Error", f"Failed to extract characters:\n\n{error}")

        def on_progress(message, percentage):
            progress.setLabelText(message)
            progress.setValue(percentage)

        self.worker.finished.connect(on_finished)
        self.worker.error.connect(on_error)
        self.worker.progress.connect(on_progress)
        progress.canceled.connect(self.worker.terminate)

        self.worker.start()

    def extract_locations(self):
        """Extract locations from manuscript"""
        from models.project import ItemType

        chapters = [c.to_dict() for c in self.db_manager.load_items(self.project_id, ItemType.CHAPTER)]
        scenes = [s.to_dict() for s in self.db_manager.load_items(self.project_id, ItemType.SCENE)]

        if not scenes:
            QMessageBox.warning(self.parent, "No Content", "Please write some scenes first.")
            return

        progress = QProgressDialog("Extracting locations...", "Cancel", 0, 100, self.parent)
        progress.setWindowTitle("Location Analysis")
        progress.setMinimumDuration(0)
        progress.setValue(0)

        self.worker = ExtractionWorker("locations", chapters, scenes)

        def on_finished(data):
            progress.close()
            locations = data.get('locations', {})

            if not locations:
                QMessageBox.information(self.parent, "No Locations", "No locations were found.")
                return

            # Prepare items for selection dialog
            items = []
            for name, loc_data in sorted(locations.items(), key=lambda x: -x[1]['appearances']):
                items.append({
                    'id': name,
                    'display_name': f"{name} ({loc_data['type']}) - {loc_data['appearances']} chapters",
                    'description': loc_data.get('description', ''),
                    'original_data': loc_data
                })

            dialog = SelectionDialog(items, "Select Locations to Import", self.parent)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                selected_locations = dialog.get_selected()
                if selected_locations:
                    # Clear existing locations first
                    self._clear_existing_items('location')
                    # Save new locations
                    self._save_locations(selected_locations)

        def on_error(error):
            progress.close()
            QMessageBox.critical(self.parent, "Error", f"Failed to extract locations:\n\n{error}")

        def on_progress(message, percentage):
            progress.setLabelText(message)
            progress.setValue(percentage)

        self.worker.finished.connect(on_finished)
        self.worker.error.connect(on_error)
        self.worker.progress.connect(on_progress)
        progress.canceled.connect(self.worker.terminate)

        self.worker.start()

    def analyze_plot(self):
        """Analyze plot structure"""
        from models.project import ItemType

        chapters = [c.to_dict() for c in self.db_manager.load_items(self.project_id, ItemType.CHAPTER)]
        scenes = [s.to_dict() for s in self.db_manager.load_items(self.project_id, ItemType.SCENE)]

        if not scenes:
            QMessageBox.warning(self.parent, "No Content", "Please write some scenes first.")
            return

        progress = QProgressDialog("Analyzing plot...", "Cancel", 0, 100, self.parent)
        progress.setWindowTitle("Plot Analysis")
        progress.setMinimumDuration(0)
        progress.setValue(0)

        self.worker = ExtractionWorker("plot", chapters, scenes)

        def on_finished(data):
            progress.close()
            plot_analysis = data.get('plot_analysis', [])
            plot_threads = data.get('plot_threads', {})

            if not plot_analysis:
                QMessageBox.information(self.parent, "No Analysis", "No plot analysis generated.")
                return

            # Format the report
            report = "\n\n".join([
                f"=== {item['chapter']} ===\n{item['analysis']}"
                for item in plot_analysis
            ])

            # Show in dialog
            msg = QMessageBox(self.parent)
            msg.setWindowTitle("Plot Analysis")
            msg.setText("Chapter-by-Chapter Plot Analysis")
            msg.setDetailedText(report)
            msg.setIcon(QMessageBox.Icon.Information)
            msg.exec()

            # Ask to save plot threads
            if plot_threads:
                # Prepare items for selection dialog
                items = []
                for name, thread_data in sorted(plot_threads.items(), key=lambda x: -len(x[1]['chapters'])):
                    items.append({
                        'id': name,
                        'display_name': f"{name} - {len(thread_data['chapters'])} chapters",
                        'description': thread_data.get('description', ''),
                        'original_data': thread_data
                    })

                dialog = SelectionDialog(items, "Select Plot Threads to Import", self.parent)
                if dialog.exec() == QDialog.DialogCode.Accepted:
                    selected_threads = dialog.get_selected()
                    if selected_threads:
                        # Clear existing plot threads first
                        self._clear_existing_items('plot_thread')
                        # Save new plot threads
                        self._save_plot_threads(selected_threads)

        def on_error(error):
            progress.close()
            QMessageBox.critical(self.parent, "Error", f"Failed to analyze plot:\n\n{error}")

        def on_progress(message, percentage):
            progress.setLabelText(message)
            progress.setValue(percentage)

        self.worker.finished.connect(on_finished)
        self.worker.error.connect(on_error)
        self.worker.progress.connect(on_progress)
        progress.canceled.connect(self.worker.terminate)

        self.worker.start()

    def _save_characters(self, characters: Dict):
        """Save extracted characters to database"""
        from models.project import Character

        saved_count = 0
        for name, data in characters.items():
            char = Character(
                name=name,
                role=data['significance'].title(),
                description=data['role'],
                motivation=f"Appears in: {', '.join(data['chapters'][:3])}"
            )
            self.db_manager.save_item(self.project_id, char)
            saved_count += 1

        QMessageBox.information(
            self.parent,
            "Characters Saved",
            f"Successfully added {saved_count} characters to your project!"
        )

        # Reload the project tree
        if hasattr(self.parent, 'project_tree'):
            self.parent.project_tree.load_project(self.db_manager, self.project_id)

    def _clear_existing_items(self, item_type: str):
        """Clear existing items of a specific type before adding new ones"""
        from models.project import ItemType

        # Map string types to ItemType enum
        type_map = {
            'character': ItemType.CHARACTER,
            'location': ItemType.LOCATION,
            'plot_thread': ItemType.PLOT_THREAD
        }

        if item_type not in type_map:
            return

        # Load all items of this type
        items = self.db_manager.load_items(self.project_id, type_map[item_type])

        # Delete each one
        for item in items:
            self.db_manager.delete_item(item.id)

        print(f"Cleared {len(items)} existing {item_type}s")

    def _save_locations(self, locations: Dict):
        """Save extracted locations to database"""
        from models.project import Location

        saved_count = 0
        for name, data in locations.items():
            loc = Location(
                name=name,
                description=data['description'],
                significance=f"{data['type'].title()} - appears {data['appearances']} times"
            )
            self.db_manager.save_item(self.project_id, loc)
            saved_count += 1

        QMessageBox.information(
            self.parent,
            "Locations Saved",
            f"Successfully added {saved_count} locations to your project!"
        )

        # Reload the project tree
        if hasattr(self.parent, 'project_tree'):
            self.parent.project_tree.load_project(self.db_manager, self.project_id)

    def _save_plot_threads(self, plot_threads: Dict):
        """Save extracted plot threads to database"""
        try:
            print(f"Saving {len(plot_threads)} plot threads...")
            from models.project import PlotThread

            saved_count = 0
            for name, data in plot_threads.items():
                print(f"Creating plot thread: {name}")
                print(f"  Data: {data}")

                # Determine importance based on how many chapters it appears in
                chapter_count = len(data.get('chapters', []))
                if chapter_count >= 10:
                    importance = "main"
                elif chapter_count >= 5:
                    importance = "major"
                else:
                    importance = "minor"

                # Create plot thread with correct fields
                thread = PlotThread(
                    name=name,
                    description=data.get('description', f"Plot thread identified from story analysis"),
                    importance=importance,
                    resolution="ongoing",
                    notes=f"Appears in {chapter_count} chapters: {', '.join(data.get('chapters', [])[:5])}"
                )

                print(f"  Saving to database...")
                self.db_manager.save_item(self.project_id, thread)
                saved_count += 1
                print(f"  Saved successfully")

            print(f"All {saved_count} plot threads saved")

            QMessageBox.information(
                self.parent,
                "Plot Threads Saved",
                f"Successfully added {saved_count} plot threads to your project!"
            )

            # Reload the project tree
            print("Reloading project tree...")
            if hasattr(self.parent, 'project_tree'):
                self.parent.project_tree.load_project(self.db_manager, self.project_id)
            print("Done!")

        except Exception as e:
            print(f"ERROR in _save_plot_threads: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(
                self.parent,
                "Save Error",
                f"Failed to save plot threads:\n\n{str(e)}"
            )