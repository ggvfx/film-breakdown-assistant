import asyncio
import os
import logging
from src.core.parser import ScriptParser
from src.core.analyzer import ScriptAnalyzer
from src.core.exporter import DataExporter
from src.ai.ollama_client import OllamaClient
from src.core.config import DEFAULT_CONFIG
from src.core.models import MMS_CATEGORIES

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

    # --- 3. ANALYSIS & PROCESSING ---
    logging.info("Step 2: Running Unified Pipeline (Harvester -> Continuity -> Flags)...")
    
    # This now handles everything internally and provides its own logs
    analyzed_scenes = await analyzer.run_full_pipeline(scenes, MMS_CATEGORIES)

    # --- 4. EXPORT ---
    logging.info("Step 3: Generating Excel validation sheet...")
    export_path = "outputs/breakdown_test.xlsx"
    
    # Ensure the output directory exists
    os.makedirs("outputs", exist_ok=True)
    
    exporter.export_to_excel(analyzed_scenes, export_path)
    logging.info(f"DONE! Review your breakdown here: {export_path}")

if __name__ == "__main__":
    asyncio.run(main())