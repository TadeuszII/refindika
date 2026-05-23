import json
import re
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractScrollArea,
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


METADATA_BY_TYPE = {
    "Video": [
        "original_name",
        "duration",
        "resolution",
        "fps",
        "codec",
        "bitrate",
        "extension",
    ],
    "Audio": [
        "original_name",
        "duration",
        "sample_rate",
        "bitrate",
        "codec",
        "extension",
    ],
    "PDF": [
        "original_name",
        "title",
        "author",
        "pages",
        "word_count",
        "extension",
    ],
    "Word": [
        "original_name",
        "title",
        "author",
        "pages",
        "word_count",
        "extension",
    ],
}


class TemplatesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.templates = []
        self.metadata_checkboxes = {}
        self.templates_file = self.get_templates_file()
        self.selected_template = None

        self.setup_ui()
        self.load_templates()
        self.refresh_metadata_table()
        self.refresh_templates_table()

    # ---- Funkcja tworzy pelny interfejs zakladki templates ----
    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(0)

        form_widget = QWidget()
        form_widget.setMaximumWidth(820)
        form_layout = QVBoxLayout(form_widget)
        form_layout.setContentsMargins(0, 0, 0, 0)
        form_layout.setSpacing(8)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self.template_name_input = QLineEdit()
        self.template_name_input.setPlaceholderText("Template name")
        self.template_name_input.setFixedWidth(300)
        top_row.addWidget(self.template_name_input)

        self.file_type_select = QComboBox()
        self.file_type_select.addItems(["Video", "Audio", "PDF", "Word"])
        self.file_type_select.currentTextChanged.connect(self.refresh_metadata_table)
        self.file_type_select.setFixedWidth(190)
        top_row.addWidget(self.file_type_select)

        top_row.addStretch()
        form_layout.addLayout(top_row)

        metadata_label = QLabel("Metadata columns")
        metadata_label.setObjectName("SectionTitle")
        form_layout.addWidget(metadata_label)

        self.metadata_table = QTableWidget(0, 3)
        self.metadata_table.setHorizontalHeaderLabels(["Show", "Metadata", "Action"])
        self.setup_compact_table(self.metadata_table)
        self.metadata_table.setFixedWidth(320)
        self.metadata_table.setAlternatingRowColors(True)
        self.metadata_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        form_layout.addWidget(self.metadata_table)

        template_row = QHBoxLayout()
        template_row.setSpacing(10)

        template_label = QLabel("File name pattern:")
        template_row.addWidget(template_label)

        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText("File_{original_name}_{fps}")
        self.pattern_input.setFixedWidth(360)
        template_row.addWidget(self.pattern_input)

        self.use_button = QPushButton("Use")
        self.use_button.setObjectName("PrimaryButton")
        self.use_button.setFixedWidth(70)
        self.use_button.clicked.connect(self.use_current_template)
        template_row.addWidget(self.use_button)

        self.save_button = QPushButton("Save")
        self.save_button.setObjectName("PrimaryButton")
        self.save_button.setFixedWidth(70)
        self.save_button.clicked.connect(self.save_current_template)
        template_row.addWidget(self.save_button)

        template_row.addStretch()
        form_layout.addLayout(template_row)

        saved_label = QLabel("Saved templates")
        saved_label.setObjectName("SectionTitle")
        form_layout.addWidget(saved_label)

        self.saved_templates_table = QTableWidget(0, 3)
        self.saved_templates_table.setHorizontalHeaderLabels(["Name", "Category", "Action"])
        self.setup_compact_table(self.saved_templates_table)
        self.saved_templates_table.setFixedWidth(340)
        self.saved_templates_table.setAlternatingRowColors(True)
        self.saved_templates_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        form_layout.addWidget(self.saved_templates_table)

        main_layout.addWidget(form_widget)
        main_layout.addStretch()

    # ---- Funkcja ustawia tabele jako male i bez pustych obszarow ----
    def setup_compact_table(self, table):
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(False)
        table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        table.setShowGrid(True)

        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

    # ---- Funkcja ustawia wysokosc tabeli wedlug liczby wierszy ----
    def set_table_height(self, table, row_count):
        header_height = table.horizontalHeader().height()
        row_height = table.verticalHeader().defaultSectionSize()
        frame_size = 2
        table.setFixedHeight(header_height + row_height * row_count + frame_size)

    # ---- Funkcja zwraca sciezke do pliku z template ----
    def get_templates_file(self):
        project_folder = Path(__file__).resolve().parent.parent
        data_folder = project_folder / "data"
        return data_folder / "templates.json"

    # ---- Funkcja odswieza liste metadanych dla wybranego typu pliku ----
    def refresh_metadata_table(self):
        selected_type = self.file_type_select.currentText()
        metadata_list = METADATA_BY_TYPE[selected_type]

        self.metadata_checkboxes = {}
        self.metadata_table.setRowCount(len(metadata_list))
        self.metadata_table.setColumnWidth(0, 58)
        self.metadata_table.setColumnWidth(1, 150)
        self.metadata_table.setColumnWidth(2, 82)

        # --- Loops wypelnia tabele metadanych checkboxami i przyciskami Add ---
        for row, metadata_name in enumerate(metadata_list):
            checkbox_item = QTableWidgetItem()
            checkbox_item.setFlags(
                Qt.ItemFlag.ItemIsEnabled
                | Qt.ItemFlag.ItemIsUserCheckable
                | Qt.ItemFlag.ItemIsSelectable
            )
            checkbox_item.setCheckState(Qt.CheckState.Checked)
            checkbox_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.metadata_checkboxes[metadata_name] = checkbox_item
            self.metadata_table.setItem(row, 0, checkbox_item)

            metadata_item = QTableWidgetItem(metadata_name)
            self.metadata_table.setItem(row, 1, metadata_item)

            add_button = QPushButton("Add")
            add_button.setFixedWidth(64)
            add_button.clicked.connect(
                lambda _checked=False, name=metadata_name: self.add_metadata_to_pattern(
                    name
                )
            )
            self.metadata_table.setCellWidget(row, 2, add_button)

        self.set_table_height(self.metadata_table, len(metadata_list))

    # ---- Funkcja dodaje placeholder do patternu po kliknieciu Add ----
    def add_metadata_to_pattern(self, metadata_name):
        placeholder = "{" + metadata_name + "}"
        current_pattern = self.pattern_input.text()

        # -- if dodaje placeholder tylko jeden raz --
        if placeholder not in current_pattern:
            self.pattern_input.setText(current_pattern + placeholder)

    # ---- Funkcja wczytuje zapisane templates z pliku json ----
    def load_templates(self):
        if not self.templates_file.exists():
            self.templates = []
            return

        try:
            with self.templates_file.open("r", encoding="utf-8") as file:
                loaded_templates = json.load(file)
        except (OSError, json.JSONDecodeError):
            self.templates = []
            return

        # -- if sprawdza czy plik zawiera liste danych --
        if isinstance(loaded_templates, list):
            self.templates = loaded_templates
        else:
            self.templates = []

    # ---- Funkcja zapisuje templates do pliku json ----
    def save_templates(self):
        self.templates_file.parent.mkdir(parents=True, exist_ok=True)

        with self.templates_file.open("w", encoding="utf-8") as file:
            json.dump(self.templates, file, indent=4)

    # ---- Funkcja zapisuje aktualny template po walidacji danych ----
    def save_current_template(self):
        template_data = self.get_form_data()
        errors = self.validate_template(template_data)

        # -- if zatrzymuje zapis jezeli template jest niepoprawny --
        if errors:
            QMessageBox.warning(self, "Invalid template", "\n".join(errors))
            return

        self.add_or_update_template(template_data)
        self.save_templates()
        self.refresh_templates_table()
        QMessageBox.information(self, "Saved", "Template has been saved.")

    # ---- Funkcja ustawia aktualny template jako uzywany w programie ----
    def use_current_template(self):
        template_data = self.get_form_data()
        errors = self.validate_template(template_data)

        # -- if zatrzymuje uzycie jezeli template jest niepoprawny --
        if errors:
            QMessageBox.warning(self, "Invalid template", "\n".join(errors))
            return

        self.selected_template = template_data
        QMessageBox.information(self, "Template", "Template has been selected.")

    # ---- Funkcja zbiera dane wpisane przez uzytkownika ----
    def get_form_data(self):
        return {
            "name": self.template_name_input.text().strip(),
            "file_type": self.file_type_select.currentText(),
            "pattern": self.pattern_input.text().strip(),
        }

    # ---- Funkcja sprawdza czy template moze byc zapisany albo uzyty ----
    def validate_template(self, template_data):
        errors = []
        template_name = template_data.get("name", "").strip()
        file_type = template_data.get("file_type", "")
        pattern = template_data.get("pattern", "").strip()
        found_metadata = re.findall(r"{([^{}]+)}", pattern)

        # -- if sprawdza nazwe template --
        if not template_name:
            errors.append("Enter template name.")

        # -- if sprawdza tresc template --
        if not pattern:
            errors.append("Enter file name pattern.")

        # -- if sprawdza czy typ pliku istnieje w programie --
        if file_type not in METADATA_BY_TYPE:
            errors.append("Invalid file type in template.")
            return errors

        allowed_metadata = set(METADATA_BY_TYPE[file_type])

        # --- Loops sprawdza wszystkie placeholdery w patternie ---
        for metadata_name in found_metadata:
            if metadata_name not in allowed_metadata:
                errors.append(
                    f"Metadata {{{metadata_name}}} does not match {file_type}."
                )

        # -- if sprawdza czy klamry sa poprawnie zamkniete --
        if "{" in re.sub(r"{[^{}]+}", "", pattern) or "}" in re.sub(
            r"{[^{}]+}", "", pattern
        ):
            errors.append("Check curly brackets in template.")

        return errors

    # ---- Funkcja dodaje nowy template albo aktualizuje istniejacy ----
    def add_or_update_template(self, template_data):
        # --- Loops szuka template o tej samej nazwie i typie pliku ---
        for index, saved_template in enumerate(self.templates):
            same_name = saved_template.get("name") == template_data["name"]
            same_type = saved_template.get("file_type") == template_data["file_type"]

            # -- if aktualizuje istniejacy template --
            if same_name and same_type:
                self.templates[index] = template_data
                return

        self.templates.append(template_data)

    # ---- Funkcja odswieza tabele zapisanych templates ----
    def refresh_templates_table(self):
        self.saved_templates_table.setRowCount(len(self.templates))
        self.saved_templates_table.setColumnWidth(0, 150)
        self.saved_templates_table.setColumnWidth(1, 90)
        self.saved_templates_table.setColumnWidth(2, 82)

        # --- Loops wypelnia tabele zapisanych templates ---
        for row, template_data in enumerate(self.templates):
            name = template_data.get("name", "")
            file_type = template_data.get("file_type", "")
            name_item = QTableWidgetItem(name)
            self.saved_templates_table.setItem(row, 0, name_item)

            type_item = QTableWidgetItem(file_type)
            self.saved_templates_table.setItem(row, 1, type_item)

            use_button = QPushButton("Use")
            use_button.setObjectName("PrimaryButton")
            use_button.setFixedWidth(64)
            use_button.clicked.connect(
                lambda _checked=False, data=template_data: self.load_saved_template(
                    data
                )
            )
            self.saved_templates_table.setCellWidget(row, 2, use_button)

        visible_rows = max(len(self.templates), 1)
        self.set_table_height(self.saved_templates_table, visible_rows)

    # ---- Funkcja laduje zapisany template do pol na gorze ----
    def load_saved_template(self, template_data):
        errors = self.validate_template(template_data)

        # -- if blokuje ladowanie uszkodzonego template --
        if errors:
            QMessageBox.warning(self, "Invalid template", "\n".join(errors))
            return

        self.template_name_input.setText(template_data["name"])
        self.file_type_select.setCurrentText(template_data["file_type"])
        self.pattern_input.setText(template_data["pattern"])
        self.selected_template = template_data
