# gui_app.py
import sys
from PySide6.QtWidgets import QApplication

# 1. Import your existing logic (Exactly as you have them in main.py)
from src.ai.ollama_client import OllamaClient
from src.core.analyzer import ScriptAnalyzer
from src.core.parser import ScriptParser
from src.core.exporter import DataExporter
from src.core.config import DEFAULT_CONFIG

# 2. Import your new GUI visuals
from src.ui.main_window import MainWindow

def run_gui():
    # Initialize the Qt Application
    app = QApplication(sys.argv)
    
    # Initialize your existing backend objects
    # These are the "hours of work" we are preserving
    client = OllamaClient(model_name=DEFAULT_CONFIG.ollama_model) 
    analyzer = ScriptAnalyzer(client, config=DEFAULT_CONFIG)
    parser = ScriptParser()
    exporter = DataExporter()

    # Pass everything to the Window
    # The Window now has access to the analyzer, parser, and exporter
    # Pass the analyzer, config, parser, and exporter into the window
    window = MainWindow(analyzer, DEFAULT_CONFIG, parser=parser, exporter=exporter)
    
    # Attach the parser and exporter to the window so it can use them later
    window.parser = parser
    window.exporter = exporter
    
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    run_gui()