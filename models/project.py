from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class ItemType(Enum):
    PROJECT = "project"
    PART = "part"
    CHAPTER = "chapter"
    SCENE = "scene"
    CHARACTER = "character"
    LOCATION = "location"
    PLOT_THREAD = "plot_thread"
    NOTE = "note"
    WORLD_RULE = "world_rule"


@dataclass
class ProjectItem:
    """Base class for all project items"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    item_type: ItemType = ItemType.SCENE
    created: datetime = field(default_factory=datetime.now)
    modified: datetime = field(default_factory=datetime.now)
    parent_id: Optional[str] = None
    order: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'item_type': self.item_type.value,
            'created': self.created.isoformat(),
            'modified': self.modified.isoformat(),
            'parent_id': self.parent_id,
            'order': self.order
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ProjectItem':
        data['item_type'] = ItemType(data['item_type'])
        data['created'] = datetime.fromisoformat(data['created'])
        data['modified'] = datetime.fromisoformat(data['modified'])
        return cls(**data)


@dataclass
class Scene(ProjectItem):
    """A scene in the novel"""
    content: str = ""
    summary: str = ""
    goal: str = ""
    conflict: str = ""
    outcome: str = ""
    pov_character_id: Optional[str] = None
    location_id: Optional[str] = None
    word_count: int = 0
    status: str = "draft"  # draft, revision, final

    def __post_init__(self):
        self.item_type = ItemType.SCENE

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            'content': self.content,
            'summary': self.summary,
            'goal': self.goal,
            'conflict': self.conflict,
            'outcome': self.outcome,
            'pov_character_id': self.pov_character_id,
            'location_id': self.location_id,
            'word_count': self.word_count,
            'status': self.status
        })
        return base


@dataclass
class Chapter(ProjectItem):
    """A chapter containing scenes"""
    description: str = ""
    summary: str = ""

    def __post_init__(self):
        self.item_type = ItemType.CHAPTER

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            'description': self.description,
            'summary': self.summary
        })
        return base


@dataclass
class Part(ProjectItem):
    """A part/section containing chapters"""
    description: str = ""

    def __post_init__(self):
        self.item_type = ItemType.PART

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            'description': self.description
        })
        return base


@dataclass
class Character(ProjectItem):
    """A character in the novel"""
    role: str = "minor"  # protagonist, antagonist, major, minor
    description: str = ""
    motivation: str = ""
    conflict: str = ""
    arc: str = ""
    notes: str = ""
    # Physical attributes
    age: str = ""
    appearance: str = ""
    # Personality
    personality: str = ""
    strengths: str = ""
    weaknesses: str = ""
    # Voice attributes
    sentence_length: str = ""
    vocabulary: str = ""
    formality: str = ""
    sarcasm_tone: str = ""
    # Dynamic tracking
    internal_conflict: str = ""
    external_conflict: str = ""
    secrets: str = ""
    last_seen: str = ""  # Track when they last appeared
    # Relationships
    relationships: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        self.item_type = ItemType.CHARACTER

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            'role': self.role,
            'description': self.description,
            'motivation': self.motivation,
            'conflict': self.conflict,
            'arc': self.arc,
            'notes': self.notes,
            'age': self.age,
            'appearance': self.appearance,
            'personality': self.personality,
            'strengths': self.strengths,
            'weaknesses': self.weaknesses,
            'sentence_length': self.sentence_length,
            'vocabulary': self.vocabulary,
            'formality': self.formality,
            'sarcasm_tone': self.sarcasm_tone,
            'internal_conflict': self.internal_conflict,
            'external_conflict': self.external_conflict,
            'secrets': self.secrets,
            'last_seen': self.last_seen,
            'relationships': self.relationships
        })
        return base


@dataclass
class Location(ProjectItem):
    """A location in the novel"""
    description: str = ""
    significance: str = ""
    notes: str = ""

    def __post_init__(self):
        self.item_type = ItemType.LOCATION

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            'description': self.description,
            'significance': self.significance,
            'notes': self.notes
        })
        return base


@dataclass
class PlotThread(ProjectItem):
    """A plot thread running through the novel"""
    description: str = ""
    importance: str = "minor"  # main, major, minor
    resolution: str = ""
    notes: str = ""

    def __post_init__(self):
        self.item_type = ItemType.PLOT_THREAD

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            'description': self.description,
            'importance': self.importance,
            'resolution': self.resolution,
            'notes': self.notes
        })
        return base


@dataclass
class WorldRule(ProjectItem):
    """A law of the universe, magic system, or cultural rule"""
    rule_category: str = "Magic"  # Magic, Tech, Culture, Physics, Reality, Other
    description: str = ""
    consequences: str = ""  # What happens if broken or used
    is_active: bool = True

    def __post_init__(self):
        self.item_type = ItemType.WORLD_RULE

    def to_dict(self) -> Dict[str, Any]:
        base = super().to_dict()
        base.update({
            'rule_category': self.rule_category,
            'description': self.description,
            'consequences': self.consequences,
            'is_active': self.is_active
        })
        return base


@dataclass
class Project:
    """The novel project container"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "Untitled Novel"
    author: str = ""
    genre: str = ""
    target_word_count: int = 80000
    description: str = ""
    created: datetime = field(default_factory=datetime.now)
    modified: datetime = field(default_factory=datetime.now)
    world_rules: List[WorldRule] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'name': self.name,
            'author': self.author,
            'genre': self.genre,
            'target_word_count': self.target_word_count,
            'description': self.description,
            'created': self.created.isoformat(),
            'modified': self.modified.isoformat(),
            'world_rules': [r.to_dict() for r in self.world_rules]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        data['created'] = datetime.fromisoformat(data['created'])
        data['modified'] = datetime.fromisoformat(data['modified'])
        
        rules_data = data.pop('world_rules', [])
        project = cls(**data)
        project.world_rules = [WorldRule.from_dict(r) if isinstance(r, dict) else r for r in rules_data]
        return project