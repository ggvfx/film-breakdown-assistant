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

def get_continuity_prompt(
    current_scene_text: str,
    current_scene_num: str,
    history_summary: str
) -> str:
    """
    Generates a prompt for the Script Supervisor agent.
    Maintains all extraction rules while enforcing schema compliance.
    """
    return f"""
    TASK: Script Supervisor Continuity Check for Scene {current_scene_num}.
    
    CONTEXT (PREVIOUSLY ESTABLISHED ITEMS): 
    {history_summary}
    
    CURRENT SCRIPT TEXT:
    {current_scene_text}

    --- EXTRACTION RULES ---
    1. SPECIFICITY MAPPING: Map generic mentions (e.g., 'the car', 'the bags') to established specific items (e.g., 'PORSCHE', 'DUFFEL BAGS').
    2. CALL-OUT: Link generic mentions to specific production items in the note.
    3. STATE CHANGES: Identify if items are destroyed or altered (e.g., 'Pillar is now shattered').
    4. LOGIC ONLY: Do not hallucinate. Only map current text to established history.

    --- OUTPUT INSTRUCTIONS ---
    You MUST return a JSON object with the key "continuity_notes".
    Every finding (Mapping or State Change) must be an object in that list.

    EXAMPLE FOR STATE CHANGE:
    item_name: "Pillar", resolved_specificity: "MARBLE PILLAR", note: "Now shattered by police blast"

    OUTPUT FORMAT:
    {{
      "continuity_notes": [
        {{
          "item_name": "string",
          "resolved_specificity": "string",
          "note": "string"
        }}
      ]
    }}
    """