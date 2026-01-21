"""
AI Prompt Templates for Script Analysis.

This module focuses strictly on extraction of production elements. 
Narrative tracking (Script Days/Time Instances) is omitted to allow 
the AD to manage scheduling logic directly in Movie Magic.
"""

from typing import List

# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = """
You are a professional Film Assistant Director's breakdown assistant.
Your task is to extract production elements and header metadata from script text.
You must output ONLY valid, minified JSON. No conversational filler.
"""

def get_breakdown_prompt(scene_text: str, selected_categories: List[str], page_num: int) -> str:
    """
    Constructs the prompt for Ollama to analyze a single scene.
    
    Args:
        scene_text: The raw text of the current scene.
        selected_categories: MMS categories the user has checked in the UI.
        page_num: The physical page number of the script.
    """
    
    categories_str = ", ".join(selected_categories)
    
    return f"""
    CONTEXT:
    Script Page: {page_num}

    TASK:
    1. HEADERS: Extract Scene Number, Slugline, INT/EXT, Set Name, and Time of Day.
    2. LENGTH: Estimate the scene length in 8ths of a page (e.g., 4/8, 1 2/8).
    3. SUMMARIES:
       - 'synopsis': A punchy summary of 6 words or less.
       - 'description': A 2-3 sentence overview of the action and characters.
    4. ELEMENTS: Extract every item belonging to these categories: [{categories_str}].

    RULES FOR ELEMENTS:
    - Mark 'source' as 'explicit' if the item is named in the text.
    - Mark 'source' as 'implied' if the item is logically necessary but not named.
    - Provide a 'confidence' score between 0.0 and 1.0.

    OUTPUT FORMAT (JSON):
    {{
        "scene_number": "string",
        "slugline": "string",
        "int_ext": "string",
        "set_name": "string",
        "day_night": "string",
        "pages_whole": integer,
        "pages_eighths": integer,
        "synopsis": "string",
        "description": "string",
        "elements": [
            {{
                "name": "string",
                "category": "string",
                "source": "explicit/implied",
                "confidence": float
            }}
        ],
        "flags": [
            {{
                "flag_type": "string",
                "note": "string",
                "severity": 1-3
            }}
        ]
    }}

    SCRIPT TEXT:
    {scene_text}
    """