"""
AI Prompts - Centralized prompts for all AI features
"""
from typing import Dict, Any, List
import json


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
    def rewrite_in_character_voice(original_text: str, character_name: str, character_profile: Dict[str, Any]) -> dict:
        """Prompt for rewriting dialogue/text in a specific character's voice"""
        system = "You are a professional novelist and character voice expert."

        voice_lock = f"""CHARACTER PROFILE:
Name: {character_name}
Role: {character_profile.get('role', 'unknown')}
Description: {character_profile.get('description', '')}
Personality: {character_profile.get('personality', '')}
Motivation: {character_profile.get('motivation', '')}
Internal Conflict: {character_profile.get('internal_conflict', '')}
External Conflict: {character_profile.get('external_conflict', '')}
Secrets: {character_profile.get('secrets', '')}

VOICE ATTRIBUTES:
Sentence Length: {character_profile.get('sentence_length', 'varies')}
Vocabulary: {character_profile.get('vocabulary', 'standard')}
Formality: {character_profile.get('formality', 'neutral')}
Sarcasm/Tone: {character_profile.get('sarcasm_tone', 'neutral')}
"""

        user = f"""Please rewrite the following text in the voice of {character_name}.

{voice_lock}

IMPORTANT GUIDELINES:
1. Maintain {character_name}'s specific sentence structure, vocabulary, and tone.
2. Keep the core meaning and any important plot points.
3. If this is dialogue, ensure it sounds like {character_name} would actually say it.
4. Use the internal and external conflicts to inform their tone and subtext.

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
            f"• {c.get('name', 'Unknown')}: {c.get('role', 'unknown role')} - {c.get('description', '')[:100]}\n"
            f"  Voice: {c.get('sentence_length', 'N/A')}, {c.get('vocabulary', 'N/A')}, {c.get('formality', 'N/A')}, {c.get('sarcasm_tone', 'N/A')}"
            for c in characters[:20]  # Limit to first 20 characters
        ])

        user = f"""Check this story for consistency issues and continuity errors.
Also warn if dialogue doesn't match the established voice of the characters.

CHARACTERS:
{character_text}

SCENES:
{scene_text}

