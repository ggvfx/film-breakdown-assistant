import os
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QCheckBox, QComboBox, QProgressBar, 
    QTextEdit, QTableWidget, QFileDialog, QGroupBox, QScrollArea, 
    QHeaderView, QTableWidgetItem, QDoubleSpinBox, QSpinBox
)
from PySide6.QtCore import Qt, QThread, QTimer
from src.ui.worker import AnalysisWorker
from src.core.models import MMS_CATEGORIES

class MainWindow(QMainWindow):
    def __init__(self, analyzer, config, parser=None, exporter=None):
        super().__init__()
        self.analyzer = analyzer
        self.config = config
        self.parser = parser      
        self.exporter = exporter
        self.current_scenes = [] # Populated after file selection/parsing
        
        self.setWindowTitle("Film Script AI Breakdown Tool")
        self.resize(1200, 850)

        # Main Tab Widget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Initialize Tabs
        self.setup_tab = QWidget()
        self.review_tab = QWidget()
        self.tabs.addTab(self.setup_tab, "Setup & Extraction")
        self.tabs.addTab(self.review_tab, "Review Data")
        self.tabs.setTabEnabled(1, False) # Disabled until run/load

        self._build_setup_ui()
        self._build_review_ui()

    def _build_setup_ui(self):
        layout = QVBoxLayout(self.setup_tab)
        layout.setSpacing(15)
        # Add this line: it forces all widgets to stay at the top of the tab
        layout.setAlignment(Qt.AlignTop)

        # 1 Script Selection & Project Management (Renamed and Grouped)
        selection_group = QGroupBox("Script Selection & Project Management")
        sl = QVBoxLayout()
        
        # Row 1: File Button and Path
        file_row = QHBoxLayout()
        self.btn_select = QPushButton("Select Script File")
        self.btn_select.clicked.connect(self.handle_file_selection)
        self.lbl_path = QLabel("No file selected...")
        self.chk_fdx = QCheckBox("Extract Final Draft Tags")
        self.chk_fdx.setVisible(False)
        file_row.addWidget(self.btn_select)
        file_row.addWidget(self.lbl_path, 1)
        file_row.addWidget(self.chk_fdx)
        sl.addLayout(file_row)

        # Row 2: Load Button and Log Checkbox
        util_row = QHBoxLayout()
        self.btn_load = QPushButton("Load Last Checkpoint")
        self.btn_load.clicked.connect(self.load_last_checkpoint)
        self.chk_expand_log = QCheckBox("Expand Log")
        # Logic to expand window down
        self.chk_expand_log.toggled.connect(self.toggle_log_expansion)
        util_row.addWidget(self.btn_load)
        util_row.addStretch()
        util_row.addWidget(self.chk_expand_log)
        sl.addLayout(util_row)
        
        selection_group.setLayout(sl)
        layout.addWidget(selection_group)

        # 2 Element Settings (Vertical Reading Grid)
        element_group = QGroupBox("Elements to Extract")
        ext_v = QVBoxLayout()
        scroll = QScrollArea()
        scroll_content = QWidget()
        self.cat_grid = QGridLayout(scroll_content)
        
        # Grid math for Vertical Reading
        rows_desired = 8 
        self.cat_boxes = {}
        for i, cat in enumerate(MMS_CATEGORIES):
            cb = QCheckBox(cat)
            cb.setChecked(True)
            self.cat_boxes[cat] = cb
            self.cat_grid.addWidget(cb, i % rows_desired, i // rows_desired)
            
        scroll.setWidget(scroll_content)
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(220)
        ext_v.addWidget(scroll)

        # Agent Toggles
        agent_l = QHBoxLayout()
        self.chk_cont = QCheckBox("Run Continuity Agent")
        self.chk_flag = QCheckBox("Run Review Flag Agent")
        self.chk_cont.setChecked(self.config.use_continuity_agent)
        self.chk_flag.setChecked(self.config.use_flag_agent)
        agent_l.addWidget(self.chk_cont); agent_l.addWidget(self.chk_flag)
        ext_v.addLayout(agent_l)
        element_group.setLayout(ext_v)
        layout.addWidget(element_group)

        # 3 Technical Settings
        tech_group = QGroupBox("Technical Settings")
        tl = QVBoxLayout()
        
        # Top Row: Temp, Conservative, Implied
        top_row = QHBoxLayout()
        top_row.addWidget(QLabel("Temperature:"))
        self.spin_temp = QDoubleSpinBox()
        self.spin_temp.setRange(0.0, 1.0); self.spin_temp.setSingleStep(0.1); self.spin_temp.setValue(0.0)
        self.chk_cons = QCheckBox("Conservative Mode")
        self.chk_implied = QCheckBox("Extract Implied")
        self.chk_cons.setChecked(self.config.conservative_mode)
        top_row.addWidget(self.spin_temp); top_row.addWidget(self.chk_cons); top_row.addWidget(self.chk_implied)
        tl.addLayout(top_row)

        # Bottom Row: Performance
        perf_row = QHBoxLayout()
        self.combo_perf = QComboBox()
        self.combo_perf.addItems(["Eco", "Power", "Turbo", "Max"])
        self.combo_perf.setCurrentText(self.config.performance_mode)
        perf_row.addWidget(QLabel("Performance Level:"))
        perf_row.addWidget(self.combo_perf)
        perf_row.addStretch()
        tl.addLayout(perf_row)
        
        tech_group.setLayout(tl)
        layout.addWidget(tech_group)

        # 4. Styled Run Button (Gray to Green Hover)
        layout.addSpacing(20) # Head space
        self.btn_run = QPushButton("RUN")
        self.btn_run.setFixedHeight(50)
        self.btn_run.setStyleSheet("""
            QPushButton { background-color: #424242; color: white; border-radius: 5px; font-weight: bold; font-size: 14px; }
            QPushButton:hover { background-color: #2e7d32; }
        """)
        self.btn_run.clicked.connect(self.start_analysis)
        
        # 5. Centered Progress Bar
        self.pbar = QProgressBar()
        self.pbar.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(self.btn_run)
        layout.addWidget(self.pbar)
        # 1. Add the log first
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setVisible(False)
        layout.addWidget(self.log_output)

        # 2. Insert a spacer ABOVE the log (at the index before the log)
        # We don't save it to a variable, we will find it by its position.
        #layout.addStretch(1)

    def toggle_log_expansion(self, visible):
        """Grows the window down. Items stay at the top due to AlignTop."""
        current_w = self.width()
        current_h = self.height()
        log_height = 250 

        if visible:
            self.log_output.setFixedHeight(log_height)
            self.log_output.setVisible(True)
            self.resize(current_w, current_h + log_height)
        else:
            self.log_output.setVisible(False)
            # This ensures the window actually snaps back up
            self.resize(current_w, current_h - log_height)
            
        # Forces the window to recalculate and remove any 'ghost' grey space
        self.update()

    def _build_review_ui(self):
        layout = QVBoxLayout(self.review_tab)
        
        self.table = QTableWidget()
        # Set to 32 columns based on your CSV reference
        self.table.setColumnCount(32) 
        self.table.setHorizontalHeaderLabels([
            "Scene", "Int/Ext", "Set", "Day/Night", "Pages", "Synopsis", "Description",
            "Cast Members", "Background Actors", "Stunts", "Vehicles", "Props", "Camera",
            "Special Effects", "Wardrobe", "Makeup/Hair", "Animals", "Animal Wrangler",
            "Music", "Sound", "Art Department", "Set Dressing", "Greenery", 
            "Special Equipment", "Security", "Additional Labor", "Visual Effects", 
            "Mechanical Effects", "Miscellaneous", "Notes", "Continuity Notes", "Review Flags"
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setWordWrap(True)
        layout.addWidget(self.table)

        # Bottom Bar
        bot = QHBoxLayout()
        
        # User Save Button
        self.btn_save = QPushButton("Save Checkpoint")
        self.btn_save.clicked.connect(self.handle_user_save) 
        
        # Autosave Controls
        self.chk_auto = QCheckBox("Autosave every")
        self.chk_auto.setChecked(True)
        
        self.spin_auto_interval = QSpinBox()
        self.spin_auto_interval.setRange(1, 60)
        self.spin_auto_interval.setValue(5) 
        self.spin_auto_interval.setSuffix(" mins")
        # Update timer if the user changes the number
        self.spin_auto_interval.valueChanged.connect(self.reset_autosave_timer)

        # Setup the Timer
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.run_autosave)
        self.autosave_timer.start(5 * 60 * 1000) # Start at 5 mins (ms)

        # Export Group
        export_box = QGroupBox("Export Options")
        eb_l = QHBoxLayout()
        self.chk_xls = QCheckBox("Excel")
        self.chk_csv = QCheckBox("CSV")
        self.chk_sex = QCheckBox("MMS (.sex)")
        self.btn_export = QPushButton("EXPORT")
        self.btn_export.clicked.connect(self.handle_export)
        eb_l.addWidget(self.chk_xls); eb_l.addWidget(self.chk_csv); eb_l.addWidget(self.chk_sex); eb_l.addWidget(self.btn_export)
        export_box.setLayout(eb_l)

        # Assemble Bottom Bar
        bot.addWidget(self.btn_save)
        bot.addSpacing(20) # Space between User Save and Autosave
        bot.addWidget(self.chk_auto)
        bot.addWidget(self.spin_auto_interval)
        bot.addStretch()
        bot.addWidget(export_box)
        layout.addLayout(bot)

    def populate_table(self, scenes):
        """Fills the Review Tab table with all 32 columns from core.models."""
        self.table.setRowCount(len(scenes))
        
        # List of element categories in the exact order they appear in your CSV (columns 7 to 29)
        element_categories = [
            "Cast Members", "Background Actors", "Stunts", "Vehicles", "Props", "Camera",
            "Special Effects", "Wardrobe", "Makeup/Hair", "Animals", "Animal Wrangler",
            "Music", "Sound", "Art Department", "Set Dressing", "Greenery", 
            "Special Equipment", "Security", "Additional Labor", "Visual Effects", 
            "Mechanical Effects", "Miscellaneous", "Notes"
        ]
        
        for row, scene in enumerate(scenes):
            # Header & Info (Cols 0-6)
            self.table.setItem(row, 0, QTableWidgetItem(str(scene.scene_number)))
            self.table.setItem(row, 1, QTableWidgetItem(scene.int_ext))
            self.table.setItem(row, 2, QTableWidgetItem(scene.set_name))
            self.table.setItem(row, 3, QTableWidgetItem(scene.day_night))
            self.table.setItem(row, 4, QTableWidgetItem(scene.total_pages_display))
            self.table.setItem(row, 5, QTableWidgetItem(scene.synopsis))
            self.table.setItem(row, 6, QTableWidgetItem(scene.description))
            
            # Element Categories (Cols 7-29)
            for i, cat_name in enumerate(element_categories):
                # Filter elements belonging to this category and join their names
                elements_str = ", ".join([e.name for e in scene.elements if e.category == cat_name])
                self.table.setItem(row, 7 + i, QTableWidgetItem(elements_str))
                
            # Final Analysis Columns (Cols 30-31)
            self.table.setItem(row, 30, QTableWidgetItem(scene.continuity_notes or ""))
            
            # Review Flags - using 'note' and 'flag_type' from your ReviewFlag model
            flag_texts = [f"[{f.flag_type}] {f.note}" for f in scene.flags]
            self.table.setItem(row, 31, QTableWidgetItem(" | ".join(flag_texts)))

    def handle_file_selection(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Script", "", "Scripts (*.pdf *.fdx *.txt *.docx *.doc *.rtf)")
        if path:
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
        import glob
        
        # 1. Look for the most recent checkpoint file
        files = glob.glob(os.path.join("outputs", "*_checkpoint.json"))
        if not files:
            self.log_output.append("ERROR: No checkpoints found in outputs folder.")
            return

        latest_file = max(files, key=os.path.getctime)
        self.log_output.append(f"INFO: Loading checkpoint: {latest_file}")

        # 2. Use your existing utils logic to load the data
        from src.core.utils import load_checkpoint # Assuming this exists in utils
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

    def start_analysis(self):
        """Prepares config and starts the background worker."""
        if not self.current_scenes:
            self.log_output.append("ERROR: No scenes to analyze. Please select a script first.")
            return

        # 1. Sync UI Settings to Config
        self.config.set_performance_level(self.combo_perf.currentText())
        self.config.use_continuity_agent = self.chk_cont.isChecked()
        self.config.use_flag_agent = self.chk_flag.isChecked()
        self.config.temperature = self.spin_temp.value()
        self.config.conservative_mode = self.chk_cons.isChecked()
        self.config.extract_implied_elements = self.chk_implied.isChecked() # Updated this line
        
        # 2. Identify selected categories
        active_cats = [c for c, cb in self.cat_boxes.items() if cb.isChecked()]
        
        # 3. Setup Worker & Thread
        self.btn_run.setEnabled(False)
        self.pbar.setValue(0)
        
        self.worker_thread = QThread()
        self.worker = AnalysisWorker(self.analyzer, self.current_scenes, active_cats)
        self.worker.moveToThread(self.worker_thread)
        
        # 4. Connect Signals
        self.worker_thread.started.connect(self.worker.run)
        self.worker.log_signal.connect(self.log_output.append)
        
        # Ensure AnalysisWorker has a progress_signal(int)
        if hasattr(self.worker, 'progress_signal'):
            self.worker.progress_signal.connect(self.pbar.setValue) 
        
        self.worker.finished.connect(self.on_analysis_finished)
        
        self.worker_thread.start()
        self.log_output.append(f"START: Analyzing {len(self.current_scenes)} scenes...")

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

    def reset_autosave_timer(self):
        """Restarts timer with the new interval from the spinbox."""
        mins = self.spin_auto_interval.value()
        self.autosave_timer.start(mins * 60 * 1000)

    def handle_user_save(self):
        """Manual save triggered by the user - asks for a filename."""
        path, _ = QFileDialog.getSaveFileName(self, "Save Checkpoint", "outputs/", "JSON (*.json)")
        if path:
            from src.core.utils import save_checkpoint
            save_checkpoint(self.current_scenes, path)
            self.log_output.append(f"SUCCESS: Manual checkpoint saved to {path}")

    def run_autosave(self):
        """Automatic background save. Rotates through 10 files in /outputs/autosaves/"""
        if not self.chk_auto.isChecked() or not self.current_scenes:
            return

        from src.core.utils import save_checkpoint
        
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
            