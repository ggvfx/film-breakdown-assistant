"""
Scene Analyzer & Task Manager.

The 'Brain' that coordinates between the Parser and the AI Client.
Handles concurrency (Eco/Power mode) and scene range filtering.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional

# Local modules
from src.ai.ollama_client import OllamaClient
# Import the two new pass prompts
from src.ai.harvester import get_core_prompt, get_set_prompt, get_action_prompt, get_gear_prompt
# Import the category split lists
from src.core.models import PASS_1_CATEGORIES, PASS_2_CATEGORIES, PASS_3_CATEGORIES, PASS_4_CATEGORIES

# Agentic passes
from src.ai.continuity_agent import get_matchmaker_prompt, get_observer_prompt


class ScriptAnalyzer:
    """
    Manages the batch processing of scenes through the AI.
    """

    def __init__(self, client: OllamaClient, config):
        self.client = client
        self.config = config 
        self.semaphore = asyncio.Semaphore(config.worker_threads) 
        self.is_running = True

    async def run_breakdown(
        self, 
        scenes: List[Dict[str, Any]], 
        selected_categories: List[str],
        from_scene: Optional[str] = None,
        to_scene: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Processes a list of scenes, respecting the selected range and Eco/Power mode.
        """
        # 1. Filter scenes by range ('Mapping' logic)
        target_scenes = self._filter_scenes(scenes, from_scene, to_scene)

        # If the user provided a range that found nothing, we stop early
        if not target_scenes:
            logging.warning("No scenes found in the selected range.")
            return []
        
        # 2. Create a list of 'Tasks' for the AI
        tasks = [
            self._process_single_scene(scene, selected_categories) 
            for scene in target_scenes
        ]
        
        # 3. Execute all tasks and wait for results
        # 'gather' runs them concurrently up to the semaphore limit
        results = await asyncio.gather(*tasks)
        
        # Filter out any 'None' results from failed AI calls
        return [r for r in results if r is not None]

    async def _process_single_scene(self, scene: Dict[str, Any], categories: List[str]):
        """
        Coordinates the 4-Pass breakdown (Core, Set, Action, Gear) for a single scene.
        """
        async with self.semaphore:
            if not self.is_running:
                return None

            # --- 1. PREP SETTINGS & CATEGORIES ---
            llm_options = {"temperature": self.config.temperature}
            is_conservative = self.config.conservative_mode
            allow_implied = self.config.extract_implied_elements

            # Map categories to their respective departmental passes
            active_p1 = [c for c in categories if c in PASS_1_CATEGORIES]
            active_p2 = [c for c in categories if c in PASS_2_CATEGORIES]
            active_p3 = [c for c in categories if c in PASS_3_CATEGORIES]
            active_p4 = [c for c in categories if c in PASS_4_CATEGORIES]

            # Store original parser math to prevent AI hallucination overwrite
            original_math = {
                "pages_whole": scene.get("pages_whole", 0),
                "pages_eighths": scene.get("pages_eighths", 0),
                "scene_number": scene.get("scene_number"),
                "scene_index": scene.get("scene_index")
            }

            # --- 2. EXECUTE PASSES ---
            # Pass 1: Core Narrative & People
            core_prompt = get_core_prompt(
                scene_text=scene["raw_text"],
                scene_num=scene["scene_number"],
                set_name=scene["set_name"],
                day_night=scene["day_night"],
                int_ext=scene["int_ext"],
                selected_core_cats=active_p1,
                conservative=is_conservative,
                implied=allow_implied
            )
            core_result = await self.client.generate_breakdown(core_prompt, options=llm_options)

            # Pass 2: Set (Vehicles, Art Dept, Greenery, etc.)
            set_result = {"elements": []}
            if active_p2:
                set_prompt = get_set_prompt(
                    scene_text=scene["raw_text"],
                    scene_num=scene["scene_number"],
                    selected_tech_cats=active_p2,
                    conservative=is_conservative,
                    implied=allow_implied
                )
                set_result = await self.client.generate_breakdown(set_prompt, options=llm_options)

            # Pass 3: Action (Props, SFX, Labor, etc.)
            action_result = {"elements": []}
            if active_p3:
                action_prompt = get_action_prompt(
                    scene_text=scene["raw_text"],
                    scene_num=scene["scene_number"],
                    selected_tech_cats=active_p3,
                    conservative=is_conservative,
                    implied=allow_implied
                )
                action_result = await self.client.generate_breakdown(action_prompt, options=llm_options)

            # Pass 4: Gear (Camera, Sound, Gear, Misc)
            gear_result = {"elements": []}
            if active_p4:
                gear_prompt = get_gear_prompt(
                    scene_text=scene["raw_text"],
                    scene_num=scene["scene_number"],
                    selected_tech_cats=active_p4,
                    conservative=is_conservative,
                    implied=allow_implied
                )
                gear_result = await self.client.generate_breakdown(gear_prompt, options=llm_options)

            # --- 3. MERGE & VALIDATE ---
            if core_result:
                # Merge Pass 1 as the base (Synopsis and Description)
                scene.update(core_result)
                
                # Consolidate elements from all technical passes
                all_elements = []
                if "elements" in core_result:
                    all_elements.extend(core_result["elements"])
                
                for res in [set_result, action_result, gear_result]:
                    if res and "elements" in res:
                        all_elements.extend(res["elements"])
                
                scene["elements"] = all_elements

                # Restore original metadata to maintain integrity
                scene.update(original_math)
                
                return scene
            
            return None
        

    async def run_continuity_pass(self, scene_data: dict, history_summary: str) -> str:
        
        # 1. Call both specialized prompts
        res_a = await self.client.generate_breakdown(
            get_matchmaker_prompt(scene_data.get('raw_text', ""), scene_data.get('scene_number', "0"), history_summary)
        )
        res_b = await self.client.generate_breakdown(
            get_observer_prompt(scene_data.get('raw_text', ""), scene_data.get('scene_number', "0"))
        )
        
        # 2. Extract and combine the lists
        notes_a = res_a.get('continuity_notes') if res_a else []
        notes_b = res_b.get('continuity_notes') if res_b else []
        
        # This creates one master list for your existing loop to process
        notes = (notes_a if isinstance(notes_a, list) else []) + \
                (notes_b if isinstance(notes_b, list) else [])

        if not notes:
            return ""
        
        formatted = []
        for n in notes:
            if isinstance(n, dict):
                # Map potential halluncinated keys back to our required format
                name = n.get('item_name') or n.get('item') or "Unknown"
                spec = n.get('resolved_specificity') or n.get('specificity_mapping') or "N/A"
                note = n.get('note') or n.get('call_out') or n.get('message') or ""
                formatted.append(f"{name} -> {spec}: {note}")
            elif isinstance(n, str):
                formatted.append(n)

        return "\n".join(formatted)


    def _filter_scenes(self, scenes, start_num, end_num):
        """Filters the master list based on scene IDs like '15A'."""
        if not start_num and not end_num:
            return scenes
        
        # Convert to strings for safe comparison
        start_str = str(start_num).strip().upper() if start_num else None
        end_str = str(end_num).strip().upper() if end_num else None

        # Logic: Find the index of the 'start' and 'end' scenes in our Map
        start_idx = 0
        end_idx = len(scenes)

        for i, s in enumerate(scenes):
            current_num = str(s["scene_number"]).strip().upper()
            if start_str and current_num == start_str:
                start_idx = i
            if end_str and current_num == end_str:
                end_idx = i + 1
        
        return scenes[start_idx:end_idx]

    def stop(self):
        """Emergency stop for the analysis process."""
        self.is_running = False