import asyncio
import os
import logging
from src.core.parser import ScriptParser
from src.core.analyzer import ScriptAnalyzer
from src.core.exporter import DataExporter
from src.ai.ollama_client import OllamaClient
from src.core.config import DEFAULT_CONFIG

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

async def main():
    # --- 1. INITIALIZATION ---
    parser = ScriptParser()
    
    # Use the model name defined in your config (llama3.2)
    client = OllamaClient(model_name=DEFAULT_CONFIG.ollama_model) 
    
    # Use the worker_threads from your config (currently 1)
    analyzer = ScriptAnalyzer(client, config=DEFAULT_CONFIG)
    #supervisor = SupervisorAgent(client)
    exporter = DataExporter()

    # --- 2. LOAD & PARSE ---
    # Ensure this matches the name of the multi-scene script you generated
    script_path = "tests/TheHeistExit-script.pdf"
    #script_path = "tests/TheBrokenWindow - script.docx" 
    #script_path = "tests/TheDiscovery -script.txt"  
    
    if not os.path.exists(script_path):
        logging.error(f"File not found: {script_path}. Please check your 'tests' folder.")
        return

    logging.info(f"Step 1: Parsing {script_path} into scenes...")
    raw_text = parser.load_script(script_path)
    print(f"DEBUG: Raw text length: {len(raw_text)} characters.")
    print(f"DEBUG: First 500 characters: {raw_text[:500]}")
    scenes = parser.split_into_scenes(raw_text)
    logging.info(f"Found {len(scenes)} scenes.")

    # --- 3. ANALYZE (The AI Part) ---
    logging.info(f"Step 2: Sending {len(scenes)} scenes to AI (Ollama)...")
    
    selected_categories = DEFAULT_CONFIG.mms_categories
    
    # We use from_scene="1" and to_scene="4" to match your 4 parsed scenes
    analyzed_scenes = await analyzer.run_breakdown(
        scenes=scenes,
        selected_categories=selected_categories,
        from_scene=None,
        to_scene=None
    )

    # CLI Progress: This confirms each scene processed with its unique name
    for scene in analyzed_scenes:
        logging.info(f"DONE: Scene {scene.get('scene_number')} - {scene.get('set_name')} ({scene.get('day_night')})")

    # --- 3.5 CONTINUITY PASS (Conditional) ---
    if DEFAULT_CONFIG.use_continuity_agent:
        logging.info("Step 2.5: Running Script Supervisor check...")
        master_history_dict = {}

        for scene in analyzed_scenes:
            # 1. Format history as a clean "Catalog"
            history_lines = []
            for cat, items in master_history_dict.items():
                # Sorting items helps the model process them consistently
                sorted_items = sorted(list(items))
                history_lines.append(f"CATEGORY {cat}: {', '.join(sorted_items)}")
            
            history_str = "\n".join(history_lines) if history_lines else "CATALOG EMPTY."
            
            # 2. Run continuity
            notes = await analyzer.run_continuity_pass(scene, history_str)
            scene['continuity_notes'] = notes
            
            # 3. Update history (Keep it categorized)
            for el in scene.get('elements', []):
                if isinstance(el, dict) and el.get('name') and el.get('category'):
                    cat = el['category'].upper()
                    name = el['name'].upper()
                    if cat not in master_history_dict:
                        master_history_dict[cat] = set()
                    master_history_dict[cat].add(name)

    # --- 4. EXPORT ---
    logging.info("Step 3: Generating Excel validation sheet...")
    export_path = "outputs/breakdown_test.xlsx"
    
    # Ensure the output directory exists
    os.makedirs("outputs", exist_ok=True)
    
    exporter.export_to_excel(analyzed_scenes, export_path)
    logging.info(f"DONE! Review your breakdown here: {export_path}")

if __name__ == "__main__":
    asyncio.run(main())