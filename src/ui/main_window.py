"""
Main Application Window.

Defines the primary UI layout and assembly. Inherits functional logic 
from Handler Mixins to maintain a clean separation of concerns.
"""

import os
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QCheckBox, QComboBox, QProgressBar, 
    QTextEdit, QTableWidget, QGroupBox, QScrollArea, 
    QHeaderView, QDoubleSpinBox, QSpinBox, QRadioButton, QLineEdit
)
from PySide6.QtCore import Qt,  QTimer
from src.core.models import MMS_CATEGORIES

from .table_manager import TableManagerMixin
from .file_handlers import FileHandlerMixin
from .analysis_handlers import AnalysisHandlerMixin

class MainWindow(QMainWindow, TableManagerMixin, FileHandlerMixin, AnalysisHandlerMixin):
    def __init__(self, analyzer, config, parser=None, exporter=None):
        super().__init__()
        self.analyzer = analyzer
        self.config = config
        self.parser = parser      
        self.exporter = exporter
        self.current_scenes = [] # Populated after file selection/parsing
        
        self.setWindowTitle("Film Script AI Breakdown Tool")
        self.resize(700, 720)

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

    def reset_for_new_project(self):
        """Factory reset for UI when a new script is loaded."""
        self.table.setRowCount(0)      # Wipes the review table
        self.log_output.clear()        # Clears the log
        self.pbar.setValue(0)          # Resets progress
        self.tabs.setTabEnabled(1, False) # Locks Review tab until analyzed

    def _build_setup_ui(self):
        layout = QVBoxLayout(self.setup_tab)
        layout.setSpacing(15)
        layout.setAlignment(Qt.AlignTop)

        # --- 0. PRE-INITIALIZE WIDGETS ---
        self.rad_all = QRadioButton("All Scenes")
        self.rad_range = QRadioButton("Scene Range:")
        self.rad_all.setChecked(True)
        
        self.txt_range_from = QLineEdit()
        self.txt_range_from.setPlaceholderText("From (e.g. 1)")
        self.txt_range_from.setFixedWidth(100)
        self.txt_range_from.setEnabled(False)
        
        self.txt_range_to = QLineEdit()
        self.txt_range_to.setPlaceholderText("To (e.g. 15A)")
        self.txt_range_to.setFixedWidth(100)
        self.txt_range_to.setEnabled(False)

        # Toggle boxes based on radio choice
        self.rad_range.toggled.connect(self.txt_range_from.setEnabled)
        self.rad_range.toggled.connect(self.txt_range_to.setEnabled)

        # --- 1 Production Setup ---
        selection_group = QGroupBox("Production Setup")
        sl = QVBoxLayout()
        sl.setSpacing(10) 
        
        # Row 1: File Button and Path
        file_row = QHBoxLayout()
        self.btn_select = QPushButton("Select Script File")
        self.btn_select.setToolTip("Select a PDF, FDX, RTF, or DOCX script file.") # Tooltip
        self.btn_select.clicked.connect(self.handle_file_selection)
        self.lbl_path = QLabel("No file selected...")
        self.chk_fdx = QCheckBox("Extract Final Draft Tags")
        self.chk_fdx.setVisible(False)
        file_row.addWidget(self.btn_select)
        file_row.addWidget(self.lbl_path, 1)
        file_row.addWidget(self.chk_fdx)
        sl.addLayout(file_row)

        sl.addSpacing(10) # Minimal Vertical Spacer (Requirement 2b)

        # Row 2: Load Buttons and Log Checkbox
        util_row = QHBoxLayout()
        
        # Define buttons
        self.btn_load = QPushButton("Load Last Checkpoint")
        self.btn_load.setToolTip("Quickly resume the most recent analysis session.") # Tooltip
        self.btn_load.clicked.connect(self.load_last_checkpoint)
        
        self.btn_load_manual = QPushButton("Load Checkpoint...")
        self.btn_load_manual.setToolTip("Browse for a specific JSON checkpoint.") # Tooltip
        self.btn_load_manual.clicked.connect(self.load_manual_checkpoint)

        self.btn_load_excel = QPushButton("Load Excel Checkpoint...")
        self.btn_load_excel.setToolTip("Re-import edited Excel data.") # Tooltip
        self.btn_load_excel.clicked.connect(self.load_excel_checkpoint)

        self.chk_expand_log = QCheckBox("Expand Log")
        self.chk_expand_log.setToolTip("Show or hide the technical processing log.") # Tooltip
        self.chk_expand_log.toggled.connect(self.toggle_log_expansion)
        
        # Add with spacing
        util_row.addWidget(self.btn_load)
        util_row.addSpacing(15) 
        util_row.addWidget(self.btn_load_manual)
        util_row.addSpacing(15)
        util_row.addWidget(self.btn_load_excel)
        util_row.addStretch()
        util_row.addWidget(self.chk_expand_log)
        sl.addLayout(util_row)
        
        selection_group.setLayout(sl)
        layout.addWidget(selection_group)

        # --- 2. Extraction Selection ---
        element_group = QGroupBox("Extraction Selection")
        ext_v = QVBoxLayout()
        ext_v.setSpacing(15)

        range_l = QHBoxLayout()
        range_label = QLabel("Analysis Range:")
        range_label.setToolTip("Choose whether to analyze the entire script or a specific segment.")
        
        self.rad_all.setText("All Scenes")
        self.rad_range.setText("Scene Range:")
        
        range_l.addWidget(range_label)
        range_l.addWidget(self.rad_all)
        range_l.addSpacing(10)
        range_l.addWidget(self.rad_range)
        range_l.addWidget(self.txt_range_from)
        range_l.addWidget(QLabel("-"))
        range_l.addWidget(self.txt_range_to)
        range_l.addStretch()
        ext_v.addLayout(range_l)

        # Scroll area for categories
        scroll = QScrollArea()
        scroll_content = QWidget()
        self.cat_grid = QGridLayout(scroll_content)

        self.cat_grid.setHorizontalSpacing(10) 
        self.cat_grid.setVerticalSpacing(5)
        
        rows_desired = 8 
        self.cat_boxes = {}
        for i, cat in enumerate(MMS_CATEGORIES):
            cb = QCheckBox(cat)
            cb.setToolTip(f"Extract elements for the {cat} category.")
            cb.setChecked(True)
            self.cat_boxes[cat] = cb
            self.cat_grid.addWidget(cb, i % rows_desired, i // rows_desired)

        self.cat_grid.setColumnStretch(3, 1)
            
        scroll.setWidget(scroll_content)
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(220)
        scroll.setMaximumWidth(600)
        ext_v.addWidget(scroll)

        # Agent Toggles - Fixed the 'sea of grey' by anchoring left
        agent_l = QHBoxLayout()
        agent_l.setAlignment(Qt.AlignLeft)
        self.chk_cont = QCheckBox("Run Continuity Agent")
        self.chk_cont.setToolTip("Tracks items across scenes for script consistency.")
        self.chk_flag = QCheckBox("Run Review Flag Agent")
        self.chk_flag.setToolTip("Scans for safety hazards and production risks.")
        
        self.chk_cont.setChecked(self.config.use_continuity_agent)
        self.chk_flag.setChecked(self.config.use_flag_agent)
        
        agent_l.addWidget(self.chk_cont)
        agent_l.addSpacing(40) # Gap between agents
        agent_l.addWidget(self.chk_flag)
        agent_l.addStretch() # This removes the floating 'sea of grey'
        ext_v.addLayout(agent_l)
        
        element_group.setLayout(ext_v)
        layout.addWidget(element_group)

        # --- 3. Technical Settings (Stacked & Aligned) ---
        tech_group = QGroupBox("Technical Settings")
        tl = QVBoxLayout()
        tl.setSpacing(12)

        # Row 1: Model Temperature
        temp_row = QHBoxLayout()
        temp_label = QLabel("Model Temperature:")
        temp_label.setToolTip("Controls randomness: 0.0 is deterministic, 1.0 is highly creative.")
        
        self.spin_temp = QDoubleSpinBox()
        self.spin_temp.setRange(0.0, 1.0)
        self.spin_temp.setSingleStep(0.1)
        self.spin_temp.setValue(self.config.temperature)
        self.spin_temp.setFixedWidth(150) # Fixed width for alignment
        
        temp_row.addWidget(temp_label)
        temp_row.addWidget(self.spin_temp)
        temp_row.addStretch() # Anchors to left
        tl.addLayout(temp_row)

        # Row 2: Checkboxes (Stacked between Temp and Performance)
        check_row = QHBoxLayout()
        self.chk_cons = QCheckBox("Conservative Mode")
        self.chk_cons.setToolTip("Prioritizes accuracy; AI will only extract elements explicitly named in text.")
        self.chk_cons.setChecked(self.config.conservative_mode)

        self.chk_implied = QCheckBox("Extract Implied")
        self.chk_implied.setToolTip("Allows AI to extract logical but unnamed elements (e.g., 'Table' in a 'Dining Room').")
        self.chk_implied.setChecked(self.config.extract_implied_elements)
        
        check_row.addWidget(self.chk_cons)
        check_row.addSpacing(20)
        check_row.addWidget(self.chk_implied)
        check_row.addStretch()
        tl.addLayout(check_row)

        # Row 3: Performance Level
        perf_row = QHBoxLayout()
        perf_label = QLabel("Performance Level:")
        perf_label.setToolTip("Determines how many CPU threads are dedicated to the AI processing.")
        
        self.combo_perf = QComboBox()
        self.combo_perf.addItems(["Eco", "Power", "Turbo", "Max"])
        self.combo_perf.setCurrentText(self.config.performance_mode)
        self.combo_perf.setFixedWidth(150) # Fixed width to align with spinbox row
        
        perf_row.addWidget(perf_label)
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
        self.btn_run.setToolTip("Begin the AI-powered breakdown of the selected script range.")
        
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

        # Top Control Bar for Table
        top_bar = QHBoxLayout()
        self.chk_wrap = QCheckBox("Wrap Text / Expand Rows")
        self.chk_wrap.toggled.connect(self.toggle_word_wrap)
        top_bar.addWidget(self.chk_wrap)
        top_bar.addStretch()
        layout.addLayout(top_bar)
        
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
        self.table.setShowGrid(True)
        self.table.setStyleSheet("""
            QTableWidget {
                gridline-color: #555555; /* Light grey lines */
                background-color: #2b2b2b;
            }
            QHeaderView::section {
                background-color: #3d3d3d;
                color: white;
                padding: 4px;
                border: 1px solid #555555;
            }
        """)

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

    

    

    

    

    

    

    

    
            