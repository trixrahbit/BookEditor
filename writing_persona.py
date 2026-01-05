"""
Writing Persona System - Defines consistent voice/style for AI rewrites
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import json
import uuid
from datetime import datetime


@dataclass
class WritingPersona:
    """Defines a writing style/voice persona"""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""

    # Voice characteristics
    voice_tone: str = "Professional, engaging"  # warm, clinical, humorous, dark, etc.
    pov_style: str = "Third person limited"  # first, third limited, third omniscient
    tense: str = "Past tense"  # past, present

    # Prose style
    sentence_variety: str = "Mix of short and long sentences for rhythm"
    paragraph_length: str = "Medium paragraphs (3-5 sentences)"
    vocabulary_level: str = "Accessible but literary"  # simple, accessible, literary, academic

    # Specific techniques
    show_vs_tell: str = "Heavily favor showing through action and dialogue"
    dialogue_style: str = "Natural, character-driven, with subtext"
    description_style: str = "Vivid sensory details, avoid purple prose"
    internal_thought: str = "Deep POV with character's voice in narration"

    # Emotional depth
    emotional_range: str = "Full range: subtle to intense"
    character_depth: str = "Complex motivations, internal conflicts"
    tension_building: str = "Escalating stakes, delayed gratification"

    # Genre-specific
    genre_conventions: str = "Literary fiction with thriller pacing"
    target_audience: str = "Adult readers who appreciate literary craft"
    comparative_authors: str = "Gillian Flynn, Celeste Ng, Tana French"

    # Rules and constraints
    avoid_words: List[str] = field(default_factory=list)  # ["suddenly", "very", "just"]
    avoid_phrases: List[str] = field(default_factory=list)  # ["it was", "there was"]
    prefer_techniques: List[str] = field(default_factory=list)  # ["active voice", "concrete details"]

    # Custom instructions
    custom_instructions: str = ""
    example_text: str = ""  # Sample of desired style

    # Metadata
    created: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    modified: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    is_default: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'voice_tone': self.voice_tone,
            'pov_style': self.pov_style,
            'tense': self.tense,
            'sentence_variety': self.sentence_variety,
            'paragraph_length': self.paragraph_length,
            'vocabulary_level': self.vocabulary_level,
            'show_vs_tell': self.show_vs_tell,
            'dialogue_style': self.dialogue_style,
            'description_style': self.description_style,
            'internal_thought': self.internal_thought,
            'emotional_range': self.emotional_range,
            'character_depth': self.character_depth,
            'tension_building': self.tension_building,
            'genre_conventions': self.genre_conventions,
            'target_audience': self.target_audience,
            'comparative_authors': self.comparative_authors,
            'avoid_words': self.avoid_words,
            'avoid_phrases': self.avoid_phrases,
            'prefer_techniques': self.prefer_techniques,
            'custom_instructions': self.custom_instructions,
            'example_text': self.example_text,
            'created': self.created,
            'modified': self.modified,
            'is_default': self.is_default
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WritingPersona':
        """Create from dictionary"""
        return cls(**data)

    def build_rewrite_prompt(self, original_text: str, scope: str = "scene") -> str:
        """
        Build comprehensive prompt for rewriting text with this persona

        Args:
            original_text: The text to rewrite
            scope: "selection", "scene", "chapter"
        """

        scope_guidance = {
            "selection": "Rewrite this passage maintaining context with surrounding text.",
            "scene": "Rewrite this complete scene, enhancing emotional depth and narrative flow.",
            "chapter": "Rewrite this chapter, ensuring consistency in voice and pacing throughout."
        }

        # Build avoid list
        avoid_section = ""
        if self.avoid_words or self.avoid_phrases:
            avoid_items = []
            if self.avoid_words:
                avoid_items.append(f"Words: {', '.join(self.avoid_words)}")
            if self.avoid_phrases:
                avoid_items.append(f"Phrases: {', '.join(self.avoid_phrases)}")
            avoid_section = f"\n\nAVOID:\n" + "\n".join(avoid_items)

        # Build technique preferences
        technique_section = ""
        if self.prefer_techniques:
            technique_section = f"\n\nPREFER:\n" + "\n".join([f"• {t}" for t in self.prefer_techniques])

        # Build example section
        example_section = ""
        if self.example_text:
            example_section = f"\n\nSTYLE EXAMPLE:\n{self.example_text[:500]}"

        prompt = f"""Rewrite the following text using this precise writing style. {scope_guidance.get(scope, '')}

