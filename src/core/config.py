"""
Global Configuration Management.

Handles user preferences, LLM parameters, and safety triggers.
Designed to be serializable for GUI state persistence.
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field
import subprocess
import psutil
import logging

from src.core.models import MMS_CATEGORIES


# --- PERFORMANCE MAPPING ---
PERFORMANCE_LEVELS = {
    "Eco": 1,
    "Balanced": 2,
    "Turbo": 4
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
    performance_mode: str = "Balanced" 
    worker_threads: int = Field(default=4, ge=1, le=4)

    # Hardware Preference
    use_gpu: bool = True  
    
    # Detected Hardware Info (for UI display)
    detected_gpu_info: str = "Scanning..."
    
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


    def assess_system_hardware(self):
        """
        Detects CPU and GPU to suggest the best initial settings. 
        """
        results = {
            "level": "Eco", 
            "use_gpu": False, 
            "info": "Standard System"
        }
        
        # 1. Check for NVIDIA GPU via nvidia-smi 
        try:
            # check_output returns the status; if it fails, it raises an exception 
            subprocess.check_output(['nvidia-smi'], stderr=subprocess.STDOUT)
            results["use_gpu"] = True
            results["level"] = "Turbo" # Suggested for GPU users 
            results["info"] = "NVIDIA GPU Detected (RTX/GTX)"
        except (Exception, FileNotFoundError):
            # 2. Fallback: Check CPU cores for non-GPU systems 
            cpu_count = psutil.cpu_count(logical=False) or 4
            if cpu_count >= 6:
                results["level"] = "Balanced"
                results["info"] = f"{cpu_count}-Core CPU Detected"
            else:
                results["level"] = "Eco"
                results["info"] = "Mobile/Low-power CPU Detected"
        
        self.detected_gpu_info = results["info"]
        return results

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