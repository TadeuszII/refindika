import json
import re
from pathlib import Path

from PyQt6.QtWidgets import (
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
        self.checkbox_by_metadata = {}
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
        main_layout.setSpacing(10)

        title = QLabel("2. Templates")
        title.setObjectName("PageTitle")
        main_layout.addWidget(title)

        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self.template_name_input = QLineEdit()
        self.template_name_input.setPlaceholderText("Nazwa")
        top_row.addWidget(self.template_name_input, 1)

        self.file_type_select = QComboBox()
        self.file_type_select.addItems(["Video", "Audio", "PDF", "Word"])
        self.file_type_select.currentTextChanged.connect(self.refresh_metadata_table)
        top_row.addWidget(self.file_type_select, 1)

        top_row.addStretch(2)
        main_layout.addLayout(top_row)

        hint = QLabel(
            "Construct the ideal filename using the available variables. "
            "Click a variable to append it."
        )
        hint.setObjectName("MutedText")
        main_layout.addWidget(hint)

        self.metadata_table = QTableWidget(0, 2)
        self.metadata_table.setHorizontalHeaderLabels(["Metadana", "Dodaj"])
        self.metadata_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.metadata_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.metadata_table.setMaximumHeight(170)
        self.metadata_table.setAlternatingRowColors(True)
        self.metadata_table.verticalHeader().setVisible(False)
        self.metadata_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        main_layout.addWidget(self.metadata_table)

        template_row = QHBoxLayout()
        template_row.setSpacing(10)

        template_label = QLabel("Template:")
        template_row.addWidget(template_label)

        self.pattern_input = QLineEdit()
        self.pattern_input.setPlaceholderText("Plik_{original_name}_{fps}")
        self.pattern_input.textChanged.connect(self.sync_checkboxes_with_pattern)
        template_row.addWidget(self.pattern_input, 1)

        self.use_button = QPushButton("Use template")
        self.use_button.setObjectName("PrimaryButton")
        self.use_button.clicked.connect(self.use_current_template)
        template_row.addWidget(self.use_button)

        self.save_button = QPushButton("Save Template")
        self.save_button.setObjectName("PrimaryButton")
        self.save_button.clicked.connect(self.save_current_template)
        template_row.addWidget(self.save_button)

        main_layout.addLayout(template_row)

        self.saved_templates_table = QTableWidget(0, 2)
        self.saved_templates_table.setHorizontalHeaderLabels(["Nazwa", ""])
        self.saved_templates_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        self.saved_templates_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.ResizeToContents
        )
        self.saved_templates_table.setAlternatingRowColors(True)
        self.saved_templates_table.verticalHeader().setVisible(False)
        self.saved_templates_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        main_layout.addWidget(self.saved_templates_table, 1)

    # ---- Funkcja zwraca sciezke do pliku z template ----
    def get_templates_file(self):
        project_folder = Path(__file__).resolve().parent.parent
        data_folder = project_folder / "data"
        return data_folder / "templates.json"

    # ---- Funkcja odswieza liste metadanych dla wybranego typu pliku ----
    def refresh_metadata_table(self):
        selected_type = self.file_type_select.currentText()
        metadata_list = METADATA_BY_TYPE[selected_type]

        self.checkbox_by_metadata = {}
        self.metadata_table.setRowCount(len(metadata_list))

        # --- Loops wypelnia tabele metadanych checkboxami ---
        for row, metadata_name in enumerate(metadata_list):
            metadata_item = QTableWidgetItem(f"{{{metadata_name}}}")
            self.metadata_table.setItem(row, 0, metadata_item)

            checkbox = QCheckBox()
            checkbox.stateChanged.connect(
                lambda _state, name=metadata_name: self.update_pattern_from_checkbox(
                    name
                )
            )
            self.checkbox_by_metadata[metadata_name] = checkbox
            self.metadata_table.setCellWidget(row, 1, checkbox)

        self.sync_checkboxes_with_pattern()

    # ---- Funkcja dodaje albo usuwa placeholder po kliknieciu checkboxa ----
    def update_pattern_from_checkbox(self, metadata_name):
        checkbox = self.checkbox_by_metadata[metadata_name]
        placeholder = "{" + metadata_name + "}"
        current_pattern = self.pattern_input.text()

        # -- if dodaje placeholder tylko jeden raz --
        if checkbox.isChecked() and placeholder not in current_pattern:
            self.pattern_input.setText(current_pattern + placeholder)
            return

        # -- if usuwa placeholder po odznaczeniu checkboxa --
        if not checkbox.isChecked() and placeholder in current_pattern:
            self.pattern_input.setText(current_pattern.replace(placeholder, ""))

    # ---- Funkcja ustawia checkboxy zgodnie z aktualnym tekstem template ----
    def sync_checkboxes_with_pattern(self, _text=None):
        current_pattern = self.pattern_input.text()

        # --- Loops sprawdza ktore metadane sa juz w patternie ---
        for metadata_name, checkbox in self.checkbox_by_metadata.items():
            checkbox.blockSignals(True)
            checkbox.setChecked("{" + metadata_name + "}" in current_pattern)
            checkbox.blockSignals(False)

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
            QMessageBox.warning(self, "Nieprawidlowy template", "\n".join(errors))
            return

        self.add_or_update_template(template_data)
        self.save_templates()
        self.refresh_templates_table()
        QMessageBox.information(self, "Zapisano", "Template zostal zapisany.")

    # ---- Funkcja ustawia aktualny template jako uzywany w programie ----
    def use_current_template(self):
        template_data = self.get_form_data()
        errors = self.validate_template(template_data)

        # -- if zatrzymuje uzycie jezeli template jest niepoprawny --
        if errors:
            QMessageBox.warning(self, "Nieprawidlowy template", "\n".join(errors))
            return

        self.selected_template = template_data
        QMessageBox.information(self, "Template", "Template zostal wybrany.")

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
            errors.append("Podaj nazwe template.")

        # -- if sprawdza tresc template --
        if not pattern:
            errors.append("Podaj wzor nowej nazwy pliku.")

        # -- if sprawdza czy typ pliku istnieje w programie --
        if file_type not in METADATA_BY_TYPE:
            errors.append("Nieprawidlowy typ pliku w template.")
            return errors

        allowed_metadata = set(METADATA_BY_TYPE[file_type])

        # --- Loops sprawdza wszystkie placeholdery w patternie ---
        for metadata_name in found_metadata:
            if metadata_name not in allowed_metadata:
                errors.append(
                    f"Metadana {{{metadata_name}}} nie pasuje do typu {file_type}."
                )

        # -- if sprawdza czy klamry sa poprawnie zamkniete --
        if "{" in re.sub(r"{[^{}]+}", "", pattern) or "}" in re.sub(
            r"{[^{}]+}", "", pattern
        ):
            errors.append("Sprawdz nawiasy klamrowe w template.")

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

        # --- Loops wypelnia tabele zapisanych templates ---
        for row, template_data in enumerate(self.templates):
            name = template_data.get("name", "")
            file_type = template_data.get("file_type", "")
            name_item = QTableWidgetItem(f"{name} ({file_type})")
            self.saved_templates_table.setItem(row, 0, name_item)

            use_button = QPushButton("Use template")
            use_button.setObjectName("PrimaryButton")
            use_button.clicked.connect(
                lambda _checked=False, data=template_data: self.load_saved_template(
                    data
                )
            )
            self.saved_templates_table.setCellWidget(row, 1, use_button)

    # ---- Funkcja laduje zapisany template do pol na gorze ----
    def load_saved_template(self, template_data):
        errors = self.validate_template(template_data)

        # -- if blokuje ladowanie uszkodzonego template --
        if errors:
            QMessageBox.warning(self, "Nieprawidlowy template", "\n".join(errors))
            return

        self.template_name_input.setText(template_data["name"])
        self.file_type_select.setCurrentText(template_data["file_type"])
        self.pattern_input.setText(template_data["pattern"])
        self.sync_checkboxes_with_pattern()
        self.selected_template = template_data
