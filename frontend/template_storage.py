import json
import re
from pathlib import Path


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
        "custom_name",
        "file_type",
        "modified",
        "path",
        "title",
        "author",
        "subject",
        "keywords",
        "description",
        "created",
        "modified_tika",
        "last_author",
        "pages",
        "word_count",
        "character_count",
        "paragraph_count",
        "table_count",
        "application_name",
        "content_type",
        "resource_name",
        "parser_warning",
    ],
}


# ---- Funkcja normalizuje typ pliku do nazwy uzywanej w programie ----
def normalize_file_type(file_type):
    for known_type in METADATA_BY_TYPE:
        if known_type.lower() == str(file_type).lower():
            return known_type
    return str(file_type)


# ---- Funkcja zwraca sciezke do pliku z template uzytkownika ----
def get_templates_file():
    project_folder = Path(__file__).resolve().parent.parent
    data_folder = project_folder / "data"
    return data_folder / "templates.json"


# ---- Funkcja zwraca sciezke do pliku z domyslnymi template ----
def get_default_templates_file():
    project_folder = Path(__file__).resolve().parent.parent
    data_folder = project_folder / "data"
    return data_folder / "default_template.json"


# ---- Funkcja normalizuje template do jednego formatu danych ----
def normalize_template(template_data):
    file_type = template_data.get("Type", template_data.get("file_type", ""))
    normalized_type = normalize_file_type(file_type)

    normalized_template = {
        "Name": template_data.get("Name", template_data.get("name", "")),
        "Type": normalized_type.lower(),
        "Template": template_data.get("Template", template_data.get("pattern", "")),
    }

    # --- Loops przenosi zapisane ustawienia checkboxow metadanych ---
    if normalized_type in METADATA_BY_TYPE:
        for metadata_name in METADATA_BY_TYPE[normalized_type]:
            normalized_template[metadata_name] = template_data.get(
                metadata_name, True
            )

    return normalized_template


# ---- Funkcja wczytuje liste template z podanego pliku json ----
def read_templates_file(file_path):
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


# ---- Funkcja zapisuje templates uzytkownika do pliku json ----
def save_templates_file(file_path, templates):
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with file_path.open("w", encoding="utf-8") as file:
        json.dump(templates, file, indent=4)


# ---- Funkcja sprawdza czy template moze byc zapisany albo uzyty ----
def validate_template(template_data):
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

    template_without_placeholders = re.sub(r"{[^{}]+}", "", pattern)

    # -- if sprawdza czy klamry sa poprawnie zamkniete --
    if "{" in template_without_placeholders or "}" in template_without_placeholders:
        errors.append("Check curly brackets in template.")

    return errors


# ---- Funkcja sprawdza czy dwa templates maja ta sama nazwe i typ ----
def is_same_template(first_template, second_template):
    first_name = first_template.get("Name", first_template.get("name", ""))
    second_name = second_template.get("Name", second_template.get("name", ""))
    first_type = first_template.get("Type", first_template.get("file_type", ""))
    second_type = second_template.get("Type", second_template.get("file_type", ""))

    same_name = first_name.lower() == second_name.lower()
    same_type = first_type.lower() == second_type.lower()
    return same_name and same_type
