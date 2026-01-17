
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, 
                               QLineEdit, QHBoxLayout, QMessageBox, QWidget, QFrame,
                               QTextEdit, QProgressBar)
from PySide6.QtCore import Qt, QThread, Signal, QUrl
from PySide6.QtGui import QDesktopServices
from backend.contribution import ContributionManager

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
        self.setWindowTitle("Beitrag zum LLMark Benchmark")
        self.resize(500, 400)
        self.benchmark_data = benchmark_data
        
        layout = QVBoxLayout(self)
        
        # Header Info
        lbl_info = QLabel("Möchten Sie Ihre Ergebnisse zum Community-Benchmark beitragen?")
        lbl_info.setWordWrap(True)
        lbl_info.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(lbl_info)
        
        lbl_sub = QLabel("Ihr Ergebnis wird als Pull Request submissions auf GitHub hochgeladen.")
        lbl_sub.setWordWrap(True)
        lbl_sub.setStyleSheet("color: #aaa; margin-bottom: 15px;")
        layout.addWidget(lbl_sub)
        
        # --- Authenticated Section ---
        self.group_auth = QFrame()
        self.group_auth.setStyleSheet("background-color: #3b3b3b; border-radius: 5px; padding: 10px;")
        l_auth = QVBoxLayout(self.group_auth)
        
        self.btn_auth_expand = QPushButton("Mit eigenem GitHub Account hochladen")
        self.btn_auth_expand.setCheckable(True)
        self.btn_auth_expand.clicked.connect(self.toggle_auth_view)
        l_auth.addWidget(self.btn_auth_expand)
        
        self.container_auth_input = QWidget()
        self.container_auth_input.setVisible(False)
        l_input = QVBoxLayout(self.container_auth_input)
        l_input.setContentsMargins(0, 10, 0, 0)
        
        l_help = QLabel('Benötigt einen <a href="https://github.com/settings/tokens/new">GitHub Access Token</a> (Set expiration to however long you want. | Just activate the public_repo scope, nothing more is needed).')
        l_help.setOpenExternalLinks(True)
        l_input.addWidget(l_help)
        
        self.input_token = QLineEdit()
        self.input_token.setPlaceholderText("ghp_...")
        self.input_token.setEchoMode(QLineEdit.Password)
        l_input.addWidget(self.input_token)
        
        self.btn_upload = QPushButton("Jetzt hochladen")
        self.btn_upload.clicked.connect(self.start_upload)
        self.btn_upload.setStyleSheet("background-color: #007bff; font-weight: bold;")
        l_input.addWidget(self.btn_upload)
        
        l_auth.addWidget(self.container_auth_input)
        
        layout.addWidget(self.group_auth)
        
        # --- Anonymous Section (Disabled) ---
        self.group_anon = QFrame()
        self.group_anon.setStyleSheet("background-color: #2b2b2b; border: 1px dashed #555; border-radius: 5px; padding: 10px; margin-top: 10px;")
        l_anon = QHBoxLayout(self.group_anon)
        
        btn_anon = QPushButton("Anonym hochladen")
        btn_anon.setEnabled(False) # Disabled
        btn_anon.setToolTip("Coming Soon - Requires Server Infrastructure")
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

    def toggle_auth_view(self):
        visible = self.btn_auth_expand.isChecked()
        self.container_auth_input.setVisible(visible)

    def start_upload(self):
        token = self.input_token.text().strip()
        if not token:
            QMessageBox.warning(self, "Fehler", "Bitte geben Sie einen GitHub Token ein.")
            return
            
        self.btn_upload.setEnabled(False)
        self.input_token.setEnabled(False)
        self.progress.setVisible(True)
        self.log_area.setVisible(True)
        self.log("Starte Upload...")
        
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
            self.log("Upload erfolgreich!")
            self.log(f"PR URL: {result}")
            QMessageBox.information(self, "Erfolg", "Benchmark erfolgreich hochgeladen!\nGitHub Pull Request wurde erstellt.")
            QDesktopServices.openUrl(QUrl(result))
            self.accept()
        else:
            self.log(f"Fehler: {result}")
            QMessageBox.critical(self, "Fehler", f"Upload fehlgeschlagen:\n{result}")
