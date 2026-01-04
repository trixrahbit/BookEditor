"""
Enhanced Azure OpenAI integration for comprehensive AI-powered analysis
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from PyQt6.QtCore import QSettings
import json

try:
    from openai import AzureOpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


@dataclass
class AnalysisResult:
    """Result from an AI analysis"""
    analysis_type: str
    content: str
    metadata: Dict[str, Any]
    success: bool
    error_message: Optional[str] = None


class AIAnalyzer:
    """Enhanced AI analyzer using Azure OpenAI"""

    def __init__(self):
        self.settings = QSettings()
        self.client: Optional[AzureOpenAI] = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Azure OpenAI client"""
        if not OPENAI_AVAILABLE:
            return

        api_key = self.settings.value("azure/api_key", "")
        endpoint = self.settings.value("azure/endpoint", "")
        api_version = self.settings.value("azure/api_version", "2024-02-15-preview")

        if api_key and endpoint:
            try:
                self.client = AzureOpenAI(
                    api_key=api_key,
                    azure_endpoint=endpoint,
                    api_version=api_version
                )
            except Exception as e:
                print(f"Error initializing Azure OpenAI client: {e}")

    def is_configured(self) -> bool:
        """Check if Azure OpenAI is properly configured"""
        return self.client is not None

    def analyze_characters(self, scenes: List[Dict[str, Any]],
                           characters: List[Dict[str, Any]]) -> AnalysisResult:
        """Analyze character consistency and development"""
        if not self.is_configured():
            return self._not_configured_result("character")

        prompt = self._build_character_analysis_prompt(scenes, characters)

        try:
            response = self._call_api(prompt)
            return AnalysisResult(
                analysis_type="character",
                content=response,
                metadata={"characters_analyzed": len(characters)},
                success=True
            )
        except Exception as e:
            return self._error_result("character", str(e))

    def analyze_plot(self, scenes: List[Dict[str, Any]],
                     plot_threads: List[Dict[str, Any]]) -> AnalysisResult:
        """Analyze plot structure and consistency"""
        if not self.is_configured():
            return self._not_configured_result("plot")

        prompt = self._build_plot_analysis_prompt(scenes, plot_threads)

        try:
            response = self._call_api(prompt)
            return AnalysisResult(
                analysis_type="plot",
                content=response,
                metadata={"scenes_analyzed": len(scenes)},
                success=True
            )
        except Exception as e:
            return self._error_result("plot", str(e))

    def analyze_conflicts(self, scenes: List[Dict[str, Any]],
                          chapters: List[Dict[str, Any]]) -> AnalysisResult:
        """Analyze key conflicts overall and per chapter"""
        if not self.is_configured():
            return self._not_configured_result("conflicts")

        prompt = self._build_conflict_analysis_prompt(scenes, chapters)

        try:
            response = self._call_api(prompt)
            return AnalysisResult(
                analysis_type="conflicts",
                content=response,
                metadata={"chapters_analyzed": len(chapters)},
                success=True
            )
        except Exception as e:
            return self._error_result("conflicts", str(e))

    def analyze_themes(self, scenes: List[Dict[str, Any]]) -> AnalysisResult:
        """Analyze themes throughout the novel"""
        if not self.is_configured():
            return self._not_configured_result("themes")

        prompt = self._build_theme_analysis_prompt(scenes)

        try:
            response = self._call_api(prompt)
            return AnalysisResult(
                analysis_type="themes",
                content=response,
                metadata={"scenes_analyzed": len(scenes)},
                success=True
            )
        except Exception as e:
            return self._error_result("themes", str(e))

    def analyze_tone(self, scenes: List[Dict[str, Any]]) -> AnalysisResult:
        """Analyze tone consistency and shifts"""
        if not self.is_configured():
            return self._not_configured_result("tone")

        prompt = self._build_tone_analysis_prompt(scenes)

        try:
            response = self._call_api(prompt)
            return AnalysisResult(
                analysis_type="tone",
                content=response,
                metadata={"scenes_analyzed": len(scenes)},
                success=True
            )
        except Exception as e:
            return self._error_result("tone", str(e))

    def analyze_market(self, project_data: Dict[str, Any],
                       scenes: List[Dict[str, Any]]) -> AnalysisResult:
        """Analyze market potential and positioning"""
        if not self.is_configured():
            return self._not_configured_result("market")

        prompt = self._build_market_analysis_prompt(project_data, scenes)

        try:
            response = self._call_api(prompt)
            return AnalysisResult(
                analysis_type="market",
                content=response,
                metadata={"genre": project_data.get('genre', 'Unknown')},
                success=True
            )
        except Exception as e:
            return self._error_result("market", str(e))

    def analyze_flow(self, scenes: List[Dict[str, Any]],
                     chapters: List[Dict[str, Any]]) -> AnalysisResult:
        """Analyze narrative flow and pacing"""
        if not self.is_configured():
            return self._not_configured_result("flow")

        prompt = self._build_flow_analysis_prompt(scenes, chapters)

        try:
            response = self._call_api(prompt)
            return AnalysisResult(
                analysis_type="flow",
                content=response,
                metadata={"total_scenes": len(scenes)},
                success=True
            )
        except Exception as e:
            return self._error_result("flow", str(e))

    def analyze_insights(self, scenes: List[Dict[str, Any]],
                         characters: List[Dict[str, Any]],
                         plot_threads: List[Dict[str, Any]]) -> AnalysisResult:
        """Provide comprehensive insights and suggestions"""
        if not self.is_configured():
            return self._not_configured_result("insights")

        prompt = self._build_insights_prompt(scenes, characters, plot_threads)

        try:
            response = self._call_api(prompt)
            return AnalysisResult(
                analysis_type="insights",
                content=response,
                metadata={
                    "scenes": len(scenes),
                    "characters": len(characters),
                    "plots": len(plot_threads)
                },
                success=True
            )
        except Exception as e:
            return self._error_result("insights", str(e))

    def analyze_timeline(self, scenes: List[Dict[str, Any]]) -> AnalysisResult:
        """Analyze timeline consistency"""
        if not self.is_configured():
            return self._not_configured_result("timeline")

        prompt = self._build_timeline_analysis_prompt(scenes)

        try:
            response = self._call_api(prompt)
            return AnalysisResult(
                analysis_type="timeline",
                content=response,
                metadata={"scenes_analyzed": len(scenes)},
                success=True
            )
        except Exception as e:
            return self._error_result("timeline", str(e))

    def analyze_style(self, scenes: List[Dict[str, Any]]) -> AnalysisResult:
        """Analyze writing style and provide suggestions"""
        if not self.is_configured():
            return self._not_configured_result("style")

        prompt = self._build_style_analysis_prompt(scenes)

        try:
            response = self._call_api(prompt)
            return AnalysisResult(
                analysis_type="style",
                content=response,
                metadata={"scenes_analyzed": len(scenes)},
                success=True
            )
        except Exception as e:
            return self._error_result("style", str(e))

    # Prompt builders

    def _build_character_analysis_prompt(self, scenes: List[Dict[str, Any]],
                                         characters: List[Dict[str, Any]]) -> str:
        """Build prompt for character analysis"""
        character_info = "\n".join([
            f"Character: {c['name']}\n"
            f"Role: {c.get('role', 'unknown')}\n"
            f"Description: {c.get('description', 'N/A')}\n"
            f"Motivation: {c.get('motivation', 'N/A')}\n"
            for c in characters
        ])

        scene_excerpts = "\n\n".join([
            f"Scene {i + 1}: {s['name']}\n{s.get('content', '')[:500]}..."
            for i, s in enumerate(scenes[:10])
        ])

        return f"""Analyze the following novel's character development and consistency.

CHARACTERS:
{character_info}

SCENE EXCERPTS:
{scene_excerpts}

Provide:
1. Character consistency analysis
2. Character development tracking
3. Relationship dynamics
4. Potential issues or inconsistencies
5. Suggestions for improvement

Format as a detailed analysis report."""

    def _build_plot_analysis_prompt(self, scenes: List[Dict[str, Any]],
                                    plot_threads: List[Dict[str, Any]]) -> str:
        """Build prompt for plot analysis"""
        plot_info = "\n".join([
            f"Plot Thread: {p['name']}\n"
            f"Importance: {p.get('importance', 'unknown')}\n"
            f"Description: {p.get('description', 'N/A')}\n"
            for p in plot_threads
        ])

        scene_summaries = "\n".join([
            f"{i + 1}. {s['name']}: {s.get('summary', 'No summary')}"
            for i, s in enumerate(scenes)
        ])

        return f"""Analyze plot structure and consistency.

PLOT THREADS:
{plot_info}

SCENE SUMMARIES:
{scene_summaries}

Provide:
1. Plot structure analysis
2. Plot hole detection
3. Pacing analysis
4. Thread tracking and resolution
5. Improvement suggestions"""

    def _build_conflict_analysis_prompt(self, scenes: List[Dict[str, Any]],
                                        chapters: List[Dict[str, Any]]) -> str:
        """Build prompt for conflict analysis"""
        content = f"""Analyze key conflicts in this novel.

CHAPTERS: {len(chapters)}
SCENES: {len(scenes)}

For each chapter and overall:
1. Identify main conflicts (internal/external)
2. Conflict escalation patterns
3. Resolution effectiveness
4. Chapter-by-chapter conflict map
5. Improvement recommendations"""
        return content

    def _build_theme_analysis_prompt(self, scenes: List[Dict[str, Any]]) -> str:
        """Build prompt for theme analysis"""
        excerpts = "\n\n".join([
            f"{s['name']}: {s.get('content', '')[:400]}"
            for s in scenes[:8]
        ])

        return f"""Identify and analyze themes in this novel.

EXCERPTS:
{excerpts}

Provide:
1. Major themes identified
2. Theme development throughout story
3. Symbolic elements
4. Thematic consistency
5. Suggestions for strengthening themes"""

    def _build_tone_analysis_prompt(self, scenes: List[Dict[str, Any]]) -> str:
        """Build prompt for tone analysis"""
        return f"""Analyze tone and mood throughout the novel.

Provide:
1. Overall tone identification
2. Tone shifts and their effectiveness
3. Consistency with genre expectations
4. Mood progression
5. Recommendations for tone adjustments"""

    def _build_market_analysis_prompt(self, project_data: Dict[str, Any],
                                      scenes: List[Dict[str, Any]]) -> str:
        """Build prompt for market analysis"""
        return f"""Analyze market potential for this novel.

GENRE: {project_data.get('genre', 'Unknown')}
WORD COUNT: {project_data.get('target_word_count', 0)}

Provide:
1. Target audience identification
2. Comparable titles in market
3. Unique selling points
4. Genre fit assessment
5. Marketing angle suggestions
6. Potential publishing paths"""

    def _build_flow_analysis_prompt(self, scenes: List[Dict[str, Any]],
                                    chapters: List[Dict[str, Any]]) -> str:
        """Build prompt for flow analysis"""
        return f"""Analyze narrative flow and pacing.

STRUCTURE:
- Chapters: {len(chapters)}
- Scenes: {len(scenes)}

Provide:
1. Pacing assessment
2. Chapter transitions effectiveness
3. Scene sequencing
4. Momentum analysis
5. Pacing recommendations"""

    def _build_insights_prompt(self, scenes: List[Dict[str, Any]],
                               characters: List[Dict[str, Any]],
                               plot_threads: List[Dict[str, Any]]) -> AnalysisResult:
        """Build prompt for comprehensive insights"""
        return f"""Provide comprehensive insights for this novel.

STATISTICS:
- Scenes: {len(scenes)}
- Characters: {len(characters)}
- Plot Threads: {len(plot_threads)}

Provide:
1. Strengths of the manuscript
2. Areas needing work
3. Unexpected patterns or issues
4. Developmental editing priorities
5. Next steps for the author"""

    def _build_timeline_analysis_prompt(self, scenes: List[Dict[str, Any]]) -> str:
        """Build prompt for timeline analysis"""
        scene_info = "\n".join([
            f"{i + 1}. {s['name']}: {s.get('summary', 'No summary')}"
            for i, s in enumerate(scenes)
        ])

        return f"""Analyze timeline consistency.

SCENES:
{scene_info}

Provide:
1. Timeline consistency check
2. Time references validation
3. Causality assessment
4. Timeline issues
5. Fixing recommendations"""

    def _build_style_analysis_prompt(self, scenes: List[Dict[str, Any]]) -> str:
        """Build prompt for style analysis"""
        samples = "\n\n".join([
            f"{s['name']}:\n{s.get('content', '')[:800]}"
            for s in scenes[:5]
        ])

        return f"""Analyze writing style.

SAMPLES:
{samples}

Provide:
1. Voice and tone analysis
2. Prose quality assessment
3. Show vs. Tell balance
4. Dialogue quality
5. Style improvement suggestions"""

    def _call_api(self, prompt: str) -> str:
        """Make API call to Azure OpenAI"""
        deployment = self.settings.value("azure/deployment", "gpt-4")
        temperature = float(self.settings.value("ai/temperature", 70)) / 100.0
        max_tokens = int(self.settings.value("ai/max_tokens", 2000))

        response = self.client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "You are an expert literary analyst and developmental editor."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )

        return response.choices[0].message.content

    def _not_configured_result(self, analysis_type: str) -> AnalysisResult:
        """Return not configured error result"""
        return AnalysisResult(
            analysis_type=analysis_type,
            content="",
            metadata={},
            success=False,
            error_message="Azure OpenAI is not configured. Please set up credentials in Settings."
        )

    def _error_result(self, analysis_type: str, error: str) -> AnalysisResult:
        """Return error result"""
        return AnalysisResult(
            analysis_type=analysis_type,
            content="",
            metadata={},
            success=False,
            error_message=error
        )

    def test_connection(self) -> tuple[bool, str]:
        """Test the Azure OpenAI connection"""
        if not OPENAI_AVAILABLE:
            return False, "OpenAI library not installed"

        if not self.is_configured():
            return False, "Not configured"

        try:
            response = self.client.chat.completions.create(
                model=self.settings.value("azure/deployment", "gpt-4"),
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=10
            )
            return True, "Connection successful!"
        except Exception as e:
            return False, f"Connection failed: {str(e)}"