"""
Scene Analyzer & Task Manager.

Coordinates the 4-Pass AI breakdown, continuity checks, and safety flagging.
Manages concurrency and scene range filtering.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional

from src.ai.ollama_client import OllamaClient
from src.ai.harvester import get_core_prompt, get_set_prompt, get_action_prompt, get_gear_prompt
from src.ai.continuity_agent import get_matchmaker_prompt, get_observer_prompt
from src.ai.flag_agent import get_flag_prompt
from src.core.models import (
    Scene, Element, ReviewFlag,
    PASS_1_CATEGORIES, PASS_2_CATEGORIES, PASS_3_CATEGORIES, PASS_4_CATEGORIES
)

class ScriptAnalyzer:
    """
    Orchestrates the AI analysis pipeline for script scenes.
    """

    def __init__(self, client: OllamaClient, config):
        self.client = client
        self.config = config
        self.semaphore = asyncio.Semaphore(config.worker_threads)
        self.master_history = {}
        self.is_running = True

    async def run_full_pipeline(
        self, 
        scenes: List[Scene], 
        categories: List[str],
        from_scene: Optional[str] = None,
        to_scene: Optional[str] = None,
        progress_callback: Optional[callable] = None
    ) -> List[Scene]:
        """
        Processes the filtered scene list through the multi-pass AI pipeline.
        """
        
        # --- PERFORMANCE CHECK ---
        self.semaphore = asyncio.Semaphore(self.config.worker_threads)

        # 1. APPLY FILTERING
        active_scenes = self._filter_scenes(scenes, from_scene, to_scene)
        
        processed_scenes = []
        total = len(active_scenes)
        
        for i, scene in enumerate(active_scenes, 0):
            if not self.is_running:
                break
                
            print(f"\n>>> [Scene {i + 1}/{total}] Processing Scene {scene.scene_number}...")

            # Milestone: Scene Started (20% through this scene)
            if progress_callback: progress_callback(i + 0.2, total)
            
            # 2. HARVEST (Passes 1-4)
            # We pass a list of one scene to maintain the run_breakdown signature
            harvest_results = await self.run_breakdown([scene], categories)
            if not harvest_results:
                continue
            
            current_scene = harvest_results[0]

            # Milestone: Harvest Complete (50% through this scene)
            if progress_callback: progress_callback(i + 0.5, total)
                
            # 3. CONTINUITY
            if self.config.use_continuity_agent:
                print(f"    - Running Continuity...")
                history_str = self._get_history_summary()
                # Pass the raw text and number from the model
                notes = await self.run_continuity_pass(current_scene, history_str)
                # This prevents the description from becoming a giant wall of text
                current_scene.continuity_notes = notes

            # Milestone: Continuity Done (80% through this scene)
            if progress_callback: progress_callback(i + 0.8, total)
                
            # 4. HISTORY UPDATE
            # Pass the scene_number so the dictionary can store it
            self._update_history(current_scene.elements, current_scene.scene_number)

            # 5. FLAGS
            if self.config.use_flag_agent:
                print(f"    - Scanning for Safety & Risk Flags...")
                flags = await self.run_flag_pass(
                    current_scene.script_text, 
                    current_scene.elements, 
                    current_scene.scene_number
                )
                current_scene.flags = flags
                print(f"      Found {len(flags)} review flags.")
                
            processed_scenes.append(current_scene)

            # Milestone: Scene Finished (100% through this scene)
            if progress_callback: progress_callback(i + 1.0, total)
        
        return processed_scenes
    
    async def run_breakdown(
        self, 
        scenes: List[Scene], 
        selected_categories: List[str]
    ) -> List[Scene]:
        """Coordinates the concurrent harvesting of elements."""
        tasks = [
            self._process_single_scene(scene, selected_categories) 
            for scene in scenes
        ]
        results = await asyncio.gather(*tasks)
        return [r for r in results if r is not None]

    async def _process_single_scene(self, scene: Scene, categories: List[str]) -> Optional[Scene]:
        """Coordinates the 4-Pass breakdown for a single scene using worker threads."""
        if not self.is_running:
            return None

        llm_options = {
            "temperature": self.config.temperature,
            "num_gpu": 99 if self.config.use_gpu else 0
        }
        is_conservative = self.config.conservative_mode
        allow_implied = self.config.extract_implied_elements

        # --- HELPER: Handles one AI call and respects the Thread Limit ---
        async def run_ai_call(prompt_func, active_cats, label):
            # Each individual pass checks the semaphore bowl for a token
            async with self.semaphore:
                print(f"      [Sc {scene.scene_number}] Pass {label}...")
                prompt = prompt_func(
                    scene_text=scene.description if label != "Core Narrative" else scene.script_text,
                    scene_num=scene.scene_number,
                    selected_tech_cats=active_cats,
                    conservative=is_conservative,
                    implied=allow_implied
                )
                # If it's Pass 1, we use the core prompt logic
                if label == "Core Narrative":
                    # Note: Pass 1 uses more variables, usually handled in the prompt_func itself
                    pass 
                
                return await self.client.generate_breakdown(prompt, options=llm_options)

        # 1. CATEGORY MAPPING
        active_p1 = [c for c in categories if c in PASS_1_CATEGORIES]
        active_p2 = [c for c in categories if c in PASS_2_CATEGORIES]
        active_p3 = [c for c in categories if c in PASS_3_CATEGORIES]
        active_p4 = [c for c in categories if c in PASS_4_CATEGORIES]

        # 2. PASS 1 (CORE) - Must run first to generate the scene description
        # We call the core prompt directly here to maintain your current variables
        async with self.semaphore:
            print(f"      [Sc {scene.scene_number}] Pass 1/4: Core Narrative...")
            core_prompt = get_core_prompt(
                scene.script_text, scene.scene_number, scene.set_name,
                scene.day_night, scene.int_ext, active_p1, is_conservative, allow_implied
            )
            core_result = await self.client.generate_breakdown(core_prompt, options=llm_options)

        if not core_result:
            return None

        scene.synopsis = core_result.get("synopsis", "")[:150]
        scene.description = core_result.get("description", "")
        
        all_elements = []
        if "elements" in core_result:
            all_elements.extend([Element(**e) for e in core_result["elements"]])

        # 3. PASSES 2-4 (TECHNICAL) - Run these in parallel
        tech_tasks = []
        if active_p2: tech_tasks.append(run_ai_call(get_set_prompt, active_p2, "Set & Vehicles"))
        if active_p3: tech_tasks.append(run_ai_call(get_action_prompt, active_p3, "Props & SFX"))
        if active_p4: tech_tasks.append(run_ai_call(get_gear_prompt, active_p4, "Technical Gear"))

        # Fire all technical passes at once!
        # If worker_threads=1, they run one-by-one. If worker_threads=4, they run all at once.
        results = await asyncio.gather(*tech_tasks)

        for res in results:
            if res and "elements" in res:
                all_elements.extend([Element(**e) for e in res["elements"]])

        scene.elements = all_elements
        return scene
        

    async def run_continuity_pass(self, scene: Scene, history_summary: str) -> str:
        """Runs Matchmaker and Observer agents to check for script consistency."""
        res_a = await self.client.generate_breakdown(
            get_matchmaker_prompt(scene.script_text, scene.scene_number, history_summary)
        )
        res_b = await self.client.generate_breakdown(
            get_observer_prompt(scene.script_text, scene.scene_number)
        )
        
        notes_a = res_a.get('continuity_notes') if res_a else []
        notes_b = res_b.get('continuity_notes') if res_b else []
        
        all_notes = (notes_a if isinstance(notes_a, list) else []) + \
                    (notes_b if isinstance(notes_b, list) else [])

        formatted = []
        for n in all_notes:
            if isinstance(n, dict):
                name = n.get('item_name') or n.get('item') or "Unknown"
                spec = n.get('resolved_specificity') or "N/A"
                note = n.get('note') or ""
                formatted.append(f"{name} -> {spec}: {note}")
            elif isinstance(n, str):
                formatted.append(n)

        return " | ".join(formatted) if formatted else ""
    
    async def run_flag_pass(self, text: str, elements: List[Element], scene_num: str) -> List[ReviewFlag]:
        """Safety pass to identify production risks."""
        elem_str = "\n".join([f"- {e.category}: {e.name}" for e in elements])
        prompt = get_flag_prompt(text, elem_str, scene_num)
        
        response = await self.client.generate_breakdown(prompt)
        flags = []
        for f in response.get("review_flags", []):
            try:
                flags.append(ReviewFlag(
                    flag_type=f.get("flag_type", "GENERAL"),
                    note=f.get("note", ""),
                    severity=int(f.get("severity", 1))
                ))
            except Exception:
                continue
        return flags

    def _update_history(self, elements: List[Element], scene_num: str):
        """Updates history with item name and the specific scene number."""
        for el in elements:
            cat = el.category.upper()
            name = el.name.upper().strip()
            if cat not in self.master_history:
                self.master_history[cat] = {}  # Now a dictionary
            # Store the scene number as the value
            self.master_history[cat][name] = scene_num

    def _get_history_summary(self) -> str:
        """Formats history: 'CATEGORY: ITEM (Sc 1), ITEM (Sc 2)'"""
        if not self.master_history:
            return "CATALOG EMPTY."
        
        lines = []
        for cat, items in self.master_history.items():
            # Create strings that look like "DUFFEL BAGS (Sc 1)"
            item_refs = [f"{name} (Sc {sn})" for name, sn in items.items()]
            lines.append(f"CATEGORY {cat}: {', '.join(sorted(item_refs))}")
        return "\n".join(lines)
    
    def _filter_scenes(self, scenes: List[Scene], start_num: str, end_num: str) -> List[Scene]:
        """Filters the scene list based on start and end scene numbers."""
        if not start_num and not end_num:
            return scenes
        
        start_idx = 0
        end_idx = len(scenes)

        for i, s in enumerate(scenes):
            if start_num and s.scene_number.strip().upper() == str(start_num).upper():
                start_idx = i
            if end_num and s.scene_number.strip().upper() == str(end_num).upper():
                end_idx = i + 1
        
        return scenes[start_idx:end_idx]

    def stop(self):
        """Signals the analyzer to stop processing."""
        self.is_running = False