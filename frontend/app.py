import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from PyQt6.QtWidgets import QApplication, QMainWindow, QTabWidget

try:
    from .folder_tab import FolderTab
    from .templates_tab import TemplatesTab
except ImportError:
    from folder_tab import FolderTab
    from templates_tab import TemplatesTab


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Refindika")
        self.resize(990, 610)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.template_tab = TemplatesTab()
        self.folder_tab = FolderTab(self.template_tab)
        self.template_tab.template_changed = self.folder_tab.refresh_table

        self.tabs.addTab(self.folder_tab, "Folder")
        self.tabs.addTab(self.template_tab, "Templates")

        self.apply_styles()

    # ---- Funkcja ustawia style calej aplikacji ----
    def apply_styles(self):
        self.setStyleSheet(
            """
            QWidget {
                font-family: Segoe UI, Arial, sans-serif;
                font-size: 12px;
            }
            QMainWindow, QTabWidget::pane, QWidget {
                background: #fbfcfd;
            }
            QTabWidget::pane {
                border: none;
                top: -1px;
            }
            QTabWidget::tab-bar {
                left: 2px;
            }
            QTabBar::tab {
                min-width: 86px;
                min-height: 29px;
                margin: 0 4px 2px 0;
                padding: 0 2px;
                color: #3f4650;
                background: #ffffff;
                border: 1px solid #edf0f3;
                border-radius: 8px;
                font-weight: 600;
            }
            QTabBar::tab:selected {
                color: #2d333a;
                background: #ffffff;
                border-color: #dfe5eb;
            }
            QTabBar::tab:!selected {
                color: #5d6470;
            }
            QLineEdit {
                min-height: 28px;
                padding: 0 12px;
                border: 1px solid #e1e5e9;
                border-radius: 7px;
                background: #ffffff;
            }
            QPushButton {
                min-height: 28px;
                padding: 0 18px;
                border: 1px solid #e2e6ea;
                border-radius: 7px;
                background: #ffffff;
                color: #2f3742;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #f5f8fb;
            }
            QPushButton#PrimaryButton {
                color: #2b3744;
                border-color: #d5e7fb;
                background: #e8f2ff;
            }
            QPushButton#PrimaryButton:hover {
                background: #dbeeff;
            }
            QPushButton#FilterButton {
                padding: 0 12px;
            }
            QListWidget {
                border: none;
                background: #ffffff;
                padding: 2px 8px 8px 0;
                outline: none;
            }
            QListWidget::item {
                min-height: 36px;
                padding: 4px 10px;
                border-radius: 6px;
                color: #46505d;
            }
            QListWidget::item:selected {
                color: #334155;
                background: #dcecff;
                font-weight: 600;
            }
            QFrame#Sidebar {
                border-right: 1px solid #edf0f3;
                background: #ffffff;
            }
            QLabel#SidebarTitle {
                min-height: 28px;
                padding-left: 2px;
                border: 1px solid #edf0f3;
                border-radius: 8px;
                background: #ffffff;
                color: #344054;
                font-weight: 700;
            }
            QFrame#TableFrame {
                border-left: 1px solid #edf0f3;
                border-top: 1px solid #edf0f3;
                border-radius: 0;
                background: #ffffff;
            }
            QTableWidget {
                border: 1px solid #edf0f3;
                gridline-color: #edf0f3;
                background: #ffffff;
                alternate-background-color: #fbfcfd;
                selection-background-color: #dcecff;
                selection-color: #1f2937;
            }
            QHeaderView::section {
                min-height: 28px;
                padding: 0 8px;
                border: none;
                border-right: 1px solid #e4e8ec;
                border-bottom: 1px solid #e4e8ec;
                background: #f5f5f5;
                color: #374151;
                font-weight: 600;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QLabel#PageTitle {
                font-size: 22px;
                font-weight: 700;
            }
            QLabel#SectionTitle {
                color: #344054;
                font-weight: 700;
            }
            QLabel#DialogTitle {
                font-size: 16px;
                font-weight: 700;
            }
            QLabel#MutedText {
                color: #5e6b78;
            }
            QLabel#StatusWaiting {
                color: #6b7280;
            }
            QLabel#StatusInProgress {
                color: #1976bd;
                font-weight: 600;
            }
            QLabel#StatusDone {
                color: #198754;
                font-weight: 600;
            }
            QLabel#StatusError {
                color: #b42318;
                font-weight: 600;
            }
            """
        )


# ---- Funkcja startuje aplikacje desktopowa ----
def main():
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
