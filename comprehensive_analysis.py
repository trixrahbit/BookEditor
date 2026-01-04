"""
Comprehensive Analysis System - Chapter-by-chapter with tracked insights
"""

from PyQt6.QtWidgets import QMessageBox, QProgressDialog, QDialog, QVBoxLayout, QTextEdit, QPushButton, QLabel, \
    QScrollArea, QWidget, QHBoxLayout
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
            else:
                result = {}

            self.finished.emit(result)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))

    def _analyze_timeline_comprehensive(self):
        """Analyze timeline chapter by chapter, then compile"""
        chapter_analyses = []
        all_issues = []
        total_chapters = len(self.chapters)

        for idx, chapter in enumerate(self.chapters):
            chapter_name = chapter.get('name', f'Chapter {idx + 1}')
            self.progress.emit(f"Analyzing timeline in {chapter_name}...", int((idx / total_chapters) * 70))

            # Get scenes for this chapter
            chapter_scenes = [s for s in self.scenes if s.get('parent_id') == chapter.get('id')]
            if not chapter_scenes:
                continue

            # Build scene text
            scene_text = self._build_scene_text(chapter_scenes)

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
                    max_tokens=1000
                )

                chapter_analyses.append({
                    'chapter': chapter_name,
                    'analysis': response
                })

                # Parse issues
                issues = self._parse_issues(response, chapter_name, 'timeline')
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
            chapter_name = chapter.get('name', f'Chapter {idx + 1}')
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
                    max_tokens=1000
                )

                chapter_analyses.append({
                    'chapter': chapter_name,
                    'analysis': response
                })

                issues = self._parse_issues(response, chapter_name, 'consistency')
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

        for idx, chapter in enumerate(self.chapters[:10]):  # Limit to 10 chapters for style
            chapter_name = chapter.get('name', f'Chapter {idx + 1}')
            self.progress.emit(f"Analyzing style in {chapter_name}...", int((idx / min(10, total_chapters)) * 70))

            chapter_scenes = [s for s in self.scenes if s.get('parent_id') == chapter.get('id')]
            if not chapter_scenes:
                continue

            # Get actual prose samples
            prose_samples = []
            for scene in chapter_scenes[:3]:  # First 3 scenes
                content = scene.get('content', '')
                text = re.sub(r'<[^>]+>', ' ', content)
                prose_samples.append(text[:800])

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
                    max_tokens=1000
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
        """Build readable scene text for analysis"""
        scene_parts = []
        for scene in scenes:
            name = scene.get('name', 'Untitled')
            summary = scene.get('summary', '')
            if not summary:
                content = scene.get('content', '')
                text = re.sub(r'<[^>]+>', ' ', content)
                summary = text[:400]

            scene_parts.append(f"SCENE: {name}\n{summary}")

        return "\n\n".join(scene_parts)

    def _parse_issues(self, response: str, chapter_name: str, issue_type: str) -> List[Dict]:
        """Parse AI response into structured issues"""
        issues = []
        issue_blocks = response.split('---')

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

            if issue_data['issue']:
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

    def _compile_timeline_report(self, chapter_analyses: List[Dict[str, Any]], issues: List[Any]) -> str:
        """Compile final timeline report from all chapters (defensive against bad issue shapes)."""

        # Keep only dict-like issues
        issues_dicts: List[Dict[str, Any]] = [i for i in (issues or []) if isinstance(i, dict)]

        def sev(i: Dict[str, Any]) -> str:
            return str(i.get("severity", "Minor")).strip() or "Minor"

        critical = [i for i in issues_dicts if sev(i).lower() == "critical"]
        major = [i for i in issues_dicts if sev(i).lower() == "major"]
        minor = [i for i in issues_dicts if sev(i).lower() == "minor"]

        # Anything with unknown severity → treat as Minor (or put in separate bucket if you prefer)
        unknown = [i for i in issues_dicts if sev(i).lower() not in {"critical", "major", "minor"}]
        minor.extend(unknown)

        def fmt_issue(i: Dict[str, Any], include_detail: bool) -> str:
            title = str(i.get("issue", "Unspecified issue")).strip()
            chapter = str(i.get("chapter", "Unknown chapter")).strip()
            location = str(i.get("location", "Unknown location")).strip()
            detail = str(i.get("detail", "")).strip()

            line = f"• {title} ({chapter} - {location})"
            if include_detail and detail:
                line += f"\n  {detail}"
            return line

        report = (
            "TIMELINE ANALYSIS SUMMARY\n\n"
            f"Total Issues Found: {len(issues_dicts)}\n"
            f"- Critical: {len(critical)}\n"
            f"- Major: {len(major)}\n"
            f"- Minor: {len(minor)}\n\n"
            "CRITICAL ISSUES:\n"
        )

        if critical:
            report += "\n" + "\n".join(fmt_issue(i, include_detail=True) for i in critical) + "\n"
        else:
            report += "• None\n"

        report += "\nMAJOR ISSUES:\n"
        if major:
            report += "\n" + "\n".join(fmt_issue(i, include_detail=False) for i in major[:10]) + "\n"
        else:
            report += "• None\n"

        # Optional: include minor count summary without dumping everything
        report += f"\nMINOR ISSUES: {len(minor)}\n"

        # If input was junky, mention how many were dropped (helps debugging without crashing)
        dropped = len((issues or [])) - len(issues_dicts)
        if dropped > 0:
            report += f"\n(Note: {dropped} non-dict issue entries were ignored.)\n"

        return report


    def _compile_consistency_report(
            self,
            chapter_analyses: List[Dict[str, Any]],
            issues: List[Any]
    ) -> str:
        """Compile consistency report (defensive against malformed issue entries)."""

        issues_dicts: List[Dict[str, Any]] = [i for i in (issues or []) if isinstance(i, dict)]

        def sev(i: Dict[str, Any]) -> str:
            return str(i.get("severity", "Minor")).strip() or "Minor"

        critical = [i for i in issues_dicts if sev(i).lower() == "critical"]

        def fmt_issue(i: Dict[str, Any]) -> str:
            severity = sev(i)
            title = str(i.get("issue", "Unspecified issue")).strip()
            chapter = str(i.get("chapter", "Unknown chapter")).strip()
            location = str(i.get("location", "Unknown location")).strip()
            detail = str(i.get("detail", "")).strip()

            block = f"• [{severity}] {title}\n  Location: {chapter} - {location}"
            if detail:
                block += f"\n  {detail}"
            return block

        report = (
            "CONSISTENCY ANALYSIS SUMMARY\n\n"
            f"Total Issues: {len(issues_dicts)}\n"
            f"Critical Issues: {len(critical)}\n\n"
            "TOP ISSUES:\n"
        )

        if issues_dicts:
            report += "\n" + "\n".join(fmt_issue(i) for i in issues_dicts[:15]) + "\n"
        else:
            report += "• No issues found.\n"

        dropped = len((issues or [])) - len(issues_dicts)
        if dropped > 0:
            report += f"\n(Note: {dropped} malformed issue entries were ignored.)\n"

        return report


    def _compile_style_report(self, chapter_analyses: List[Dict], observations: List[Dict]) -> str:
        """Compile style report"""
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

    def save_analysis(self, analysis_data: Dict):
        """Save analysis results with tracked issues"""
        # Store as JSON in project settings or separate table
        analysis_type = analysis_data['type']

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