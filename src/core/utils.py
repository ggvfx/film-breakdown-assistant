import json
import os
from typing import List
from src.core.models import Scene

def save_checkpoint(scenes: List[Scene], file_path: str):
    """
    Serializes analyzed scenes to a JSON file.
    Uses Pydantic's .dict() for clean serialization.
    """
    # Convert list of Scene objects to list of dictionaries
    data = [scene.dict() for scene in scenes]
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)

def load_checkpoint(file_path: str) -> List[Scene]:
    """
    Loads analyzed scenes from a JSON file back into Scene objects.
    """
    if not os.path.exists(file_path):
        return []
        
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    # Re-instantiate the Pydantic models from the dictionaries
    return [Scene(**item) for item in data]