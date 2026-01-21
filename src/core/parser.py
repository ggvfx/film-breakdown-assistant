"""
Script Parsing Logic.

Level 2 Logic: Extracts raw text from multiple file formats (.txt, .rtf) 
and identifies scene boundaries using slugline patterns.
"""

import re
import os
from typing import List, Dict, Any
# Note: You will need to run 'pip install striprtf' for the RTF part
from striprtf.striprtf import rtf_to_text

# --- CORE LOGIC ---

class ScriptParser:
    """
    Handles the extraction of text from various file formats 
    and splits them into individual scenes for the AI.
    """

    def __init__(self):
        # Patterns to identify the start of a scene in a standard script
        self.slugline_patterns = [
            r'^INT\.', r'^EXT\.', r'^I/E\.', r'^INT/EXT\.'
        ]

    def load_script(self, file_path: str) -> str:
        """
        Determines the file type and extracts the raw text.

        Args:
            file_path: The full path to the script file.
        """
        extension = os.path.splitext(file_path)[1].lower()
        
        try:
            if extension == ".txt":
                return self._read_txt(file_path)
            elif extension == ".rtf":
                return self._read_rtf(file_path)
            else:
                print(f"Unsupported file type: {extension}")
                return ""
        except Exception as e:
            print(f"Error loading {extension} file: {e}")
            return ""

    def _read_txt(self, file_path: str) -> str:
        """Standard text file reader."""
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()

    def _read_rtf(self, file_path: str) -> str:
        """Converts RTF formatting into plain text."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            return rtf_to_text(content)

    def split_into_scenes(self, full_text: str) -> List[Dict[str, Any]]:
        """
        Splits the text into chunks whenever a slugline is detected.
        
        Returns:
            A list of 'Scene Blocks' for the AI to process.
        """
        # We look for INT. or EXT. at the start of a line
        pattern = r'^(?=(?:INT\.|EXT\.|I/E\.|INT/EXT\.))'
        
        # Split but keep the delimiter (the slugline) in the text
        scene_chunks = re.split(pattern, full_text, flags=re.MULTILINE)
        
        processed_scenes = []
        for index, chunk in enumerate(scene_chunks):
            text = chunk.strip()
            if text:
                processed_scenes.append({
                    "scene_index": index + 1,
                    "raw_text": text,
                    "page_estimate": 1  # Placeholder until we add PDF logic
                })
        
        return processed_scenes
