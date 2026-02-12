"""
Scene Analyzer & Task Manager.

The 'Brain' that coordinates between the Parser and the AI Client.
Handles concurrency (Eco/Power mode) and scene range filtering.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional

from src.ai.ollama_client import OllamaClient
from src.ai.harvester import get_core_prompt, get_set_prompt, get_action_prompt, get_gear_prompt
from src.ai.continuity_agent import get_matchmaker_prompt, get_observer_prompt
from src.ai.flag_agent import get_flag_prompt
from src.core.models import (
    PASS_1_CATEGORIES, PASS_2_CATEGORIES, PASS_3_CATEGORIES, PASS_4_CATEGORIES,
    ReviewFlag
)

class ScriptAnalyzer:
    def __init__(self, client: OllamaClient, config):
        self.client = client
        self.config = config
        self.semaphore = asyncio.Semaphore(config.worker_threads)
        self.master_history = {}
        self.is_running = True

    async def run_full_pipeline(
        self, 
        scenes: List[Dict[str, Any]], 
        categories: List[str],
        from_scene: Optional[str] = None,
        to_scene: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """The main entry point: Filters, then processes scenes through the pipeline."""
        
        # 1. APPLY FILTERING
        active_scenes = self._filter_scenes(scenes, from_scene, to_scene)
        
        processed_scenes = []
        total = len(active_scenes)
        
        for i, scene in enumerate(active_scenes, 1):
            scene_num = scene.get('scene_number', '??')
            print(f"\n>>> [Scene {i}/{total}] Processing Scene {scene_num}...")
            
            # 2. Harvest
            print(f"    - Harvesting elements...")
            harvest_results = await self.run_breakdown([scene], categories)
            current_scene_data = harvest_results[0]
                
            # 3. Continuity
            if self.config.use_continuity_agent:
                print(f"    - Running Continuity...")
                history_str = self._get_history_summary()
                notes = await self.run_continuity_pass(current_scene_data, history_str)
                current_scene_data['continuity_notes'] = notes
                
            # 4. History Update (Silent)
            self._update_history(current_scene_data.get('elements', []))

            # 5. Flags
            if self.config.use_flag_agent:
                print(f"    - Scanning for Safety & Risk Flags...")
                elements_list = current_scene_data.get('elements', [])
                flags = await self.run_flag_pass(current_scene_data['raw_text'], elements_list, scene_num)
                current_scene_data['review_flags'] = flags
                print(f"      Found {len(flags)} review flags.")
                
            processed_scenes.append(current_scene_data)
        
        return processed_scenes
    
    async def run_breakdown(
        self, 
        scenes: List[Dict[str, Any]], 
        selected_categories: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Coordinates the harvesting of elements for the provided scenes.
        """
        tasks = [
            self._process_single_scene(scene, selected_categories) 
            for scene in scenes
        ]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]


    async def _process_single_scene(self, scene: Dict[str, Any], categories: List[str]):
        """
        Coordinates the 4-Pass breakdown (Core, Set, Action, Gear) for a single scene.
        """
        async with self.semaphore:
            if not self.is_running:
                return None

            # ADDED: Define scene number for the print statements below
            s_num = scene.get("scene_number", "??")

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
            print(f"      [Sc {s_num}] Pass 1/4: Core Narrative & Cast...")

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
                print(f"      [Sc {s_num}] Pass 2/4: Set & Vehicles...")
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
                print(f"      [Sc {s_num}] Pass 3/4: Props & SFX...")
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
                print(f"      [Sc {s_num}] Pass 4/4: Technical Gear & Misc...")
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
    
    async def run_flag_pass(self, scene_text: str, elements: List[Dict[str, Any]], scene_num: str) -> List[ReviewFlag]:
        """Final safety pass using the 8B model logic."""
        formatted_elements = "\n".join([f"- {e['category']}: {e['name']}" for e in elements])
        prompt = get_flag_prompt(scene_text, formatted_elements, scene_num)
        
        response = await self.client.generate_breakdown(prompt)
        flags = []
        for f in response.get("review_flags", []):
            try:
                flags.append(ReviewFlag(
                    flag_type=f.get("flag_type", "GENERAL"),
                    note=f.get("note", ""),
                    severity=int(f.get("severity", 1))
                ))
            except Exception as e:
                logging.warning(f"Flag Parse Error: {e}")
        return flags

    def _update_history(self, elements: List[Dict[str, Any]]):
        """Internal helper to keep the 8B model's reference catalog updated."""
        for el in elements:
            cat = el['category'].upper()
            name = el['name'].upper()
            if cat not in self.master_history:
                self.master_history[cat] = set()
            self.master_history[cat].add(name)

    def _get_history_summary(self) -> str:
        """Formats the master history for the Matchmaker prompt."""
        lines = []
        for cat, items in self.master_history.items():
            lines.append(f"CATEGORY {cat}: {', '.join(sorted(list(items)))}")
        return "\n".join(lines) if lines else "CATALOG EMPTY."
    
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