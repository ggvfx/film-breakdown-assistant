"""
Global Configuration and User Settings.

This module defines the ProjectConfig dataclass which stores user-adjustable 
parameters for LLM interaction, extraction depth, performance modes, and 
Movie Magic Scheduling category defaults.
"""

from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ProjectConfig:
    """
    Stores all user-adjustable settings for the breakdown process.
    """
    # LLM Settings
    ollama_model: str = "llama3.2:3b"
    temperature: float = 0.1  # Low temperature ensures factual extraction
    
    # Extraction Logic
    conservative_mode: bool = True
    extract_implied_elements: bool = False  # Determines if AI infers non-stated items
    
    # Performance Settings
    # Eco Mode: 1 worker thread. Power Mode: >1 worker threads.
    worker_threads: int = 1 
    
    # Range Selection Settings
    # range_mode options: "All", "Scene", "Page"
    range_mode: str = "All"
    range_start: Optional[int] = None
    range_end: Optional[int] = None
    
    # UI & Workspace
    last_open_directory: str = ""
    auto_save_enabled: bool = True
    
    # Movie Magic Defaults
    mms_categories: List[str] = field(default_factory=lambda: [
        "Cast Members", "Background Actors", "Stunts", "Vehicles", "Props",
        "Camera", "Special Effects", "Wardrobe", "Makeup/Hair", "Animals",
        "Animal Wrangler", "Music", "Sound", "Art Department", "Set Dressing",
        "Greenery", "Special Equipment", "Security", "Additional Labor",
        "Visual Effects", "Mechanical Effects", "Miscellaneous", "Notes"
    ])

# --- APP-WIDE DEFAULTS ---
# Initialized instance of the config used as the application's base state.
DEFAULT_CONFIG = ProjectConfig()