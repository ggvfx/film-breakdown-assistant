# src/ui/worker.py
from PySide6.QtCore import QObject, Signal, Slot
import asyncio
import builtins

class AnalysisWorker(QObject):
    """The engine that runs the AI in the background."""
    finished = Signal(list)  # Sends the list of processed scenes
    log_signal = Signal(str) # Sends strings to the UI log window

    def __init__(self, analyzer, scenes, categories):
        super().__init__()
        self.analyzer = analyzer
        self.scenes = scenes
        self.categories = categories

    @Slot()
    def run(self):
        """Entry point for the thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # This captures 'print' statements and sends them to the UI
        original_print = builtins.print
        def custom_print(*args, **kwargs):
            msg = " ".join(map(str, args))
            self.log_signal.emit(msg)
            original_print(*args, **kwargs)
        
        builtins.print = custom_print 

        try:
            # This runs your existing analyzer logic
            results = loop.run_until_complete(
                self.analyzer.run_full_pipeline(self.scenes, self.categories)
            )
            self.finished.emit(results)
        finally:
            builtins.print = original_print 
            loop.close()