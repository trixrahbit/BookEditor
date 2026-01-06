"""
Clean AI Integration - Uses centralized AI manager and prompts
"""

from PyQt6.QtWidgets import QMessageBox, QProgressDialog, QInputDialog
from PyQt6.QtCore import QThread, pyqtSignal
from ai_manager import ai_manager
from ai_prompts import AIPrompts, PromptParser
from typing import Dict, Any, List
from comprehensive_analysis import ComprehensiveAnalysisWorker, StoryInsightsDatabase
from story_insights_viewer import StoryInsightsViewer

class AIWorker(QThread):
    """Worker thread for AI operations"""
    finished = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, operation_type: str, **kwargs):
        super().__init__()
        self.operation_type = operation_type
        self.kwargs = kwargs

    def run(self):
        try:
            if self.operation_type == "rewrite":
                result = self._rewrite_text()
            elif self.operation_type == "fill_scene":
                result = self._fill_scene_properties()
            elif self.operation_type == "consistency":
                result = self._check_consistency()
            elif self.operation_type == "analyze_characters":
                result = self._analyze_characters()
            elif self.operation_type == "analyze_plot":
                result = self._analyze_plot()
            elif self.operation_type == "analyze_style":
                result = self._analyze_style()
            elif self.operation_type == "analyze_timeline":
                result = self._analyze_timeline()
            else:
                result = None

            self.finished.emit(result)
        except Exception as e:
            self.error.emit(str(e))

    def _rewrite_text(self):
        """Rewrite text using AI"""
        try:
            text = self.kwargs['text']
            instruction = self.kwargs['instruction']

            print(f"Rewrite worker started: {len(text)} chars, instruction: {instruction[:50]}...")

            self.progress.emit("Rewriting text...")

            # Get prompt
            prompt = AIPrompts.rewrite_text(text, instruction)

            print("Calling AI manager...")

            # Call API
            response = ai_manager.call_api(
                messages=[{"role": "user", "content": prompt["user"]}],
                system_message=prompt["system"],
                temperature=0.8
            )

            print(f"Got response: {len(response)} chars")

            return response.strip()
        except Exception as e:
            print(f"Error in _rewrite_text: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    def _fill_scene_properties(self):
        """Fill scene properties using AI"""
        scene = self.kwargs['scene']

        self.progress.emit("Analyzing scene...")

        # Get prompt
        prompt = AIPrompts.fill_scene_properties(scene.content, scene.name)

        # Call API
        response = ai_manager.call_api(
            messages=[{"role": "user", "content": prompt["user"]}],
            system_message=prompt["system"],
            temperature=0.5,
            max_tokens=500
        )

        # Parse response
        properties = PromptParser.parse_scene_properties(response)
        return properties

    def _check_consistency(self):
        """Check story consistency"""
        scenes = self.kwargs['scenes']
        characters = self.kwargs['characters']

        self.progress.emit("Checking consistency...")

        # Get prompt
        prompt = AIPrompts.check_consistency(scenes, characters)

        # Call API
        response = ai_manager.call_api(
            messages=[{"role": "user", "content": prompt["user"]}],
            system_message=prompt["system"],
            temperature=0.3,
            max_tokens=1500
        )

        return response

    def _analyze_characters(self):
        """Analyze characters"""
        scenes = self.kwargs['scenes']
        characters = self.kwargs['characters']

        self.progress.emit("Analyzing characters...")

        prompt = AIPrompts.analyze_characters(scenes, characters)

        response = ai_manager.call_api(
            messages=[{"role": "user", "content": prompt["user"]}],
            system_message=prompt["system"]
        )

        return response

    def _analyze_plot(self):
        """Analyze plot"""
        scenes = self.kwargs['scenes']

        self.progress.emit("Analyzing plot...")

        prompt = AIPrompts.analyze_plot(scenes)

        response = ai_manager.call_api(
            messages=[{"role": "user", "content": prompt["user"]}],
            system_message=prompt["system"]
        )

        return response

    def _analyze_style(self):
        """Analyze writing style"""
        scenes = self.kwargs['scenes']

        self.progress.emit("Analyzing writing style...")

        prompt = AIPrompts.analyze_style(scenes)

        response = ai_manager.call_api(
            messages=[{"role": "user", "content": prompt["user"]}],
            system_message=prompt["system"]
        )

        return response

    def _analyze_timeline(self):
        """Analyze timeline consistency"""
        scenes = self.kwargs['scenes']

        self.progress.emit("Analyzing timeline...")

        # Build scene timeline
        scene_summaries = []
        for i, scene in enumerate(scenes[:30], 1):  # Limit to 30 scenes
            summary = scene.get('summary', '')
            if not summary:
                # Use first 200 chars of content
                import re
                content = scene.get('content', '')
                text = re.sub(r'<[^>]+>', ' ', content)
                summary = text[:200]

            scene_summaries.append(f"{i}. {scene.get('name', 'Untitled')}: {summary}")

        scenes_text = "\n".join(scene_summaries)

        prompt = f"""Analyze the timeline for consistency issues:

SCENES IN ORDER:
{scenes_text}

Check for:
1. TIME CONTRADICTIONS: Events happening in impossible order
2. CHARACTER PRESENCE: Characters being in two places at once
3. TRAVEL TIME: Unrealistic travel between locations
4. CONTINUITY: Day/night cycles, seasons, dates mentioned
5. PACING: Time moving too fast or too slow

Provide a detailed report of any timeline issues found."""

        response = ai_manager.call_api(
            messages=[{"role": "user", "content": prompt}],
            system_message="You are a continuity expert analyzing story timelines.",
            temperature=0.3
        )

        return response

class AIFeatures:
    """Clean AI features class"""

    def __init__(self, parent, db_manager, project_id):
        self.parent = parent
        self.db_manager = db_manager
        self.project_id = project_id
        self.worker = None
        self.insights_db = StoryInsightsDatabase(db_manager, project_id)

    def check_configured(self) -> bool:
        """Check if AI is configured"""
        if not ai_manager.is_configured():
            QMessageBox.warning(
                self.parent,
                "AI Not Configured",
                "Please configure Azure OpenAI credentials in Settings:\n\n"
                "1. Go to Settings (Ctrl+,)\n"
                "2. Open Azure OpenAI tab\n"
                "3. Enter your API credentials\n"
                "4. Click Test Connection"
            )
            return False
        return True

    def rewrite_text(self, text: str, callback=None):
        """Rewrite selected text"""
        if not self.check_configured():
            return

        # Ask for instruction
        instruction, ok = QInputDialog.getText(
            self.parent,
            "Rewrite with AI",
            "How should I rewrite this text?\n\n"
            "Examples:\n"
            "• Make it more dramatic\n"
            "• Simplify and clarify\n"
            "• Add more sensory detail\n"
            "• Change tone to suspenseful\n\n"
            "Your instruction:",
            text="Improve and enhance this text"
        )

        if not ok or not instruction:
            return

        # Show progress
        progress = QProgressDialog("Rewriting...", "Cancel", 0, 0, self.parent)
        progress.setWindowTitle("AI Rewrite")
        progress.setMinimumDuration(0)
        progress.setValue(0)

        # Start worker
        self.worker = AIWorker("rewrite", text=text, instruction=instruction)

        def on_finished(rewritten):
            progress.close()
            if rewritten and callback:
                callback(rewritten)

        def on_error(error):
            progress.close()
            QMessageBox.critical(
                self.parent,
                "AI Error",
                f"Failed to rewrite text:\n\n{error}"
            )

        self.worker.finished.connect(on_finished)
        self.worker.error.connect(on_error)
        self.worker.progress.connect(progress.setLabelText)
        progress.canceled.connect(self.worker.terminate)

        self.worker.start()

    def fill_scene_properties(self, scene_id: str, callback=None):
        """Auto-fill scene properties"""
        if not self.check_configured():
            return

        scene = self.db_manager.load_item(scene_id)
        if not scene or not scene.content:
            QMessageBox.warning(
                self.parent,
                "No Content",
                "This scene has no content to analyze."
            )
            return

        # Show progress
        progress = QProgressDialog("Analyzing scene...", "Cancel", 0, 0, self.parent)
        progress.setWindowTitle("AI Analysis")
        progress.setMinimumDuration(0)
        progress.setValue(0)

        # Start worker
        self.worker = AIWorker("fill_scene", scene=scene)

        def on_finished(properties):
            progress.close()
            if properties:
                # Update scene
                if 'summary' in properties:
                    scene.summary = properties['summary']
                if 'goal' in properties:
                    scene.goal = properties['goal']
                if 'conflict' in properties:
                    scene.conflict = properties['conflict']
                if 'outcome' in properties:
                    scene.outcome = properties['outcome']

                self.db_manager.save_item(self.project_id, scene)

                # Call callback BEFORE message box so UI updates immediately
                if callback:
                    callback()

                QMessageBox.information(
                    self.parent,
                    "Success",
                    "Scene properties updated!\n\n"
                    "Summary, Goal, Conflict, and Outcome have been filled in.\n"
                    "Check the Properties panel to review."
                )
            else:
                QMessageBox.warning(
                    self.parent,
                    "AI Warning",
                    "The AI generated a response, but it couldn't be parsed into scene properties.\n"
                    "Try again or check your scene content."
                )

        def on_error(error):
            progress.close()
            QMessageBox.critical(
                self.parent,
                "AI Error",
                f"Failed to analyze scene:\n\n{error}"
            )

        self.worker.finished.connect(on_finished)
        self.worker.error.connect(on_error)
        self.worker.progress.connect(progress.setLabelText)
        progress.canceled.connect(self.worker.terminate)

        self.worker.start()

    def check_consistency(self):
        """Check story consistency chapter by chapter"""
        if not self.check_configured():
            return

        # Get data
        from models.project import ItemType
        chapters = [c.to_dict() for c in self.db_manager.load_items(self.project_id, ItemType.CHAPTER)]
        scenes = [s.to_dict() for s in self.db_manager.load_items(self.project_id, ItemType.SCENE)]

        if not scenes:
            QMessageBox.warning(
                self.parent,
                "No Content",
                "Please write some scenes before checking consistency."
            )
            return

        # Show progress
        progress = QProgressDialog("Checking consistency chapter by chapter...", "Cancel", 0, 100, self.parent)
        progress.setWindowTitle("Consistency Check")
        progress.setMinimumDuration(0)
        progress.setValue(0)

        # Start comprehensive worker
        self.worker = ComprehensiveAnalysisWorker("consistency", chapters, scenes)

        def on_finished(data):
            progress.close()

            # Save to insights database
            self.insights_db.save_analysis(data)

            # Show results
            QMessageBox.information(
                self.parent,
                "Consistency Check Complete",
                data.get('summary', 'Analysis complete')
            )

            # Open Story Insights viewer
            self.show_story_insights()

        def on_error(error):
            progress.close()
            QMessageBox.critical(
                self.parent,
                "Error",
                f"Failed to check consistency:\n\n{error}"
            )

        def on_progress(message, percentage):
            progress.setLabelText(message)
            progress.setValue(percentage)

        self.worker.finished.connect(on_finished)
        self.worker.error.connect(on_error)
        self.worker.progress.connect(on_progress)
        progress.canceled.connect(self.worker.terminate)

        self.worker.start()

    def analyze_timeline(self):
        """Analyze story timeline chapter by chapter"""
        if not self.check_configured():
            return

        # Get data
        from models.project import ItemType
        chapters = [c.to_dict() for c in self.db_manager.load_items(self.project_id, ItemType.CHAPTER)]
        scenes = [s.to_dict() for s in self.db_manager.load_items(self.project_id, ItemType.SCENE)]

        if not scenes:
            QMessageBox.warning(
                self.parent,
                "No Content",
                "Please write some scenes before analyzing timeline."
            )
            return

        # Show progress
        progress = QProgressDialog("Analyzing timeline chapter by chapter...", "Cancel", 0, 100, self.parent)
        progress.setWindowTitle("Timeline Analysis")
        progress.setMinimumDuration(0)
        progress.setValue(0)

        # Start comprehensive worker
        self.worker = ComprehensiveAnalysisWorker("timeline", chapters, scenes)

        def on_finished(data):
            progress.close()

            # Save to insights database
            self.insights_db.save_analysis(data)

            # Show results
            QMessageBox.information(
                self.parent,
                "Timeline Analysis Complete",
                data.get('summary', 'Analysis complete')
            )

            # Open Story Insights viewer
            self.show_story_insights()

        def on_error(error):
            progress.close()
            QMessageBox.critical(
                self.parent,
                "Error",
                f"Failed to analyze timeline:\n\n{error}"
            )

        def on_progress(message, percentage):
            progress.setLabelText(message)
            progress.setValue(percentage)

        self.worker.finished.connect(on_finished)
        self.worker.error.connect(on_error)
        self.worker.progress.connect(on_progress)
        progress.canceled.connect(self.worker.terminate)

        self.worker.start()

    def analyze_writing_style(self):
        """Analyze writing style chapter by chapter"""
        if not self.check_configured():
            return

        # Get data
        from models.project import ItemType
        chapters = [c.to_dict() for c in self.db_manager.load_items(self.project_id, ItemType.CHAPTER)]
        scenes = [s.to_dict() for s in self.db_manager.load_items(self.project_id, ItemType.SCENE)]

        if not scenes:
            QMessageBox.warning(
                self.parent,
                "No Content",
                "Please write some scenes before analyzing style."
            )
            return

        # Show progress
        progress = QProgressDialog("Analyzing writing style chapter by chapter...", "Cancel", 0, 100, self.parent)
        progress.setWindowTitle("Style Analysis")
        progress.setMinimumDuration(0)
        progress.setValue(0)

        # Start comprehensive worker
        self.worker = ComprehensiveAnalysisWorker("style", chapters, scenes)

        def on_finished(data):
            progress.close()

            # Save to insights database
            self.insights_db.save_analysis(data)

            # Show results
            QMessageBox.information(
                self.parent,
                "Style Analysis Complete",
                data.get('summary', 'Analysis complete')
            )

            # Open Story Insights viewer
            self.show_story_insights()

        def on_error(error):
            progress.close()
            QMessageBox.critical(
                self.parent,
                "Error",
                f"Failed to analyze style:\n\n{error}"
            )

        def on_progress(message, percentage):
            progress.setLabelText(message)
            progress.setValue(percentage)

        self.worker.finished.connect(on_finished)
        self.worker.error.connect(on_error)
        self.worker.progress.connect(on_progress)
        progress.canceled.connect(self.worker.terminate)

        self.worker.start()

    def show_story_insights(self):
        """Show the Story Insights viewer with all saved analyses"""
        from story_insights_viewer import StoryInsightsViewer

        # Pass db_manager and project_id for AI Fix feature
        viewer = StoryInsightsViewer(self.parent, self.db_manager, self.project_id)

        # Load saved analyses
        timeline_data = self.insights_db.load_analysis('timeline')
        if timeline_data:
            viewer.load_timeline_data(timeline_data)

        consistency_data = self.insights_db.load_analysis('consistency')
        if consistency_data:
            viewer.load_consistency_data(consistency_data)

        style_data = self.insights_db.load_analysis('style')
        if style_data:
            viewer.load_style_data(style_data)

        viewer.exec()