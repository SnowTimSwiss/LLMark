import sys
from PySide6.QtWidgets import QApplication
from gui.main_window import MainWindow

def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Dark Mode Stylesheet
    dark_style = """
    QMainWindow, QWidget {
        background-color: #2b2b2b;
        color: #e0e0e0;
        font-family: "Segoe UI", sans-serif;
    }
    
    QGroupBox {
        border: 1px solid #555;
        border-radius: 5px;
        margin-top: 10px;
        font-weight: bold;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px;
    }
    
    QPushButton {
        background-color: #3d3d3d;
        border: 1px solid #555;
        border-radius: 4px;
        padding: 5px 15px;
        color: #fff;
    }
    QPushButton:hover {
        background-color: #4d4d4d;
    }
    QPushButton:pressed {
        background-color: #2d2d2d;
    }
    QPushButton:disabled {
        background-color: #2b2b2b;
        color: #666;
    }
    
    QComboBox {
        background-color: #3b3b3b;
        border: 1px solid #555;
        border-radius: 3px;
        padding: 5px;
        color: #fff;
    }
    QComboBox::drop-down {
        border: none;
    }
    
    QTableWidget {
        background-color: #3b3b3b;
        gridline-color: #555;
        color: #fff;
    }
    QHeaderView::section {
        background-color: #444;
        color: #fff;
        padding: 5px;
        border: 1px solid #555;
    }
    QTableCornerButton::section {
        background-color: #444;
        border: 1px solid #555;
    }
    
    QProgressBar {
        border: 1px solid #555;
        border-radius: 3px;
        text-align: center;
        background-color: #3d3d3d;
    }
    QProgressBar::chunk {
        background-color: #007bff;
        width: 10px;
    }
    
    QTextEdit {
        background-color: #1e1e1e;
        color: #dcdcdc;
        border: 1px solid #555;
    }
    
    QTabWidget::pane {
        border: 1px solid #555;
    }
    QTabBar::tab {
        background: #3d3d3d;
        color: #fff;
        padding: 8px 12px;
        margin-right: 2px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    QTabBar::tab:selected {
        background: #007bff;
        font-weight: bold;
    }
    """
    
    import argparse
    parser = argparse.ArgumentParser(description="LLMark Benchmark Suite")
    parser.set_defaults(autopilot=False)
    parser.add_argument("--autopilot", action="store_true", help="Start in Auto-Pilot mode")
    parser.add_argument("--token", type=str, help="GitHub Token for Auto-Pilot")
    args, unknown = parser.parse_known_args()

    app.setStyleSheet(dark_style)
    
    window = MainWindow()
    
    if args.autopilot:
        if args.token:
            window.token_input.setText(args.token)
        # We need to wait for the window to be shown before starting the worker
        # or use a QTimer to start it right after show
        from PySide6.QtCore import QTimer
        QTimer.singleShot(500, window.start_autopilot_if_requested)

    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
