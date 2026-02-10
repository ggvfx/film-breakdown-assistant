"""
flag_agent.py
-------------
Role: Production Safety & Risk Assessment
Goal: Scans elements for high-risk items and generates a single 'Review Flags' 
      list for the AD to audit.
"""

from pydantic import BaseModel, Field
from typing import List

class ReviewFlag(BaseModel):
    category: str = Field(description="The production area (e.g., SAFETY, BUDGET, LOGISTICS)")
    issue: str = Field(description="What the AD needs to check (e.g., 'Confirm fire permit for explosion')")
    severity: str = Field(description="Low, Medium, or High")

class FlagResponse(BaseModel):
    review_flags: List[ReviewFlag]


"""
        --- 3. REVIEW FLAG SCANNING ---
    Generate 'ReviewFlag' for:
    - REGULATORY: 'Minor', 'Child', 'Baby' -> Severity 3 (Legal requirement).
    - SENSITIVE: 'Intimacy', 'Nudity', 'Kiss' -> Severity 2 (Closed set needed).
    - SAFETY: 'Fire', 'Explosion', 'Fight', 'Fall' -> Severity 3 (Stunt Coordinator needed).
    - WEAPONRY: 'Gun', 'Knife', 'Sword' -> Severity 3 (Armorer needed).
    - LOGISTICS: 'Rain', 'Water', 'Car', 'Animal' -> Severity 1 (High cost/prep).
    - EQUIPMENT: 'Cranes', 'Drones', 'Underwater' -> Severity 1 (High cost/prep).
    *If none, return []*

"""
	
	"flags": [
            {{
                "flag_type": "string",
                "note": "string",
                "severity": integer
            }}
        ]