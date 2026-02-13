"""
AI Analysis Coordination Mixin.

Handles the orchestration of the 4-Pass AI breakdown process, including
UI-to-Config synchronization, scene range filtering, and thread management.
"""
from PySide6.QtCore import QThread
from src.ui.worker import AnalysisWorker

class AnalysisHandlerMixin:
    def start_analysis(self):
        """Prepares config and starts the background worker with optional range filtering."""
        # 1. Safety Check
        if not self.current_scenes:
            self.log_output.append("ERROR: No scenes to analyze. Please select a script first.")
            return

        # 2. Identify selected categories
        active_cats = [c for c, cb in self.cat_boxes.items() if cb.isChecked()]
        if not active_cats:
            self.log_output.append("WARNING: No categories selected for extraction.")

        # 3. Sync UI Settings to Config
        self.config.set_performance_level(self.combo_perf.currentText())
        self.config.use_continuity_agent = self.chk_cont.isChecked()
        self.config.use_flag_agent = self.chk_flag.isChecked()
        self.config.temperature = self.spin_temp.value()
        self.config.conservative_mode = self.chk_cons.isChecked()
        self.config.extract_implied_elements = self.chk_implied.isChecked()
        
        # 4. Handle Scene Range Filtering
        scenes_to_process = self.current_scenes
        if self.rad_range.isChecked():
            start_scene = self.txt_range_from.text().strip().upper()
            end_scene = self.txt_range_to.text().strip().upper()
            
            filtered = []
            active = False
            for s in self.current_scenes:
                # Use string comparison for alphanumeric scene numbers
                curr_num = str(s.scene_number).upper()
                if curr_num == start_scene: 
                    active = True
                if active: 
                    filtered.append(s)
                if curr_num == end_scene: 
                    break
            
            if not filtered:
                self.log_output.append(f"ERROR: Range {start_scene} to {end_scene} not found in current script.")
                return
            
            scenes_to_process = filtered
            self.log_output.append(f"INFO: Range selected. Processing {len(scenes_to_process)} scenes.")

        # 5. Setup Worker & Thread
        self.btn_run.setEnabled(False)
        self.pbar.setValue(0)
        
        self.worker_thread = QThread()
        self.worker = AnalysisWorker(self.analyzer, scenes_to_process, active_cats)
        self.worker.moveToThread(self.worker_thread)
        
        # 6. Connect Signals
        self.worker_thread.started.connect(self.worker.run)
        self.worker.log_signal.connect(self.log_output.append)
        
        if hasattr(self.worker, 'progress_signal'):
            self.worker.progress_signal.connect(self.pbar.setValue) 
        
        self.worker.finished.connect(self.on_analysis_finished)
        
        self.worker_thread.start()
        self.log_output.append(f"START: Analyzing {len(scenes_to_process)} scenes...")

    def on_analysis_finished(self, results):
        """Called when AI processing is complete."""
        self.btn_run.setEnabled(True)
        self.worker_thread.quit()
        
        # Update memory with the analyzed scenes
        self.current_scenes = results
        
        # Fill the table
        self.populate_table(self.current_scenes)
        
        # Unlock the review tab and switch to it
        self.tabs.setTabEnabled(1, True)
        self.tabs.setCurrentIndex(1) 
        
        self.log_output.append("SUCCESS: Analysis complete. Data moved to Review Tab.")
        self.pbar.setValue(100)