VOICE & TONE:
{self.voice_tone}

POV & TENSE:
{self.pov_style}, {self.tense}

PROSE STYLE:
• Sentence Variety: {self.sentence_variety}
• Paragraphs: {self.paragraph_length}
• Vocabulary: {self.vocabulary_level}

NARRATIVE TECHNIQUES:
• Show vs Tell: {self.show_vs_tell}
• Dialogue: {self.dialogue_style}
• Description: {self.description_style}
• Internal Thought: {self.internal_thought}

EMOTIONAL DEPTH:
• Range: {self.emotional_range}
• Character Depth: {self.character_depth}
• Tension: {self.tension_building}

GENRE & AUDIENCE:
• Genre: {self.genre_conventions}
• Audience: {self.target_audience}
• Comparable to: {self.comparative_authors}
{avoid_section}{technique_section}{example_section}

CUSTOM INSTRUCTIONS:
{self.custom_instructions}

ORIGINAL TEXT:
{original_text}

INSTRUCTIONS:
1. Maintain all plot points and character actions
2. Preserve dialogue intent (but refine delivery)
3. Enhance emotional depth and sensory details
4. Apply the writing style consistently
5. Keep the same general length (±20%)
6. Sound like a professional author, not AI
7. Show character psychology through action and thought
8. Create vivid, immersive scenes

Return ONLY the rewritten text with NO explanations or preamble."""

        return prompt

    def get_system_message(self) -> str:
        """Get system message for AI"""
        return f"""You are a professional fiction writer and editor specializing in {self.genre_conventions}. 
Your voice is similar to {self.comparative_authors}. You write with emotional depth, vivid prose, 
and masterful technique. You never sound like AI - your writing is human, nuanced, and compelling.
Your rewrites enhance the author's vision while elevating the craft."""


class PersonaManager:
    """Manages writing personas for a project"""

    def __init__(self, db_manager, project_id: str):
        self.db_manager = db_manager
        self.project_id = project_id
        self.personas: Dict[str, WritingPersona] = {}
        self._load_personas()

    def _get_personas_path(self) -> str:
        """Get path to personas file"""
        import os
        db_path = self.db_manager.db_path
        base_path = os.path.dirname(db_path)
        return os.path.join(base_path, f".personas_{self.project_id}.json")

    def _load_personas(self):
        """Load personas from file"""
        import os
        path = self._get_personas_path()

        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.personas = {
                        p['id']: WritingPersona.from_dict(p)
                        for p in data.get('personas', [])
                    }
            except Exception as e:
                print(f"Error loading personas: {e}")
                self.personas = {}
        else:
            # Create default persona
            self._create_default_persona()

    def _save_personas(self):
        """Save personas to file"""
        path = self._get_personas_path()

        data = {
            'personas': [p.to_dict() for p in self.personas.values()],
            'version': '1.0'
        }

        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving personas: {e}")

    def _create_default_persona(self):
        """Create default persona"""
        default = WritingPersona(
            name="Default Professional",
            description="Professional literary fiction style with emotional depth",
            is_default=True,
            avoid_words=["suddenly", "very", "really", "just", "quite"],
            avoid_phrases=["it was", "there was", "could see", "could hear"],
            prefer_techniques=[
                "Active voice",
                "Concrete sensory details",
                "Character-driven conflict",
                "Subtext in dialogue",
                "Deep POV"
            ],
            custom_instructions="Focus on character psychology. Show emotional states through physical reactions and thoughts. Build tension through what's unsaid."
        )
        self.personas[default.id] = default
        self._save_personas()

    def create_persona(self, persona: WritingPersona) -> str:
        """Create new persona"""
        self.personas[persona.id] = persona
        self._save_personas()
        return persona.id

    def update_persona(self, persona: WritingPersona):
        """Update existing persona"""
        persona.modified = datetime.utcnow().isoformat()
        self.personas[persona.id] = persona
        self._save_personas()

    def delete_persona(self, persona_id: str) -> bool:
        """Delete persona"""
        if persona_id in self.personas:
            # Don't delete default
            if self.personas[persona_id].is_default:
                return False
            del self.personas[persona_id]
            self._save_personas()
            return True
        return False

    def get_persona(self, persona_id: str) -> Optional[WritingPersona]:
        """Get persona by ID"""
        return self.personas.get(persona_id)

    def get_default_persona(self) -> Optional[WritingPersona]:
        """Get default persona"""
        for persona in self.personas.values():
            if persona.is_default:
                return persona
        return None

    def list_personas(self) -> List[WritingPersona]:
        """List all personas"""
        return list(self.personas.values())

    def set_default(self, persona_id: str):
        """Set persona as default"""
        # Clear existing default
        for p in self.personas.values():
            p.is_default = False

        # Set new default
        if persona_id in self.personas:
            self.personas[persona_id].is_default = True
            self._save_personas()


