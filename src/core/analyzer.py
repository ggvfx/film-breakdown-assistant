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
from src.ai.harvester import get_breakdown_prompt

class ScriptAnalyzer:
    """
    Manages the batch processing of scenes through the AI.
    """

    def __init__(self, client: OllamaClient, concurrency_limit: int = 1):
        self.client = client
        # This 'gatekeeper' controls how many scenes run at once
        self.semaphore = asyncio.Semaphore(concurrency_limit)
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
        A single worker task that waits for its turn to talk to the AI.
        """
        async with self.semaphore:
            if not self.is_running:
                return None

            # Build the prompt using the Parser's clean components
            prompt = get_breakdown_prompt(
                scene_text=scene["raw_text"],
                selected_categories=categories,
                scene_num=scene["scene_number"],
                set_name=scene["set_name"],
                day_night=scene["day_night"],
                int_ext=scene["int_ext"]
            )

            # Send to AI
            raw_result = await self.client.generate_breakdown(prompt)
            
            if raw_result:
                # 1. Capture the Parser's valid math before the AI merge
                pages_whole = scene.get("pages_whole", 0)
                pages_eighths = scene.get("pages_eighths", 0)

                # 2. Existing safety overrides - Fix the AI result before merging
                raw_result["scene_number"] = scene["scene_number"]
                raw_result["scene_index"] = scene["scene_index"]

                # 3. Merge AI results into the scene dictionary
                scene.update(raw_result)

                # Put Review Flags in AD Alerts for export
                if "flags" in raw_result:
                    for flag in raw_result["flags"]:
                        # 1. Extract the logic OUTSIDE of the dictionary literal
                        raw_type = flag.get('flag_type') or "GENERAL"
                        flag_note = flag.get('note') or "Review required"
                            
                        # 2. Now build the alert_element dictionary
                        alert_element = {
                            "name": f"ALERT: {raw_type.upper()} - {flag_note}",
                            "category": "AD Alerts",
                            "count": "1",
                            "source": "implied",
                            "confidence": 1.0
                        }
                        # This 'sticks' it into the elements list for the exporter
                        if "elements" not in scene:
                            scene["elements"] = []
                        scene["elements"].append(alert_element)

                # 4. Force-restore the Parser's math to prevent AI 'None' overwrites
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