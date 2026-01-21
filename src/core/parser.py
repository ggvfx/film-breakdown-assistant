"""
Multi-Format Script Parser.

Level 2 Logic: Extracts text from .txt, .rtf, .docx, .pdf, and .fdx files.
Identifies scene boundaries and surgically breaks sluglines into Movie Magic 
components (INT/EXT, Set Name, Day/Night).
"""

import re
import os
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional

import pdfplumber
from docx import Document
from striprtf.striprtf import rtf_to_text

class ScriptParser:
    """
    Handles script extraction and scene mapping for industry-standard formats.
    """

    def __init__(self):
        # Patterns to identify the start of a scene (Sluglines)
        self.slug_regex = r'^(INT\.|EXT\.|I/E\.|INT/EXT\.)'
        
        # Memory to handle 'CONTINUOUS' or 'LATER' logic
        self.last_set_name = ""
        self.last_day_night = ""
        self.last_int_ext = ""

    def load_script(self, file_path: str) -> str:
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
                return self._extract_fdx(file_path)
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

    def _extract_fdx(self, path: str) -> str:
        """Parses Final Draft XML tags directly for high accuracy."""
        tree = ET.parse(path)
        root = tree.getroot()
        lines = []
        for para in root.findall(".//Paragraph"):
            texts = [t.text for t in para.findall("Text") if t.text]
            lines.append("".join(texts))
        return "\n".join(lines)

    def _extract_rtf(self, path: str) -> str:
        """Cleans RTF formatting codes into plain text."""
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return rtf_to_text(f.read())

    def _extract_txt(self, path: str) -> str:
        """Reads standard text files."""
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
        
    def split_into_scenes(self, full_text: str) -> List[Dict[str, Any]]:
        """
        Splits text into components ready for Movie Magic export.
        """
        pattern = f"(?m)({self.slug_regex})"
        parts = re.split(pattern, full_text)
        
        scene_chunks = []
        
        for i in range(1, len(parts), 2):
            prefix = parts[i]
            body = parts[i+1]
            header_line = (prefix + body.split('\n')[0]).strip()
            
            # Extract Components and handle look-back memory
            components = self._get_scene_components(header_line)
            
            # Clean body text (remove the slugline from the start of the body)
            scene_body = "\n".join(body.split('\n')[1:]).strip()
            
            scene_chunks.append({
                "scene_number": self._extract_scene_number(header_line),
                "int_ext": components["int_ext"],
                "set_name": components["set_name"],
                "day_night": components["day_night"],
                "raw_text": scene_body,
                "scene_index": len(scene_chunks) + 1
            })
            
        return scene_chunks

    def _get_scene_components(self, header: str) -> Dict[str, str]:
        """
        Surgically extracts INT/EXT, Set, and Time. 
        Supports standard (INT/EXT) and special prefixes (UNDERWATER, I/E).
        """
        h_up = header.upper().strip()
        triggers = ["CONTINUOUS", "LATER", "SAME", "FOLLOWING", "MOMENTS"]
        
        # 1. Flexible INT/EXT Detection
        # We look at the first word. If it's a common prefix, we use it.
        # Otherwise, we check if it's a "known" special prefix.
        words = h_up.split()
        first_word = words[0].replace(".", "") if words else ""
        
        current_ie = ""
        standard_prefixes = ["INT", "EXT", "IE", "INT/EXT"]
        
        if first_word in standard_prefixes:
            current_ie = first_word
        elif first_word in ["UNDERWATER", "SPACE", "VIRTUAL"]:
            current_ie = first_word
            
        # 2. Split for Set and Time (same as before)
        parts = header.split('-')
        current_set = ""
        current_tod = ""
        
        if len(parts) >= 2:
            current_tod = parts[-1].strip().upper()
            # Clean the set name from the prefix
            current_set = parts[0]
            for pref in standard_prefixes + ["UNDERWATER", "SPACE", "VIRTUAL"]:
                current_set = current_set.upper().replace(f"{pref}.", "").replace(pref, "").strip()
        else:
            current_set = h_up # Mini-slug backup
            
        # 3. Memory Inheritance (as discussed)
        is_lazy = any(word in h_up for word in triggers)
        
        final_ie = current_ie if current_ie or not is_lazy else self.last_int_ext
        final_set = current_set if (len(parts) >= 2 and not is_lazy) else (self.last_set_name if is_lazy else current_set)
        final_tod = self.last_day_night if is_lazy else current_tod

        # Update Memory
        self.last_int_ext = final_ie
        self.last_set_name = final_set
        self.last_day_night = final_tod

        return {
            "int_ext": final_ie,
            "set_name": final_set,
            "day_night": final_tod
        }

    def _extract_scene_number(self, header: str) -> str:
        """Strips 'SCENE' or 'SC' to return just the ID like '15A'."""
        # Remove common prefixes
        clean_header = re.sub(r'(?i)SCENE|SC\.?\s*', '', header).strip()
        # Find the first alphanumeric group
        match = re.search(r'(\d+[A-Z]*)', clean_header)
        return match.group(1) if match else "UNNUMBERED"