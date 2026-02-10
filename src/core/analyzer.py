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
from src.ai.harvester import get_core_prompt, get_elements_prompt
# Import the category split lists
from src.core.models import PASS_1_CATEGORIES, PASS_2_CATEGORIES

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
        Coordinates the 2-Pass breakdown for a single scene.
        """
        async with self.semaphore:
            if not self.is_running:
                return None

            # --- 1. PREP SETTINGS & CATEGORIES ---
            llm_options = {"temperature": self.config.temperature}
            is_conservative = self.config.conservative_mode
            allow_implied = self.config.extract_implied_elements

            # Identify which selected categories belong in which pass
            active_p1 = [c for c in categories if c in PASS_1_CATEGORIES]
            active_p2 = [c for c in categories if c in PASS_2_CATEGORIES]

            # --- 2. PASS 1: CORE (Synopsis, Description, Cast, BG, Stunts) ---
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

            # --- 3. PASS 2: ELEMENTS (Physical Departments) ---
            # We only run Pass 2 if there are technical categories selected
            elements_result = {"elements": []}
            if active_p2:
                elements_prompt = get_elements_prompt(
                    scene_text=scene["raw_text"],
                    scene_num=scene["scene_number"],
                    selected_tech_cats=active_p2,
                    conservative=is_conservative,
                    implied=allow_implied
                )
                elements_result = await self.client.generate_breakdown(elements_prompt, options=llm_options)

            # --- 4. MERGE & RESTORE ---
            if core_result:
                # Capture Parser math to prevent AI overwrite
                pages_whole = scene.get("pages_whole", 0)
                pages_eighths = scene.get("pages_eighths", 0)

                # Merge Pass 1 (Synopsis, Elements, etc.)
                scene.update(core_result)

                # Merge Pass 2 Elements into the existing list
                if elements_result and "elements" in elements_result:
                    if "elements" not in scene:
                        scene["elements"] = []
                    scene["elements"].extend(elements_result["elements"])

                # Safety: Fix scene identification and restore math
                scene["scene_number"] = scene["scene_number"]
                scene["scene_index"] = scene["scene_index"]
                scene["pages_whole"] = pages_whole
                scene["pages_eighths"] = pages_eighths
                
                return scene
            
            return None

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