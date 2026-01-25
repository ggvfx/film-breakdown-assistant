"""
AI Prompt Templates for Script Analysis.

This module focuses strictly on extraction of production elements. 
Header data is provided by the Parser to ensure 100% accuracy for 
Movie Magic Scheduling exports.
"""

from typing import List

# --- SYSTEM PROMPT ---
SYSTEM_PROMPT = """
You are a professional Film Assistant Director's breakdown assistant.
Your task is to extract production elements and metadata from script text.
You must output ONLY valid, minified JSON. No conversational filler.
"""

def get_breakdown_prompt(
    scene_text: str, 
    selected_categories: List[str], 
    page_num: int,
    scene_num: str,
    set_name: str,
    day_night: str,
    int_ext: str
) -> str:
    """
    Constructs the prompt for Llama 3.2. Provides known header info as context.
    """
    
    categories_str = ", ".join(selected_categories)
    
    return f"""
    CONTEXT:
    Current Scene: {scene_num}
    Type: {int_ext}
    Set: {set_name}
    Time of Day: {day_night}
    Script Page: {page_num}

    TASK:
    1. LENGTH: Estimate the scene length in 8ths of a page (e.g., 4/8, 1 2/8).
    2. SUMMARIES:
       - 'synopsis': A punchy summary of 6 words or less for Movie Magic.
       - 'description': A 2-3 sentence overview of the action.
    3. ELEMENTS: Extract every item belonging to these categories: [{categories_str}].

    RULES FOR ELEMENTS:
    - 'name': The name of the item or character.
    - 'count': How many? (e.g., "6", "2", or "1"). Use "1" as default.
    - 'source': 'explicit' if literally in text, 'implied' if it must exist (e.g. 'Smoke' for a 'Fire').
    - 'confidence': score between 0.0 and 1.0.

    OUTPUT FORMAT (JSON):
    {{
        "pages_whole": integer,
        "pages_eighths": integer,
        "synopsis": "string",
        "description": "string",
        "elements": [
            {{
                "name": "string",
                "category": "string",
                "count": "string",
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