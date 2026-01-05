"""
AI Prompts - Centralized prompts for all AI features
"""
from typing import Dict, Any, List


class AIPrompts:
    """Collection of all AI prompts used in the application"""

    @staticmethod
    def rewrite_text(original_text: str, instruction: str) -> dict:
        """Prompt for rewriting text with specific instruction"""
        system = "You are a professional editor and writing coach helping authors improve their prose."

        user = f"""Please rewrite the following text according to this instruction: {instruction}

ORIGINAL TEXT:
{original_text}

Provide ONLY the rewritten text with no explanations or preamble."""

        return {
            "system": system,
            "user": user
        }

    @staticmethod
    def fill_scene_properties(scene_content: str, scene_name: str) -> dict:
        """Prompt for auto-filling scene properties"""
        system = "You are a literary analyst helping authors organize their novels."

        # Strip HTML and get plain text
        import re
        plain_text = re.sub(r'<[^>]+>', ' ', scene_content)
        plain_text = plain_text[:2000]  # Limit length

        user = f"""Analyze this scene and provide structured information.

SCENE: {scene_name}

CONTENT:
{plain_text}

Please provide EXACTLY in this format (use the exact labels):

SUMMARY: [2-3 sentence summary of what happens]

GOAL: [What the protagonist/main character wants to achieve]

CONFLICT: [The obstacle, problem, or opposing force]

OUTCOME: [What changes or is resolved by the end]"""

        return {
            "system": system,
            "user": user
        }

    @staticmethod
    def check_consistency(scenes: list, characters: list) -> dict:
        """Prompt for checking story consistency"""
        system = "You are an expert story editor specializing in continuity and consistency."

        # Build scene summaries
        scene_text = "\n\n".join([
            f"Scene {i + 1}: {s.get('name', 'Untitled')}\n{s.get('summary', 'No summary')[:300]}"
            for i, s in enumerate(scenes[:30])  # Limit to first 30 scenes
        ])

        # Build character info
        character_text = "\n".join([
            f"• {c.get('name', 'Unknown')}: {c.get('role', 'unknown role')} - {c.get('description', '')[:100]}"
            for c in characters[:20]  # Limit to first 20 characters
        ])

        user = f"""Check this story for consistency issues and continuity errors.

CHARACTERS:
{character_text}

SCENES:
{scene_text}

Please identify:
1. Character inconsistencies (name changes, personality contradictions, forgotten traits)
2. Timeline issues (events out of order, time contradictions)
3. Plot holes (unresolved threads, logical gaps, contradictions)
4. Continuity errors (objects appearing/disappearing, location errors)

Format your response as a numbered list of specific issues found. If no issues, say "No major consistency issues found."""

        return {
            "system": system,
            "user": user
        }

    @staticmethod
    def analyze_characters(scenes: list, characters: list) -> dict:
        """Prompt for character analysis"""
        system = "You are a character development expert and literary analyst."

        # Build context
        character_text = "\n\n".join([
            f"CHARACTER: {c.get('name', 'Unknown')}\n"
            f"Role: {c.get('role', 'unknown')}\n"
            f"Motivation: {c.get('motivation', 'not specified')}\n"
            f"Arc: {c.get('arc', 'not specified')}"
            for c in characters
        ])

        scene_excerpts = "\n\n".join([
            f"Scene {i + 1}: {s.get('name', 'Untitled')}"
            for i, s in enumerate(scenes[:15])
        ])

        user = f"""Analyze character development and consistency.

CHARACTERS:
{character_text}

SCENES:
{scene_excerpts}

Provide analysis covering:
1. Character arc clarity and progression
2. Consistency in voice and behavior
3. Relationship dynamics
4. Areas needing development
5. Strengths and weaknesses"""

        return {
            "system": system,
            "user": user
        }

    @staticmethod
    def analyze_plot(scenes: list) -> dict:
        """Prompt for plot analysis"""
        system = "You are a plot structure expert and developmental editor."

        scene_text = "\n".join([
            f"{i + 1}. {s.get('name', 'Untitled')}: {s.get('summary', 'No summary')[:200]}"
            for i, s in enumerate(scenes)
        ])

        user = f"""Analyze the plot structure and pacing.

SCENES:
{scene_text}

Provide analysis of:
1. Plot structure and story beats
2. Pacing (too fast/slow, momentum)
3. Plot holes or inconsistencies
4. Unresolved threads
5. Climax and resolution effectiveness"""

        return {
            "system": system,
            "user": user
        }

    @staticmethod
    def analyze_style(scene_contents: list) -> dict:
        """Prompt for writing style analysis"""
        system = "You are a writing style expert and prose analyst."

        # Get sample text from scenes
        samples = []
        for scene in scene_contents[:5]:
            import re
            text = re.sub(r'<[^>]+>', ' ', scene.get('content', ''))
            samples.append(text[:800])

        sample_text = "\n\n---\n\n".join(samples)

        user = f"""Analyze the writing style in these samples.

SAMPLES:
{sample_text}

Analyze:
1. Voice and tone
2. Sentence structure patterns
3. Show vs. Tell balance
4. Dialogue quality
5. Prose strengths and areas for improvement"""

        return {
            "system": system,
            "user": user
        }

    @staticmethod
    def system_story_bible() -> str:
        return (
            "You are a story architect. You create machine-readable story bibles that are consistent, "
            "conservative (do not invent), and grounded in the text. Output VALID JSON only."
        )

    @staticmethod
    def system_timeline() -> str:
        return "You are a timeline and continuity expert. Be precise. Use the provided paragraph references."

    @staticmethod
    def system_consistency() -> str:
        return "You are a story consistency expert. Be precise. Use the provided paragraph references."

    @staticmethod
    def system_style() -> str:
        return "You are a professional writing coach. Be specific and practical. Use paragraph references."

    @staticmethod
    def system_reader_sim() -> str:
        return "You simulate readers realistically. Be concrete, not vague."

    def book_bible_prompt(book_context: Dict[str, Any]) -> str:
        """
        book_context: {
            "chapters": [{id,name,scenes:[{id,name,numbered_text}]}...],
            "existing_bible": {..} or None
        }
        """
        existing = book_context.get("existing_bible")
        existing_json = existing if existing else {}

        return f"""
    Build or update a Canonical Story Bible from the manuscript.

    RULES:
    - Output MUST be valid JSON only (no prose).
    - Do not invent details not supported by the manuscript.
    - If unsure, omit or mark as "unknown".
    - Keep it compact but useful.

    OUTPUT JSON SCHEMA:
    {{
      "themes": [string],
      "characters": {{
        "<name>": {{
          "arc": string,
          "traits": [string],
          "core_wound": string,
          "relationships": {{ "<other>": string }}
        }}
      }},
      "rules_of_world": [string],
      "promises_to_reader": [string],
      "open_questions": [string],
      "notes": [string]
    }}

    EXISTING_BIBLE (may be empty):
    {existing_json}

    MANUSCRIPT EXCERPTS (numbered paragraphs by scene):
    {book_context.get("compiled_text", "")}

    Return JSON only.
    """.strip()

    @staticmethod
    def chapter_timeline_prompt(chapter_name: str, scene_blocks: List[Dict[str, Any]]) -> str:
        compiled = []
        for s in scene_blocks:
            compiled.append(f"SCENE: {s['scene_name']}\n{s['numbered_text']}")
        compiled_text = "\n\n---\n\n".join(compiled)

        return f"""
    Analyze timeline issues in this chapter.

    CHAPTER: {chapter_name}

    SCENES (each paragraph has an anchor like [P3]):
    {compiled_text}

    Identify SPECIFIC issues:
    - time contradictions
    - impossible sequences
    - location conflicts
    - day/night inconsistencies
    - implied time jumps that break logic

    OUTPUT: JSON array only, each issue must include anchors.
    [
      {{
        "type": "timeline",
        "severity": "Critical|Major|Minor",
        "issue": "...",
        "detail": "...",
        "location": "<scene name>",
        "anchors": ["P3","P4"],     // paragraph ids within that scene
        "quote": "short excerpt from relevant paragraph"
      }}
    ]

    Return JSON only.
    """.strip()

    def chapter_consistency_prompt(chapter_name: str, scene_blocks: List[Dict[str, Any]]) -> str:
        compiled = []
        for s in scene_blocks:
            compiled.append(f"SCENE: {s['scene_name']}\n{s['numbered_text']}")
        compiled_text = "\n\n---\n\n".join(compiled)

        return f"""
    Check for story consistency issues in this chapter.

    CHAPTER: {chapter_name}

    SCENES (each paragraph has an anchor like [P3]):
    {compiled_text}

    Identify:
    - character behavior inconsistencies
    - contradictions with earlier events (within this chapter’s scenes)
    - continuity errors
    - forgotten context inside the chapter

    OUTPUT: JSON array only.
    [
      {{
        "type": "consistency",
        "severity": "Critical|Major|Minor",
        "issue": "...",
        "detail": "...",
        "location": "<scene name>",
        "anchors": ["P2"],
        "quote": "short excerpt"
      }}
    ]

    Return JSON only.
    """.strip()

    def chapter_style_prompt(chapter_name: str, scene_blocks: List[Dict[str, Any]]) -> str:
        # style can sample; but we’ll keep full anchors for now
        compiled = []
        for s in scene_blocks:
            compiled.append(f"SCENE: {s['scene_name']}\n{s['numbered_text']}")
        compiled_text = "\n\n---\n\n".join(compiled)

        return f"""
    Analyze writing style in this chapter.

    CHAPTER: {chapter_name}

    SCENES (paragraph anchors like [P3]):
    {compiled_text}

    Identify strengths and improvements:
    - sentence variety
    - show vs tell
    - dialogue quality
    - pacing
    - voice consistency

    OUTPUT: JSON array only.
    [
      {{
        "type": "style",
        "severity": "Strength|Suggestion|Observation",
        "issue": "...",
        "detail": "...",
        "location": "<scene name>",
        "anchors": ["P5"],
        "quote": "short excerpt",
        "suggestions": ["...", "..."]
      }}
    ]
    Return JSON only.
    """.strip()

    def chapter_reader_snapshot_prompt(chapter_name: str, scene_blocks: List[Dict[str, Any]]) -> str:
        compiled = []
        for s in scene_blocks:
            compiled.append(f"SCENE: {s['scene_name']}\n{s['numbered_text']}")
        compiled_text = "\n\n---\n\n".join(compiled)

        return f"""
    At the end of this chapter, produce a reader-knowledge snapshot.

    CHAPTER: {chapter_name}
    TEXT:
    {compiled_text}

    Return JSON only:
    {{
      "reader_beliefs": [string],
      "facts_true": [string],
      "facts_ambiguous": [string],
      "questions_raised": [string]
    }}
    """.strip()

    def book_threads_prompt(book_context: Dict[str, Any]) -> str:
        return f"""
    Track threads across the whole book: themes, character arcs, mysteries.

    Return JSON only:
    {{
      "themes": [
        {{
          "name": "Theme name",
          "introduced": ["Chapter X"],
          "strongest": ["Chapter Y"],
          "missing": ["Chapter Z"],
          "notes": ["..."]
        }}
      ],
      "characters": [
        {{
          "name": "Character",
          "arc": "arc summary",
          "progression": [{{"chapter": "Chapter 1", "state": "..."}}, ...],
          "regressions": [{{"chapter": "...", "note": "..."}}]
        }}
      ],
      "mysteries": [
        {{
          "name": "Mystery",
          "introduced": ["..."],
          "developed": ["..."],
          "resolved": ["..."],
          "dropped": ["..."]
        }}
      ]
    }}

    MANUSCRIPT EXCERPTS:
    {book_context.get("compiled_text", "")}
    """.strip()

    def book_promise_payoff_prompt(book_context: Dict[str, Any]) -> str:
        return f"""
    Audit promise-payoff across the book.

    Return JSON only:
    {{
      "promises": [{{"promise": "...", "introduced": "Chapter X", "status": "Fulfilled|Unfulfilled|Ambiguous", "notes": "..."}}],
      "questions": [{{"question": "...", "raised": "Chapter X", "status": "Answered|Unanswered|Ambiguous", "notes": "..."}}]
    }}

    MANUSCRIPT:
    {book_context.get("compiled_text", "")}
    """.strip()

    def book_voice_drift_prompt(book_context: Dict[str, Any]) -> str:
        return f"""
    Analyze narrative voice and tone consistency across the manuscript.

    Return JSON only:
    {{
      "overall_voice": "...",
      "tone_shifts": [{{"chapter": "Chapter X", "note": "...", "severity": "minor|major"}}],
      "pacing_spikes": [{{"chapter": "Chapter X", "note": "..."}}],
      "recommendations": [string]
    }}

    MANUSCRIPT:
    {book_context.get("compiled_text", "")}
    """.strip()

    def book_reader_sim_prompt(book_context: Dict[str, Any]) -> str:
        return f"""
    Simulate 3 readers:
    - careful reader
    - skimmer
    - distracted reader

    Return JSON only:
    {{
      "careful_reader": {{"misunderstandings": [string], "missed": [string]}},
      "skimmer": {{"misunderstandings": [string], "missed": [string]}},
      "distracted_reader": {{"misunderstandings": [string], "missed": [string]}}
    }}

    MANUSCRIPT:
    {book_context.get("compiled_text", "")}
    """.strip()