# ============================================================================
# Pre-built persona templates
# ============================================================================

PERSONA_TEMPLATES = {
    "literary_contemporary": WritingPersona(
        name="Literary Contemporary",
        description="Character-driven literary fiction with emotional depth and lyrical prose",
        voice_tone="Introspective, nuanced, emotionally resonant with quiet intensity",
        pov_style="Third person limited",
        tense="Past tense",
        sentence_variety="Varied rhythm: short punchy sentences for impact, longer lyrical ones for atmosphere",
        paragraph_length="Medium paragraphs (3-5 sentences), shorter for tension",
        vocabulary_level="Accessible but literary",
        show_vs_tell="Heavy emphasis on showing through sensory details, body language, and subtext",
        dialogue_style="Authentic and character-driven, what's unsaid matters as much as words",
        description_style="Vivid sensory details that serve character emotion, avoid purple prose",
        internal_thought="Deep POV with character's voice bleeding into narration",
        emotional_range="Full spectrum from subtle longing to raw devastation",
        character_depth="Complex motivations, internal contradictions, psychological realism",
        tension_building="Subtle escalation through emotional stakes and relationship dynamics",
        genre_conventions="Literary fiction with strong character psychology",
        target_audience="Adult readers who appreciate emotional depth and literary craft",
        comparative_authors="Celeste Ng, Ann Patchett, Ocean Vuong, Anthony Doerr",
        avoid_words=["suddenly", "very", "really", "just", "quite", "began to", "started to"],
        avoid_phrases=["it was", "there was", "could see", "could hear", "seemed to"],
        prefer_techniques=["Metaphor grounded in character POV", "Layered meaning", "Emotional subtext", "Deep POV", "Active voice"],
        custom_instructions="Focus on character psychology revealed through small details. Every description should filter through the character's emotional state. Use precise verbs instead of adverbs. Build emotional resonance through specificity, not abstraction.",
        is_default=False
    ),

    "psychological_thriller": WritingPersona(
        name="Psychological Thriller",
        description="Tense, atmospheric thriller with unreliable narration and psychological depth",
        voice_tone="Tense, paranoid, psychologically intense with creeping dread",
        pov_style="First person",
        tense="Present tense",
        sentence_variety="Short, staccato sentences for tension; fragmented during panic; longer for false calm",
        paragraph_length="Varies dramatically: single-sentence paragraphs for impact, longer blocks for unease",
        vocabulary_level="Accessible but literary",
        show_vs_tell="Show psychological state through physical reactions, distorted perceptions",
        dialogue_style="Loaded with subtext, what characters don't say creates tension",
        description_style="Atmospheric details that build paranoia, every description hints at threat",
        internal_thought="Unreliable narrator's thoughts blur reality and perception",
        emotional_range="From surface normalcy to spiraling panic, paranoia, obsession",
        character_depth="Psychological complexity, hidden motivations, moral ambiguity",
        tension_building="Constant escalation, false sense of safety, delayed reveals, mounting dread",
        genre_conventions="Psychological thriller with literary character development",
        target_audience="Adult readers who love mind-bending psychological suspense",
        comparative_authors="Gillian Flynn, Paula Hawkins, Ruth Ware, Tana French, Sarah Waters",
        avoid_words=["suddenly", "very", "obviously"],
        avoid_phrases=["it was", "there was"],
        prefer_techniques=["Unreliable narration", "Foreshadowing", "Red herrings", "Emotional manipulation", "Pacing control"],
        custom_instructions="Every detail should hint at something wrong beneath the surface. Use the narrator's paranoia to color all descriptions. Build suspense through what's not said. Create atmosphere of creeping unease. Short sentences amp tension; longer ones create false security.",
        is_default=False
    ),

    "commercial_fiction": WritingPersona(
        name="Commercial Fiction",
        description="Fast-paced, engaging commercial fiction with strong voice and accessibility",
        voice_tone="Warm, witty, emotionally accessible with authentic humor",
        pov_style="Third person limited",
        tense="Past tense",
        sentence_variety="Conversational rhythm with variety, avoid monotony",
        paragraph_length="Short to medium (2-4 sentences) for readability and pace",
        vocabulary_level="Accessible but literary",
        show_vs_tell="Balance showing key moments with efficient telling for pace",
        dialogue_style="Snappy, character-specific, includes humor and banter naturally",
        description_style="Efficient vivid details, don't slow the pace",
        internal_thought="Close third POV with character voice in narration",
        emotional_range="Full range but accessible, earns the big emotions",
        character_depth="Relatable flaws, clear motivations, emotional authenticity",
        tension_building="Strong hooks, page-turning pacing, satisfying payoffs",
        genre_conventions="Commercial fiction with heart and craft",
        target_audience="Wide adult readership seeking engaging, well-crafted stories",
        comparative_authors="Taylor Jenkins Reid, Emily Henry, Fredrik Backman, Liane Moriarty",
        avoid_words=["suddenly", "very", "really", "just", "quite"],
        avoid_phrases=["it was", "there was", "began to"],
        prefer_techniques=["Strong voice", "Natural humor", "Emotional authenticity", "Page-turning pace", "Relatable characters"],
        custom_instructions="Write with warmth and wit. Keep the pace moving while earning emotional moments. Make characters immediately likable/interesting. Use specific details for humor and heart. Balance light moments with genuine emotion.",
        is_default=True
    ),

    "dark_fantasy": WritingPersona(
        name="Dark Fantasy",
        description="Atmospheric dark fantasy with visceral imagery and moral complexity",
        voice_tone="Dark, visceral, morally complex with haunting beauty",
        pov_style="Third person limited",
        tense="Past tense",
        sentence_variety="Lyrical flowing sentences that can turn sharp and brutal",
        paragraph_length="Medium length, lush with detail but never purple",
        vocabulary_level="Literary",
        show_vs_tell="Show violence and beauty in equal measure, unflinching detail",
        dialogue_style="Formal or archaic when appropriate, weighted with meaning",
        description_style="Lush dark imagery, visceral sensory details, unsettling beauty",
        internal_thought="Character psychology through dark lens, no sugarcoating",
        emotional_range="Despair, rage, twisted love, fleeting hope, moral compromise",
        character_depth="Morally gray characters, dark pasts, complex motivations",
        tension_building="Dread and inevitable tragedy, high stakes, brutal consequences",
        genre_conventions="Dark fantasy with literary prose and moral ambiguity",
        target_audience="Adult readers who appreciate dark, complex fantasy",
        comparative_authors="N.K. Jemisin, Joe Abercrombie, R.F. Kuang, Mark Lawrence",
        avoid_words=["very", "really", "quite"],
        avoid_phrases=["it was", "seemed to"],
        prefer_techniques=["Dark metaphor", "Visceral imagery", "Moral complexity", "Unflinching detail", "Poetic brutality"],
        custom_instructions="Don't shy from darkness or violence, but make it meaningful. Use beautiful language for terrible things. Every character should have blood on their hands. Build atmosphere through sensory details that unsettle. Magic should have cost.",
        is_default=False
    ),
    "scifi_thriller": WritingPersona(
    name="Anchor Protocol Sci-Fi Thriller",
    description=(
        "Sci-fi thriller voice built for The Anchor Trilogy: time-skips, reality drift, and "
        "controlled confusion with relentless clarity and tension."
    ),

    # Voice characteristics
    voice_tone=(
        "Taut, cinematic, intellectually sharp. Quiet dread under the surface. "
        "Occasional dry wit. Always confident, never melodramatic."
    ),
    pov_style="Third person limited (tight close POV; occasional controlled omniscient edge for system-level beats)",
    tense="Past tense (with strategic present-tense fragments for glitch moments only)",

    # Prose style
    sentence_variety=(
        "Knife-edge rhythm: crisp short lines for tension and perception shifts; "
        "longer sentences for analysis, memory bleed, or system logic—kept clean and readable."
    ),
    paragraph_length=(
        "Short to medium (1–4 sentences). Use single-line paragraphs for reveals, glitches, and reversals."
    ),
    vocabulary_level=(
        "Accessible, modern sci-fi. Precise verbs and concrete nouns. Minimal jargon unless it’s character-native."
    ),

    # Specific techniques
    show_vs_tell=(
        "Show first. Tell only to orient after a time/reality jump. "
        "Every abstract idea should be grounded in a physical cue or decision."
    ),
    dialogue_style=(
        "Economical, high-subtext, pressure-cooker dialogue. People dodge, deflect, negotiate power. "
        "No exposition dumps—fold context into conflict."
    ),
    description_style=(
        "Sensory anchoring with purposeful detail: light, sound, temperature, pressure, motion. "
        "Reality drift is described through contradictions and misalignments, not adjectives."
    ),
    internal_thought=(
        "Deep POV with cognitive friction: intrusive memories, split interpretations, competing certainties. "
        "Thoughts arrive like diagnostics and gut reactions, sometimes disagreeing."
    ),

    # Emotional depth
    emotional_range=(
        "Controlled intensity: dread, urgency, awe, grief, relief that never fully lands. "
        "Emotion is shown through action, micro-reactions, and decision-making under threat."
    ),
    character_depth=(
        "Characters carry hidden constraints and private bargains. "
        "Motivations are layered: survival vs. duty vs. obsession vs. love."
    ),
    tension_building=(
        "Escalate via uncertainty + consequence. "
        "Use reversals, narrowing options, ticking constraints, and 'wrongness' that grows more specific."
    ),

    # Genre-specific
    genre_conventions=(
        "Sci-fi thriller with mind-bending reality mechanics and investigative momentum."
    ),
    target_audience=(
        "Adult readers who want page-turning tension plus cerebral reality-play, without confusion fatigue."
    ),
    comparative_authors=(
        "Blake Crouch, Emily St. John Mandel, Ted Chiang (clarity), Christopher Nolan-style crosscut pacing"
    ),

    # Rules and constraints
    avoid_words=[
        "suddenly", "very", "really", "just", "quite", "somehow", "obviously", "literally",
        "began to", "started to"
    ],
    avoid_phrases=[
        "it was", "there was", "could see", "could hear", "as if", "felt like"
    ],
    prefer_techniques=[
        "Active voice",
        "Concrete sensory anchors after every shift",
        "Micro-orientation (WHO/WHERE/WHEN/WHAT CHANGED) within 1–2 lines after a cut",
        "Contradictions expressed as specific mismatches (not vague surrealism)",
        "Threat + goal stated or implied in every paragraph",
        "Strategic fragment sentences during glitches",
        "Subtext-heavy dialogue",
        "Chekhov details: small objects recur as anchors across realities"
    ],

    # Custom instructions
    custom_instructions=(
        "ANCHOR TRILOGY RULESET:\n"
        "1) TIME/REALITY CUTS ARE ALLOWED—but after any jump, immediately orient the reader using:\n"
        "   • a sensory anchor (sound/light/temperature/pressure),\n"
        "   • a concrete location cue, and\n"
        "   • one sentence clarifying what changed (even if the character is unsure).\n"
        "2) CONTROLLED DISORIENTATION: keep the prose clear even when reality isn't. Confusion should be felt, not caused.\n"
        "3) PRESERVE INTENTIONAL AMBIGUITY: do not 'explain away' contradictions. Let them stand—then show the character adapting.\n"
        "4) SYSTEM/MECHANIC MOMENTS: when referencing Anchor/system behavior, write like a diagnostic readout translated into narrative.\n"
        "5) NO EXPOSITION DUMPS: any worldbuilding must arrive through conflict, consequences, or a character's constraint.\n"
        "6) STITCHING ACROSS CHAPTERS: favor recurring motifs (a phrase, object, bodily sensation, or sound) that reappear across jumps.\n"
        "7) ENDING BEATS: land scenes with a hook—new constraint, new contradiction, or a choice that closes one door.\n"
        "\n"
        "OUTPUT REQUIREMENTS:\n"
        "• Maintain all plot and events.\n"
        "• Improve clarity and pacing without reducing the reality-bending nature.\n"
        "• Keep the voice cinematic, sharp, and human.\n"
    ),

    # Optional: include a short style sample if you want the model to mimic a very specific vibe
    example_text=(
        "The streetlight held steady—until it didn’t.\n"
        "Not a flicker. A decision.\n"
        "Green stayed green while the crosswalk counted down from eight to twelve.\n"
        "Maya’s phone buzzed in her pocket like a trapped insect. The notification timestamp read tomorrow.\n"
        "She looked up. The building across the street wore a different name, the same cracked stone.\n"
        "Reality hadn’t broken.\n"
        "It had updated."
    ),

    is_default=False
)
}