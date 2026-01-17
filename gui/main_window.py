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
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title & Settings
        top_layout = QHBoxLayout()
        title_lbl = QLabel("LLMark Suite")
        title_lbl.setFont(QFont("Segoe UI", 24, QFont.Bold))
        title_lbl.setAlignment(Qt.AlignCenter)
        
        self.settings_btn = QPushButton()
        self.settings_btn.setFixedSize(40, 40)
        self.settings_btn.setToolTip("Settings")
        
        # Simple SVG Gear Icon
        gear_svg = """
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
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

        self.settings_btn.setStyleSheet("""
            QPushButton {
                background-color: #f8f9fa; 
                border: 1px solid #dee2e6; 
                border-radius: 20px;
                color: #495057;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
        """)
        self.settings_btn.clicked.connect(self.open_settings)

        top_layout.addStretch()
        top_layout.addWidget(title_lbl)
        top_layout.addStretch()
        top_layout.addWidget(self.settings_btn)
        layout.addLayout(top_layout)

        # Hardware Info Section
        hw_group = QGroupBox("System Hardware")
        hw_layout = QHBoxLayout()
        
        cpu_lbl = QLabel(f"<b>CPU:</b> {self.hardware_info['cpu']}")
        ram_lbl = QLabel(f"<b>RAM:</b> {self.hardware_info['ram_total_gb']} GB")
        gpu_lbl = QLabel(f"<b>GPU:</b> {self.hardware_info['gpu'] or 'N/A'}")
        
        vram_text = f"<b>VRAM:</b> {self.hardware_info['vram_total_mb'] or 0} MB"
        if self.hardware_info.get('vram_used_mb'):
             vram_text += f" (Used: {self.hardware_info['vram_used_mb']} MB)"
        
        self.vram_lbl = QLabel(vram_text)
        
        hw_layout.addWidget(cpu_lbl)
        hw_layout.addWidget(ram_lbl)
        hw_layout.addWidget(gpu_lbl)
        hw_layout.addWidget(self.vram_lbl)
        hw_group.setLayout(hw_layout)
        layout.addWidget(hw_group)

        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

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

    def setup_control_tab(self):
        layout = QVBoxLayout(self.tab_control)
        
        # Selection
        form_layout = QFormLayout()
        self.model_combo = QComboBox()
        self.refresh_btn = QPushButton("Refresh Models")
        self.refresh_btn.clicked.connect(self.load_models)
        
        h_layout = QHBoxLayout()
        h_layout.addWidget(self.model_combo)
        h_layout.addWidget(self.refresh_btn)
        
        form_layout.addRow("Test Model:", h_layout)
        
        # Judge Section
        judge_layout = QHBoxLayout()
        self.judge_status_lbl = QLabel("qwen2.5:14b-instruct (Checking...)")
        self.judge_status_lbl.setStyleSheet("color: #888;")
        judge_layout.addWidget(self.judge_status_lbl)
        
        self.install_judge_btn = QPushButton("Install Judge Model")
        self.install_judge_btn.setVisible(False)
        self.install_judge_btn.clicked.connect(self.install_judge)
        self.install_judge_btn.setStyleSheet("background-color: #28a745; color: white;")
        judge_layout.addWidget(self.install_judge_btn)

        form_layout.addRow("Judge Model:", judge_layout)
        
        layout.addLayout(form_layout)
        
        # Start Button
        self.start_btn = QPushButton("Start Benchmark")
        self.start_btn.setMinimumHeight(50)
        self.start_btn.setStyleSheet("background-color: #007bff; color: white; font-weight: bold; font-size: 16px;")
        self.start_btn.clicked.connect(self.start_benchmark)
        layout.addWidget(self.start_btn)
        
        # Progress Area
        self.progress_group = QGroupBox("Progress")
        p_layout = QVBoxLayout()
        
        self.overall_progress = QProgressBar()
        self.overall_progress.setMaximum(10)
        
        p_layout.addWidget(QLabel("Overall:"))
        p_layout.addWidget(self.overall_progress)
        
        self.current_task_lbl = QLabel("Ready")
        self.current_task_lbl.setStyleSheet("font-size: 14px; font-weight: bold;")
        p_layout.addWidget(self.current_task_lbl)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        p_layout.addWidget(self.log_area)
        
        self.progress_group.setLayout(p_layout)
        layout.addWidget(self.progress_group)

    def check_judge_status(self):
        from backend.benchmarks import JUDGE_MODEL
        if self.client.check_model_availability(JUDGE_MODEL):
            self.judge_status_lbl.setText(f"{JUDGE_MODEL} (Ready)")
            self.judge_status_lbl.setStyleSheet("color: #00ff00; font-weight: bold;")
            self.install_judge_btn.setVisible(False)
            self.start_btn.setEnabled(True)
        else:
            self.judge_status_lbl.setText(f"{JUDGE_MODEL} (MISSING)")
            self.judge_status_lbl.setStyleSheet("color: #ff4444; font-weight: bold;")
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
        
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(4)
        self.results_table.setHorizontalHeaderLabels(["Benchmark", "Score / Value", "Comment", "Status"])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.results_table)
        
        self.total_score_lbl = QLabel("Total Score (Quality): 0/90")
        self.total_score_lbl.setFont(QFont("Arial", 16, QFont.Bold))
        self.total_score_lbl.setAlignment(Qt.AlignRight)
        layout.addWidget(self.total_score_lbl)
        
        btn_layout = QHBoxLayout()
        self.open_json_btn = QPushButton("JSON Datei öffnen")
        self.open_json_btn.clicked.connect(self.open_json_file)
        self.open_json_btn.setEnabled(False)
        btn_layout.addWidget(self.open_json_btn)
        layout.addLayout(btn_layout)

    def setup_json_tab(self):
        layout = QVBoxLayout(self.tab_json)
        self.json_view = QTextEdit()
        self.json_view.setReadOnly(True)
        self.json_view.setFont(QFont("Consolas", 10))
        layout.addWidget(self.json_view)

    def setup_detail_log_tab(self):
        layout = QVBoxLayout(self.tab_detail_log)
        self.detail_log_view = QTextEdit()
        self.detail_log_view.setReadOnly(True)
        self.detail_log_view.setFont(QFont("Consolas", 10))
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
            QMessageBox.critical(self, "Missing Judge", "The judge model 'qwen2.5:14b-instruct' was not found.\nPlease run 'ollama pull qwen2.5:14b-instruct'.")
            return

        self.start_btn.setEnabled(False)
        self.results_table.setRowCount(0)
        self.total_score_lbl.setText("Total Score (Quality): 0/90")
        self.log_area.clear()
        self.detail_log_view.clear()
        self.overall_progress.setValue(0)
        
        self.worker = BenchmarkWorker(test_model, self.hardware_info)
        self.worker.progress_update.connect(self.on_progress)
        self.worker.verbose_log.connect(self.on_verbose_log)
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

    @Slot(str, dict)
    def on_benchmark_finished(self, bench_id, result):
        self.overall_progress.setValue(self.overall_progress.value() + 1)
        row = self.results_table.rowCount()
        self.results_table.insertRow(row)
        
        name_map = {
            "A": "A: Geschwindigkeit",
            "B": "B: English Quality",
            "C": "C: German Quality",
            "D": "D: Fact Checking",
            "E": "E: Context",
            "F": "F: Logic",
            "G": "G: Creativity",
            "H": "H: ELI5/Explanation",
            "I": "I: Programming",
            "J": "J: Roleplay"
        }
        
        name = name_map.get(bench_id, bench_id)
        score = str(result.get('score', 0))
        comment = result.get('comment', '')
        
        if bench_id == "A":
            score = f"{result.get('score', 0)} t/s"
        else:
            score = str(result.get('score', 0))

        self.results_table.setItem(row, 0, QTableWidgetItem(name))
        self.results_table.setItem(row, 1, QTableWidgetItem(score))
        self.results_table.setItem(row, 2, QTableWidgetItem(comment))
        
        # Color code
        status_item = QTableWidgetItem("OK")
        if "Error" in comment:
            status_item.setText("Fail")
            status_item.setBackground(QColor("#ffcccc"))
        else:
            status_item.setBackground(QColor("#ccffcc"))
            # Dark mode friendly colors logic needed? 
            # Simple text is better for now.
        
        self.results_table.setItem(row, 3, status_item)

    @Slot(dict)
    def on_all_finished(self, results):
        self.results_data = results
        self.start_btn.setEnabled(True)
        self.current_task_lbl.setText("Finished!")
        self.log("All benchmarks completed.")
        
        # Total score should only be B-J (Quality)
        quality_score = sum(b['score'] for b in results['benchmarks'] if b['name'] in list("BCDEFGHIJ"))
        self.total_score_lbl.setText(f"Total Score (Quality): {quality_score}/90")
        
        # Save JSON
        if not os.path.exists("results"):
            os.makedirs("results")
            
        # Safer filename generation from ISO date string
        timestamp = results['date'].replace(':', '').replace('-', '').replace('.', '_')
        filename = f"results/benchmark_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
            self.last_json_path = os.path.abspath(filename)
            self.open_json_btn.setEnabled(True)
            self.log(f"Saved to: {filename}")
            
            # Show JSOn
            self.json_view.setText(json.dumps(results, indent=2, ensure_ascii=False))
            self.tabs.setCurrentIndex(1) # Switch to results
            
        except Exception as e:
            self.log(f"Error while saving: {e}")

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
        dialog_layout = QVBoxLayout(dialog)
        
        form_layout = QFormLayout()
        url_input = QLineEdit(config.get("ollama_api_url", "http://localhost:11434/api"))
        url_input.setMinimumWidth(300)
        form_layout.addRow("Ollama API URL:", url_input)
        dialog_layout.addLayout(form_layout)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        dialog_layout.addWidget(buttons)
        
        if dialog.exec() == QDialog.Accepted:
            new_url = url_input.text().strip()
            if new_url:
                config["ollama_api_url"] = new_url
                save_config(config)
                self.client.base_url = new_url
                QMessageBox.information(self, "Success", "Ollama API URL has been updated.")
                self.load_models()
