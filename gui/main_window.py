```python
import json
import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QComboBox, QPushButton, QProgressBar, 
                               QTableWidget, QTableWidgetItem, QTextEdit, QTabWidget,
                               QHeaderView, QMessageBox, QGroupBox, QFormLayout,
                               QDialog, QLineEdit, QDialogButtonBox, QCheckBox)
from PySide6.QtCore import Qt, Slot, QTimer, QSize
from PySide6.QtGui import QFont, QColor, QIcon, QPixmap, QPainter, QTextCursor

from backend.ollama_client import OllamaClient
from backend.hardware import get_hardware_info
from gui.workers import BenchmarkWorker, PullWorker, HardwareMonitor
from gui.contribution_dialog import ContributionDialog

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("LLMark")
        self.resize(1000, 800)
        
        self.hardware_info = get_hardware_info()
        self.client = OllamaClient()
        self.worker = None
        self.pull_worker = None
        self.results_data = None

        self.setup_ui()
        self.load_models()
        self.check_judge_status()
        
        # Background VRAM Monitor (Fixed: No GUI Freeze)
        self.hw_monitor = HardwareMonitor(interval=2.0)
        self.hw_monitor.vram_updated.connect(self.update_vram_display)
        self.hw_monitor.start()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Apply VS Code Dark Theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QWidget {
                color: #cccccc;
                font-family: 'Segoe UI', 'Roboto', 'Inter', sans-serif;
                font-size: 14px;
            }
            QDialog {
                background-color: #1e1e1e;
            }
            QLabel {
                background-color: transparent;
                color: #cccccc;
            }
            QLabel[heading="true"] {
                color: #ffffff;
                font-weight: 600;
            }
            QTabWidget::pane {
                border: 1px solid #3e3e42;
                background: #1e1e1e;
                top: -1px;
            }
            QTabBar::tab {
                background: #2d2d2d;
                color: #969696;
                padding: 10px 20px;
                border: 1px solid #252526;
                border-bottom: none;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #1e1e1e;
                color: #ffffff;
                border-top: 2px solid #007acc;
            }
            QTabBar::tab:hover {
                background: #2a2d2e;
                color: #ffffff;
            }
            QGroupBox {
                border: 1px solid #3e3e42;
                border-radius: 6px;
                margin-top: 24px;
                padding-top: 15px;
                background-color: #252526;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #007acc;
                font-weight: bold;
                font-size: 16px;
                background-color: transparent;
            }
            QPushButton {
                background-color: #0e639c;
                border: none;
                border-radius: 4px;
                padding: 6px 14px;
                color: #ffffff;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #1177bb;
            }
            QPushButton:pressed {
                background-color: #094771;
            }
            QComboBox {
                background-color: #3c3c3c;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                padding: 6px;
                color: #cccccc;
            }
            QComboBox::drop-down {
                border: none;
            }
            QProgressBar {
                border: 1px solid #3e3e42;
                border-radius: 4px;
                text-align: center;
                background-color: #3c3c3c;
                color: transparent;
            }
            QProgressBar::chunk {
                background-color: #007acc;
                border-radius: 3px;
            }
            QTextEdit {
                background-color: #1e1e1e;
                border: 1px solid #3e3e42;
                border-radius: 4px;
                color: #cccccc;
                padding: 8px;
            }
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)

        # Top Bar
        header_frame = QWidget()
        header_frame.setFixedHeight(100)
        header_frame.setStyleSheet("background-color: #252526; border-bottom: 1px solid #3e3e42;")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(30, 0, 30, 0)

        title_lbl = QLabel("LLMark-Suite")
        title_lbl.setProperty("heading", "true")
        title_lbl.setStyleSheet("color: #007acc; border: none; font-family: 'Segoe UI'; font-size: 60px; font-weight: bold;")
        
        self.settings_btn = QPushButton()
        self.settings_btn.setFixedSize(40, 40)
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #3e3e42;
            }
            QPushButton:pressed {
                background-color: #333333;
            }
        """)
        
        # Simple SVG Gear Icon
        gear_svg = """
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#cccccc" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
        </svg>
        """
        pixmap = QPixmap(QSize(24, 24))
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        from PySide6.QtSvg import QSvgRenderer
        renderer = QSvgRenderer(gear_svg.encode())
        renderer.render(painter)
        painter.end()
        self.settings_btn.setIcon(QIcon(pixmap))
        self.settings_btn.setIconSize(QSize(24, 24))
        self.settings_btn.clicked.connect(self.open_settings)

        header_layout.addWidget(title_lbl)
        header_layout.addStretch()
        header_layout.addWidget(self.settings_btn)
        layout.addWidget(header_frame)

        # Content Area
        main_content = QWidget()
        main_content_layout = QVBoxLayout(main_content)
        main_content_layout.setContentsMargins(25, 15, 25, 25)
        main_content_layout.setSpacing(20)

        # Hardware Info Bar
        hw_group = QGroupBox("System Hardware")
        hw_layout = QHBoxLayout()
        hw_layout.setContentsMargins(15, 15, 15, 15)
        
        cpu_lbl = QLabel(f"<span style='color: #858585;'>CPU:</span> <span style='color: #cccccc;'>{self.hardware_info['cpu']}</span>")
        ram_lbl = QLabel(f"<span style='color: #858585;'>RAM:</span> <span style='color: #cccccc;'>{self.hardware_info['ram_total_gb']} GB</span>")
        gpu_lbl = QLabel(f"<span style='color: #858585;'>GPU:</span> <span style='color: #cccccc;'>{self.hardware_info['gpu'] or 'N/A'}</span>")
        
        vram_text = f"<span style='color: #858585;'>VRAM:</span> <span style='color: #cccccc;'>{self.hardware_info['vram_total_mb'] or 0} MB</span>"
        self.vram_lbl = QLabel(vram_text)
        
        hw_layout.addWidget(cpu_lbl)
        hw_layout.addWidget(ram_lbl)
        hw_layout.addWidget(gpu_lbl)
        hw_layout.addWidget(self.vram_lbl)
        hw_group.setLayout(hw_layout)
        main_content_layout.addWidget(hw_group)

        # Tabs
        self.tabs = QTabWidget()
        main_content_layout.addWidget(self.tabs)

        # Tab 1: Control & Progress
        self.tab_control = QWidget()
        self.setup_control_tab()
        self.tabs.addTab(self.tab_control, "Benchmark Run")

        # Tab 2: Results
        self.tab_results = QWidget()
        self.setup_results_tab()
        self.tabs.addTab(self.tab_results, "Results")

        # Tab 3: JSON
        self.tab_json = QWidget()
        self.setup_json_tab()
        self.tabs.addTab(self.tab_json, "JSON Detail")

        # Tab 4: Detail-Log
        self.tab_detail_log = QWidget()
        self.setup_detail_log_tab()
        self.tabs.addTab(self.tab_detail_log, "Detail-Log")

        # Tab 5: Auto-Pilot
        self.tab_autopilot = QWidget()
        self.setup_autopilot_tab()
        self.tabs.addTab(self.tab_autopilot, "Auto-Pilot")
        
        layout.addWidget(main_content)

    def setup_autopilot_tab(self):
        layout = QVBoxLayout(self.tab_autopilot)
        layout.setContentsMargins(15, 15, 15, 15)
        
        info_group = QGroupBox("Automatter Benchmark & Upload")
        info_layout = QVBoxLayout()
        info_lbl = QLabel("This mode will automatically download standard models, test them, and upload results to the LLMark repository.")
        info_lbl.setWordWrap(True)
        info_layout.addWidget(info_lbl)
        
        self.token_input = QLineEdit()
        from backend.ollama_client import get_config
        config = get_config()
        self.token_input.setText(config.get("github_token", ""))
        self.token_input.setPlaceholderText("GitHub Personal Access Token (classic with 'public_repo' scope)")
        self.token_input.setEchoMode(QLineEdit.Password)
        self.token_input.setStyleSheet("background-color: #3c3c3c; border: 1px solid #3e3e42; padding: 10px; color: #cccccc;")
        info_layout.addWidget(QLabel("GitHub Token:"))
        info_layout.addWidget(self.token_input)
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Model List Group
        model_group = QGroupBox("Models to Test")
        m_layout = QVBoxLayout()
        self.autopilot_models_text = QTextEdit()
        # Default list - Expanded & Diverse
        default_models = [
            "llama3.2:1b",
            "llama3.2:3b",
            "llama3.1:8b",
            "qwen2.5:0.5b",
            "qwen2.5:1.5b",
            "qwen2.5:3b",
            "qwen2.5:7b",
            "qwen2.5:14b",
            "qwen2.5:32b",
            "phi4-mini:latest",
            "gemma2:2b",
            "gemma2:9b",
            "gemma2:27b",
            "gemma3:1b",
            "gemma3:4b",
            "gemma3:12b",
            "qwen3-vl:2b",
            "qwen3-vl:4b",
            "qwen3-vl:8b",
            "mistral:latest",
            "mistral-nemo:latest",
            "mixtral:8x7b",
            "deepseek-v2.5:latest",
            "deepseek-r1:1.5b",
            "deepseek-r1:7b",
            "deepseek-r1:8b",
            "deepseek-r1:14b",
        ]
        self.autopilot_models_text.setPlainText("\n".join(default_models))
        self.autopilot_models_text.setStyleSheet("background-color: #1e1e1e; color: #ce9178; font-family: 'Consolas';")
        self.autopilot_models_text.setMaximumHeight(150)
        m_layout.addWidget(self.autopilot_models_text)
        model_group.setLayout(m_layout)
        layout.addWidget(model_group)
        
        # Options Group
        options_group = QGroupBox("Options")
        opt_layout = QHBoxLayout()
        self.autocleanup_cb = QCheckBox("Auto-Cleanup models after test (saves disk space)")
        self.autocleanup_cb.setChecked(True)
        self.autocleanup_cb.setStyleSheet("color: #cccccc;")
        opt_layout.addWidget(self.autocleanup_cb)
        options_group.setLayout(opt_layout)
        layout.addWidget(options_group)
        
        # Start/Stop Button
        self.autopilot_btn = QPushButton("🚀 Start Auto-Pilot")
        self.autopilot_btn.setMinimumHeight(60)
        self.autopilot_btn.setStyleSheet("""
            QPushButton {
                background-color: #388a34; 
                color: #ffffff; 
                font-weight: 600; 
                font-size: 16px;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #2e702a; }
        """)
        self.autopilot_btn.clicked.connect(self.toggle_autopilot)
        layout.addWidget(self.autopilot_btn)
        
        # Log & Progress
        self.auto_status_lbl = QLabel("IDLE")
        self.auto_status_lbl.setStyleSheet("color: #007acc; font-weight: bold; font-size: 14px;")
        layout.addWidget(self.auto_status_lbl)
        
        self.auto_progress = QProgressBar()
        layout.addWidget(self.auto_progress)
        
        self.auto_log = QTextEdit()
        self.auto_log.setReadOnly(True)
        self.auto_log.setStyleSheet("background-color: #1e1e1e; color: #9cdcfe; font-family: 'Consolas', monospace;")
        layout.addWidget(self.auto_log)

    def toggle_autopilot(self):
        if hasattr(self, 'auto_worker') and self.auto_worker and self.auto_worker.isRunning():
            self.auto_worker.stop()
            self.autopilot_btn.setText("Stopping...")
            self.autopilot_btn.setEnabled(False)
            return

        token = self.token_input.text().strip()
        if not token:
            QMessageBox.warning(self, "Token required", "Please enter your GitHub Token.")
            return
            
        models = [m.strip() for m in self.autopilot_models_text.toPlainText().split("\n") if m.strip()]
        if not models:
            QMessageBox.warning(self, "Models required", "Please enter at least one model.")
            return

        from backend.ollama_client import get_config, save_config
        config = get_config()
        config["github_token"] = token
        save_config(config)

        self.autopilot_btn.setText("🛑 Stop Auto-Pilot")
        self.autopilot_btn.setStyleSheet("background-color: #e51400; color: white; font-weight: bold;")
        self.auto_log.clear()
        self.auto_log.append("Starting Auto-Pilot mode...")
        
        autocleanup = self.autocleanup_cb.isChecked()
        context_window = config.get("context_window")
        from gui.workers import ContinuousTestWorker
        self.auto_worker = ContinuousTestWorker(token, models, self.hardware_info, context_window=context_window, autocleanup=autocleanup)
        self.auto_worker.status_update.connect(lambda s: self.auto_status_lbl.setText(s))
        self.auto_worker.progress_update.connect(lambda t, p: self.auto_progress.setValue(p))
        self.auto_worker.log_update.connect(lambda l: self.auto_log.append(l))
        self.auto_worker.error_occurred.connect(lambda e: QMessageBox.critical(self, "Error", e))
        self.auto_worker.finished.connect(self.on_autopilot_finished)
        self.auto_worker.start()

    def on_autopilot_finished(self):
        self.autopilot_btn.setText("🚀 Start Auto-Pilot")
        self.autopilot_btn.setStyleSheet("background-color: #388a34; color: white; font-weight: bold;")
        self.autopilot_btn.setEnabled(True)
        self.auto_status_lbl.setText("Finished.")
        self.auto_log.append("\n--- Auto-Pilot Session Finished ---")

    def start_autopilot_if_requested(self):
        self.tabs.setCurrentWidget(self.tab_autopilot)
        self.toggle_autopilot()

    def setup_control_tab(self):
        layout = QVBoxLayout(self.tab_control)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Selection
        config_group = QGroupBox("Configuration")
        form_layout = QFormLayout()
        
        self.model_combo = QComboBox()
        self.model_combo.setMinimumHeight(40)
        self.refresh_btn = QPushButton("Refresh")
        self.refresh_btn.setFixedWidth(100)
        self.refresh_btn.clicked.connect(self.load_models)
        
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.model_combo)
        h_layout.addWidget(self.refresh_btn)
        
        form_layout.addRow("Test Model:", h_layout)
        
        # Judge Section
        judge_layout = QHBoxLayout()
        self.judge_status_lbl = QLabel("Checking...")
        self.judge_status_lbl.setStyleSheet("color: #858585;")
        judge_layout.addWidget(self.judge_status_lbl)
        
        self.install_judge_btn = QPushButton("Install Judge")
        self.install_judge_btn.setVisible(False)
        self.install_judge_btn.clicked.connect(self.install_judge)
        self.install_judge_btn.setStyleSheet("background-color: #388a34; color: white; border: none; border-radius: 4px; padding: 6px 12px;")
        judge_layout.addWidget(self.install_judge_btn)

        form_layout.addRow("Judge Model:", judge_layout)
        config_group.setLayout(form_layout)
        layout.addWidget(config_group)
        
        # Start Button
        self.start_btn = QPushButton("🚀 Start Benchmark Suite")
        self.start_btn.setMinimumHeight(60)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #007acc; 
                color: #ffffff; 
                font-weight: 600; 
                font-size: 16px;
                border: none;
                border-radius: 6px;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #0062a3;
            }
            QPushButton:disabled {
                background-color: #3e3e42;
                color: #6d6d6d;
            }
        """)
        self.start_btn.clicked.connect(self.start_benchmark)
        layout.addWidget(self.start_btn)
        
        # Progress Area
        self.progress_group = QGroupBox("Live Progress")
        p_layout = QVBoxLayout()
        
        self.overall_progress = QProgressBar()
        self.overall_progress.setFixedHeight(25)
        self.overall_progress.setMaximum(10)
        
        p_layout.addWidget(QLabel("Overall Progress:"))
        p_layout.addWidget(self.overall_progress)
        
        self.current_task_lbl = QLabel("System Ready")
        self.current_task_lbl.setProperty("heading", "true")
        self.current_task_lbl.setStyleSheet("font-size: 14px;")
        p_layout.addWidget(self.current_task_lbl)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background-color: #1e1e1e; color: #9cdcfe; font-family: 'Consolas', monospace; border: 1px solid #3e3e42;")
        p_layout.addWidget(self.log_area)
        
        self.progress_group.setLayout(p_layout)
        layout.addWidget(self.progress_group)

    def check_judge_status(self):
        from backend.benchmarks import JUDGE_MODEL
        if self.client.check_model_availability(JUDGE_MODEL):
            self.judge_status_lbl.setText(f"{JUDGE_MODEL} (Ready)")
            self.judge_status_lbl.setStyleSheet("color: #89d185; font-weight: bold;")
            self.install_judge_btn.setVisible(False)
            self.start_btn.setEnabled(True)
        else:
            self.judge_status_lbl.setText(f"{JUDGE_MODEL} (MISSING)")
            self.judge_status_lbl.setStyleSheet("color: #f48771; font-weight: bold;")
            self.install_judge_btn.setVisible(True)
            self.start_btn.setEnabled(False)

    def install_judge(self):
        from backend.benchmarks import JUDGE_MODEL
        self.install_judge_btn.setEnabled(False)
        self.log_area.append(f"Installing {JUDGE_MODEL}...")
        
        self.pull_worker = PullWorker(JUDGE_MODEL)
        self.pull_worker.progress_update.connect(self.on_pull_progress)
        self.pull_worker.finished.connect(self.on_pull_finished)
        self.pull_worker.start()

    @Slot(str, int)
    def on_pull_progress(self, status, percent):
         self.current_task_lbl.setText(f"Installing Judge: {status} ({percent}%)")
    
    @Slot(bool, str)
    def on_pull_finished(self, success, msg):
        self.install_judge_btn.setEnabled(True)
        if success:
            self.log_area.append("Judge installation successful.")
            self.check_judge_status()
            self.current_task_lbl.setText("Ready.")
        else:
             self.log_area.append(f"Judge installation failed: {msg}")
             QMessageBox.critical(self, "Install Error", f"Failed to install judge: {msg}")

    def setup_results_tab(self):
        layout = QVBoxLayout(self.tab_results)
        layout.setContentsMargins(15, 15, 15, 15)
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Benchmark", "Score / Value", "Comment", "Status"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.results_table.setAlternatingRowColors(True)
        self.results_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.verticalHeader().setVisible(False)
        self.results_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #3e3e42;
                border: 1px solid #3e3e42;
                border-radius: 8px;
                background-color: #1e1e1e;
                alternate-background-color: #252526;
                color: #cccccc;
            }
            QHeaderView::section {
                background-color: #252526;
                padding: 10px;
                border: none;
                border-bottom: 2px solid #3e3e42;
                font-weight: bold;
                color: #007acc;
            }
        """)
        
        layout.addWidget(self.results_table)
        
        self.total_score_lbl = QLabel("Total Score: 0/110")
        self.total_score_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        self.total_score_lbl.setAlignment(Qt.AlignRight)
        self.total_score_lbl.setStyleSheet("color: #007acc; margin-top: 10px;")
        layout.addWidget(self.total_score_lbl)
        
        btn_layout = QHBoxLayout()
        self.open_json_btn = QPushButton("Open JSON File")
        self.open_json_btn.setMinimumHeight(45)
        self.open_json_btn.setStyleSheet("""
            QPushButton {
                background-color: #2d2d2d; 
                border-radius: 6px; 
                padding: 0 25px;
                color: #cccccc;
            }
            QPushButton:hover { background-color: #3e3e42; }
        """)
        self.open_json_btn.clicked.connect(self.open_json_file)
        self.open_json_btn.setEnabled(False)
        btn_layout.addStretch()
        btn_layout.addWidget(self.open_json_btn)
        layout.addLayout(btn_layout)

    def setup_json_tab(self):
        layout = QVBoxLayout(self.tab_json)
        self.json_view = QTextEdit()
        self.json_view.setReadOnly(True)
        self.json_view.setFont(QFont("Consolas", 11))
        self.json_view.setStyleSheet("background-color: #1e1e1e; color: #ce9178; border: 1px solid #3e3e42;")
        layout.addWidget(self.json_view)

    def setup_detail_log_tab(self):
        layout = QVBoxLayout(self.tab_detail_log)
        self.detail_log_view = QTextEdit()
        self.detail_log_view.setReadOnly(True)
        self.detail_log_view.setFont(QFont("Consolas", 11))
        self.detail_log_view.setStyleSheet("background-color: #1e1e1e; color: #9cdcfe; border: 1px solid #3e3e42;")
        layout.addWidget(self.detail_log_view)

    def load_models(self):
        self.model_combo.clear()
        models = self.client.list_models()
        if models:
            self.model_combo.addItems(models)
        else:
            self.model_combo.addItem("No models found or Ollama unreachable")

    def log(self, msg):
        self.log_area.append(msg)

    @Slot(float)
    def update_vram_display(self, used):
        total = self.hardware_info.get('vram_total_mb', 0)
        vram_text = f"<span style='color: #858585;'>VRAM:</span> <span style='color: #cccccc;'>{total} MB (Used: {used} MB)</span>"
        if hasattr(self, 'vram_lbl'):
             self.vram_lbl.setText(vram_text)

    def start_benchmark(self):
        test_model = self.model_combo.currentText()
        if not test_model or "No models" in test_model:
            QMessageBox.warning(self, "Error", "No model selected")
            return
            
        # Verify Judge
        if not self.client.check_model_availability("qwen2.5:14b-instruct"):
            QMessageBox.critical(self, "Missing Judge", "The judge model 'qwen2.5:14b-instruct' was not found.\nPlease install it first.")
            return

        self.start_btn.setEnabled(False)
        self.results_table.setRowCount(0)
        self.total_score_lbl.setText("Total Score: 0/110")
        self.log_area.clear()
        self.detail_log_view.clear()
        self.overall_progress.setValue(0)
        
        from backend.ollama_client import get_config
        config = get_config()
        context_window = config.get("context_window")
        
        self.worker = BenchmarkWorker(test_model, self.hardware_info, context_window=context_window)
        self.worker.progress_update.connect(self.on_progress)
        self.worker.verbose_log.connect(self.on_verbose_log)
        self.worker.stream_chunk.connect(self.on_stream_chunk)
        self.worker.benchmark_finished.connect(self.on_benchmark_finished)
        self.worker.all_finished.connect(self.on_all_finished)
        self.worker.start()

    @Slot(str, str)
    def on_progress(self, bench_id, msg):
        self.current_task_lbl.setText(f"Benchmark {bench_id}: {msg}")
        self.log(f"[{bench_id}] {msg}")

    @Slot(str)
    def on_verbose_log(self, msg):
        self.detail_log_view.append(msg)

    @Slot(str)
    def on_stream_chunk(self, chunk):
        # Insert chunk at the end of detail log
        cursor = self.detail_log_view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(chunk)
        self.detail_log_view.setTextCursor(cursor)
        self.detail_log_view.ensureCursorVisible()

    @Slot(str, dict)
    def on_benchmark_finished(self, bench_id, result):
        self.overall_progress.setValue(self.overall_progress.value() + 1)
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        name_map = {
            "A": "A: Velocity/Speed",
            "B": "B: English Quality",
            "C": "C: German Quality",
            "D": "D: Fact Checking",
            "E": "E: Context Extr.",
            "F": "F: Logic/Timetable",
            "G": "G: Creative Writing",
            "H": "H: Technical Expl.",
            "I": "I: Python Coding",
            "J": "J: Customer Support",
            "W": "W: Knowledge",
            "X": "X: Uncertainty"
        }
        
        # Use description from result if available, otherwise fallback to name_map
        desc = result.get('description')
        if desc:
            name = f"{bench_id}: {desc}"
        else:
            name = name_map.get(bench_id, bench_id)
            
        comment = result.get('comment', '')
        
        if bench_id == "A":
            score_text = f"{result.get('score', 0)} t/s"
        else:
            score_text = str(result.get('score', 0))

        # Items
        name_item = QTableWidgetItem(name)
        score_item = QTableWidgetItem(score_text)
        score_item.setTextAlignment(Qt.AlignCenter)
        comment_item = QTableWidgetItem(comment)
        
        self.results_table.setItem(row, 0, name_item)
        self.results_table.setItem(row, 1, score_item)
        self.results_table.setItem(row, 2, comment_item)
        
        # Status Badges
        status_item = QTableWidgetItem()
        status_item.setTextAlignment(Qt.AlignCenter)
        
        if "Error" in comment or result.get('score') == 0:
            status_item.setText(" FAIL ")
            status_item.setBackground(QColor("#f48771"))
        else:
            status_item.setText(" PASS ")
            status_item.setBackground(QColor("#388a34"))
        
        status_item.setForeground(QColor("white"))
        self.results_table.setItem(row, 3, status_item)
        self.results_table.setRowHeight(row, 50)

    @Slot(dict)
    def on_all_finished(self, results):
        self.results_data = results
        self.start_btn.setEnabled(True)
        self.current_task_lbl.setText("Benchmark Completed")
        self.log("All tasks finished successfully.")
        
        # Calculate sum of categories B through X
        quality_score = sum(b.get('score', 0) for b in results['benchmarks'] if b.get('id') in list("BCDEFGHIJWX") or b.get('category_id') in list("BCDEFGHIJWX"))
        self.total_score_lbl.setText(f"Total Quality Score: {round(quality_score, 2)}/110")
        
        if not os.path.exists("results"):
            os.makedirs("results")
            
        timestamp = results['date'].replace(':', '').replace('-', '').replace('.', '_')
        filename = f"results/llmark_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            self.last_json_path = os.path.abspath(filename)
            self.open_json_btn.setEnabled(True)
            self.log(f"Results saved to {filename}")
            
            self.json_view.setText(json.dumps(results, indent=2, ensure_ascii=False))
            self.tabs.setCurrentIndex(1) # Switch to results
            
            # Show Contribution Dialog
            dlg = ContributionDialog(results, self)
            dlg.exec()
            
        except Exception as e:
            self.log(f"Error saving results: {e}")

    def open_json_file(self):
        if hasattr(self, 'last_json_path'):
            import subprocess
            if os.name == 'nt':
                os.startfile(self.last_json_path)
            else:
                subprocess.call(('xdg-open', self.last_json_path))

    def open_settings(self):
        from backend.ollama_client import get_config, save_config
        config = get_config()
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.setMinimumWidth(400)
        dialog.setStyleSheet("background-color: #1e1e1e; color: #cccccc;")
        dialog_layout = QVBoxLayout(dialog)
        
        form_layout = QFormLayout()
        url_input = QLineEdit(config.get("ollama_api_url", "http://localhost:11434/api"))
        url_input.setMinimumWidth(300)
        url_input.setStyleSheet("background-color: #3c3c3c; border: 1px solid #3e3e42; padding: 5px; color: #cccccc;")
        form_layout.addRow("Ollama API URL:", url_input)
        
        ctx_input = QLineEdit(str(config.get("context_window", "")))
        ctx_input.setPlaceholderText("e.g. 4096 (Leave empty for model default)")
        ctx_input.setStyleSheet("background-color: #3c3c3c; border: 1px solid #3e3e42; padding: 5px; color: #cccccc;")
        form_layout.addRow("Context Window:", ctx_input)
        
        dialog_layout.addLayout(form_layout)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        buttons.setStyleSheet("QPushButton { background-color: #0e639c; color: white; padding: 5px 15px; }")
        dialog_layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.Accepted:
            new_url = url_input.text().strip()
            new_ctx = ctx_input.text().strip()
            
            if new_url:
                config["ollama_api_url"] = new_url
                self.client.base_url = new_url
            
            if new_ctx:
                try:
                    config["context_window"] = int(new_ctx)
                except ValueError:
                    QMessageBox.warning(self, "Error", "Context Window must be a number.")
                    return
            else:
                config["context_window"] = None
                
            save_config(config)
            QMessageBox.information(self, "Success", "Settings updated.")
            self.load_models()
