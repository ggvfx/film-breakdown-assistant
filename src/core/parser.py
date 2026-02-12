"""
Multi-Format Script Parser.

Extracts text from various script formats and identifies scene boundaries.
Converts raw script text into validated Scene models.
"""

import re
import os
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional

import pdfplumber
from docx import Document
from striprtf.striprtf import rtf_to_text

from src.core.config import ProjectConfig
from src.core.models import Scene

class ScriptParser:
    """
    Handles script extraction and scene mapping for industry-standard formats.
    """

    def __init__(self):
        # Patterns to identify the start of a scene (Sluglines)
        self.slug_regex = r'^\s*(?:\d+\s+)?(?:INT\.|EXT\.|I/E\.|INT/EXT\.)'
        
        # Memory to handle 'CONTINUOUS' or 'LATER' logic inheritance
        self.last_set_name = ""
        self.last_day_night = ""
        self.last_int_ext = ""

    def load_script(self, file_path: str, config: ProjectConfig) -> str:
        """Determines file type and routes to the correct extractor."""
        extension = os.path.splitext(file_path)[1].lower()
        
        try:
            if extension == ".pdf":
                return self._extract_pdf(file_path)
            elif extension == ".docx":
                return self._extract_docx(file_path)
            elif extension == ".rtf":
                return self._extract_rtf(file_path)
            elif extension == ".fdx":
                return self._extract_fdx(file_path, import_tags=config.import_fdx_tags)
            elif extension == ".txt":
                return self._extract_txt(file_path)
            else:
                return f"Unsupported format: {extension}"
        except Exception as e:
            return f"Error extracting {extension}: {str(e)}"

    def _extract_pdf(self, path: str) -> str:
        """Extracts text while maintaining script layout columns."""
        text = ""
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text += page.extract_text(layout=True) + "\n"
        return text

    def _extract_docx(self, path: str) -> str:
        """Extracts text from Word paragraphs."""
        doc = Document(path)
        return "\n".join([para.text for para in doc.paragraphs])

    def _extract_fdx(self, path: str, import_tags: bool = False) -> str:
        """Parses Final Draft XML tags directly for high accuracy."""
        tree = ET.parse(path)
        root = tree.getroot()
        lines = []
        for para in root.findall(".//Paragraph"):
            texts = [t.text for t in para.findall("Text") if t.text]
            combined_text = "".join(texts)
            
            if import_tags:
                tags = para.findall(".//Tag")
                for tag in tags:
                    tag_val = tag.get("Value")
                    if tag_val:
                        combined_text += f" [[TAG: {tag_val}]]"
            
            lines.append(combined_text)
        return "\n".join(lines)

    def _extract_rtf(self, path: str) -> str:
        """Cleans RTF formatting codes into plain text."""
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return rtf_to_text(f.read())

    def _extract_txt(self, path: str) -> str:
        """Reads standard text files."""
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
        
    def split_into_scenes(self, full_text: str) -> List[Scene]:
        """
        Splits text into Scene objects ready for breakdown.
        
        This list acts as the foundation for the 4-Pass AI Analysis.
        """
        pattern = f"(?m)({self.slug_regex})"
        parts = re.split(pattern, full_text)
        
        scenes = []
        
        for i in range(1, len(parts), 2):
            prefix = parts[i]
            body = parts[i+1]
            header_line = (prefix + body.split('\n')[0]).strip()
            
            components = self._get_scene_components(header_line)
            scene_body = "\n".join(body.split('\n')[1:]).strip()
            
            # Page Math
            line_count = len(scene_body.split('\n'))
            total_eighths = max(1, round((line_count / 54) * 8))

            # Create the Scene object
            new_scene = Scene(
                scene_number=self._extract_scene_number(header_line),
                int_ext=components["int_ext"],
                set_name=components["set_name"],
                day_night=components["day_night"],
                pages_whole=total_eighths // 8,
                pages_eighths=total_eighths % 8,
                script_text=scene_body,
                description="",
                scene_index=len(scenes) + 1
            )
            scenes.append(new_scene)
            
        return scenes

    def _get_scene_components(self, header: str) -> Dict[str, str]:
        """Surgically extracts INT/EXT, Set, and Time from a slugline."""
        header = re.sub(r'^\s*(\d+[A-Z]*|[A-Z]+\d+)\b', '', header, flags=re.IGNORECASE).strip()
        header = re.sub(r'\b(\d+[A-Z]*|[A-Z]+\d+)\s*$', '', header, flags=re.IGNORECASE).strip()
        
        h_up = header.upper().strip()
        triggers = ["CONTINUOUS", "LATER", "SAME", "FOLLOWING", "MOMENTS"]
        
        # 1. Determine INT/EXT
        standard_prefixes = ["INT", "EXT", "INT/EXT", "I/E"]
        current_ie = ""
        
        words = h_up.split()
        if words:
            first_word = words[0].replace(".", "")
            if first_word in standard_prefixes:
                current_ie = "INT/EXT" if first_word == "IE" else first_word
            elif first_word in ["UNDERWATER", "SPACE", "VIRTUAL"]:
                current_ie = "INT"
        
        # 2. Split Set and Time
        parts = header.rsplit('-', 1)
        current_set = ""
        current_tod = ""
        
        if len(parts) >= 2:
            current_set = parts[0].strip()
            current_tod = parts[1].strip().upper()
            
            for pref in standard_prefixes + ["UNDERWATER", "SPACE", "VIRTUAL"]:
                pattern = re.compile(re.escape(pref) + r'\.?\s*', re.IGNORECASE)
                current_set = pattern.sub('', current_set).strip()
        else:
            current_set = header.strip()
            
        # 3. Handle Inheritance
        is_lazy = any(word in h_up for word in triggers)
        
        final_ie = current_ie if current_ie else (self.last_int_ext if is_lazy else "INT")
        final_set = current_set if current_set else (self.last_set_name if is_lazy else "UNKNOWN SET")
        final_tod = current_tod if (current_tod and not is_lazy) else (self.last_day_night if is_lazy else "DAY")

        self.last_int_ext = final_ie
        self.last_set_name = final_set
        self.last_day_night = final_tod

        return {
            "int_ext": final_ie,
            "set_name": final_set,
            "day_night": final_tod
        }

    def _extract_scene_number(self, header: str) -> str:
        """Returns the scene ID (e.g., '15A')."""
        clean_header = re.sub(r'(?i)SCENE|SC\.?\s*', '', header).strip()
        match = re.search(r'(\d+[A-Z]*)', clean_header)
        return match.group(1) if match else "0"