"""
Main Application Orchestrator.

Ties together the Parser, Analyzer, and Exporters.
Coordinates the flow from raw script file to production-ready breakdown data.
"""

import asyncio
import os
import logging
from src.core.parser import ScriptParser
from src.core.analyzer import ScriptAnalyzer
from src.core.exporter import DataExporter
from src.ai.ollama_client import OllamaClient
from src.core.config import DEFAULT_CONFIG
from src.core.models import MMS_CATEGORIES
from src.core.utils import save_checkpoint

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

async def main():

    # --- 1. INITIALIZATION ---
    parser = ScriptParser()
    client = OllamaClient(model_name=DEFAULT_CONFIG.ollama_model) 
    analyzer = ScriptAnalyzer(client, config=DEFAULT_CONFIG)
    exporter = DataExporter()

    # --- 2. LOAD & PARSE ---
    script_path = "tests/TheHeistExit-script.pdf"
    
    if not os.path.exists(script_path):
        logging.error(f"File not found: {script_path}.")
        return

    DEFAULT_CONFIG.last_directory = os.path.dirname(os.path.abspath(script_path))

    logging.info(f"Step 1: Parsing {script_path}...")
    raw_text = parser.load_script(script_path, DEFAULT_CONFIG)
    
    # Updated: Parser now returns objects, not dicts, based on our earlier review
    scenes = parser.split_into_scenes(raw_text)
    logging.info(f"Found {len(scenes)} scenes.")

    # --- 3. ANALYSIS & PROCESSING ---
    logging.info("Step 2: Running Unified AI Pipeline...")
    analyzed_scenes = await analyzer.run_full_pipeline(scenes, MMS_CATEGORIES)

    # --- 4. DATA PERSISTENCE (AUTO-SAVE) ---
    if DEFAULT_CONFIG.auto_save_enabled:
        base_filename = os.path.splitext(os.path.basename(script_path))[0]
        checkpoint_path = os.path.join("outputs", f"{base_filename}_checkpoint.json")
        os.makedirs("outputs", exist_ok=True)
        save_checkpoint(analyzed_scenes, checkpoint_path)
        logging.info(f"Auto-save: Data saved to {checkpoint_path}")

    # --- 5. EXPORT ---
    base_filename = os.path.splitext(os.path.basename(script_path))[0]
    os.makedirs("outputs", exist_ok=True)

    # Excel Export (Human Review)
    if DEFAULT_CONFIG.export_excel:
        export_path = os.path.join("outputs", f"{base_filename}_breakdown.xlsx")
        exporter.export_to_excel(analyzed_scenes, export_path)
        logging.info(f"Exported Excel: {export_path}")

    # CSV Export (General Interchange)
    if DEFAULT_CONFIG.export_csv:
        csv_path = os.path.join("outputs", f"{base_filename}_breakdown.csv")
        exporter.export_to_csv(analyzed_scenes, csv_path)
        logging.info(f"Exported CSV: {csv_path}")

    # Movie Magic Export (Primary Production Target)
    if DEFAULT_CONFIG.export_mms:
        mms_path = os.path.join("outputs", f"{base_filename}_breakdown.sex")
        exporter.export_to_mms(analyzed_scenes, mms_path)
        logging.info(f"Exported Movie Magic XML: {mms_path}")

if __name__ == "__main__":
    asyncio.run(main())