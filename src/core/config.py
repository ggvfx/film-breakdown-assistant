"""
Global Configuration and User Settings.

This module stores the default settings for the application. 
At runtime, the UI will modify an instance of ProjectConfig 
based on user selections.
"""

from dataclasses import dataclass, field
from typing import List

@dataclass
class ProjectConfig:
    """
    Stores all user-adjustable settings for the breakdown process.
    """
    # LLM Settings
    ollama_model: str = "llama3.2:3b"
    temperature: float = 0.1  # Low temperature = more factual, less creative
    
    # Extraction Logic
    conservative_mode: bool = True
    extract_implied_elements: bool = False  # Linked to conservative_mode logic
    
    # UI & Workspace
    last_open_directory: str = ""
    auto_save_enabled: bool = True
    
    # Movie Magic Defaults (The 'Buckets' we discussed)
    mms_categories: List[str] = field(default_factory=lambda: [
        "Cast Members", "Background Actors", "Stunts", "Vehicles", "Props",
        "Camera", "Special Effects", "Wardrobe", "Makeup/Hair", "Animals",
        "Animal Wrangler", "Music", "Sound", "Art Department", "Set Dressing",
        "Greenery", "Special Equipment", "Security", "Additional Labor",
        "Visual Effects", "Mechanical Effects", "Miscellaneous", "Notes"
    ])

# --- APP-WIDE DEFAULTS ---
# This is the 'Master Template' the app loads on startup.
DEFAULT_CONFIG = ProjectConfig()