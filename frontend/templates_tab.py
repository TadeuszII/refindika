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

try:
    from .template_storage import (
        METADATA_BY_TYPE,
        get_default_templates_file,
        get_templates_file,
        is_same_template,
        normalize_file_type,
        normalize_template,
        read_templates_file,
        save_templates_file,
        validate_template,
    )
except ImportError:
    from template_storage import (
        METADATA_BY_TYPE,
        get_default_templates_file,
        get_templates_file,
        is_same_template,
        normalize_file_type,
        normalize_template,
        read_templates_file,
        save_templates_file,
        validate_template,
    )


class TemplatesTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.default_templates = []
        self.templates = []
        self.metadata_checkboxes = {}
        self.default_templates_file = get_default_templates_file()
        self.templates_file = get_templates_file()
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

        self.saved_templates_table = QTableWidget(0, 4)
        self.saved_templates_table.setHorizontalHeaderLabels(
            ["Name", "Category", "Use", "Delete"]
        )
        self.setup_compact_table(self.saved_templates_table)
        self.saved_templates_table.setFixedWidth(540)
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

    # ---- Funkcja wczytuje domyslne i uzytkownika templates ----
    def load_templates(self):
        default_templates = read_templates_file(self.default_templates_file)
        user_templates = read_templates_file(self.templates_file)

        self.default_templates = [
            normalize_template(template_data)
            for template_data in default_templates
            if validate_template(template_data) == []
        ]

        self.templates = []

        # --- Loops zostawia tylko templates uzytkownika ---
        for template_data in user_templates:
            normalized_template = normalize_template(template_data)
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

    # ---- Funkcja zapisuje templates do pliku json ----
    def save_templates(self):
        save_templates_file(self.templates_file, self.templates)

    # ---- Funkcja zapisuje aktualny template po walidacji danych ----
    def save_current_template(self):
        template_data = self.get_form_data()
        errors = validate_template(template_data)

        # -- if blokuje zapisywanie domyslnych templates --
        if template_data["Name"].lower() == "default":
            errors.append("Default templates cannot be changed.")

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
        errors = validate_template(template_data)

        # -- if zatrzymuje uzycie jezeli template jest niepoprawny --
        if errors:
            QMessageBox.warning(self, "Invalid template", "\n".join(errors))
            return

        self.apply_template(template_data)
        QMessageBox.information(self, "Template", "Template has been selected.")

    # ---- Funkcja ustawia template jako aktywny dla jego typu pliku ----
    def apply_template(self, template_data):
        normalized_template = normalize_template(template_data)
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

    # ---- Funkcja dodaje nowy template albo aktualizuje istniejacy ----
    def add_or_update_template(self, template_data):
        normalized_template = normalize_template(template_data)

        # --- Loops szuka template o tej samej nazwie i typie pliku ---
        for index, saved_template in enumerate(self.templates):
            # -- if aktualizuje istniejacy template --
            if is_same_template(saved_template, normalized_template):
                self.templates[index] = normalized_template
                return

        self.templates.append(normalized_template)

    # ---- Funkcja przywraca default template dla wybranego typu pliku ----
    def restore_default_template(self, file_type):
        normalized_type = normalize_file_type(file_type).lower()

        # --- Loops szuka default template dla podanego typu pliku ---
        for template_data in self.default_templates:
            if template_data["Type"] == normalized_type:
                self.active_templates_by_type[normalized_type] = template_data
                self.selected_template = template_data
                return

    # ---- Funkcja usuwa template uzytkownika z listy ----
    def delete_user_template(self, template_data):
        normalized_template = normalize_template(template_data)
        template_name = normalized_template["Name"]
        file_type = normalized_template["Type"]

        # -- if blokuje usuwanie default template --
        if template_name.lower() == "default":
            QMessageBox.warning(
                self, "Delete template", "Default templates cannot be deleted."
            )
            return

        question = f"Delete template '{template_name}'?"
        answer = QMessageBox.question(self, "Delete template", question)

        # -- if uzytkownik nie potwierdzil usuwania --
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.templates = [
            saved_template
            for saved_template in self.templates
            if not is_same_template(saved_template, normalized_template)
        ]

        active_template = self.active_templates_by_type.get(file_type)

        # -- if usuniety template byl aktywny, przywraca default --
        if active_template is not None and is_same_template(
            active_template, normalized_template
        ):
            self.restore_default_template(file_type)

            if self.template_changed is not None:
                self.template_changed()

        self.save_templates()
        self.refresh_templates_table()
        QMessageBox.information(self, "Deleted", "Template has been deleted.")

    # ---- Funkcja odswieza tabele zapisanych templates ----
    def refresh_templates_table(self):
        all_templates = self.default_templates + self.templates
        self.saved_templates_table.setRowCount(len(all_templates))
        self.saved_templates_table.setColumnWidth(0, 180)
        self.saved_templates_table.setColumnWidth(1, 100)
        self.saved_templates_table.setColumnWidth(2, 110)
        self.saved_templates_table.setColumnWidth(3, 110)

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
            use_button.setFixedWidth(82)
            use_button.clicked.connect(
                lambda _checked=False, data=template_data: self.use_saved_template(data)
            )
            self.saved_templates_table.setCellWidget(row, 2, use_button)

            delete_button = QPushButton("Delete")
            delete_button.setFixedWidth(82)
            is_default = name.lower() == "default"
            delete_button.setEnabled(not is_default)
            delete_button.clicked.connect(
                lambda _checked=False, data=template_data: self.delete_user_template(
                    data
                )
            )
            self.saved_templates_table.setCellWidget(row, 3, delete_button)

        visible_rows = max(len(all_templates), 1)
        self.set_table_height(self.saved_templates_table, visible_rows)

    # ---- Funkcja laduje i stosuje template z tabeli zapisanych templates ----
    def use_saved_template(self, template_data):
        if not self.load_saved_template(template_data):
            return

        self.apply_template(template_data)

    # ---- Funkcja laduje zapisany template do pol na gorze ----
    def load_saved_template(self, template_data):
        errors = validate_template(template_data)

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

        self.selected_template = normalize_template(template_data)
        return True
