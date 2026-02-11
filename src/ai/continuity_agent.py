"""
continuity_agent.py
-------------------
Role: Script Supervisor
Goal: Tracks item specificity (e.g., 'Car' vs 'Porsche') and cross-scene persistence.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

class ContinuityFlag(BaseModel):
    item_name: str = Field(description="The generic name used in the current scene (e.g. 'The bags')")
    resolved_specificity: str = Field(description="The specific identity established previously (e.g. '6 DUFFEL BAGS')")
    note: str = Field(description="Concise continuity instruction for the crew")

class ContinuityResponse(BaseModel):
    continuity_notes: List[ContinuityFlag] = Field(description="List of specificity or tracking call-outs")


def get_matchmaker_prompt(current_scene_text: str, current_scene_num: str, history_summary: str) -> str:
    return f"""
    TASK: Script Supervisor Matchmaker - Scene {current_scene_num}
    
    REFERENCE CATALOG:
    {history_summary}
    
    CURRENT SCRIPT TEXT:
    {current_scene_text}

    --- MANDATORY LOGIC ---
    1. SPECIFICITY LOOKUP: Identify generic nouns in the CURRENT SCRIPT. Look for a match in the REFERENCE CATALOG. 
       - If Script says "The [Generic Item]" and Catalog has a "[Specific Version]", map them.
    2. ZERO HALLUCINATION RULE: 
       - Do NOT use items from the prompt examples. 
       - Do NOT use items from the catalog unless they are the SAME OBJECT as the script noun.
       - If no match exists, return "continuity_notes": [].
    3. IGNORE CHARACTERS: Do not map people (George, Mary, etc).

    --- OUTPUT FORMAT ---
    Return ONLY valid JSON:
    {{
      "continuity_notes": [
        {{
          "item_name": "Noun from script",
          "resolved_specificity": "Exact match from Reference Catalog",
          "note": "State change or production instruction"
        }}
      ]
    }}
    """

def get_observer_prompt(current_scene_text: str, current_scene_num: str) -> str:
    return f"""
    TASK: Script Supervisor Observer - Scene {current_scene_num}
    
    CURRENT SCRIPT TEXT:
    {current_scene_text}

    --- MANDATORY LOGIC ---
    1. STATE CHANGES: If an item in the script is damaged or altered, record its NEW CONDITION in the 'note' field.
    2. ZERO HALLUCINATION RULE: 
       - Do NOT use items from the prompt examples. 
       - Do NOT use items from the catalog unless they are the SAME OBJECT as the script noun.
       - If no match exists, return "continuity_notes": [].

    --- OUTPUT FORMAT ---
    Return ONLY valid JSON:
    {{
      "continuity_notes": [
        {{
          "item_name": "Noun from script",
          "resolved_specificity": "N/A",
          "note": "State change or production instruction"
        }}
      ]
    }}
    """