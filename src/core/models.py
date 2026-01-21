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
    "Visual Effects", "Mechanical Effects", "Miscellaneous", "Notes"
]

class SourceType(str, Enum):
    """Extensible source tracking for element origin."""
    EXPLICIT = "explicit"
    IMPLIED = "implied"
    # Future: MANUAL = "manual"

# --- ELEMENT MODELS ---

class Element(BaseModel):
    """Represents a production item for the MMS 'Library'."""
    name: str
    category: str
    source: SourceType = SourceType.EXPLICIT
    confidence: float = 1.0
    count: str = "1"

# --- REVIEW & SAFETY MODELS ---

class ReviewFlag(BaseModel):
    """High-priority alerts for the AD's safety review."""
    flag_type: str
    note: str
    severity: int = Field(ge=1, le=3, default=1)

# --- CORE SCENE MODEL ---

class Scene(BaseModel):
    """The complete breakdown data for one MMS Sheet."""
    sheet_number: str
    scene_number: str
    int_ext: str
    set_name: str
    day_night: str
    
    # Page count split for XML precision
    pages_whole: int = 0
    pages_eighths: int = 0 
    
    script_page: str
    script_day: str
    synopsis: str = Field(default="", max_length=100)
    description: str = ""
    
    elements: List[Element] = []
    flags: List[ReviewFlag] = []

    class Config:
        populate_by_name = True