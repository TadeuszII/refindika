import sys
import threading
import time
from pathlib import Path
from queue import Queue

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
)

from backend.audio_metadata import extract_audio_metadata
from backend.pdf_metadata import extract_pdf_metadata
from backend.video_metadata import extract_video_metadata
from backend.word_metadata import extract_word_metadata


FILE_TYPES = {
    "Video": {
        ".mp4",
        ".m4v",
        ".mov",
        ".3gp",
        ".3g2",
        ".flv",
        ".ogg",
        ".ogv",
        ".avi",
        ".mpeg",
        ".mpg",
        ".mkv",
        ".webm",
    },
    "Audio": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"},
    "PDF": {".pdf"},
    "Word": {".doc", ".docx", ".odt", ".rtf"},
}


# ---- Funkcja formatuje rozmiar pliku do czytelnego tekstu ----
def format_file_size(size):
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.0f} KB"
    if size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.0f} MB"
    return f"{size / (1024 * 1024 * 1024):.1f} GB"


# ---- Funkcja formatuje date modyfikacji pliku ----
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

        # --- Loops tworzy checkbox dla kazdej kategorii plikow ---
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

    # ---- Funkcja zwraca kategorie wybrane przez uzytkownika ----
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

    # ---- Funkcja uruchamia ekstrakcje metadanych dla jednej kategorii ----
    def run(self):
        self.events.put(("status", self.category, "in progress"))
        extracted = []

        try:
            # --- Loops ekstraktuje kazdy plik z kategorii ---
            for index, path in enumerate(self.files):
                time.sleep(0.18)
                extracted.append(self.extract_file(path))

                # -- if ostatni plik daje krotka pauze dla widoku statusu --
                if index == len(self.files) - 1:
                    time.sleep(0.12)

            self.events.put(("status", self.category, "done"))
            self.events.put(("finished", self.category, extracted))
        except Exception:
            self.events.put(("status", self.category, "error"))
            self.events.put(("finished", self.category, extracted))

    # ---- Funkcja ekstraktuje metadane jednego pliku wedlug kategorii ----
    def extract_file(self, path):
        if self.category == "Audio":
            template = self.templates_by_type.get("audio")
            return extract_audio_metadata(path, template)

        base_record = {
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

        # -- if plik jest video, dodaje metadane video --
        if self.category == "Video":
            video_metadata = extract_video_metadata(path)
            base_record.update(video_metadata)

        # -- if plik jest PDF, dodaje metadane PDF --
        if self.category == "PDF":
            pdf_metadata = extract_pdf_metadata(path)
            base_record.update(pdf_metadata)

        # -- if plik jest Word, dodaje metadane Word --
        if self.category == "Word":
            word_metadata = extract_word_metadata(path)
            base_record.update(word_metadata)

        return base_record


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

        # --- Loops tworzy status dla kazdej kategorii ---
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

    # ---- Funkcja startuje watki ekstrakcji metadanych ----
    def start_extraction(self):
        if not self.categorized_files:
            self.progress.setRange(0, 1)
            self.progress.setValue(1)
            self.ok_button.setEnabled(True)
            return

        # --- Loops tworzy osobny watek dla kazdej kategorii ---
        for category, files in self.categorized_files.items():
            worker = ExtractionWorker(
                category, files, self.events, self.templates_by_type
            )
            thread = threading.Thread(target=worker.run, daemon=True)
            self.threads.append(thread)
            thread.start()

        self.poll_timer.start(80)

    # ---- Funkcja odbiera zdarzenia z watkow ekstrakcji ----
    def process_events(self):
        while not self.events.empty():
            event_type, category, payload = self.events.get()

            # -- if zdarzenie aktualizuje status kategorii --
            if event_type == "status":
                self.update_status(category, payload)
            elif event_type == "finished":
                self.collect_results(category, payload)
                self.check_finished()

    # ---- Funkcja aktualizuje tekst statusu kategorii ----
    def update_status(self, category, status):
        label = self.status_labels[category]
        label.setText(status)
        label.setObjectName(f"Status{status.title().replace(' ', '')}")
        label.style().unpolish(label)
        label.style().polish(label)

    # ---- Funkcja zbiera wyniki ekstrakcji ----
    def collect_results(self, _category, results):
        self.results.extend(results)

    # ---- Funkcja sprawdza czy wszystkie watki zakonczyly prace ----
    def check_finished(self):
        self.finished_count += 1

        # -- if wszystkie watki skonczyly, odblokowuje dialog --
        if self.finished_count == len(self.threads):
            self.poll_timer.stop()
            self.progress.setRange(0, 1)
            self.progress.setValue(1)
            self.ok_button.setEnabled(True)
            self.extraction_finished.emit(self.results)