class PromptParser:
    """Helper to parse AI responses"""

    @staticmethod
    def parse_scene_properties(response: str) -> dict:
        """Parse scene properties response"""
        properties = {}

        lines = response.strip().split('\n')
        current_key = None
        current_value = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check if line starts with a property label
            if line.startswith('SUMMARY:'):
                if current_key:
                    properties[current_key] = ' '.join(current_value).strip()
                current_key = 'summary'
                current_value = [line.split(':', 1)[1].strip()]
            elif line.startswith('GOAL:'):
                if current_key:
                    properties[current_key] = ' '.join(current_value).strip()
                current_key = 'goal'
                current_value = [line.split(':', 1)[1].strip()]
            elif line.startswith('CONFLICT:'):
                if current_key:
                    properties[current_key] = ' '.join(current_value).strip()
                current_key = 'conflict'
                current_value = [line.split(':', 1)[1].strip()]
            elif line.startswith('OUTCOME:'):
                if current_key:
                    properties[current_key] = ' '.join(current_value).strip()
                current_key = 'outcome'
                current_value = [line.split(':', 1)[1].strip()]
            elif current_key:
                # Continuation of current property
                current_value.append(line)

        # Don't forget the last property
        if current_key:
            properties[current_key] = ' '.join(current_value).strip()

        return properties


# Create module-level convenience functions for analyzer.py
_prompts = AIPrompts()

# System messages
system_timeline = AIPrompts.system_timeline
system_consistency = AIPrompts.system_consistency
system_style = AIPrompts.system_style
system_reader_sim = AIPrompts.system_reader_sim
system_story_bible = AIPrompts.system_story_bible

# Chapter prompts
chapter_timeline_prompt = AIPrompts.chapter_timeline_prompt
chapter_consistency_prompt = AIPrompts.chapter_consistency_prompt
chapter_style_prompt = AIPrompts.chapter_style_prompt
chapter_reader_snapshot_prompt = AIPrompts.chapter_reader_snapshot_prompt

# Book prompts
book_bible_prompt = AIPrompts.book_bible_prompt
book_threads_prompt = AIPrompts.book_threads_prompt
book_promise_payoff_prompt = AIPrompts.book_promise_payoff_prompt
book_voice_drift_prompt = AIPrompts.book_voice_drift_prompt
book_reader_sim_prompt = AIPrompts.book_reader_sim_prompt