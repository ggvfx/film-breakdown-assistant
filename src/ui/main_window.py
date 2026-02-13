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
        layout.setAlignment(Qt.AlignTop)

        # 1 Script Selection & Project Management
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

        # NEW Row: Scene Range Selection (Task 1)
        range_row = QHBoxLayout()
        self.rad_all = QRadioButton("Analyze ALL Scenes")
        self.rad_range = QRadioButton("Analyze RANGE:")
        self.rad_all.setChecked(True)
        
        self.txt_range_from = QLineEdit()
        self.txt_range_from.setPlaceholderText("From (e.g. 1)")
        self.txt_range_from.setFixedWidth(100)
        self.txt_range_from.setEnabled(False) # Disabled unless 'Range' is picked
        
        self.txt_range_to = QLineEdit()
        self.txt_range_to.setPlaceholderText("To (e.g. 15A)")
        self.txt_range_to.setFixedWidth(100)
        self.txt_range_to.setEnabled(False)

        # Toggle boxes based on radio choice
        self.rad_range.toggled.connect(self.txt_range_from.setEnabled)
        self.rad_range.toggled.connect(self.txt_range_to.setEnabled)

        range_row.addWidget(self.rad_all)
        range_row.addSpacing(20)
        range_row.addWidget(self.rad_range)
        range_row.addWidget(self.txt_range_from)
        range_row.addWidget(QLabel("-"))
        range_row.addWidget(self.txt_range_to)
        range_row.addStretch()
        sl.addLayout(range_row)

        # Row 2: Load Buttons and Log Checkbox
        util_row = QHBoxLayout()
        
        # FIX: Define buttons BEFORE adding them to the layout
        self.btn_load = QPushButton("Load Last Checkpoint")
        self.btn_load.clicked.connect(self.load_last_checkpoint)
        
        self.btn_load_manual = QPushButton("Load Checkpoint...")
        self.btn_load_manual.clicked.connect(self.load_manual_checkpoint)

        self.btn_load_excel = QPushButton("Load Excel Checkpoint...")
        self.btn_load_excel.clicked.connect(self.load_excel_checkpoint)

        self.chk_expand_log = QCheckBox("Expand Log")
        self.chk_expand_log.toggled.connect(self.toggle_log_expansion)
        
        util_row.addWidget(self.btn_load)
        util_row.addWidget(self.btn_load_manual)
        util_row.addWidget(self.btn_load_excel)
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

    

    

    

    

    

    

    

    
            