"""
Comprehensive Analysis System - Chapter-by-chapter with tracked insights
"""

from PyQt6.QtWidgets import QMessageBox, QProgressDialog, QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel, QScrollArea, QWidget, QHBoxLayout
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtGui import QFont
from ai_manager import ai_manager
from typing import List, Dict, Any
import re
import json


class ComprehensiveAnalysisWorker(QThread):
    """Worker that analyzes chapter by chapter, then compiles final report"""
    progress = pyqtSignal(str, int)  # message, percentage
    finished = pyqtSignal(dict)  # Complete analysis with tracked issues
    error = pyqtSignal(str)

    def __init__(self, analysis_type: str, chapters: List[Dict], scenes: List[Dict]):
        super().__init__()
        self.analysis_type = analysis_type
        self.chapters = chapters
        self.scenes = scenes

    def run(self):
        try:
            if self.analysis_type == "timeline":
                result = self._analyze_timeline_comprehensive()
            elif self.analysis_type == "consistency":
                result = self._analyze_consistency_comprehensive()
            elif self.analysis_type == "style":
                result = self._analyze_style_comprehensive()
            elif self.analysis_type == "pacing":
                result = self._analyze_pacing_comprehensive()
            else:
                result = {}

            self.finished.emit(result)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))

    def _analyze_pacing_comprehensive(self):
        """Analyze book pacing and tension chapter by chapter"""
        from analyzer import AnalysisEngine, ChapterData
        from ai_manager import ai_manager
        
        engine = AnalysisEngine(ai_manager)
        all_pacing_data = []
        total_chapters = len(self.chapters)
        
        for idx, chapter in enumerate(self.chapters):
            chapter_name = chapter.get('name', f'Chapter {idx+1}')
            self.progress.emit(f"Analyzing pacing in {chapter_name}...", int((idx / total_chapters) * 90))
            
            # Get scenes for this chapter
            chapter_scenes = [s for s in self.scenes if s.get('parent_id') == chapter.get('id')]
            if not chapter_scenes:
                continue
                
            # Create ChapterData for engine
            # We need to format scenes as expected by AnalysisEngine
            cd = ChapterData(
                id=chapter.get('id'),
                name=chapter_name,
                scenes=chapter_scenes
            )
            
            try:
                result = engine.analyze_chapter_pacing(cd)
                payload = result.get('payload', {})
                chapter_pacing = payload.get('pacing_data', [])
                all_pacing_data.extend(chapter_pacing)
            except Exception as e:
                print(f"Error analyzing pacing for {chapter_name}: {e}")

        # Format results for consistent handling
        data = {
            'type': 'pacing',
            'payload': {'pacing_data': all_pacing_data},
            'summary': f"Analyzed pacing for {len(self.chapters)} chapters.",
            'final_report': "Pacing Heatmap data generated chapter by chapter."
        }
        
        self.progress.emit("Pacing analysis complete", 100)
        return data

    def _analyze_timeline_comprehensive(self):
        """Analyze timeline chapter by chapter, then compile"""
        chapter_analyses = []
        all_issues = []
        total_chapters = len(self.chapters)

        for idx, chapter in enumerate(self.chapters):
            chapter_name = chapter.get('name', f'Chapter {idx+1}')
            print(f"Timeline: Analyzing chapter {idx+1}/{total_chapters}: {chapter_name}")
            self.progress.emit(f"Analyzing timeline in {chapter_name}...", int((idx / total_chapters) * 70))

            # Get scenes for this chapter
            chapter_scenes = [s for s in self.scenes if s.get('parent_id') == chapter.get('id')]
            if not chapter_scenes:
                continue

            # Build scene text
            scene_text = self._build_scene_text(chapter_scenes)
            print(f"  → Sending {len(scene_text)} characters from {len(chapter_scenes)} scenes")

            # Analyze this chapter
            prompt = f"""Analyze timeline issues in this chapter:

Chapter: {chapter_name}

{scene_text}

Identify SPECIFIC timeline issues:
- Time contradictions
- Impossible sequences
- Character location conflicts
- Day/night inconsistencies

Format EACH issue as:
ISSUE: [Brief description]
LOCATION: Scene name or "Multiple scenes"
SEVERITY: Critical/Major/Minor
DETAIL: [Explanation]

---
(Use --- to separate issues)"""

            try:
                response = ai_manager.call_api(
                    messages=[{"role": "user", "content": prompt}],
                    system_message="You are a timeline continuity expert.",
                    temperature=0.3,
                    max_tokens=8000
                )

                chapter_analyses.append({
                    'chapter': chapter_name,
                    'analysis': response
                })

                # Parse issues
                issues = self._parse_issues(response, chapter_name, 'timeline', chapter_scenes)

                all_issues.extend(issues)

            except Exception as e:
                print(f"Error analyzing {chapter_name}: {e}")

        # Compile final report
        self.progress.emit("Compiling final timeline report...", 80)
        final_report = self._compile_timeline_report(chapter_analyses, all_issues)

        return {
            'type': 'timeline',
            'chapter_analyses': chapter_analyses,
            'issues': all_issues,
            'final_report': final_report,
            'summary': f"Found {len(all_issues)} timeline issues across {len(chapter_analyses)} chapters"
        }

    def _analyze_consistency_comprehensive(self):
        """Analyze consistency chapter by chapter"""
        chapter_analyses = []
        all_issues = []
        total_chapters = len(self.chapters)

        # Also get character info for context
        character_names = set()

        for idx, chapter in enumerate(self.chapters):
            chapter_name = chapter.get('name', f'Chapter {idx+1}')
            print(f"Consistency: Analyzing chapter {idx+1}/{total_chapters}: {chapter_name}")
            self.progress.emit(f"Checking consistency in {chapter_name}...", int((idx / total_chapters) * 70))

            chapter_scenes = [s for s in self.scenes if s.get('parent_id') == chapter.get('id')]
            if not chapter_scenes:
                continue

            scene_text = self._build_scene_text(chapter_scenes)

            prompt = f"""Check for story consistency issues in this chapter:

Chapter: {chapter_name}

{scene_text}

Identify:
- Character behavior inconsistencies
- Contradictions with earlier events
- Forgotten plot points
- Continuity errors

Format EACH issue as:
ISSUE: [Brief description]
LOCATION: Scene name
SEVERITY: Critical/Major/Minor
DETAIL: [Explanation]

---"""

            try:
                response = ai_manager.call_api(
                    messages=[{"role": "user", "content": prompt}],
                    system_message="You are a story consistency expert.",
                    temperature=0.3,
                    max_tokens=8000
                )

                chapter_analyses.append({
                    'chapter': chapter_name,
                    'analysis': response
                })

                issues = self._parse_issues(response, chapter_name, 'consistency', chapter_scenes)
                all_issues.extend(issues)

            except Exception as e:
                print(f"Error analyzing {chapter_name}: {e}")

        self.progress.emit("Compiling consistency report...", 80)
        final_report = self._compile_consistency_report(chapter_analyses, all_issues)

        return {
            'type': 'consistency',
            'chapter_analyses': chapter_analyses,
            'issues': all_issues,
            'final_report': final_report,
            'summary': f"Found {len(all_issues)} consistency issues"
        }

    def _analyze_style_comprehensive(self):
        """Analyze writing style across chapters"""
        chapter_analyses = []
        all_issues = []
        total_chapters = len(self.chapters)

        for idx, chapter in enumerate(self.chapters):  # Analyze ALL chapters
            chapter_name = chapter.get('name', f'Chapter {idx+1}')
            print(f"Style: Analyzing chapter {idx+1}/{total_chapters}: {chapter_name}")
            self.progress.emit(f"Analyzing style in {chapter_name}...", int((idx / total_chapters) * 70))

            chapter_scenes = [s for s in self.scenes if s.get('parent_id') == chapter.get('id')]
            if not chapter_scenes:
                continue

            # Get actual prose samples
            prose_samples = []
            for scene in chapter_scenes[:3]:  # First 3 scenes
                content = scene.get('content', '')
                text = re.sub(r'<[^>]+>', ' ', content)
                prose_samples.append(text[:4000])

            sample_text = "\n\n---\n\n".join(prose_samples)

            prompt = f"""Analyze writing style in this chapter:

Chapter: {chapter_name}

{sample_text}

Identify specific style issues and strengths:
- Sentence variety
- Show vs Tell
- Dialogue quality
- Pacing
- Voice consistency

Format observations as:
OBSERVATION: [What you noticed]
LOCATION: Scene name or "Throughout chapter"
TYPE: Strength/Weakness
DETAIL: [Specific example or explanation]

---"""

            try:
                response = ai_manager.call_api(
                    messages=[{"role": "user", "content": prompt}],
                    system_message="You are a professional writing coach.",
                    temperature=0.4,
                    max_tokens=2000
                )

                chapter_analyses.append({
                    'chapter': chapter_name,
                    'analysis': response
                })

                issues = self._parse_style_observations(response, chapter_name)
                all_issues.extend(issues)

            except Exception as e:
                print(f"Error analyzing {chapter_name}: {e}")

        self.progress.emit("Compiling style report...", 80)
        final_report = self._compile_style_report(chapter_analyses, all_issues)

        return {
            'type': 'style',
            'chapter_analyses': chapter_analyses,
            'issues': all_issues,
            'final_report': final_report,
            'summary': f"Analyzed {len(chapter_analyses)} chapters for style patterns"
        }

    def _build_scene_text(self, scenes: List[Dict]) -> str:
        """Build readable scene text for analysis - uses FULL content"""
        scene_parts = []
        MAX_CHARS_PER_SCENE = 20000
        for scene in scenes:
            name = scene.get('name', 'Untitled')

            # ALWAYS use full content for analysis, not summaries
            content = scene.get('content', '')
            if content:
                # Strip HTML but keep full text
                text = re.sub(r'<[^>]+>', ' ', content)
                text = re.sub(r'\s+', ' ', text).strip()
                # Use up to 5000 characters per scene for thorough analysis
                text = text[:MAX_CHARS_PER_SCENE] if text else "No content"
            else:
                # Fallback to summary only if there's literally no content
                text = scene.get('summary', 'No content')

            scene_parts.append(f"SCENE: {name}\n{text}")

        return "\n\n".join(scene_parts)

    def _parse_issues(self, response: str, chapter_name: str, issue_type: str, chapter_scenes: List[Dict]) -> List[
        Dict]:
        """Parse AI response into structured issues and attach scene_id when possible"""
        issues = []
        issue_blocks = response.split('---')

        # Build fast lookup: scene name -> scene dict
        scenes_by_name = {}
        for s in chapter_scenes or []:
            name = (s.get("name") or "").strip()
            if name:
                scenes_by_name[name.lower()] = s  # case-insensitive

        for block in issue_blocks:
            if not block.strip():
                continue

            issue_data = {
                'chapter': chapter_name,
                'type': issue_type,
                'issue': '',
                'location': '',
                'severity': 'Minor',
                'detail': ''
            }

            lines = block.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('ISSUE:'):
                    issue_data['issue'] = line.split(':', 1)[1].strip()
                elif line.startswith('LOCATION:'):
                    issue_data['location'] = line.split(':', 1)[1].strip()
                elif line.startswith('SEVERITY:'):
                    issue_data['severity'] = line.split(':', 1)[1].strip()
                elif line.startswith('DETAIL:'):
                    issue_data['detail'] = line.split(':', 1)[1].strip()

            if not issue_data['issue']:
                continue

            # ✅ Attach scene_id for timeline/consistency when LOCATION names a single scene
            location = (issue_data.get("location") or "").strip()
            if issue_type in {"timeline", "consistency"}:
                # Don't assign scene_id for clearly multi-scene locations
                multi_markers = {"multiple scenes", "throughout chapter", "unknown", "entire chapter"}
                if location and location.lower() not in multi_markers:
                    scene = scenes_by_name.get(location.lower())
                    if scene and scene.get("id"):
                        issue_data["scene_id"] = scene["id"]
                    else:
                        # If AI slightly mismatches names, you can optionally add a fallback here later
                        issue_data["scene_id"] = None
                else:
                    issue_data["scene_id"] = None

            issues.append(issue_data)

        return issues

    def _parse_style_observations(self, response: str, chapter_name: str) -> List[Dict]:
        """Parse style observations"""
        observations = []
        obs_blocks = response.split('---')

        for block in obs_blocks:
            if not block.strip():
                continue

            obs_data = {
                'chapter': chapter_name,
                'type': 'style',
                'issue': '',
                'location': '',
                'severity': 'Observation',
                'detail': '',
                'is_strength': False
            }

            lines = block.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line.startswith('OBSERVATION:'):
                    obs_data['issue'] = line.split(':', 1)[1].strip()
                elif line.startswith('LOCATION:'):
                    obs_data['location'] = line.split(':', 1)[1].strip()
                elif line.startswith('TYPE:'):
                    type_val = line.split(':', 1)[1].strip()
                    obs_data['is_strength'] = 'strength' in type_val.lower()
                    obs_data['severity'] = 'Strength' if obs_data['is_strength'] else 'Suggestion'
                elif line.startswith('DETAIL:'):
                    obs_data['detail'] = line.split(':', 1)[1].strip()

            if obs_data['issue']:
                observations.append(obs_data)

        return observations

    def _compile_timeline_report(self, chapter_analyses: List[Dict], issues: List[Dict]) -> str:
        """Compile final timeline report from all chapters"""
        if not issues:
            return "TIMELINE ANALYSIS SUMMARY\n\nNo timeline issues found! ✓"

        critical = [i for i in issues if i.get('severity') == 'Critical']
        major = [i for i in issues if i.get('severity') == 'Major']
        minor = [i for i in issues if i.get('severity') == 'Minor']

        report = f"""TIMELINE ANALYSIS SUMMARY

Total Issues Found: {len(issues)}
- Critical: {len(critical)}
- Major: {len(major)}
- Minor: {len(minor)}

CRITICAL ISSUES:
"""
        for issue in critical:
            report += f"\n• {issue['issue']} ({issue['chapter']} - {issue['location']})\n  {issue['detail']}\n"

        report += "\n\nMAJOR ISSUES:\n"
        for issue in major[:10]:
            report += f"\n• {issue['issue']} ({issue['chapter']} - {issue['location']})\n"

        return report

    def _compile_consistency_report(self, chapter_analyses: List[Dict], issues: List[Dict]) -> str:
        """Compile consistency report"""
        if not issues:
            return "CONSISTENCY ANALYSIS SUMMARY\n\nNo consistency issues found! ✓"

        critical = [i for i in issues if i.get('severity') == 'Critical']

        report = f"""CONSISTENCY ANALYSIS SUMMARY

Total Issues: {len(issues)}
Critical Issues: {len(critical)}

TOP ISSUES:
"""
        for issue in issues[:15]:
            report += f"\n• [{issue['severity']}] {issue['issue']}\n  Location: {issue['chapter']} - {issue['location']}\n  {issue['detail']}\n"

        return report

    def _compile_style_report(self, chapter_analyses: List[Dict], observations: List[Dict]) -> str:
        """Compile style report"""
        if not observations:
            return "WRITING STYLE ANALYSIS\n\nNo style observations generated."

        strengths = [o for o in observations if o.get('is_strength', False)]
        suggestions = [o for o in observations if not o.get('is_strength', False)]

        report = f"""WRITING STYLE ANALYSIS

Strengths Identified: {len(strengths)}
Areas for Improvement: {len(suggestions)}

STRENGTHS:
"""
        for strength in strengths[:10]:
            report += f"\n• {strength['issue']} ({strength['chapter']})\n"

        report += "\n\nSUGGESTIONS:\n"
        for suggestion in suggestions[:15]:
            report += f"\n• {suggestion['issue']} ({suggestion['chapter']} - {suggestion['location']})\n  {suggestion['detail']}\n"

        return report


