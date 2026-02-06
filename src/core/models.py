"""
Core Data Models for the Film Breakdown Assistant.

Level 1 Foundation: This file is now fully aligned with Movie Magic Scheduling 6
import requirements and the 8ths-of-a-page industry standard.
"""

from typing import List, Optional
from enum import Enum
from pydantic import BaseModel, Field

# --- INDUSTRY CONSTANTS ---
MMS_CATEGORIES = [
    "Cast Members", "Background Actors", "Stunts", "Vehicles", "Props",
    "Camera", "Special Effects", "Wardrobe", "Makeup/Hair", "Animals",
    "Animal Wrangler", "Music", "Sound", "Art Department", "Set Dressing",
    "Greenery", "Special Equipment", "Security", "Additional Labor",
    "Visual Effects", "Mechanical Effects", "Miscellaneous", "Notes", "AD Alerts"
]

class SourceType(str, Enum):
    """Tracks if an element was literally in the text or logically inferred."""
    EXPLICIT = "explicit"
    IMPLIED = "implied"
    # Future: MANUAL = "manual"

# --- ELEMENT MODELS ---

class Element(BaseModel):
    """Represents a single production item (Prop, Cast, etc.)."""
    name: str
    category: str
    source: SourceType = SourceType.EXPLICIT
    confidence: float = 1.0
    count: str = "1"

# --- REVIEW & SAFETY MODELS ---

class ReviewFlag(BaseModel):
    """Alerts for the AD (e.g., Stunt detected, high cost item)."""
    flag_type: str
    note: str
    severity: int = Field(ge=1, le=3, default=1)

# --- CORE SCENE MODEL ---

class Scene(BaseModel):
    """The final structured data for one scene breakdown."""
    # From Parser
    scene_number: str
    int_ext: str
    set_name: str
    day_night: str
    scene_index: int
    
    # Page Math
    pages_whole: int = 0
    pages_eighths: int = 0 
    
    # From AI
    synopsis: str = Field(default="", max_length=100)
    description: str = ""
    elements: List[Element] = []
    flags: List[ReviewFlag] = []
