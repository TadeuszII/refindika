import os
import sys
import threading
import time
from queue import Queue
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from backend.audio_metadata import AUDIO_METADATA_FIELDS, extract_audio_metadata
from templates_tab import METADATA_BY_TYPE, TemplatesTab, normalize_file_type


FILE_TYPES = {
    "Video": {".mp4", ".avi", ".mov", ".mkv", ".webm"},
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"},
    "PDF": {".pdf"},
    "Word": {".doc", ".docx", ".odt", ".rtf"},
}


def format_file_size(size):
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.0f} KB"
    if size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.0f} MB"
    return f"{size / (1024 * 1024 * 1024):.1f} GB"


def format_modified_time(path):
    return time.strftime("%d.%m.%Y %H:%M", time.localtime(path.stat().st_mtime))


class CategoryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select categories")
        self.setModal(True)
        self.resize(360, 230)

        layout = QVBoxLayout(self)

        title = QLabel("Choose file types for metadata extraction")
        title.setObjectName("DialogTitle")
        layout.addWidget(title)

        hint = QLabel("All categories are selected by default.")
        hint.setObjectName("MutedText")
        layout.addWidget(hint)

        self.checkboxes = {}
        for category in FILE_TYPES:
            checkbox = QCheckBox(category)
            checkbox.setChecked(True)
            self.checkboxes[category] = checkbox
            layout.addWidget(checkbox)

        buttons = QHBoxLayout()
        buttons.addStretch()

        self.exit_button = QPushButton("Exit")
        self.exit_button.clicked.connect(self.reject)
        buttons.addWidget(self.exit_button)

        self.ok_button = QPushButton("OK")
        self.ok_button.setDefault(True)
        self.ok_button.clicked.connect(self.accept)
        buttons.addWidget(self.ok_button)

        layout.addLayout(buttons)

    def selected_categories(self):
        return [
            category
            for category, checkbox in self.checkboxes.items()
            if checkbox.isChecked()
        ]


class ExtractionWorker:
    def __init__(self, category, files, events, templates_by_type):
        self.category = category
        self.files = files
        self.events = events
        self.templates_by_type = templates_by_type

    def run(self):
        self.events.put(("status", self.category, "in progress"))
        extracted = []

        try:
            for index, path in enumerate(self.files):
                time.sleep(0.18)
                extracted.append(self.extract_file(path))

                if index == len(self.files) - 1:
                    time.sleep(0.12)

            self.events.put(("status", self.category, "done"))
            self.events.put(("finished", self.category, extracted))
        except Exception:
            self.events.put(("status", self.category, "error"))
            self.events.put(("finished", self.category, extracted))

    def extract_file(self, path):
        if self.category == "Audio":
            template = self.templates_by_type.get("audio")
            return extract_audio_metadata(path, template)

        return {
            "name": path.name,
            "category": self.category,
            "extension": path.suffix.lower() or "none",
            "original_name": path.name,
            "file_type": self.category.lower(),
            "modified": format_modified_time(path),
            "size": format_file_size(path.stat().st_size),
            "path": str(path),
            "custom_name": path.name,
        }


