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
        Compiles a list of unique high-value elements.
        Ensures 'NAME (AGE)' versions prioritized over plain 'NAME'.
        """
        context = {
            "cast": set(),
            "background": set(),
            "vehicles": set(),
            "props": set(),
            "stunts": set(),
            "sfx": set()
        }
        for scene in scenes:
            for element in scene.get("elements", []):
                cat = element.get("category")
                raw_name = element.get("name")
                
                if not raw_name:
                    continue
                
                name = raw_name.upper()
                
                if cat == "Cast Members":
                    context["cast"].add(name)
                elif cat == "Background Actors":
                    context["background"].add(name)
                elif cat == "Vehicles":
                    context["vehicles"].add(name)
                elif cat == "Props":
                    context["props"].add(name)
                elif cat == "Stunts":
                    context["stunts"].add(name)
                elif cat == "Special Effects":
                    context["sfx"].add(name)
        
        # --- CLEANUP LOGIC ---
        # If we have "JAX (32)" and "JAX", remove "JAX" so the AI only sees the aged version.
        cast_list = list(context["cast"])
        final_cast = [name for name in cast_list if not any(
            (name + " (") in other for other in cast_list
        )]

        return {
            "cast": final_cast,
            "background": list(context["background"]),
            "vehicles": list(context["vehicles"]),
            "props": list(context["props"]),
            "stunts": list(context["stunts"]),
            "sfx": list(context["sfx"])
        }


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
        - Background: {context['background']}
        - Vehicles: {context['vehicles']}
        - Known Props: {context['props']}
        - Known Stunts: {context['stunts']}
        - Known SFX: {context['sfx']}

        CURRENT SCENE DATA:
        - Synopsis: {scene['synopsis']}
        - Description: {scene.get('description', '')}
        - Current Elements: {[e.get('name', 'UNKNOWN') for e in scene.get('elements', [])]}
        - Current Flags: {scene.get('flags', [])}
        
        PREVIOUS SCENE CONTEXT (If relevant):
        - Set: {prev_scene.get('set_name', 'N/A') if prev_scene else 'N/A'}
        - Day/Night: {prev_scene.get('day_night', 'N/A') if prev_scene else 'N/A'}

        TASK:
        1. SPECIFICITY: Check the Global Context. If a scene mentions a generic 'CAR' or 'VAN' but the Global Context knows it is the 'GETAWAY VAN', you MUST update the name to 'GETAWAY VAN'. 
        2. CONTINUITY: Ensure character names and physical states are consistent. If JAX is established as 'JAX (32)' in the Global Context, update every instance of 'JAX' to 'JAX (32)'. If a character is 'WET' from rain in Scene 2, they must remain 'WET' in Scene 3 (Continuous).
        3. DEPARTMENTAL LOGIC: 
            - Perform a 'Rule of Touch' audit: If an item is a large architectural build (e.g., COUNTER, PILLAR, VAULT DOOR), move it from 'Props' to 'Art Department'.
            - Action-to-Element: If a synopsis/description mentions 'VAULTING', 'FIGHTING', or 'JUMPING', ensure a corresponding 'Stunt' element exists.
        4. COUNTS & DIALOGUE: 
            - Re-scan scene text for specific digits. If 'TWENTY BYSTANDERS' are mentioned, the 'BYSTANDERS' element MUST have a count of '20'.
            - Extract props mentioned in dialogue (e.g., the 'Silent Alarm') even if they aren't in the action lines.
        5. CLEANUP: If the first pass left 'None' or 'N/A' in flags/alerts, remove them and return an empty array [] unless a real risk is found.

        OUTPUT: Return ONLY a JSON object containing "elements": [] and "flags": [].
        """

        try:
            # 1. Get the raw result
            raw_response = await self.client.generate_breakdown(prompt)
            
            # 2. FORCE PARSE: Turn raw string into list or dict
            if isinstance(raw_response, str):
                audited_result = self._parse_json_response(raw_response)
            else:
                audited_result = raw_response
            
            # CASE A: AI returned a dictionary (likely containing 'elements' and 'flags')
            if isinstance(audited_result, dict):
                # If the AI included the scene_number, we merge everything (your existing logic)
                if "scene_number" in audited_result:
                    scene.update({k: v for k, v in audited_result.items() if v is not None})
                else:
                    # If it only returned the lists, we stitch them into the original scene
                    if "elements" in audited_result:
                        scene["elements"] = audited_result["elements"]
                    if "flags" in audited_result:
                        scene["flags"] = audited_result["flags"]
                return scene
            
            # CASE B: AI returned a LIST (Rescue Mission for strings)
            if isinstance(audited_result, list):
                valid_elements = []
                for item in audited_result:
                    if isinstance(item, dict):
                        valid_elements.append(item)
                    else:
                        # Your existing string protection logic
                        valid_elements.append({
                            "name": str(item).upper(), 
                            "category": "Cast Members" if "(" in str(item) else "Miscellaneous", 
                            "count": "1"
                        })
                # Re-apply to the ORIGINAL scene to keep metadata alive
                scene["elements"] = valid_elements
                return scene

            # Final Fallback
            return scene
            
        except Exception as e:
            self.logger.error(f"Audit failed for scene {scene.get('scene_number', 'Unknown')}: {e}")
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