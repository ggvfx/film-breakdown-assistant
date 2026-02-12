"""
Global Configuration Management.

Handles user preferences, LLM parameters, and safety triggers.
Designed to be serializable for GUI state persistence.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from src.core.models import MMS_CATEGORIES


# --- PERFORMANCE MAPPING ---
PERFORMANCE_LEVELS = {
    "Eco": 1,
    "Power": 4,
    "Turbo": 6,
    "Max": 8
}

class ProjectConfig(BaseModel):
    """
    Application-wide settings and user preferences.
    Using BaseModel ensures type safety and easy JSON export/import.
    """
    
    # Path Persistence
    last_directory: str = ""
    output_dir: str = "outputs"
    
    # LLM Settings
    ollama_model: str = "llama3.1:8b"
    temperature: float = Field(default=0.0, ge=0.0, le=1.0)
    
    # Extraction Logic
    conservative_mode: bool = True
    extract_implied_elements: bool = False
    
    ## Performance & Concurrency
    performance_mode: str = "Power" 
    worker_threads: int = Field(default=4, ge=1, le=8)
    
    # Movie Magic Setup
    mms_categories: List[str] = Field(default_factory=lambda: list(MMS_CATEGORIES))
    category_selection: Dict[str, bool] = Field(
        default_factory=lambda: {cat: True for cat in MMS_CATEGORIES}
    )
    
    # Safety & Logistics Triggers
    # Keywords that trigger the 'Flag Agent' to alert the AD
    safety_triggers: Dict[str, List[str]] = Field(default_factory=lambda: {
        "Regulatory": ["Minor", "Child", "8 years old", "Baby"],
        "Sensitive": ["Intimacy", "Nudity", "Kiss", "Sexual"],
        "Stunts": ["Fall", "Crash", "Fight", "Explosion", "Fire", "Flame"],
        "Logistics": ["Car", "Driving", "Rain", "Water", "Animal", "Dog", "Horse"],
        "Weaponry": ["Gun", "Pistol", "Knife", "Sword", "Rifle"],
        "Equipment": ["Crane", "Underwater", "Aerial", "Drone"]
    })

    # Agentic Workflow Toggles
    use_continuity_agent: bool = True
    use_flag_agent: bool = True
    
    # Export Settings
    export_excel: bool = True
    export_csv: bool = True
    export_mms: bool = True
    
    # GUI State
    auto_save_enabled: bool = True

    # --- HELPERS ---
    def set_performance_level(self, mode: str):
        """Updates the thread count based on the selected named mode."""
        if mode in PERFORMANCE_LEVELS:
            self.performance_mode = mode
            self.worker_threads = PERFORMANCE_LEVELS[mode]
            # Debug print to verify it's working
            print(f"DEBUG: Performance set to {mode} ({self.worker_threads} threads)")

# --- GLOBAL INSTANCE ---
# This serves as the 'Live' config the app refers to.
DEFAULT_CONFIG = ProjectConfig()