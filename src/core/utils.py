"""
Utility Functions for Data Persistence.

Handles saving and loading of scene checkpoints to JSON.
Supports the 'Auto-Save' and 'Recovery' features for the breakdown process.
"""

import json
import os
import logging
from typing import List
from src.core.models import Scene

# --- CHECKPOINT LOGIC ---

def save_checkpoint(scenes: List[Scene], file_path: str):
    """
    Serializes analyzed scenes to a JSON file.
    
    Args:
        scenes: The list of validated Scene objects.
        file_path: Destination path for the JSON save.
    """
    try:
        # Ensure the directory exists before saving
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # .model_dump() is the modern Pydantic v2 way to get a dictionary
        # We use it instead of .dict() for better compatibility
        data = [scene.model_dump() for scene in scenes]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
            
    except Exception as e:
        logging.error(f"Failed to save checkpoint to {file_path}: {e}")

def load_checkpoint(file_path: str) -> List[Scene]:
    """
    Loads analyzed scenes from a JSON file back into Scene objects.
    
    Returns:
        List[Scene]: A list of re-instantiated Scene models, or empty list on failure.
    """
    if not os.path.exists(file_path):
        return []
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # Re-instantiate the Pydantic models from the dictionaries
        # This automatically re-validates the data during the load
        return [Scene(**item) for item in data]
        
    except (json.JSONDecodeError, TypeError) as e:
        logging.error(f"Checkpoint corrupted at {file_path}: {e}")
        return []
    except Exception as e:
        logging.error(f"Unexpected error loading checkpoint: {e}")
        return []