import re
from pathlib import Path


FORBIDDEN_CHARACTERS = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']


# ---- Funkcja buduje nowa nazwe z template i metadanych pliku ----
def render_custom_name(template, record):
    pattern = ""

    # -- if template istnieje, pobiera pattern nazwy pliku --
    if template:
        pattern = template.get("Template", "")

    # -- if pattern jest pusty, zostawia obecna nazwe pliku --
    if not pattern:
        return record.get("original_name", record.get("name", ""))

    # ---- Funkcja zamienia placeholder na wartosc metadanej ----
    def replace_placeholder(match):
        metadata_name = match.group(1)
        return str(record.get(metadata_name, ""))

    return re.sub(r"{([^{}]+)}", replace_placeholder, pattern)


# ---- Funkcja usuwa znaki niedozwolone w nazwach plikow Windows ----
def clean_file_name(file_name):
    clean_name = str(file_name).strip()

    # --- Loops zamienia zakazane znaki na podkreslenie ---
    for character in FORBIDDEN_CHARACTERS:
        clean_name = clean_name.replace(character, "_")

    clean_name = clean_name.strip().strip(".")
    return clean_name


# ---- Funkcja buduje unikalna sciezke dla nowej nazwy pliku ----
def build_unique_path(old_path, new_name):
    path = Path(old_path)
    suffix = path.suffix
    clean_name = clean_file_name(new_name)

    # -- if user dodal rozszerzenie w template, nie dodaje go drugi raz --
    if suffix and clean_name.lower().endswith(suffix.lower()):
        clean_name = clean_name[: -len(suffix)]
        clean_name = clean_name.strip().strip(".")

    if not clean_name:
        raise ValueError("New file name is empty.")

    new_path = path.with_name(clean_name + suffix)

    # -- if nowa sciezka jest taka sama, rename nie jest potrzebny --
    if new_path == path:
        return new_path

    counter = 1

    # --- Loops szuka wolnej nazwy pliku ---
    while new_path.exists():
        new_path = path.with_name(f"{clean_name}_{counter}{suffix}")
        counter += 1

    return new_path


# ---- Funkcja zmienia nazwe pliku i aktualizuje rekord ----
def rename_file(record, template):
    old_path = Path(record.get("path", ""))
    new_name = render_custom_name(template, record)
    new_path = build_unique_path(old_path, new_name)

    # -- if plik ma otrzymac nowa sciezke, robi rename na dysku --
    if new_path != old_path:
        old_path.rename(new_path)

    record["name"] = new_path.name
    record["original_name"] = new_path.name
    record["custom_name"] = new_path.name
    record["extension"] = new_path.suffix.lower() or "none"
    record["path"] = str(new_path)

    return record
