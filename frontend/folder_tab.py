from pathlib import Path

from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from backend.audio_metadata import AUDIO_METADATA_FIELDS
from backend.dublicate_handler import find_duplicate_indexes
from backend.pdf_metadata import PDF_METADATA_FIELDS
from backend.rename_files import build_unique_path, rename_file, render_custom_name
from backend.video_metadata import VIDEO_METADATA_FIELDS
from backend.word_metadata import WORD_METADATA_FIELDS
try:
    from .extraction_worker import (
        FILE_TYPES,
        CategoryDialog,
        ExtractionDialog,
        format_file_size,
        format_modified_time,
    )
    from .template_storage import METADATA_BY_TYPE, normalize_file_type
except ImportError:
    from extraction_worker import (
        FILE_TYPES,
        CategoryDialog,
        ExtractionDialog,
        format_file_size,
        format_modified_time,
    )
    from template_storage import METADATA_BY_TYPE, normalize_file_type


class FolderTab(QWidget):
    def __init__(self, template_tab, parent=None):
        super().__init__(parent)
        self.template_tab = template_tab
        self.current_files = []
        self.visible_files = []
        self.active_category = "All files"

        self.setup_ui()

    # ---- Funkcja buduje zakladke Folder ----
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 8, 0, 0)
        main_layout.setSpacing(8)

        path_bar = QHBoxLayout()
        path_bar.setContentsMargins(2, 0, 8, 0)
        path_bar.setSpacing(8)

        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText(
            "Enter folder path... e.g. C:/Users/Daniel/Videos"
        )
        path_bar.addWidget(self.path_input, 1)

        open_button = QPushButton("Open")
        open_button.clicked.connect(self.open_folder)
        path_bar.addWidget(open_button)

        scan_button = QPushButton("Scan")
        scan_button.setObjectName("PrimaryButton")
        scan_button.clicked.connect(self.scan_folder)
        path_bar.addWidget(scan_button)

        main_layout.addLayout(path_bar)

        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(6)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(198)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 6, 0)
        sidebar_layout.setSpacing(8)

        sidebar_title = QLabel("Categories")
        sidebar_title.setObjectName("SidebarTitle")
        sidebar_layout.addWidget(sidebar_title)

        self.category_list = QListWidget()
        self.category_list.itemClicked.connect(self.change_category)
        sidebar_layout.addWidget(self.category_list, 1)
        content.addWidget(sidebar)

        table_frame = QFrame()
        table_frame.setObjectName("TableFrame")
        table_layout = QVBoxLayout(table_frame)
        table_layout.setContentsMargins(8, 6, 6, 6)
        table_layout.setSpacing(6)

        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(8)
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Search")
        self.filter_input.returnPressed.connect(self.refresh_table)
        filter_bar.addWidget(self.filter_input)

        filter_button = QPushButton("Filter")
        filter_button.setObjectName("FilterButton")
        filter_button.clicked.connect(self.refresh_table)
        filter_bar.addWidget(filter_button)

        self.select_all_button = QPushButton("Select All")
        self.select_all_button.clicked.connect(self.select_all_visible_files)
        filter_bar.addWidget(self.select_all_button)

        self.rename_button = QPushButton("Rename selected")
        self.rename_button.setObjectName("PrimaryButton")
        self.rename_button.clicked.connect(self.rename_selected_files)
        filter_bar.addWidget(self.rename_button)

        table_layout.addLayout(filter_bar)

        self.files_table = QTableWidget(0, 5)
        self.files_table.setHorizontalHeaderLabels(
            ["Name", "Type", "Modified", "Size", "Path"]
        )
        self.set_all_files_column_sizes()
        self.files_table.setAlternatingRowColors(True)
        self.files_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.files_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.files_table.verticalHeader().setVisible(False)
        table_layout.addWidget(self.files_table)

        content.addWidget(table_frame, 1)
        main_layout.addLayout(content, 1)

        self.reset_categories()

    # ---- Funkcja ustawia szerokosci kolumn dla widoku All files ----
    def set_all_files_column_sizes(self):
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

    # ---- Funkcja resetuje liste kategorii ----
    def reset_categories(self):
        self.category_list.clear()
        item = QListWidgetItem("All files")
        self.category_list.addItem(item)
        self.category_list.setCurrentItem(item)
        self.active_category = "All files"

        # -- if przyciski juz istnieja, wylacza rename dla All files --
        if hasattr(self, "select_all_button"):
            self.set_rename_buttons_enabled(False)

    # ---- Funkcja otwiera okno wyboru folderu ----
    def open_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Open folder")

        # -- if wybrano folder, wpisuje go do pola tekstowego --
        if folder:
            self.path_input.setText(folder)

    # ---- Funkcja sprawdza folder i uruchamia skanowanie ----
    def scan_folder(self):
        folder_text = self.path_input.text().strip()
        folder_path = Path(folder_text)

        # -- if sciezka jest niepoprawna, pokazuje blad --
        if not folder_text or not folder_path.exists() or not folder_path.is_dir():
            QMessageBox.warning(
                self,
                "Invalid folder",
                "The folder path is invalid or the folder does not exist.",
            )
            return

        all_files = [path for path in folder_path.iterdir() if path.is_file()]

        # -- if folder nie ma plikow, pokazuje informacje --
        if not all_files:
            QMessageBox.information(self, "Empty folder", "The folder is empty.")
            return

        category_dialog = CategoryDialog(self)

        # -- if uzytkownik zamknal okno, zatrzymuje skanowanie --
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

    # ---- Funkcja przypisuje pliki do wybranych kategorii ----
    def group_files_by_category(self, files, selected_categories):
        grouped = {}

        # --- Loops sprawdza rozszerzenia plikow dla kazdej kategorii ---
        for category in selected_categories:
            extensions = FILE_TYPES[category]
            matched_files = [
                path for path in files if path.suffix.lower() in extensions
            ]

            # -- if sa pliki w kategorii, dodaje je do wyniku --
            if matched_files:
                grouped[category] = matched_files

        return grouped

    # ---- Funkcja laduje zeskanowane pliki do tabeli ----
    def load_results(self, files):
        self.current_files = sorted(files, key=lambda item: item["name"].lower())

        self.category_list.clear()
        self.category_list.addItem("All files")

        # --- Loops dodaje tylko kategorie, ktore maja pliki ---
        for category in FILE_TYPES:
            if any(file["category"] == category for file in self.current_files):
                self.category_list.addItem(category)

        first_category = self.find_first_scanned_category()

        # -- if znaleziono zeskanowana kategorie, ustawia ja jako aktywna --
        if first_category is not None:
            row, category = first_category
            self.category_list.setCurrentRow(row)
            self.active_category = category
        else:
            self.category_list.setCurrentRow(0)
            self.active_category = "All files"

        self.refresh_table()

    # ---- Funkcja zwraca pierwsza zeskanowana kategorie ----
    def find_first_scanned_category(self):
        for category in FILE_TYPES:
            row = self.find_category_row(category)

            # -- if kategoria istnieje w panelu, zwraca jej numer --
            if row is not None:
                return row, category

        return None

    # ---- Funkcja znajduje kategorie w panelu bocznym ----
    def find_category_row(self, category):
        for row in range(self.category_list.count()):
            if self.category_list.item(row).text() == category:
                return row

        return None

    # ---- Funkcja zmienia aktywna kategorie ----
    def change_category(self, item):
        self.active_category = item.text()
        self.refresh_table()

    # ---- Funkcja odswieza tabele wedlug kategorii i tekstu Search ----
    def refresh_table(self):
        query = self.filter_input.text().strip().lower()
        rows = []

        # --- Loops filtruje aktualne pliki dla tabeli ---
        for file in self.current_files:
            if (
                self.active_category != "All files"
                and file["category"] != self.active_category
            ):
                continue

            searchable = " ".join(str(value) for value in file.values()).lower()

            # -- if tekst nie pasuje do wyszukiwania, pomija plik --
            if query and query not in searchable:
                continue

            rows.append(file)

        # -- if pokazuje wszystkie pliki, zostawia standardowe kolumny --
        if self.active_category == "All files":
            self.set_rename_buttons_enabled(False)
            self.show_all_files_table(rows)
            return

        self.set_rename_buttons_enabled(True)
        self.show_category_table(rows)

    # ---- Funkcja wlacza albo wylacza przyciski rename ----
    def set_rename_buttons_enabled(self, is_enabled):
        self.select_all_button.setEnabled(is_enabled)
        self.rename_button.setEnabled(is_enabled)

    # ---- Funkcja pokazuje standardowa tabele All files ----
    def show_all_files_table(self, rows):
        self.visible_files = rows
        duplicate_indexes = find_duplicate_indexes(rows)
        self.files_table.clearContents()
        self.files_table.setColumnCount(5)
        self.files_table.setHorizontalHeaderLabels(
            ["Name", "Type", "Modified", "Size", "Path"]
        )
        self.set_all_files_column_sizes()

        self.files_table.setRowCount(len(rows))

        # --- Loops wypelnia tabele podstawowymi danymi plikow ---
        for row, file in enumerate(rows):
            self.set_table_item(row, 0, file["name"], row in duplicate_indexes)
            self.set_table_item(row, 1, file["category"], row in duplicate_indexes)
            self.set_table_item(row, 2, file["modified"], row in duplicate_indexes)
            self.set_table_item(row, 3, file["size"], row in duplicate_indexes)
            self.set_table_item(row, 4, file["path"], row in duplicate_indexes)

    # ---- Funkcja pokazuje tabele kategorii wedlug aktywnego template ----
    def show_category_table(self, rows):
        self.visible_files = rows
        duplicate_indexes = find_duplicate_indexes(rows)
        metadata_columns = self.get_active_metadata_columns()
        headers = ["Select"] + [
            self.format_header_name(item) for item in metadata_columns
        ]

        self.files_table.clearContents()
        self.files_table.setColumnCount(len(headers))
        self.files_table.setHorizontalHeaderLabels(headers)
        self.files_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Interactive
        )
        self.files_table.setColumnWidth(0, 72)

        # --- Loops ustawia szerokosci kolumn kategorii ---
        for column in range(1, len(headers)):
            self.files_table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.Interactive
            )
            self.files_table.setColumnWidth(column, 140)

        # -- if sa kolumny, rozciaga ostatnia kolumne --
        if headers:
            path_column = len(headers) - 1
            self.files_table.horizontalHeader().setSectionResizeMode(
                path_column, QHeaderView.ResizeMode.Stretch
            )

        self.files_table.setRowCount(len(rows))

        # --- Loops wypelnia tabele kategoriami i metadanymi ---
        for row, file in enumerate(rows):
            checkbox = QCheckBox()

            # -- if plik jest duplikatem, koloruje checkbox --
            if row in duplicate_indexes:
                checkbox.setStyleSheet("background-color: #fff3a3;")

            self.files_table.setCellWidget(row, 0, checkbox)

            for index, metadata_name in enumerate(metadata_columns):
                value = self.get_metadata_value(file, metadata_name)
                self.set_table_item(row, index + 1, value, row in duplicate_indexes)

    # ---- Funkcja ustawia komorke tabeli i kolor duplikatu ----
    def set_table_item(self, row, column, value, is_duplicate):
        item = QTableWidgetItem(str(value))

        # -- if plik jest duplikatem, koloruje komorke --
        if is_duplicate:
            item.setBackground(QColor("#fff3a3"))

        self.files_table.setItem(row, column, item)

    # ---- Funkcja zaznacza wszystkie widoczne pliki w kategorii ----
    def select_all_visible_files(self):
        if self.active_category == "All files":
            return

        # --- Loops zaznacza checkboxy w tabeli ---
        for row in range(self.files_table.rowCount()):
            checkbox = self.files_table.cellWidget(row, 0)

            # -- if w komorce jest checkbox, zaznacza go --
            if isinstance(checkbox, QCheckBox):
                checkbox.setChecked(True)

    # ---- Funkcja zwraca zaznaczone pliki z aktualnej tabeli ----
    def get_selected_files(self):
        selected_files = []

        # --- Loops zbiera rekordy zaznaczone checkboxami ---
        for row, file in enumerate(self.visible_files):
            checkbox = self.files_table.cellWidget(row, 0)

            if isinstance(checkbox, QCheckBox) and checkbox.isChecked():
                selected_files.append(file)

        return selected_files

    # ---- Funkcja zmienia nazwy zaznaczonych plikow ----
    def rename_selected_files(self):
        if self.active_category == "All files":
            return

        active_template = self.template_tab.get_active_template(self.active_category)

        # -- if brak aktywnego template, pokazuje blad --
        if not active_template:
            QMessageBox.warning(self, "Rename", "Select a template first.")
            return

        selected_files = self.get_selected_files()

        # -- if user nie zaznaczyl plikow, pokazuje informacje --
        if not selected_files:
            QMessageBox.information(self, "Rename", "Select files to rename.")
            return

        preview_lines = self.build_rename_preview(selected_files, active_template)
        preview_text = "\n".join(preview_lines[:20])

        # -- if lista jest dluga, pokazuje tylko pierwsze elementy --
        if len(preview_lines) > 20:
            preview_text += f"\n... and {len(preview_lines) - 20} more"

        answer = QMessageBox.question(
            self,
            "Confirm rename",
            f"Rename selected files?\n\n{preview_text}",
        )

        # -- if user nie potwierdzil, nic nie zmienia --
        if answer != QMessageBox.StandardButton.Yes:
            return

        errors = []

        # --- Loops zmienia nazwy plikow na dysku ---
        for file in selected_files:
            try:
                rename_file(file, active_template)
                self.update_file_after_rename(file)
            except Exception as error:
                errors.append(f"{file.get('name', '')}: {error}")

        self.refresh_table()

        # -- if byly bledy rename, pokazuje je uzytkownikowi --
        if errors:
            QMessageBox.warning(self, "Rename errors", "\n".join(errors))
            return

        QMessageBox.information(self, "Rename", "Selected files have been renamed.")

    # ---- Funkcja buduje podglad rename dla okna potwierdzenia ----
    def build_rename_preview(self, selected_files, active_template):
        preview_lines = []

        # --- Loops tworzy linie starej i nowej nazwy ---
        for file in selected_files:
            try:
                new_name = render_custom_name(active_template, file)
                new_path = build_unique_path(file.get("path", ""), new_name)
                preview_lines.append(f"{file.get('name', '')} -> {new_path.name}")
            except Exception as error:
                preview_lines.append(f"{file.get('name', '')} -> error: {error}")

        return preview_lines

    # ---- Funkcja aktualizuje podstawowe dane pliku po rename ----
    def update_file_after_rename(self, file):
        path = Path(file.get("path", ""))

        # -- if plik istnieje po rename, odswieza rozmiar i date --
        if path.exists():
            file["modified"] = format_modified_time(path)
            file["size"] = format_file_size(path.stat().st_size)

    # ---- Funkcja zwraca aktywne metadane dla wybranej kategorii ----
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

    # ---- Funkcja zamienia nazwe metadanej na czytelny naglowek tabeli ----
    def format_header_name(self, metadata_name):
        return metadata_name.replace("_", " ").title()

    # ---- Funkcja zwraca wartosc metadanej z danych pliku ----
    def get_metadata_value(self, file, metadata_name):
        # -- if custom_name trzeba zbudowac z aktywnego template --
        if metadata_name == "custom_name":
            active_template = self.template_tab.get_active_template(
                self.active_category
            )
            return render_custom_name(active_template, file)

        if metadata_name == "extension":
            return file.get("extension", "")

        if metadata_name == "original_name":
            return file.get("original_name", file.get("name", ""))

        if metadata_name == "file_type":
            return file.get("file_type", file.get("category", "").lower())

        value = file.get(metadata_name, "")

        # -- if wartosc jest juz znormalizowana, zwraca ja bez szukania aliasow --
        if value:
            return str(value)

        return self.get_tika_metadata_value(file, metadata_name)

    # ---- Funkcja szuka wartosci bezposrednio w surowych metadanych Tika ----
    def get_tika_metadata_value(self, file, metadata_name):
        tika_metadata = file.get("tika_metadata", {})
        aliases = self.get_metadata_aliases(file, metadata_name)

        # --- Loops sprawdza aliasy dokladnie tak, jak zwrocila je Tika ---
        for alias in aliases:
            if alias in tika_metadata:
                return str(tika_metadata[alias])

        normalized_metadata = {
            str(key).strip().lower().replace("-", "_").replace(" ", "_"): value
            for key, value in tika_metadata.items()
        }

        # --- Loops sprawdza aliasy po uproszczeniu nazw kluczy ---
        for alias in aliases:
            normalized_alias = (
                str(alias).strip().lower().replace("-", "_").replace(" ", "_")
            )
            value = normalized_metadata.get(normalized_alias)

            # -- if znaleziono wartosc, zwraca ja jako tekst --
            if value:
                return str(value)

        return ""

    # ---- Funkcja zwraca aliasy metadanych dla aktywnej kategorii ----
    def get_metadata_aliases(self, file, metadata_name):
        file_type = file.get("file_type", file.get("category", "")).lower()

        # -- if plik jest video, uzywa aliasow video Tika --
        if file_type == "video":
            return VIDEO_METADATA_FIELDS.get(metadata_name, [])

        # -- if plik jest pdf, uzywa aliasow pdf Tika --
        if file_type == "pdf":
            return PDF_METADATA_FIELDS.get(metadata_name, [])

        # -- if plik jest word, uzywa aliasow Word Tika --
        if file_type == "word":
            return WORD_METADATA_FIELDS.get(metadata_name, [])

        return AUDIO_METADATA_FIELDS.get(metadata_name, [])
