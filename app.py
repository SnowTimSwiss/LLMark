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
    
    app.setStyleSheet(dark_style)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
