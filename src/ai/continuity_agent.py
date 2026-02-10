"""
continuity_agent.py
-------------------
Role: Script Supervisor
Goal: Cross-references the Harvester's output with the Scene Synopsis to ensure 
      lead characters and key elements mentioned in the story are present in the data.
"""

from pydantic import BaseModel, Field
from typing import List

class ContinuityInsight(BaseModel):
    missing_element: str = Field(description="Name of the character or item found in synopsis but missing from extraction")
    context: str = Field(description="Short quote or reason why this is needed for continuity")

class ContinuityResponse(BaseModel):
    suggested_additions: List[ContinuityInsight]