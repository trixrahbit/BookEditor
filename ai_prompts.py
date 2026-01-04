"""
AI Prompts - Centralized prompts for all AI features
"""


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