"""
Film Breakdown Assistant - Main Entry Point.

Coordinates the end-to-end pipeline: 
Load Script -> Parse Scenes -> AI Analysis -> Excel Export.
"""

import asyncio
import os
import logging
from core.parser import ScriptParser
from core.analyzer import ScriptAnalyzer
from core.exporter import DataExporter
from ai.ollama_client import OllamaClient

# Setup basic logging to see what's happening in the terminal
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

async def main():
    # --- 1. INITIALIZATION ---
    parser = ScriptParser()
    client = OllamaClient(model_name="llama3.2")
    # Concurrency: 1 = Eco Mode, 4 = Power Mode
    analyzer = ScriptAnalyzer(client, concurrency_limit=2) 
    exporter = DataExporter()

    # --- 2. LOAD & PARSE ---
    # Replace with your actual test script path
    script_path = "tests/test_script.pdf" 
    
    if not os.path.exists(script_path):
        logging.error(f"File not found: {script_path}")
        return

    logging.info("Step 1: Parsing script into scenes...")
    raw_text = parser.load_script(script_path)
    scenes = parser.split_into_scenes(raw_text)
    logging.info(f"Found {len(scenes)} scenes.")

    # --- 3. ANALYZE (The AI Part) ---
    logging.info("Step 2: Sending scenes to AI (Ollama)...")
    
    # We define which categories to look for (from our models.py list)
    selected_categories = [
        "Cast Members", "Props", "Stunts", "Vehicles", "Background Actors"
    ]
    
    # Run the analysis (you can specify scene ranges here)
    analyzed_scenes = await analyzer.run_breakdown(
        scenes=scenes,
        selected_categories=selected_categories,
        from_scene="1",
        to_scene="5"
    )

    # --- 4. EXPORT ---
    logging.info("Step 3: Generating Excel validation sheet...")
    export_path = "outputs/breakdown_test.xlsx"
    
    # Ensure the output directory exists
    os.makedirs("outputs", exist_ok=True)
    
    exporter.export_to_excel(analyzed_scenes, export_path)
    logging.info(f"DONE! Review your breakdown here: {export_path}")

if __name__ == "__main__":
    # The entry point to run our async main loop
    asyncio.run(main())