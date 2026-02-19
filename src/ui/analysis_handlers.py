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

        # --- KILL SWITCH LOGIC ---
        # If worker exists and thread is running, this click means "STOP"
        if hasattr(self, 'worker_thread') and self.worker_thread.isRunning():
            self.stop_analysis()
            return
        
        # 1. Safety Check
        if not self.current_scenes:
            self.log_output.append("ERROR: No scenes to analyze. Please select a script first.")
            return
        
        # Ensure threads from previous script run are completely dead before starting.
        if hasattr(self, 'worker_thread'):
            if self.worker_thread.isRunning():
                self.worker_thread.quit()
                self.worker_thread.wait()
        
        # Reset Analyzer engine
        if hasattr(self, 'analyzer'):
            self.analyzer.is_running = True

        # 2. Identify selected categories
        active_cats = [c for c, cb in self.cat_boxes.items() if cb.isChecked()]
        if not active_cats:
            self.log_output.append("WARNING: No categories selected for extraction.")

        # 3. Sync UI Settings to Config
        self.config.set_performance_level(self.combo_perf.currentText())
        self.config.use_continuity_agent = self.chk_cont.isChecked()
        self.config.use_flag_agent = self.chk_flag.isChecked()
        #self.config.temperature = self.spin_temp.value()
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

        scenes_to_process = [s for s in scenes_to_process if not s.synopsis or s.synopsis.strip() == ""]

        if not scenes_to_process:
            self.log_output.append("INFO: All scenes in the selected range have already been analyzed.")
            return

        self.expected_count = len(scenes_to_process)

        # 5. Setup Worker & Thread
        self.btn_run.setText("STOP EXTRACTION")
        self.btn_run.setStyleSheet("""
            QPushButton { background-color: #b71c1c; color: white; border-radius: 5px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background-color: #d32f2f; }
        """)
        self.pbar.setValue(0)

        # Ensure old thread is fully dead before starting new one
        if hasattr(self, 'worker_thread') and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()
        
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

    def stop_analysis(self):
        """Sends the stop signal to the analyzer."""
        if hasattr(self, 'analyzer'):
            self.analyzer.stop() # Sets is_running to False in the core
            self.log_output.append("\n!!! STOP SIGNAL SENT. Finishing current scene and exiting...")
            self.btn_run.setEnabled(False) # Prevent multiple clicks while winding down

    def on_analysis_finished(self, results):
        """Called when AI processing is complete (or stopped)."""
        # Reset Button to RUN mode
        self.btn_run.setEnabled(True)
        self.btn_run.setText("RUN")
        self.btn_run.setStyleSheet("""
            QPushButton { background-color: #424242; color: white; border-radius: 5px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background-color: #2e7d32; }
        """)
        self.worker_thread.quit()
        self.worker_thread.wait()

        # Only update if we actually got data back
        if results:
            # Create a lookup map for the processed scenes
            result_map = {str(s.scene_number): s for s in results}
            
            # Update only the scenes that were processed in the original list
            for i, original_scene in enumerate(self.current_scenes):
                scene_key = str(original_scene.scene_number)
                if scene_key in result_map:
                    self.current_scenes[i] = result_map[scene_key]
            
            # Now fill the table with the full, updated master list
            self.populate_table(self.current_scenes)
            
            # UI Feedback
            self.tabs.setTabEnabled(1, True)
            self.tabs.setCurrentIndex(1) 

            if len(results) >= getattr(self, 'expected_count', 0):
                self.pbar.setValue(100)
                self.log_output.append(f"SUCCESS: Analysis complete. {len(results)} scenes updated.")
            else:
                # If stopped, the bar remains at its last reported position
                self.log_output.append(f"STOPPED: Partial results saved ({len(results)}/{self.expected_count} scenes).")
        else:
            self.log_output.append("INFO: Analysis ended with no new data.")
            self.pbar.setValue(0)