"""
Enhanced Azure OpenAI integration for comprehensive AI-powered analysis
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from PyQt6.QtCore import QSettings
import json
from text_utils import format_scene_for_ai
import ai_prompts as prompts

try:
    from openai import AzureOpenAI, OpenAI

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

        api_key = (self.settings.value("azure/api_key", "", type=str) or "").strip()
        endpoint = (self.settings.value("azure/endpoint", "", type=str) or "").strip()
        api_version = (self.settings.value("azure/api_version", "2024-12-01-preview", type=str) or "").strip()

        # Normalize endpoint: keep it as the resource root (no /openai/..., no query)
        endpoint = endpoint.rstrip("/")

        if api_key and endpoint:
            try:
                self.client = AzureOpenAI(
                    api_key=api_key,
                    azure_endpoint=endpoint,
                    api_version=api_version
                )
            except Exception as e:
                self.client = None
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
        deployment = (self.settings.value("azure/deployment", "", type=str) or "").strip()
        if not deployment:
            raise RuntimeError("Missing Azure deployment name (must be your Azure *deployment* name).")

        temperature = float(self.settings.value("ai/temperature", 70)) / 100.0
        max_out = int(self.settings.value("ai/max_tokens", 2000))  # treat UI value as output tokens

        response = self.client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": "You are an expert literary analyst and developmental editor."},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_completion_tokens=max_out,  # <-- important for your api_version/doc
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
        if not OPENAI_AVAILABLE:
            return False, "OpenAI library not installed"
        if not self.is_configured():
            return False, "Not configured"

        deployment = (self.settings.value("azure/deployment", "", type=str) or "").strip()
        if not deployment:
            return False, "Missing Deployment name (must match your Azure deployment name)."

        try:
            self.client.chat.completions.create(
                model=deployment,
                messages=[{"role": "user", "content": "Test"}],
                max_completion_tokens=2000,  # <-- not max_tokens
            )
            return True, "Connection successful!"
        except Exception as e:
            return False, f"Connection failed: {e}"



def _safe_json_loads(s: str) -> Any:
    """
    AI sometimes wraps JSON with stray text. Try to extract the first JSON object/array.
    """
    raw = (s or "").strip()
    if not raw:
        return None

    # quick path
    try:
        return json.loads(raw)
    except Exception:
        pass

    # try to find a JSON array/object in the text
    start_candidates = [raw.find("["), raw.find("{")]
    start_candidates = [x for x in start_candidates if x != -1]
    if not start_candidates:
        raise ValueError("AI did not return JSON.")
    start = min(start_candidates)

    # attempt from that start
    trimmed = raw[start:]
    # try progressively trimming the end
    for cut in range(0, min(5000, len(trimmed))):
        try:
            return json.loads(trimmed[:len(trimmed)-cut])
        except Exception:
            continue

    raise ValueError("Failed to parse AI JSON output.")


@dataclass
class ChapterData:
    id: str
    name: str
    scenes: List[Dict[str, Any]]  # each includes id,name,content(html)


class AnalysisEngine:
    """
    Stateless analysis runner. Uses ai_manager.call_api to execute prompts.
    """

    def __init__(self, ai_manager):
        self.ai_manager = ai_manager

    # --------- CHAPTER ANALYSIS ----------

    def analyze_chapter_timeline(self, chapter: ChapterData, scene_max_chars: int = 12000) -> Dict[str, Any]:
        blocks = self._chapter_scene_blocks(chapter, scene_max_chars)
        prompt = prompts.chapter_timeline_prompt(chapter.name, blocks)
        resp = self.ai_manager.call_api(
            messages=[{"role": "user", "content": prompt}],
            system_message=prompts.system_timeline(),
            temperature=0.25,
            max_tokens=8000
        )
        issues = _safe_json_loads(resp) or []
        issues = self._attach_scene_ids_by_name(issues, chapter)
        return {"type": "timeline", "issues": issues, "chapter": chapter.name}

    def analyze_chapter_consistency(self, chapter: ChapterData, scene_max_chars: int = 12000) -> Dict[str, Any]:
        blocks = self._chapter_scene_blocks(chapter, scene_max_chars)
        prompt = prompts.chapter_consistency_prompt(chapter.name, blocks)
        resp = self.ai_manager.call_api(
            messages=[{"role": "user", "content": prompt}],
            system_message=prompts.system_consistency(),
            temperature=0.25,
            max_tokens=8000
        )
        issues = _safe_json_loads(resp) or []
        issues = self._attach_scene_ids_by_name(issues, chapter)
        return {"type": "consistency", "issues": issues, "chapter": chapter.name}

    def analyze_chapter_style(self, chapter: ChapterData, scene_max_chars: int = 12000) -> Dict[str, Any]:
        blocks = self._chapter_scene_blocks(chapter, scene_max_chars)
        prompt = prompts.chapter_style_prompt(chapter.name, blocks)
        resp = self.ai_manager.call_api(
            messages=[{"role": "user", "content": prompt}],
            system_message=prompts.system_style(),
            temperature=0.35,
            max_tokens=8000
        )
        issues = _safe_json_loads(resp) or []
        issues = self._attach_scene_ids_by_name(issues, chapter)
        return {"type": "style", "issues": issues, "chapter": chapter.name}

    def analyze_chapter_reader_snapshot(self, chapter: ChapterData, scene_max_chars: int = 12000) -> Dict[str, Any]:
        blocks = self._chapter_scene_blocks(chapter, scene_max_chars)
        prompt = prompts.chapter_reader_snapshot_prompt(chapter.name, blocks)
        resp = self.ai_manager.call_api(
            messages=[{"role": "user", "content": prompt}],
            system_message="You produce reader-clarity snapshots as strict JSON.",
            temperature=0.2,
            max_tokens=4000
        )
        payload = _safe_json_loads(resp) or {}
        return {"type": "reader_snapshot", "payload": payload, "chapter": chapter.name}

    # --------- BOOK ANALYSIS ----------

    def analyze_book_story_bible(self, compiled_text: str, existing_bible: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        ctx = {"compiled_text": compiled_text, "existing_bible": existing_bible or {}}
        prompt = prompts.book_bible_prompt(ctx)
        resp = self.ai_manager.call_api(
            messages=[{"role": "user", "content": prompt}],
            system_message=prompts.system_story_bible(),
            temperature=0.2,
            max_tokens=8000
        )
        bible = _safe_json_loads(resp) or {}
        return {"type": "story_bible", "payload": bible}

    def analyze_book_threads(self, compiled_text: str) -> Dict[str, Any]:
        prompt = prompts.book_threads_prompt({"compiled_text": compiled_text})
        resp = self.ai_manager.call_api(
            messages=[{"role": "user", "content": prompt}],
            system_message="You track story threads and output strict JSON only.",
            temperature=0.25,
            max_tokens=8000
        )
        return {"type": "threads", "payload": _safe_json_loads(resp) or {}}

    def analyze_book_promise_payoff(self, compiled_text: str) -> Dict[str, Any]:
        prompt = prompts.book_promise_payoff_prompt({"compiled_text": compiled_text})
        resp = self.ai_manager.call_api(
            messages=[{"role": "user", "content": prompt}],
            system_message="You audit promise-payoff. Output strict JSON only.",
            temperature=0.25,
            max_tokens=8000
        )
        return {"type": "promise_payoff", "payload": _safe_json_loads(resp) or {}}

    def analyze_book_voice_drift(self, compiled_text: str) -> Dict[str, Any]:
        prompt = prompts.book_voice_drift_prompt({"compiled_text": compiled_text})
        resp = self.ai_manager.call_api(
            messages=[{"role": "user", "content": prompt}],
            system_message="You analyze voice/tone/pacing drift and output strict JSON only.",
            temperature=0.25,
            max_tokens=6000
        )
        return {"type": "voice_drift", "payload": _safe_json_loads(resp) or {}}

    def analyze_book_reader_sim(self, compiled_text: str) -> Dict[str, Any]:
        prompt = prompts.book_reader_sim_prompt({"compiled_text": compiled_text})
        resp = self.ai_manager.call_api(
            messages=[{"role": "user", "content": prompt}],
            system_message=prompts.system_reader_sim(),
            temperature=0.35,
            max_tokens=6000
        )
        return {"type": "reader_sim", "payload": _safe_json_loads(resp) or {}}

    # --------- helpers ----------

    def _chapter_scene_blocks(self, chapter: ChapterData, scene_max_chars: int) -> List[Dict[str, Any]]:
        blocks = []
        for s in chapter.scenes:
            blocks.append(format_scene_for_ai(s.get("name","Untitled"), s.get("content",""), max_chars=scene_max_chars))
        return blocks

    def _attach_scene_ids_by_name(self, issues: List[Dict[str, Any]], chapter: ChapterData) -> List[Dict[str, Any]]:
        # stable mapping: scene name -> id (case-insensitive)
        name_to_id = {}
        for s in chapter.scenes:
            nm = (s.get("name") or "").strip().lower()
            if nm:
                name_to_id[nm] = s.get("id")
        for it in issues:
            loc = (it.get("location") or "").strip().lower()
            if loc and loc in name_to_id:
                it["scene_id"] = name_to_id[loc]
            else:
                it["scene_id"] = it.get("scene_id")  # preserve if AI returned one
        return issues
