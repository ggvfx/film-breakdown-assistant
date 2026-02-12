"""
Continuity Agent (Script Supervisor).

Tracks item specificity and cross-scene persistence.
Maintains industry-standard continuity notes for production elements.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

class ContinuityFlag(BaseModel):
    """Represents a single continuity or specificity note."""
    item_name: str = Field(description="The generic name used in the current scene (e.g. 'The bags')")
    resolved_specificity: str = Field(description="The specific identity established previously (e.g. '6 DUFFEL BAGS')")
    note: str = Field(default="", description="Concise continuity instruction for the crew")

class ContinuityResponse(BaseModel):
    """Container for AI response to ensure valid list structure."""
    continuity_notes: List[ContinuityFlag] = Field(description="List of specificity or tracking call-outs")


def get_matchmaker_prompt(scene_text: str, scene_num: str, history_summary: str) -> str:
    """Generates the prompt for syncing current items with the project history."""

    return f"""
    TASK: Script Supervisor Matchmaker - Scene {scene_num}
    
    REFERENCE CATALOG:
    {history_summary}
    
    CURRENT SCRIPT TEXT:
    {scene_text}

    --- MANDATORY LOGIC ---
    1. UNIVERSAL SPECIFICITY: Check for generic nouns. If an item exists in the REFERENCE CATALOG with more detail, create a note. 
    2. STRICT MATCHING: Only map items if they are the same type of object (e.g., "The bag" -> "Duffel Bag"). NEVER match unrelated items (e.g., do NOT map a "Pillar" to a "Counter").
    3. GAP FILLING: If an item from the CATALOG is logically present in this scene but was missed by the harvester, list it here.
    4. THE "NO-PEOPLE" RULE: Strictly ignore all Characters/People (e.g., Jax, Mira). Do not map or track them.
    5. SCOPE: Apply this to all physical production categories in the Catalog (Props, Vehicles, Wardrobe, SFX, etc.).
    6. NO REASONING/ADVICE: Do not explain your logic or provide production advice. Keep notes short and technical (e.g., "Use Scene 1 Duffel Bags").

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


def get_observer_prompt(scene_text: str, scene_num: str) -> str:
    """Generates the prompt for tracking physical state changes of objects."""
    
    return f"""
    TASK: Script Supervisor Observer - Scene {scene_num}
    
    CURRENT SCRIPT TEXT:
    {scene_text}

    --- MANDATORY LOGIC ---
    1. PHYSICAL STATE CHANGES: Record only if an item becomes: Broken, Shattered, Bloody, Burned, or Wetted.
    2. NO CHARACTER ACTIONS: Do not record "Character runs" or "Character jumps." Only record the status of the OBJECT.
    3. THE "NO-PEOPLE" RULE: Strictly ignore all Characters/People.
    4. ZERO HALLUCINATION: If no physical change occurs, return an empty list.

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