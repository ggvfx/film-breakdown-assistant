import os
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QCheckBox, QComboBox, QProgressBar, 
    QTextEdit, QTableWidget, QFileDialog, QGroupBox, QScrollArea, 
    QHeaderView, QTableWidgetItem, QDoubleSpinBox
)
from PySide6.QtCore import Qt, QThread
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
        # Base Layout
        layout = QVBoxLayout(self.setup_tab)
        layout.setSpacing(15)

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

        # 6. Expanding Log (Hidden by default)
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setVisible(False)
        layout.addWidget(self.log_output)

    def toggle_log_expansion(self, visible):
        """Manually forces the window to grow down or shrink up."""
        # 1. Capture current dimensions
        current_w = self.width()
        current_h = self.height()
        
        # 2. Toggle the visibility
        self.log_output.setVisible(visible)
        
        if visible:
            # Grow: Keep width, but add 250 pixels to the height for the log
            self.log_output.setMinimumHeight(250)
            self.resize(current_w, current_h + 250)
        else:
            # Shrink: Keep width, but subtract that 250 pixels back
            self.log_output.setMinimumHeight(0)
            self.resize(current_w, current_h - 250)
            
        # 3. Ensure the layout updates properly
        self.update()

    def _build_review_ui(self):
        layout = QVBoxLayout(self.review_tab)
        
        self.table = QTableWidget()
        # Set column count to match standard breakdown sheets
        self.table.setColumnCount(12) 
        self.table.setHorizontalHeaderLabels(["Scene", "Set", "Description", "Cast", "Props", "Wardrobe", "SFX", "Vehicles", "Stunts", "Continuity", "Flags", "Notes"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setWordWrap(True)
        layout.addWidget(self.table)

        # Bottom Bar
        bot = QHBoxLayout()
        self.btn_save = QPushButton("Save Checkpoint")
        self.chk_auto = QCheckBox("Autosave")
        self.chk_auto.setChecked(True)
        
        export_box = QGroupBox("Export Options")
        eb_l = QHBoxLayout()
        self.chk_xls = QCheckBox("Excel")
        self.chk_csv = QCheckBox("CSV")
        self.chk_sex = QCheckBox("MMS (.sex)")
        self.btn_export = QPushButton("EXPORT")
        self.btn_export.clicked.connect(self.handle_export)
        eb_l.addWidget(self.chk_xls); eb_l.addWidget(self.chk_csv); eb_l.addWidget(self.chk_sex); eb_l.addWidget(self.btn_export)
        export_box.setLayout(eb_l)

        bot.addWidget(self.btn_save); bot.addWidget(self.chk_auto)
        bot.addStretch()
        bot.addWidget(export_box)
        layout.addLayout(bot)

    def populate_table(self, scenes):
        """Fills the Review Tab table with scene data."""
        self.table.setRowCount(len(scenes))
        
        for row, scene in enumerate(scenes):
            # Column Order: Scene, Set, Description, Cast, Props, etc.
            self.table.setItem(row, 0, QTableWidgetItem(str(scene.scene_number)))
            self.table.setItem(row, 1, QTableWidgetItem(scene.set_name))
            self.table.setItem(row, 2, QTableWidgetItem(scene.description))
            
            # Group elements by category for the columns
            # This is a simple way to comma-separate names
            cast = ", ".join([e.name for e in scene.elements if e.category == "Cast Members"])
            props = ", ".join([e.name for e in scene.elements if e.category == "Props"])
            
            self.table.setItem(row, 3, QTableWidgetItem(cast))
            self.table.setItem(row, 4, QTableWidgetItem(props))
            # ... add other categories as needed ...
            
            # Continuity and Flags
            self.table.setItem(row, 9, QTableWidgetItem(scene.continuity_notes or ""))
            flag_text = " | ".join([f.warning for f in scene.flags])
            self.table.setItem(row, 10, QTableWidgetItem(flag_text))

    def handle_file_selection(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Script", "", "Scripts (*.pdf *.fdx *.txt)")
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
            
            # 3. Populate the Review Table and unlock the tab
            self.populate_table(loaded_scenes)
            self.tabs.setTabEnabled(1, True)
            self.tabs.setCurrentIndex(1) # Switch to the Review tab automatically
            self.log_output.append(f"SUCCESS: Loaded {len(loaded_scenes)} scenes from checkpoint.")
            
        except Exception as e:
            self.log_output.append(f"ERROR: Failed to load checkpoint: {str(e)}")

    def start_analysis(self):
        # 1. Sync UI to Config
        self.config.set_performance_level(self.combo_perf.currentText())
        self.config.use_continuity_agent = self.chk_cont.isChecked()
        self.config.use_flag_agent = self.chk_flag.isChecked()
        
        # 2. Setup Worker
        # For this test, assume current_scenes is populated by your parser logic
        active_cats = [c for c, cb in self.cat_boxes.items() if cb.isChecked()]
        
        self.btn_run.setEnabled(False)
        self.worker_thread = QThread()
        self.worker = AnalysisWorker(self.analyzer, self.current_scenes, active_cats)
        self.worker.moveToThread(self.worker_thread)
        
        self.worker_thread.started.connect(self.worker.run)
        self.worker.log_signal.connect(self.log_output.append)
        self.worker.finished.connect(self.on_analysis_finished)
        
        self.worker_thread.start()

    def on_analysis_finished(self, results):
        self.btn_run.setEnabled(True)
        self.tabs.setTabEnabled(1, True)
        self.tabs.setCurrentIndex(1) # Switch to Review
        self.worker_thread.quit()
        # Logic to populate table goes here

    def handle_export(self):
        """Triggered by the Export button. Uses your DataExporter logic."""
        # We need access to the exporter. Ensure it's available in __init__ 
        # or import it here if you haven't passed it in gui_app.py
        from src.core.exporter import DataExporter
        exporter = DataExporter()

        if not self.current_scenes:
            self.log_output.append("ERROR: No data to export.")
            return

        # Determine path (usually same folder as script)
        output_dir = "outputs"
        os.makedirs(output_dir, exist_ok=True)
        base_name = "Breakdown_Export"

        if self.chk_xls.isChecked():
            exporter.export_to_excel(self.current_scenes, os.path.join(output_dir, f"{base_name}.xlsx"))
        if self.chk_csv.isChecked():
            exporter.export_to_csv(self.current_scenes, os.path.join(output_dir, f"{base_name}.csv"))
        if self.chk_sex.isChecked():
            exporter.export_to_mms(self.current_scenes, os.path.join(output_dir, f"{base_name}.sex"))
            
        self.log_output.append("SUCCESS: Exported selected formats to /outputs")