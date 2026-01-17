import json
import os
from PySide6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QComboBox, QPushButton, QProgressBar, 
                               QTableWidget, QTableWidgetItem, QTextEdit, QTabWidget,
                               QHeaderView, QMessageBox, QGroupBox, QFormLayout,
                               QDialog, QLineEdit, QDialogButtonBox)
from PySide6.QtCore import Qt, Slot, QTimer, QSize
from PySide6.QtGui import QFont, QColor, QIcon, QPixmap, QPainter

from backend.ollama_client import OllamaClient
from backend.hardware import get_hardware_info
from gui.workers import BenchmarkWorker, PullWorker, HardwareMonitor

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

        # Apply Global Dark Theme Style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0f1115;
            }
            QWidget {
                color: #e0e0e0;
                font-family: 'Segoe UI', 'Roboto', sans-serif;
            }
            QTabWidget::pane {
                border-top: 2px solid #2d333b;
                background: #161b22;
            }
            QTabBar::tab {
                background: #0d1117;
                color: #8b949e;
                padding: 12px 25px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 4px;
            }
            QTabBar::tab:selected {
                background: #161b22;
                color: #58a6ff;
                border-bottom: 2px solid #58a6ff;
            }
            QGroupBox {
                border: 1px solid #30363d;
                border-radius: 10px;
                margin-top: 15px;
                font-weight: bold;
                padding-top: 10px;
                background-color: #0d1117;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
                color: #58a6ff;
            }
            QPushButton {
                background-color: #21262d;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 8px 16px;
                color: #c9d1d9;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #30363d;
                border-color: #8b949e;
            }
            QPushButton:pressed {
                background-color: #161b22;
            }
            QComboBox {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 5px;
                color: #c9d1d9;
            }
            QProgressBar {
                border: 1px solid #30363d;
                border-radius: 5px;
                text-align: center;
                background-color: #0d1117;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #238636;
                border-radius: 4px;
            }
            QTextEdit {
                background-color: #0d1117;
                border: 1px solid #30363d;
                border-radius: 8px;
                color: #c9d1d9;
                padding: 10px;
            }
            QLabel {
                color: #c9d1d9;
            }
        """)

        # Top Bar
        header_frame = QWidget()
        header_frame.setFixedHeight(100)
        header_frame.setStyleSheet("background-color: #161b22; border-bottom: 1px solid #30363d;")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(30, 0, 30, 0)

        title_lbl = QLabel("LLMark")
        title_lbl.setFont(QFont("Segoe UI", 28, QFont.Bold))
        title_lbl.setStyleSheet("color: #58a6ff; border: none;")
        
        self.settings_btn = QPushButton()
        self.settings_btn.setFixedSize(45, 45)
        self.settings_btn.setToolTip("Settings")
        self.settings_btn.setCursor(Qt.PointingHandCursor)
        
        # Simple SVG Gear Icon
        gear_svg = """
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#c9d1d9" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
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
        
        cpu_lbl = QLabel(f"<b>CPU:</b> {self.hardware_info['cpu']}")
        ram_lbl = QLabel(f"<b>RAM:</b> {self.hardware_info['ram_total_gb']} GB")
        gpu_lbl = QLabel(f"<b>GPU:</b> {self.hardware_info['gpu'] or 'N/A'}")
        
        vram_text = f"<b>VRAM:</b> {self.hardware_info['vram_total_mb'] or 0} MB"
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
        
        layout.addWidget(main_content)

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
        self.judge_status_lbl.setStyleSheet("color: #8b949e;")
        judge_layout.addWidget(self.judge_status_lbl)
        
        self.install_judge_btn = QPushButton("Install Judge")
        self.install_judge_btn.setVisible(False)
        self.install_judge_btn.clicked.connect(self.install_judge)
        self.install_judge_btn.setStyleSheet("background-color: #238636; color: white;")
        judge_layout.addWidget(self.install_judge_btn)

        form_layout.addRow("Judge Model:", judge_layout)
        config_group.setLayout(form_layout)
        layout.addWidget(config_group)
        
        # Start Button
        self.start_btn = QPushButton("🚀 Start Benchmark Suite")
        self.start_btn.setMinimumHeight(60)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #238636; 
                color: white; 
                font-weight: bold; 
                font-size: 18px;
                border: none;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #2ea043;
            }
            QPushButton:disabled {
                background-color: #1b4d24;
                color: #8b949e;
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
        self.current_task_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #58a6ff;")
        p_layout.addWidget(self.current_task_lbl)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setStyleSheet("background-color: #0d1117; font-family: 'Consolas', monospace; border: 1px solid #30363d;")
        p_layout.addWidget(self.log_area)
        
        self.progress_group.setLayout(p_layout)
        layout.addWidget(self.progress_group)

    def check_judge_status(self):
        from backend.benchmarks import JUDGE_MODEL
        if self.client.check_model_availability(JUDGE_MODEL):
            self.judge_status_lbl.setText(f"{JUDGE_MODEL} (Ready)")
            self.judge_status_lbl.setStyleSheet("color: #3fb950; font-weight: bold;")
            self.install_judge_btn.setVisible(False)
            self.start_btn.setEnabled(True)
        else:
            self.judge_status_lbl.setText(f"{JUDGE_MODEL} (MISSING)")
            self.judge_status_lbl.setStyleSheet("color: #f85149; font-weight: bold;")
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
                gridline-color: #30363d;
                border: 1px solid #30363d;
                border-radius: 8px;
                background-color: #0d1117;
                alternate-background-color: #161b22;
                color: #c9d1d9;
            }
            QHeaderView::section {
                background-color: #161b22;
                padding: 10px;
                border: none;
                border-bottom: 2px solid #30363d;
                font-weight: bold;
                color: #58a6ff;
            }
        """)
        
        layout.addWidget(self.results_table)
        
        self.total_score_lbl = QLabel("Total Score: 0/90")
        self.total_score_lbl.setFont(QFont("Segoe UI", 20, QFont.Bold))
        self.total_score_lbl.setAlignment(Qt.AlignRight)
        self.total_score_lbl.setStyleSheet("color: #58a6ff; margin-top: 10px;")
        layout.addWidget(self.total_score_lbl)
        
        btn_layout = QHBoxLayout()
        self.open_json_btn = QPushButton("Open JSON File")
        self.open_json_btn.setMinimumHeight(45)
        self.open_json_btn.setStyleSheet("""
            QPushButton {
                background-color: #21262d; 
                border-radius: 6px; 
                padding: 0 25px;
            }
            QPushButton:hover { background-color: #30363d; }
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
        self.json_view.setStyleSheet("background-color: #0d1117; color: #d1d5db; border: 1px solid #30363d;")
        layout.addWidget(self.json_view)

    def setup_detail_log_tab(self):
        layout = QVBoxLayout(self.tab_detail_log)
        self.detail_log_view = QTextEdit()
        self.detail_log_view.setReadOnly(True)
        self.detail_log_view.setFont(QFont("Consolas", 11))
        self.detail_log_view.setStyleSheet("background-color: #0d1117; color: #c9d1d9; border: 1px solid #30363d;")
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
        vram_text = f"<b>VRAM:</b> {total} MB (Used: {used} MB)"
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
        self.total_score_lbl.setText("Total Score: 0/90")
        self.log_area.clear()
        self.detail_log_view.clear()
        self.overall_progress.setValue(0)
        
        self.worker = BenchmarkWorker(test_model, self.hardware_info)
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
        cursor.movePosition(cursor.End)
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
            "H": "H: ELI5 Complexity",
            "I": "I: Python Coding",
            "J": "J: Customer Support"
        }
        
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
            status_item.setBackground(QColor("#f85149"))
        else:
            status_item.setText(" PASS ")
            status_item.setBackground(QColor("#238636"))
        
        status_item.setForeground(QColor("white"))
        self.results_table.setItem(row, 3, status_item)
        self.results_table.setRowHeight(row, 50)

    @Slot(dict)
    def on_all_finished(self, results):
        self.results_data = results
        self.start_btn.setEnabled(True)
        self.current_task_lbl.setText("Benchmark Completed")
        self.log("All tasks finished successfully.")
        
        quality_score = sum(b['score'] for b in results['benchmarks'] if b['name'] in list("BCDEFGHIJ"))
        self.total_score_lbl.setText(f"Total Quality Score: {quality_score}/90")
        
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
        dialog.setStyleSheet("background-color: #0d1117; color: #c9d1d9;")
        dialog_layout = QVBoxLayout(dialog)
        
        form_layout = QFormLayout()
        url_input = QLineEdit(config.get("ollama_api_url", "http://localhost:11434/api"))
        url_input.setMinimumWidth(300)
        url_input.setStyleSheet("background-color: #161b22; border: 1px solid #30363d; padding: 5px;")
        form_layout.addRow("Ollama API URL:", url_input)
        dialog_layout.addLayout(form_layout)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        buttons.setStyleSheet("QPushButton { background-color: #21262d; padding: 5px 15px; }")
        dialog_layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.Accepted:
            new_url = url_input.text().strip()
            if new_url:
                config["ollama_api_url"] = new_url
                save_config(config)
                self.client.base_url = new_url
                QMessageBox.information(self, "Success", "Ollama API URL updated.")
                self.load_models()