Please identify:
1. Character inconsistencies (name changes, personality contradictions, forgotten traits)
2. Dialogue Voice drift (when dialogue doesn't match established character voice attributes)
3. Timeline issues (events out of order, time contradictions)
4. Plot holes (unresolved threads, logical gaps, contradictions)
5. Continuity errors (objects appearing/disappearing, location errors)

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
    def book_pacing_prompt(book_context: Dict[str, Any]) -> str:
        return f"""
    Analyze the pacing, intensity, and tension of the book based on the manuscript excerpts.

    MANUSCRIPT EXCERPTS:
    {book_context.get("compiled_text", "")}

    For each scene, provide:
    - scene_name: The name of the scene.
    - intensity: A value from 0 (calm) to 10 (intense).
    - dialogue_ratio: A value from 0 (all exposition) to 1 (all dialogue).
    - tension: A value from 0 (low) to 10 (high).
    - length: Approximate word count or character count of the scene.

    OUTPUT: JSON only.
    {{
      "pacing_data": [
        {{
          "scene_name": "...",
          "intensity": 5,
          "dialogue_ratio": 0.4,
          "tension": 3,
          "length": 1200
        }},
        ...
      ]
    }}

    Return JSON only.
    """.strip()

    @staticmethod
    def chapter_pacing_prompt(chapter_name: str, scene_blocks: List[Dict[str, Any]]) -> str:
        compiled = []
        for s in scene_blocks:
            compiled.append(f"SCENE: {s['scene_name']}\n{s['numbered_text']}")
        compiled_text = "\n\n---\n\n".join(compiled)

        return f"""
    Analyze the pacing, intensity, and tension of this chapter.

    CHAPTER: {chapter_name}

    SCENES:
    {compiled_text}

    For each scene in this chapter, provide:
    - scene_name: The name of the scene.
    - intensity: A value from 0 (calm) to 10 (intense).
    - dialogue_ratio: A value from 0 (all exposition) to 1 (all dialogue).
    - tension: A value from 0 (low) to 10 (high).
    - length: Approximate word count or character count of the scene.

    OUTPUT: JSON only.
    {{
      "pacing_data": [
        {{
          "scene_name": "...",
          "intensity": 5,
          "dialogue_ratio": 0.4,
          "tension": 3,
          "length": 1200
        }},
        ...
      ]
    }}

    Return JSON only.
    """.strip()

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
    Analyze timeline issues and physical consistency in this chapter.

    CHAPTER: {chapter_name}

    SCENES (each paragraph has an anchor like [P3]):
    {compiled_text}

    Identify SPECIFIC issues:
    - Timeline drift (e.g., scene says Tuesday, but previous scene/chapter implied it's already Wednesday/Thursday).
    - Day/Night or Weather inconsistencies (e.g., raining in one scene, dry in the next without time for it to change).
    - Object continuity (e.g., a character holds a gun, then it's gone; or an injury disappears too quickly).
    - Outfit/Physical changes that are unexplained.
    - Impossible sequences or location conflicts (character in two places at once).

    OUTPUT: JSON array only, each issue must include anchors.
    [
      {{
        "type": "timeline",
        "severity": "Critical|Major|Minor",
        "issue": "Specific description of the contradiction",
        "detail": "Detailed explanation of why this is a conflict (reference specific scenes/paragraphs)",
        "location": "<scene name>",
        "anchors": ["P3","P4"],     // paragraph ids within that scene
        "quote": "short excerpt from relevant paragraph"
      }}
    ]

    Return JSON only.
    """.strip()

    @staticmethod
    def chapter_consistency_prompt(chapter_name: str, scene_blocks: List[Dict[str, Any]]) -> str:
        compiled = []
        for s in scene_blocks:
            compiled.append(f"SCENE: {s['scene_name']}\n{s['numbered_text']}")
        compiled_text = "\n\n---\n\n".join(compiled)

        return f"""
    Check for story and character consistency issues in this chapter.

    CHAPTER: {chapter_name}

    SCENES (each paragraph has an anchor like [P3]):
    {compiled_text}

    Identify:
    - Character eye color / age / accent drift (e.g., eyes were blue, now brown; accent was southern, now posh).
    - Personality or behavior contradictions (character acting 'out of character' without story reason).
    - Contradictions with earlier events (within this chapter’s scenes).
    - Forgotten context (e.g., character forgot they were shot in the leg earlier in the same chapter).

    OUTPUT: JSON array only.
    [
      {{
        "type": "consistency",
        "severity": "Critical|Major|Minor",
        "issue": "Character/Story drift description",
        "detail": "Explanation of the inconsistency",
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
    At the end of this chapter, produce a reader-clarity snapshot simulating 3 types of readers.

    CHAPTER: {chapter_name}
    TEXT:
    {compiled_text}

    Return JSON only:
    {{
      "careful_reader": {{
        "understanding": "detailed summary of what they know",
        "confusion": "any subtle points they might question",
        "missed": "what they definitely missed"
      }},
      "skimmer": {{
        "understanding": "high-level gist they caught",
        "confusion": "major plot points they might have mixed up",
        "missed": "subtext or secondary details lost"
      }},
      "distracted_reader": {{
        "understanding": "vague impressions",
        "confusion": "who is where and why",
        "missed": "most things except major actions"
      }}
    }}
    """.strip()

    def book_threads_prompt(book_context: Dict[str, Any]) -> str:
        existing = book_context.get("existing_threads", {})
        return f"""
    Track threads across the book: themes, character arcs, mysteries.
    You will be given an EXISTING ANALYSIS and NEW MANUSCRIPT EXCERPTS.
    Update the analysis based on the new excerpts.

    EXISTING ANALYSIS:
    {json.dumps(existing, indent=2)}

    NEW MANUSCRIPT EXCERPTS:
    {book_context.get("compiled_text", "")}

    Return UPDATED JSON only:
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
    """.strip()

    def book_promise_payoff_prompt(book_context: Dict[str, Any]) -> str:
        existing = book_context.get("existing_promises", {})
        return f"""
    Audit promise-payoff across the book.
    You will be given an EXISTING AUDIT and NEW MANUSCRIPT EXCERPTS.
    Update the audit based on the new excerpts.

    EXISTING AUDIT:
    {json.dumps(existing, indent=2)}

    NEW MANUSCRIPT EXCERPTS:
    {book_context.get("compiled_text", "")}

    Return UPDATED JSON only:
    {{
      "promises": [{{"promise": "...", "introduced": "Chapter X", "status": "Fulfilled|Unfulfilled|Ambiguous", "notes": "..."}}],
      "questions": [{{"question": "...", "raised": "Chapter X", "status": "Answered|Unanswered|Ambiguous", "notes": "..."}}]
    }}
    """.strip()

    def book_voice_drift_prompt(book_context: Dict[str, Any]) -> str:
        existing = book_context.get("existing_voice", {})
        return f"""
    Analyze narrative voice and tone consistency across the manuscript.
    You will be given an EXISTING ANALYSIS and NEW MANUSCRIPT EXCERPTS.
    Update the analysis based on the new excerpts.

    EXISTING ANALYSIS:
    {json.dumps(existing, indent=2)}

    NEW MANUSCRIPT EXCERPTS:
    {book_context.get("compiled_text", "")}

    Return UPDATED JSON only:
    {{
      "overall_voice": "...",
      "tone_shifts": [{{"chapter": "Chapter X", "note": "...", "severity": "minor|major"}}],
      "pacing_spikes": [{{"chapter": "Chapter X", "note": "..."}}],
      "recommendations": [string]
    }}
    """.strip()

    def book_reader_sim_prompt(book_context: Dict[str, Any]) -> str:
        existing = book_context.get("existing_sim", {})
        return f"""
    Simulate 3 readers for the book.
    You will be given an EXISTING SIMULATION and NEW MANUSCRIPT EXCERPTS.
    Update the simulation based on the new excerpts.

    EXISTING SIMULATION:
    {json.dumps(existing, indent=2)}

    NEW MANUSCRIPT EXCERPTS:
    {book_context.get("compiled_text", "")}

    Return UPDATED JSON only:
    {{
      "careful_reader": {{
        "understanding": "detailed summary",
        "confusion": "any subtle points",
        "missed": "what they missed"
      }},
      "skimmer": {{
        "understanding": "high-level gist",
        "confusion": "mixed up points",
        "missed": "lost details"
      }},
      "distracted_reader": {{
        "understanding": "vague impressions",
        "confusion": "unclear points",
        "missed": "most things"
      }}
    }}
    """.strip()

    @staticmethod
    def system_world_rules():
        return """
    You are a World Rules Engine. Your job is to strictly enforce the laws of the universe, magic systems, 
    technological limits, and cultural norms defined for a story.
    
    You will be provided with:
    1. A set of WORLD RULES (Laws of the Universe).
    2. A MANUSCRIPT EXCERPT (Scene or Chapter).
    
    You must identify any VIOLATIONS where the manuscript contradicts the defined rules.
    Be especially attentive to:
    - Magic system limits (e.g., mana costs, forbidden spells, physical toll).
    - Technology level (e.g., no cell phones in medieval setting).
    - Cultural rules (e.g., social taboos, language requirements).
    - Physics exceptions (e.g., how gravity works in this world).
    - Shifts in time or reality that must follow specific logic.
    
    Return your findings as a strict JSON list of violation objects.
    """.strip()

    @staticmethod
    def world_rules_validation_prompt(rules: List[Dict[str, Any]], manuscript: str) -> str:
        return f"""
    WORLD RULES:
    {json.dumps(rules, indent=2)}
    
    MANUSCRIPT EXCERPT:
    {manuscript}
    
    Analyze the excerpt for rule violations. For each violation, specify:
    - rule_name: The name of the rule violated.
    - violation: A brief description of what happened in the text that broke the rule.
    - severity: 'minor' (can be explained away) or 'major' (breaks immersion or plot logic).
    - suggestion: How to fix it.
    
    Return strict JSON only:
    [
      {{"rule_name": "...", "violation": "...", "severity": "...", "suggestion": "..."}}
    ]
    """.strip()


class PromptParser:
    """Helper to parse AI responses"""

    @staticmethod
    def parse_scene_properties(response: str) -> dict:
        """Parse scene properties response with robustness"""
        properties = {}
        if not response:
            return properties

        lines = response.strip().split('\n')
        current_key = None
        current_value = []

        # Keywords to look for (case-insensitive)
        keywords = {
            'SUMMARY': 'summary',
            'GOAL': 'goal',
            'CONFLICT': 'conflict',
            'OUTCOME': 'outcome'
        }

        for line in lines:
            clean_line = line.strip()
            if not clean_line:
                continue

            # Check if line starts with any of our keywords
            # Handle markdown like **SUMMARY:** or just SUMMARY:
            found_key = None
            for kw, key_id in keywords.items():
                # Look for keyword at start, ignoring markdown asterisks
                pattern = clean_line.upper().replace('*', '').strip()
                if pattern.startswith(kw + ':'):
                    found_key = key_id
                    # Get the content after the colon
                    content = clean_line.split(':', 1)[1].strip()
                    break

            if found_key:
                # Save previous key if exists
                if current_key:
                    properties[current_key] = ' '.join(current_value).strip()
                
                current_key = found_key
                current_value = [content]
            elif current_key:
                # Continuation of current property
                current_value.append(clean_line)

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
system_world_rules = AIPrompts.system_world_rules

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