class StoryInsightsDatabase:
    """Store and manage story insights"""

    def __init__(self, db_manager, project_id):
        self.db_manager = db_manager
        self.project_id = project_id

    def clear_analysis(self, analysis_type: str):
        """Clear previous analysis of this type"""
        import json
        from pathlib import Path

        insights_file = Path(f".insights_{self.project_id}_{analysis_type}.json")
        if insights_file.exists():
            insights_file.unlink()
            print(f"Cleared previous {analysis_type} analysis")

    def save_analysis(self, analysis_data: Dict):
        """Save analysis results with tracked issues"""
        # Store as JSON in project settings or separate table
        analysis_type = analysis_data['type']

        # Clear previous analysis first
        self.clear_analysis(analysis_type)

        # For now, store in memory/file
        # In future, add insights table to database
        import json
        from pathlib import Path

        insights_file = Path(f".insights_{self.project_id}_{analysis_type}.json")
        with open(insights_file, 'w') as f:
            json.dump(analysis_data, f, indent=2)

        print(f"Saved {len(analysis_data.get('issues', []))} {analysis_type} insights")

    def load_analysis(self, analysis_type: str) -> Dict:
        """Load saved analysis"""
        import json
        from pathlib import Path

        insights_file = Path(f".insights_{self.project_id}_{analysis_type}.json")
        if insights_file.exists():
            with open(insights_file, 'r') as f:
                return json.load(f)
        return None