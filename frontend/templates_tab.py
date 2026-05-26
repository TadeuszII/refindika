import json
import re
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractScrollArea,
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
        "custom_name",
        "file_type",
        "modified",
        "path",
        "content_type",
        "resource_name",
        "duration",
        "width",
        "height",
        "resolution",
        "video_compressor",
        "audio_sample_rate",
        "audio_channel_type",
        "audio_compressor",
        "created",
        "modified_tika",
        "latitude",
        "longitude",
        "parser_warning",
        "extension",
    ],
    "Audio": [
        "original_name",
        "custom_name",
        "file_type",
        "modified",
        "path",
        "mime_type",
        "resource_name",
        "duration",
        "sample_rate",
        "channels",
        "bitrate",
        "codec",
        "title",
        "artist",
        "album",
        "genre",
        "year",
        "track_number",
        "composer",
        "copyright",
        "encoder",
    ],
    "PDF": [
        "original_name",
        "custom_name",
        "file_type",
        "modified",
        "path",
        "content_type",
        "resource_name",
        "title",
        "author",
        "creator",
        "producer",
        "created",
        "modified_tika",
        "pages",
        "pdf_version",
        "encrypted",
        "word_count",
        "parser_warning",
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


def normalize_file_type(file_type):
    for known_type in METADATA_BY_TYPE:
        if known_type.lower() == str(file_type).lower():
            return known_type
    return str(file_type)


class TemplatesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.default_templates = []
        self.templates = []
        self.metadata_checkboxes = {}
        self.default_templates_file = self.get_default_templates_file()
        self.templates_file = self.get_templates_file()
        self.selected_template = None
        self.active_templates_by_type = {}
        self.template_changed = None

        self.setup_ui()
        self.load_templates()
        self.setup_active_templates()
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
        self.metadata_table.setFixedWidth(370)
        self.metadata_table.setFixedHeight(260)
        self.metadata_table.setAlternatingRowColors(True)
        self.metadata_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        form_layout.addWidget(self.metadata_table)

        template_row = QHBoxLayout()
        template_row.setSpacing(10)

        template_label = QLabel("File name pattern:")
        template_row.addWidget(template_label)

        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText("File_{original_name}_{video_compressor}")
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
        self.saved_templates_table.setFixedWidth(370)
        self.saved_templates_table.setFixedHeight(180)
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
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        table.setSizeAdjustPolicy(QAbstractScrollArea.SizeAdjustPolicy.AdjustToContents)
        table.setShowGrid(True)

        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

    # ---- Funkcja ustawia wysokosc tabeli wedlug liczby wierszy ----
    def set_table_height(self, table, row_count):
        table.resizeRowsToContents()

    # ---- Funkcja zwraca sciezke do pliku z template ----
    def get_templates_file(self):
        project_folder = Path(__file__).resolve().parent.parent
        data_folder = project_folder / "data"
        return data_folder / "templates.json"

    # ---- Funkcja zwraca sciezke do pliku z domyslnymi template ----
    def get_default_templates_file(self):
        project_folder = Path(__file__).resolve().parent.parent
        data_folder = project_folder / "data"
        return data_folder / "default_template.json"

    # ---- Funkcja odswieza liste metadanych dla wybranego typu pliku ----
    def refresh_metadata_table(self):
        selected_type = self.file_type_select.currentText()
        metadata_list = METADATA_BY_TYPE[selected_type]

        self.metadata_checkboxes = {}
        self.metadata_table.setRowCount(len(metadata_list))
        self.metadata_table.setColumnWidth(0, 58)
        self.metadata_table.setColumnWidth(1, 200)
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

    # ---- Funkcja normalizuje template do jednego formatu danych ----
    def normalize_template(self, template_data):
        file_type = template_data.get("Type", template_data.get("file_type", ""))
        normalized_type = normalize_file_type(file_type)

        normalized_template = {
            "Name": template_data.get("Name", template_data.get("name", "")),
            "Type": normalized_type.lower(),
            "Template": template_data.get(
                "Template", template_data.get("pattern", "")
            ),
        }

        # --- Loops przenosi zapisane ustawienia checkboxow metadanych ---
        if normalized_type in METADATA_BY_TYPE:
            for metadata_name in METADATA_BY_TYPE[normalized_type]:
                normalized_template[metadata_name] = template_data.get(
                    metadata_name, True
                )

        return normalized_template

    # ---- Funkcja wczytuje liste template z podanego pliku json ----
    def read_templates_file(self, file_path):
        if not file_path.exists():
            return []

        try:
            with file_path.open("r", encoding="utf-8") as file:
                loaded_templates = json.load(file)
        except (OSError, json.JSONDecodeError):
            return []

        # -- if sprawdza czy plik zawiera liste danych --
        if isinstance(loaded_templates, list):
            return loaded_templates

        return []

    # ---- Funkcja wczytuje domyslne i uzytkownika templates ----
    def load_templates(self):
        default_templates = self.read_templates_file(self.default_templates_file)
        user_templates = self.read_templates_file(self.templates_file)

        self.default_templates = [
            self.normalize_template(template_data)
            for template_data in default_templates
            if self.validate_template(template_data) == []
        ]

        self.templates = []

        # --- Loops zostawia tylko templates uzytkownika ---
        for template_data in user_templates:
            normalized_template = self.normalize_template(template_data)
            is_default = normalized_template["Name"].lower() == "default"

            # -- if pomija defaulty, bo sa w osobnym pliku --
            if not is_default:
                self.add_or_update_template(normalized_template)

    # ---- Funkcja ustawia aktywne templates na podstawie defaultow ----
    def setup_active_templates(self):
        self.active_templates_by_type = {}

        # --- Loops ustawia default template dla kazdego typu pliku ---
        for template_data in self.default_templates:
            file_type = template_data["Type"]
            self.active_templates_by_type[file_type] = template_data

        # --- Loops nadpisuje defaulty zapisanymi template uzytkownika ---
        for template_data in self.templates:
            file_type = template_data["Type"]

            # -- if template uzytkownika jest poprawny, ustawia go jako aktywny --
            if self.validate_template(template_data) == []:
                self.active_templates_by_type[file_type] = template_data

    # ---- Funkcja zapisuje templates do pliku json ----
    def save_templates(self):
        self.templates_file.parent.mkdir(parents=True, exist_ok=True)

        with self.templates_file.open("w", encoding="utf-8") as file:
            json.dump(self.templates, file, indent=4)

    # ---- Funkcja zapisuje aktualny template po walidacji danych ----
    def save_current_template(self):
        template_data = self.get_form_data()
        errors = self.validate_template(template_data)

        # -- if blokuje zapisywanie domyslnych templates --
        if template_data["Name"].lower() == "default":
            errors.append("Default templates cannot be changed.")

        # -- if zatrzymuje zapis jezeli template jest niepoprawny --
        if errors:
            QMessageBox.warning(self, "Invalid template", "\n".join(errors))
            return

        self.add_or_update_template(template_data)
        self.apply_template(template_data)
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

        self.apply_template(template_data)
        QMessageBox.information(self, "Template", "Template has been selected.")

    # ---- Funkcja ustawia template jako aktywny dla jego typu pliku ----
    def apply_template(self, template_data):
        normalized_template = self.normalize_template(template_data)
        file_type = normalized_template["Type"]
        self.active_templates_by_type[file_type] = normalized_template
        self.selected_template = normalized_template

        # -- if glowny widok chce odswiezyc tabele po zmianie template --
        if self.template_changed is not None:
            self.template_changed()

    # ---- Funkcja zwraca aktywny template dla wybranego typu pliku ----
    def get_active_template(self, file_type):
        normalized_type = normalize_file_type(file_type).lower()
        return self.active_templates_by_type.get(normalized_type)

    # ---- Funkcja zbiera dane wpisane przez uzytkownika ----
    def get_form_data(self):
        selected_type = self.file_type_select.currentText()
        template_data = {
            "Name": self.template_name_input.text().strip(),
            "Type": selected_type.lower(),
            "Template": self.pattern_input.text().strip(),
        }

        # --- Loops zapisuje stan kazdego checkboxa metadanych ---
        for metadata_name in METADATA_BY_TYPE[selected_type]:
            checkbox_item = self.metadata_checkboxes.get(metadata_name)
            template_data[metadata_name] = (
                checkbox_item is not None
                and checkbox_item.checkState() == Qt.CheckState.Checked
            )

        return template_data

    # ---- Funkcja sprawdza czy template moze byc zapisany albo uzyty ----
    def validate_template(self, template_data):
        errors = []
        template_name = template_data.get("Name", template_data.get("name", "")).strip()
        file_type = template_data.get("Type", template_data.get("file_type", ""))
        normalized_type = normalize_file_type(file_type)
        pattern = template_data.get("Template", template_data.get("pattern", "")).strip()
        found_metadata = re.findall(r"{([^{}]+)}", pattern)

        # -- if sprawdza nazwe template --
        if not template_name:
            errors.append("Enter template name.")

        # -- if sprawdza tresc template --
        if not pattern:
            errors.append("Enter file name pattern.")

        # -- if sprawdza czy typ pliku istnieje w programie --
        if normalized_type not in METADATA_BY_TYPE:
            errors.append("Invalid file type in template.")
            return errors

        allowed_metadata = set(METADATA_BY_TYPE[normalized_type])

        # --- Loops sprawdza wszystkie placeholdery w patternie ---
        for metadata_name in found_metadata:
            if metadata_name not in allowed_metadata:
                errors.append(
                    f"Metadata {{{metadata_name}}} does not match {normalized_type}."
                )

        # -- if sprawdza czy klamry sa poprawnie zamkniete --
        if "{" in re.sub(r"{[^{}]+}", "", pattern) or "}" in re.sub(
            r"{[^{}]+}", "", pattern
        ):
            errors.append("Check curly brackets in template.")

        return errors

    # ---- Funkcja dodaje nowy template albo aktualizuje istniejacy ----
    def add_or_update_template(self, template_data):
        normalized_template = self.normalize_template(template_data)

        # --- Loops szuka template o tym samym typie pliku ---
        for index, saved_template in enumerate(self.templates):
            saved_type = saved_template.get("Type", saved_template.get("file_type"))
            same_type = saved_type == normalized_template["Type"]

            # -- if aktualizuje istniejacy template --
            if same_type:
                self.templates[index] = normalized_template
                return

        self.templates.append(normalized_template)

    # ---- Funkcja odswieza tabele zapisanych templates ----
    def refresh_templates_table(self):
        all_templates = self.default_templates + self.templates
        self.saved_templates_table.setRowCount(len(all_templates))
        self.saved_templates_table.setColumnWidth(0, 150)
        self.saved_templates_table.setColumnWidth(1, 90)
        self.saved_templates_table.setColumnWidth(2, 82)

        # --- Loops wypelnia tabele zapisanych templates ---
        for row, template_data in enumerate(all_templates):
            name = template_data.get("Name", template_data.get("name", ""))
            file_type = template_data.get("Type", template_data.get("file_type", ""))
            name_item = QTableWidgetItem(name)
            self.saved_templates_table.setItem(row, 0, name_item)

            type_item = QTableWidgetItem(normalize_file_type(file_type))
            self.saved_templates_table.setItem(row, 1, type_item)

            use_button = QPushButton("Use")
            use_button.setObjectName("PrimaryButton")
            use_button.setFixedWidth(64)
            use_button.clicked.connect(
                lambda _checked=False, data=template_data: self.use_saved_template(data)
            )
            self.saved_templates_table.setCellWidget(row, 2, use_button)

        visible_rows = max(len(all_templates), 1)
        self.set_table_height(self.saved_templates_table, visible_rows)

    # ---- Funkcja laduje i stosuje template z tabeli zapisanych templates ----
    def use_saved_template(self, template_data):
        if not self.load_saved_template(template_data):
            return

        self.apply_template(template_data)

    # ---- Funkcja laduje zapisany template do pol na gorze ----
    def load_saved_template(self, template_data):
        errors = self.validate_template(template_data)

        # -- if blokuje ladowanie uszkodzonego template --
        if errors:
            QMessageBox.warning(self, "Invalid template", "\n".join(errors))
            return False

        template_name = template_data.get("Name", template_data.get("name", ""))
        file_type = template_data.get("Type", template_data.get("file_type", ""))
        pattern = template_data.get("Template", template_data.get("pattern", ""))
        normalized_type = normalize_file_type(file_type)

        self.template_name_input.setText(template_name)
        self.file_type_select.setCurrentText(normalized_type)
        self.pattern_input.setText(pattern)

        # --- Loops odtwarza zapisany stan checkboxow metadanych ---
        for metadata_name in METADATA_BY_TYPE[normalized_type]:
            checkbox_item = self.metadata_checkboxes.get(metadata_name)
            if checkbox_item is not None:
                is_checked = template_data.get(metadata_name, True)
                state = Qt.CheckState.Checked if is_checked else Qt.CheckState.Unchecked
                checkbox_item.setCheckState(state)

        self.selected_template = self.normalize_template(template_data)
        return True
