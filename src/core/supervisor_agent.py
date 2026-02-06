"""
Supervisor Agent: Continuity & Consistency Auditor.

This module acts as a second-pass "Agentic" layer. It reviews the entire 
script's extracted data to ensure continuity (e.g., ensuring a 'Car' in 
Scene 2 is identified as the '1967 MUSTANG' from Scene 1) and logical 
consistency (e.g., ensuring makeup wounds persist across continuous scenes).
"""

import logging
import json
from typing import List, Dict, Any
from src.ai.ollama_client import OllamaClient

class SupervisorAgent:
    def __init__(self, client: OllamaClient):
        self.client = client
        self.logger = logging.getLogger(__name__)

    async def run_audit(self, analyzed_scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Performs a global audit of all scenes to ensure story-wide continuity.
        """
        self.logger.info("Agentic Pass: Starting Script Supervisor audit...")

        # 1. Build Global Context (The "World State")
        global_context = self._build_global_context(analyzed_scenes)
        
        # 2. Process scenes in a reasoning loop
        audited_scenes = []
        for i, scene in enumerate(analyzed_scenes):
            # We provide the agent with the 'World State' and the specific scene
            # In a continuous scene, we also provide the previous scene's context
            prev_scene = audited_scenes[i-1] if i > 0 else None
            
            audited_scene = await self._audit_single_scene(scene, global_context, prev_scene)
            audited_scenes.append(audited_scene)
            
        return audited_scenes

    def _build_global_context(self, scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compiles a list of all unique high-value elements found across the script.
        """
        context = {
            "cast": set(),
            "vehicles": set(),
            "key_props": set()
        }
        for scene in scenes:
            for element in scene.get("elements", []):
                cat = element.get("category")
                name = element.get("name").upper()
                if cat == "Cast Members":
                    context["cast"].add(name)
                elif cat == "Vehicles":
                    context["vehicles"].add(name)
                elif cat == "Props":
                    context["key_props"].add(name)
        
        return {k: list(v) for k, v in context.items()}

    async def _audit_single_scene(self, scene: Dict[str, Any], context: Dict, prev_scene: Dict = None) -> Dict[str, Any]:
        """
        Sends the scene back to the AI with global context for reasoning.
        """
        # Build a prompt that asks the AI to 'reconcile' this scene with the world state
        prompt = f"""
        ACT AS A SCRIPT SUPERVISOR. 
        RECONCILE the elements of Scene {scene['scene_number']} with the Global Script Context.

        GLOBAL CONTEXT (World State):
        - Cast: {context['cast']}
        - Known Vehicles: {context['vehicles']}
        - Key Props: {context['key_props']}

        CURRENT SCENE DATA:
        - Synopsis: {scene['synopsis']}
        - Current Elements: {[e['name'] for e in scene['elements']]}
        
        PREVIOUS SCENE CONTEXT (If relevant):
        - Set: {prev_scene['set_name'] if prev_scene else 'N/A'}
        - Day/Night: {prev_scene['day_night'] if prev_scene else 'N/A'}

        TASK:
        1. SPECIFICITY: If the scene mentions a 'CAR' but the Global Context knows it is a '1967 MUSTANG', update the name.
        2. DIALOGUE: If a prop is mentioned in dialogue but missing from elements, add it.
        3. CONTINUITY: If this scene is CONTINUOUS with the previous, ensure characters and physical states (like wounds) match.

        OUTPUT: Return ONLY the updated "elements" list as JSON.
        """

        try:
            response = await self.client.generate_response(prompt)
            # Basic JSON extraction logic (similar to analyzer.py)
            updated_elements = self._parse_json_response(response)
            if updated_elements:
                scene["elements"] = updated_elements
        except Exception as e:
            self.logger.error(f"Audit failed for scene {scene['scene_number']}: {e}")

        return scene

    def _parse_json_response(self, text: str) -> List[Dict]:
        # Implementation of JSON cleaning/parsing from Ollama output
        try:
            start = text.find('[')
            end = text.rfind(']') + 1
            if start != -1 and end != 0:
                return json.loads(text[start:end])
        except:
            return None
        return None