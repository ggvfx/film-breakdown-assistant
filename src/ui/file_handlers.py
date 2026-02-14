"""
File Operations and Persistence Mixin.

Manages all disk interactions including JSON checkpoints, Excel re-imports,
Movie Magic (.sex) exports, and the automated background save system.
"""
import os
import glob
import pandas as pd
from PySide6.QtWidgets import QFileDialog
from src.core.models import Scene, Element, ReviewFlag
from src.core.utils import save_checkpoint, load_checkpoint

class FileHandlerMixin:

    def reset_ui_and_data(self):
        """Wipes all previous state to prevent cross-contamination between scripts."""
        # 1. Clear Data
        self.current_scenes = []
        
        # 2. Reset UI Elements
        if hasattr(self, 'table'):
            self.table.setRowCount(0)
        self.log_output.clear()
        self.pbar.setValue(0)
        
        # 3. Reset Engine Flag
        if hasattr(self, 'analyzer'):
            self.analyzer.is_running = True
            
        # 4. Lock Review Tab until fresh analysis is done
        self.tabs.setTabEnabled(1, False)

    def handle_file_selection(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Script", "", "Scripts (*.pdf *.fdx *.txt *.docx *.doc *.rtf)")
        if path:
            # If the AI is currently running, stop it before loading a new script
            if hasattr(self, 'worker_thread') and self.worker_thread.isRunning():
                self.stop_analysis() 
                self.worker_thread.wait() # Wait for the kill switch to finish

            self.reset_for_new_project()
            self.lbl_path.setText(path)
            # This is Step 1 from your original main.py:
            raw_text = self.parser.load_script(path, self.config)
            self.current_scenes = self.parser.split_into_scenes(raw_text)
            
            # Update the log so you know it worked
            self.log_output.append(f"INFO: Loaded {path}")
            self.log_output.append(f"INFO: Found {len(self.current_scenes)} scenes.")
            
            # Show FDX checkbox only if needed
            self.chk_fdx.setVisible(path.lower().endswith(".fdx"))

    def load_last_checkpoint(self):
        """Finds the most recent JSON in outputs and loads it into the table."""
        # 1. Look for the most recent checkpoint file
        files = glob.glob(os.path.join("outputs", "*_checkpoint.json"))
        if not files:
            self.log_output.append("ERROR: No checkpoints found in outputs folder.")
            return

        latest_file = max(files, key=os.path.getctime)

        # FACTORY RESET BEFORE LOADING
        self.reset_ui_and_data()
        self.log_output.append(f"INFO: Loading checkpoint: {latest_file}")

        # 2. Use your existing utils logic to load the data
        try:
            # This turns the JSON back into Scene objects
            loaded_scenes = load_checkpoint(latest_file) 
            self.current_scenes = loaded_scenes
            # 3. Populate the Review Table and unlock the tab
            self.populate_table(loaded_scenes)
            self.tabs.setTabEnabled(1, True)
            self.tabs.setCurrentIndex(1) # Switch to the Review tab automatically
            self.log_output.append(f"SUCCESS: Loaded {len(loaded_scenes)} scenes from checkpoint.")
            
        except Exception as e:
            self.log_output.append(f"ERROR: Failed to load checkpoint: {str(e)}")

    def load_manual_checkpoint(self):
        """Allows user to browse for a specific JSON checkpoint file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Checkpoint", 
            "outputs/", 
            "JSON Files (*.json)"
        )
        
        if file_path:
            self.reset_ui_and_data()
            self.log_output.append(f"INFO: Loading selected checkpoint: {os.path.basename(file_path)}")
            
            try:
                loaded_scenes = load_checkpoint(file_path)
                if not loaded_scenes:
                    self.log_output.append("ERROR: File was empty or invalid.")
                    return
                
                self.current_scenes = loaded_scenes
                self.populate_table(self.current_scenes)
                
                self.tabs.setTabEnabled(1, True)
                self.tabs.setCurrentIndex(1)
                self.log_output.append(f"SUCCESS: Loaded {len(loaded_scenes)} scenes.")
                
            except Exception as e:
                self.log_output.append(f"ERROR: Failed to load: {str(e)}")

    def load_excel_checkpoint(self):
        """Re-imports an edited Excel file back into the tool for MMS export."""        
        path, _ = QFileDialog.getOpenFileName(self, "Select Excel Breakdown", "outputs/", "Excel Files (*.xlsx *.xls)")
        if not path:
            return
        
        self.reset_ui_and_data()

        try:
            df = pd.read_excel(path)
            new_scenes = []
            
            # Map of column names to element categories (7 to 29)
            element_cats = [
                "Cast Members", "Background Actors", "Stunts", "Vehicles", "Props", "Camera",
                "Special Effects", "Wardrobe", "Makeup/Hair", "Animals", "Animal Wrangler",
                "Music", "Sound", "Art Department", "Set Dressing", "Greenery", 
                "Special Equipment", "Security", "Additional Labor", "Visual Effects", 
                "Mechanical Effects", "Miscellaneous", "Notes"
            ]

            for _, row in df.iterrows():
                # 1. Reconstruct Elements (Existing logic)
                elements = []
                for cat in element_cats:
                    if pd.notna(row.get(cat)):
                        names = str(row[cat]).split(", ")
                        for n in names:
                            if n.strip():
                                elements.append(Element(name=n.strip(), category=cat))

                # 2. Reconstruct Review Flags
                flags = []
                flag_raw = str(row.get('Review Flags', ''))
                if flag_raw and flag_raw != 'nan':
                    # Split by the separator we used in populate_table
                    parts = flag_raw.split(" | ")
                    for p in parts:
                        # Extract [TYPE] Note
                        if "]" in p:
                            f_type = p[p.find("[")+1 : p.find("]")]
                            f_note = p[p.find("]")+1 :].strip()
                            flags.append(ReviewFlag(flag_type=f_type, note=f_note, severity=1))

                # 3. Reconstruct Page Math
                p_whole = 0
                p_eighths = 0
                pg_str = str(row.get('Pages', '0/8'))
                if pg_str == 'nan': pg_str = '0/8'
                if " " in pg_str:
                    p_whole = int(pg_str.split(" ")[0])
                    p_eighths = int(pg_str.split(" ")[1].split("/")[0])
                elif "/" in pg_str:
                    p_eighths = int(pg_str.split("/")[0])

                # 4. Create the Scene object
                scene = Scene(
                    scene_number=str(row.get('Scene', '0')),
                    int_ext=str(row.get('Int/Ext', 'INT')),
                    set_name=str(row.get('Set', 'UNKNOWN')),
                    day_night=str(row.get('Day/Night', 'DAY')),
                    pages_whole=p_whole,
                    pages_eighths=p_eighths,
                    synopsis=str(row.get('Synopsis', '')),
                    description=str(row.get('Description', '')),
                    elements=elements,
                    continuity_notes=str(row.get('Continuity Notes', '')),
                    flags=flags, # <--- Now passing the parsed flags list
                    scene_index=len(new_scenes)
                )
                new_scenes.append(scene)

            self.current_scenes = new_scenes
            self.populate_table(self.current_scenes)
            self.tabs.setTabEnabled(1, True)
            self.tabs.setCurrentIndex(1)
            self.log_output.append(f"SUCCESS: Imported {len(new_scenes)} scenes from Excel.")

        except Exception as e:
            self.log_output.append(f"ERROR: Excel import failed: {str(e)}")

    def handle_export(self):
        """Processes the checked export formats using the DataExporter."""
        if not self.current_scenes:
            self.log_output.append("ERROR: No data available to export. Load a checkpoint first.")
            return

        # 1. Prepare the output directory
        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)
        
        # Use the script name for the filename if available, otherwise 'Breakdown'
        base_filename = "Breakdown_Export"
        if hasattr(self, 'lbl_path') and self.lbl_path.text() != "No file selected...":
            script_name = os.path.basename(self.lbl_path.text()).split('.')[0]
            base_filename = f"{script_name}_breakdown"

        # 2. Run the exports based on checkboxes
        try:
            exported_files = []
            
            if self.chk_xls.isChecked():
                path = os.path.join(output_dir, f"{base_filename}.xlsx")
                self.exporter.export_to_excel(self.current_scenes, path)
                exported_files.append("Excel")

            if self.chk_csv.isChecked():
                path = os.path.join(output_dir, f"{base_filename}.csv")
                self.exporter.export_to_csv(self.current_scenes, path)
                exported_files.append("CSV")

            if self.chk_sex.isChecked():
                path = os.path.join(output_dir, f"{base_filename}.sex")
                self.exporter.export_to_mms(self.current_scenes, path)
                exported_files.append("MMS (.sex)")

            if exported_files:
                self.log_output.append(f"SUCCESS: Exported {', '.join(exported_files)} to {output_dir}")
            else:
                self.log_output.append("WARNING: No export format selected. Check Excel, CSV, or MMS.")

        except Exception as e:
            self.log_output.append(f"ERROR: Export failed: {str(e)}")

    def handle_user_save(self):
        """Manual save triggered by the user - asks for a filename."""
        path, _ = QFileDialog.getSaveFileName(self, "Save Checkpoint", "outputs/", "JSON (*.json)")
        if path:
            save_checkpoint(self.current_scenes, path)
            self.log_output.append(f"SUCCESS: Manual checkpoint saved to {path}")

    def run_autosave(self):
        """Automatic background save. Rotates through 10 files in /outputs/autosaves/"""
        if not self.chk_auto.isChecked() or not self.current_scenes:
            return
        
        # Create folder if missing
        auto_dir = os.path.join("outputs", "autosaves")
        os.makedirs(auto_dir, exist_ok=True)
        
        if not hasattr(self, '_auto_save_counter'):
            self._auto_save_counter = 1
        
        filename = f"autosave_v{self._auto_save_counter}.json"
        path = os.path.join(auto_dir, filename)
        
        save_checkpoint(self.current_scenes, path)
        self.log_output.append(f"AUTO: Saved backup {self._auto_save_counter}/10")
        
        # Increment and wrap at 10
        self._auto_save_counter = (self._auto_save_counter % 10) + 1

    def reset_autosave_timer(self):
        """Restarts timer with the new interval from the spinbox."""
        mins = self.spin_auto_interval.value()
        self.autosave_timer.start(mins * 60 * 1000)