class ExtractionDialog(QDialog):
    extraction_finished = pyqtSignal(list)

    def __init__(self, categorized_files, templates_by_type, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Metadata extraction")
        self.setModal(True)
        self.resize(460, 300)

        self.categorized_files = categorized_files
        self.templates_by_type = templates_by_type
        self.threads = []
        self.events = Queue()
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self.process_events)
        self.results = []
        self.finished_count = 0

        layout = QVBoxLayout(self)

        title = QLabel("Extracting metadata")
        title.setObjectName("DialogTitle")
        layout.addWidget(title)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        layout.addWidget(self.progress)

        self.status_grid = QGridLayout()
        self.status_labels = {}

        for row, category in enumerate(categorized_files):
            name_label = QLabel(category)
            status_label = QLabel("waiting")
            status_label.setObjectName("StatusWaiting")
            self.status_labels[category] = status_label

            self.status_grid.addWidget(name_label, row, 0)
            self.status_grid.addWidget(status_label, row, 1)

        layout.addLayout(self.status_grid)
        layout.addStretch()

        buttons = QHBoxLayout()
        buttons.addStretch()
        self.ok_button = QPushButton("OK")
        self.ok_button.setEnabled(False)
        self.ok_button.clicked.connect(self.accept)
        buttons.addWidget(self.ok_button)
        layout.addLayout(buttons)

    def start_extraction(self):
        if not self.categorized_files:
            self.progress.setRange(0, 1)
            self.progress.setValue(1)
            self.ok_button.setEnabled(True)
            return

        for category, files in self.categorized_files.items():
            worker = ExtractionWorker(
                category, files, self.events, self.templates_by_type
            )
            thread = threading.Thread(target=worker.run, daemon=True)
            self.threads.append(thread)
            thread.start()

        self.poll_timer.start(80)

    def process_events(self):
        while not self.events.empty():
            event_type, category, payload = self.events.get()
            if event_type == "status":
                self.update_status(category, payload)
            elif event_type == "finished":
                self.collect_results(category, payload)
                self.check_finished()

    def update_status(self, category, status):
        label = self.status_labels[category]
        label.setText(status)
        label.setObjectName(f"Status{status.title().replace(' ', '')}")
        label.style().unpolish(label)
        label.style().polish(label)

    def collect_results(self, _category, results):
        self.results.extend(results)

    def check_finished(self):
        self.finished_count += 1
        if self.finished_count == len(self.threads):
            self.poll_timer.stop()
            self.progress.setRange(0, 1)
            self.progress.setValue(1)
            self.ok_button.setEnabled(True)
            self.extraction_finished.emit(self.results)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Refindika")
        self.resize(990, 610)

        self.current_files = []
        self.active_category = "All files"

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.folder_tab = QWidget()
        self.template_tab = TemplatesTab()
        self.template_tab.template_changed = self.refresh_table

        self.tabs.addTab(self.folder_tab, "Folder")
        self.tabs.addTab(self.template_tab, "Templates")

        self.setup_folder_tab()
        self.apply_styles()

    # Funkcja dla budowania glownej strony Folder.
    def setup_folder_tab(self):
        main_layout = QVBoxLayout(self.folder_tab)
        main_layout.setContentsMargins(0, 8, 0, 0)
        main_layout.setSpacing(8)

        # Pasek dla wpisania adresu folderu oraz przyciskow Open i Scan.
        path_bar = QHBoxLayout()
        path_bar.setContentsMargins(2, 0, 8, 0)
        path_bar.setSpacing(8)

        # Textbox dla adresu foldera.
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText(
            "Enter folder path... e.g. C:/Users/Daniel/Videos"
        )
        path_bar.addWidget(self.path_input, 1)

        # Przycisk dla wyboru folderu przez file explorer.
        open_button = QPushButton("Open")
        open_button.clicked.connect(self.open_folder)
        path_bar.addWidget(open_button)

        # Przycisk dla rozpoczecia skanowania folderu.
        scan_button = QPushButton("Scan")
        scan_button.setObjectName("PrimaryButton")
        scan_button.clicked.connect(self.scan_folder)
        path_bar.addWidget(scan_button)

        main_layout.addLayout(path_bar)

        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(6)

        # Lewy panel dla kategorii plikow.
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(198)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 6, 0)
        sidebar_layout.setSpacing(8)

        sidebar_title = QLabel("Categories")
        sidebar_title.setObjectName("SidebarTitle")
        sidebar_layout.addWidget(sidebar_title)

        # Lista dla wyboru kategorii wyswietlanych plikow.
        self.category_list = QListWidget()
        self.category_list.itemClicked.connect(self.change_category)
        sidebar_layout.addWidget(self.category_list, 1)
        content.addWidget(sidebar)

        # Glowny kontener dla wyszukiwarki i tabeli plikow.
        table_frame = QFrame()
        table_frame.setObjectName("TableFrame")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(8, 6, 6, 6)
        table_layout.setSpacing(6)

        # Pasek dla wyszukiwania plikow w tabeli.
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Search")
        self.filter_input.returnPressed.connect(self.refresh_table)
        filter_bar.addWidget(self.filter_input)

        # Przycisk dla zastosowania filtra wyszukiwania.
        filter_button = QPushButton("Filter")
        filter_button.setObjectName("FilterButton")
        filter_button.clicked.connect(self.refresh_table)
        filter_bar.addWidget(filter_button)
        table_layout.addLayout(filter_bar)

        # Tabela dla wynikow skanowania folderu.
        self.files_table = QTableWidget(0, 5)
        self.files_table.setHorizontalHeaderLabels(
            ["Name", "Type", "Modified", "Size", "Path"]
        )
        self.files_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Interactive
        )
        self.files_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Interactive
        )
        self.files_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Interactive
        )
        self.files_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Interactive
        )
        self.files_table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Stretch
        )
        self.files_table.setColumnWidth(0, 155)
        self.files_table.setColumnWidth(1, 150)
        self.files_table.setColumnWidth(2, 155)
        self.files_table.setColumnWidth(3, 150)
        self.files_table.setAlternatingRowColors(True)
        self.files_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.files_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.files_table.verticalHeader().setVisible(False)
        table_layout.addWidget(self.files_table)

        content.addWidget(table_frame, 1)
        main_layout.addLayout(content, 1)

        self.reset_categories()

    # Funkcja dla resetowania listy kategorii na glownej stronie.
    def reset_categories(self):
        self.category_list.clear()
        item = QListWidgetItem("All files")
        self.category_list.addItem(item)
        self.category_list.setCurrentItem(item)
        self.active_category = "All files"

    # Funkcja dla otwierania okna wyboru folderu.
    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Open folder")
        if folder:
            self.path_input.setText(folder)

    # Funkcja dla sprawdzania folderu i uruchomienia skanowania.
    def scan_folder(self):
        folder_text = self.path_input.text().strip()
        folder_path = Path(folder_text)

        if not folder_text or not folder_path.exists() or not folder_path.is_dir():
            QMessageBox.warning(
                self,
                "Invalid folder",
                "The folder path is invalid or the folder does not exist.",
            )
            return

        all_files = [path for path in folder_path.iterdir() if path.is_file()]
        if not all_files:
            QMessageBox.information(self, "Empty folder", "The folder is empty.")
            return

        category_dialog = CategoryDialog(self)
        if category_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        selected = category_dialog.selected_categories()
        categorized_files = self.group_files_by_category(all_files, selected)

        extraction_dialog = ExtractionDialog(
            categorized_files, self.template_tab.active_templates_by_type.copy(), self
        )
        extraction_dialog.extraction_finished.connect(self.load_results)
        extraction_dialog.show()
        extraction_dialog.start_extraction()
        extraction_dialog.exec()

    # Funkcja dla przypisania plikow do wybranych kategorii.
    def group_files_by_category(self, files, selected_categories):
        grouped = {}
        for category in selected_categories:
            extensions = FILE_TYPES[category]
            matched_files = [
                path for path in files if path.suffix.lower() in extensions
            ]
            if matched_files:
                grouped[category] = matched_files
        return grouped

    # Funkcja dla zaladowania zeskanowanych plikow do glownej tabeli.
    def load_results(self, files):
        self.current_files = sorted(files, key=lambda item: item["name"].lower())

        self.category_list.clear()
        self.category_list.addItem("All files")
        for category in FILE_TYPES:
            if any(file["category"] == category for file in self.current_files):
                self.category_list.addItem(category)

        audio_row = self.find_category_row("Audio")
        if audio_row is not None:
            self.category_list.setCurrentRow(audio_row)
            self.active_category = "Audio"
        else:
            self.category_list.setCurrentRow(0)
            self.active_category = "All files"

        self.refresh_table()

    # Funkcja dla znalezienia kategorii w lewym panelu.
    def find_category_row(self, category):
        for row in range(self.category_list.count()):
            if self.category_list.item(row).text() == category:
                return row

        return None

    # Funkcja dla zmiany aktywnej kategorii w lewym panelu.
    def change_category(self, item):
        self.active_category = item.text()
        self.refresh_table()

    # Funkcja dla odswiezania tabeli wedlug kategorii i tekstu Search.
    def refresh_table(self):
        query = self.filter_input.text().strip().lower()
        rows = []

        for file in self.current_files:
            if (
                self.active_category != "All files"
                and file["category"] != self.active_category
            ):
                continue

            searchable = " ".join(str(value) for value in file.values()).lower()
            if query and query not in searchable:
                continue

            rows.append(file)

        # -- if zostawia standardowy widok dla wszystkich plikow --
        if self.active_category == "All files":
            self.show_all_files_table(rows)
            return

        self.show_category_table(rows)

    # Funkcja dla wyswietlania standardowej tabeli All files.
    def show_all_files_table(self, rows):
        self.files_table.setColumnCount(5)
        self.files_table.setHorizontalHeaderLabels(
            ["Name", "Type", "Modified", "Size", "Path"]
        )
        self.files_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Interactive
        )
        self.files_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Interactive
        )
        self.files_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeMode.Interactive
        )
        self.files_table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeMode.Interactive
        )
        self.files_table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeMode.Stretch
        )
        self.files_table.setColumnWidth(0, 155)
        self.files_table.setColumnWidth(1, 150)
        self.files_table.setColumnWidth(2, 155)
        self.files_table.setColumnWidth(3, 150)

        self.files_table.setRowCount(len(rows))
        for row, file in enumerate(rows):
            self.files_table.setItem(row, 0, QTableWidgetItem(file["name"]))
            self.files_table.setItem(row, 1, QTableWidgetItem(file["category"]))
            self.files_table.setItem(row, 2, QTableWidgetItem(file["modified"]))
            self.files_table.setItem(row, 3, QTableWidgetItem(file["size"]))
            self.files_table.setItem(row, 4, QTableWidgetItem(file["path"]))

    # Funkcja dla wyswietlania tabeli kategorii wedlug aktywnego template.
    def show_category_table(self, rows):
        metadata_columns = self.get_active_metadata_columns()
        headers = [self.format_header_name(item) for item in metadata_columns]

        self.files_table.setColumnCount(len(headers))
        self.files_table.setHorizontalHeaderLabels(headers)

        # --- Loops ustawia szerokosci kolumn kategorii ---
        for column in range(len(headers)):
            self.files_table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.Interactive
            )
            self.files_table.setColumnWidth(column, 140)

        if headers:
            path_column = len(headers) - 1
            self.files_table.horizontalHeader().setSectionResizeMode(
                path_column, QHeaderView.ResizeMode.Stretch
            )

        self.files_table.setRowCount(len(rows))

        # --- Loops wypelnia tabele kategoriami i metadanymi ---
        for row, file in enumerate(rows):
            for index, metadata_name in enumerate(metadata_columns):
                value = self.get_metadata_value(file, metadata_name)
                self.files_table.setItem(row, index, QTableWidgetItem(value))

    # Funkcja zwraca aktywne metadane dla wybranej kategorii.
    def get_active_metadata_columns(self):
        active_template = self.template_tab.get_active_template(self.active_category)

        # -- if brak template, uzywa pelnej listy metadanych kategorii --
        if not active_template:
            return METADATA_BY_TYPE.get(self.active_category, [])

        selected_columns = []
        file_type = normalize_file_type(active_template.get("Type", ""))

        # --- Loops wybiera tylko zaznaczone metadane z template ---
        for metadata_name in METADATA_BY_TYPE.get(file_type, []):
            if active_template.get(metadata_name, True):
                selected_columns.append(metadata_name)

        return selected_columns

    # Funkcja zamienia nazwe metadanej na czytelny naglowek tabeli.
    def format_header_name(self, metadata_name):
        return metadata_name.replace("_", " ").title()

    # Funkcja zwraca wartosc metadanej z danych pliku.
    def get_metadata_value(self, file, metadata_name):
        # -- if podstawowe dane juz istnieja w obecnym modelu pliku --
        if metadata_name == "extension":
            return file.get("extension", "")

        if metadata_name == "original_name":
            return file.get("original_name", file.get("name", ""))

        if metadata_name == "file_type":
            return file.get("file_type", file.get("category", "").lower())

        value = file.get(metadata_name, "")
        if value:
            return str(value)

        return self.get_tika_metadata_value(file, metadata_name)

    # Funkcja szuka wartosci bezposrednio w surowych metadanych Tika.
    def get_tika_metadata_value(self, file, metadata_name):
        tika_metadata = file.get("tika_metadata", {})
        aliases = AUDIO_METADATA_FIELDS.get(metadata_name, [])

        for alias in aliases:
            if alias in tika_metadata:
                return str(tika_metadata[alias])

        normalized_metadata = {
            str(key).strip().lower().replace("-", "_").replace(" ", "_"): value
            for key, value in tika_metadata.items()
        }

        for alias in aliases:
            normalized_alias = (
                str(alias).strip().lower().replace("-", "_").replace(" ", "_")
            )
            value = normalized_metadata.get(normalized_alias)
            if value:
                return str(value)

        return ""

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


def main():
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
