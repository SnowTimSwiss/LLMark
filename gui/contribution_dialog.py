
import os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, 
                               QLineEdit, QHBoxLayout, QMessageBox, QWidget, QFrame,
                               QTextEdit, QProgressBar)
from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from backend.contribution import ContributionManager

TOKEN_FILE = ".token"

class ContributionWorker(QThread):
    finished = Signal(bool, str) # success, message_or_url
    
    def __init__(self, token, data):
        super().__init__()
        self.token = token
        self.data = data
        self.manager = ContributionManager()

    def run(self):
        try:
            pr_url = self.manager.upload_authenticated(self.token, self.data)
            self.finished.emit(True, pr_url)
        except Exception as e:
            self.finished.emit(False, str(e))

class ContributionDialog(QDialog):
    def __init__(self, benchmark_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Contribute to LLMark Benchmark")
        self.resize(500, 400)
        self.benchmark_data = benchmark_data
        
        layout = QVBoxLayout(self)
        
        # Header Info
        lbl_info = QLabel("Do you want to contribute your results to the community benchmark?")
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(lbl_info)
        
        lbl_sub = QLabel("Your results will be uploaded as a Pull Request to GitHub.")
        lbl_sub.setWordWrap(True)
        lbl_sub.setStyleSheet("color: #aaa; margin-bottom: 15px;")
        layout.addWidget(lbl_sub)
        
        # --- Authenticated Section ---
        self.group_auth = QFrame()
        self.group_auth.setStyleSheet("background-color: #3b3b3b; border-radius: 5px; padding: 10px;")
        l_auth = QVBoxLayout(self.group_auth)
        
        self.btn_auth_expand = QPushButton("Upload with your GitHub Account")
        self.btn_auth_expand.setCheckable(True)
        self.btn_auth_expand.clicked.connect(self.toggle_auth_view)
        l_auth.addWidget(self.btn_auth_expand)
        
        self.container_auth_input = QWidget()
        self.container_auth_input.setVisible(False)
        l_input = QVBoxLayout(self.container_auth_input)
        l_input.setContentsMargins(0, 10, 0, 0)
        
        l_help = QLabel('Requires a <a href="https://github.com/settings/tokens/new">GitHub Access Token (Classic)</a>.<br>Scopes needed: <b>public_repo</b>.')
        l_help.setOpenExternalLinks(True)
        l_help.setStyleSheet("color: #ccc;")
        l_input.addWidget(l_help)
        
        self.input_token = QLineEdit()
        self.input_token.setPlaceholderText("ghp_...")
        self.input_token.setEchoMode(QLineEdit.Password)
        l_input.addWidget(self.input_token)
        
        self.btn_upload = QPushButton("Upload Now")
        self.btn_upload.clicked.connect(self.start_upload)
        self.btn_upload.setStyleSheet("background-color: #007bff; font-weight: bold;")
        l_input.addWidget(self.btn_upload)
        
        l_auth.addWidget(self.container_auth_input)
        
        layout.addWidget(self.group_auth)
        
        # --- Anonymous Section (Disabled) ---
        self.group_anon = QFrame()
        self.group_anon.setStyleSheet("background-color: #2b2b2b; border: 1px dashed #555; border-radius: 5px; padding: 10px; margin-top: 10px;")
        l_anon = QHBoxLayout(self.group_anon)
        
        btn_anon = QPushButton("Upload Anonymously")
        btn_anon.setEnabled(False) # Disabled
        btn_anon.setToolTip("Coming Soon")
        l_anon.addWidget(btn_anon)
        
        lbl_soon = QLabel("(Coming Soon)")
        lbl_soon.setStyleSheet("color: #777; font-style: italic;")
        l_anon.addWidget(lbl_soon)
        
        l_anon.addStretch()
        layout.addWidget(self.group_anon)
        
        # --- Status / Log ---
        layout.addStretch()
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        self.progress.setRange(0, 0) # Infinite loading
        layout.addWidget(self.progress)
        
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(80)
        self.log_area.setVisible(False)
        layout.addWidget(self.log_area)

        # Load Token
        self.load_token()

    def toggle_auth_view(self):
        visible = self.btn_auth_expand.isChecked()
        self.container_auth_input.setVisible(visible)

    def load_token(self):
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, "r") as f:
                    token = f.read().strip()
                if token:
                    self.input_token.setText(token)
                    self.btn_auth_expand.setChecked(True)
                    self.container_auth_input.setVisible(True)
            except:
                pass

    def save_token(self, token):
        try:
            with open(TOKEN_FILE, "w") as f:
                f.write(token)
        except Exception as e:
            print(f"Failed to save token: {e}")

    def start_upload(self):
        token = self.input_token.text().strip()
        if not token:
            QMessageBox.warning(self, "Error", "Please enter a GitHub Token.")
            return
            
        self.save_token(token)
        
        self.btn_upload.setEnabled(False)
        self.input_token.setEnabled(False)
        self.progress.setVisible(True)
        self.log_area.setVisible(True)
        self.log("Starting upload...")
        
        self.worker = ContributionWorker(token, self.benchmark_data)
        self.worker.finished.connect(self.on_upload_finished)
        self.worker.start()

    def log(self, msg):
        self.log_area.append(msg)

    def on_upload_finished(self, success, result):
        self.progress.setVisible(False)
        self.btn_upload.setEnabled(True)
        self.input_token.setEnabled(True)
        
        if success:
            self.log("Upload successful!")
            self.log(f"PR URL: {result}")
            QMessageBox.information(self, "Success", "Benchmark uploaded successfully!\nGitHub Pull Request created.")
            QDesktopServices.openUrl(QUrl(result))
            self.accept()
        else:
            self.log(f"Error: {result}")
            QMessageBox.critical(self, "Error", f"Upload failed:\n{result}")
