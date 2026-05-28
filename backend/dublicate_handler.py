IGNORED_DUPLICATE_FIELDS = {
    "name",
    "original_name",
    "resource_name",
    "custom_name",
    "modified",
    "modified_tika",
    "path",
    "size",
    "category",
    "extension",
    "file_type",
    "content_type",
    "mime_type",
    "tika_metadata",
    "metadata_error",
    "parser_warning",
}


# Funkcja dla sprawdzania, czy wartosc moze brac udzial w wykrywaniu duplikatow.
def has_duplicate_value(value):
    if value is None:
        return False

    text = str(value).strip()
    return text != ""


# Funkcja dla normalizacji pojedynczej wartosci metadanych.
def normalize_duplicate_value(value):
    return str(value).strip().lower()


# Funkcja dla budowania podpisu metadanych pliku.
def build_duplicate_signature(file_data):
    signature = []

    # Loops przechodzi po metadanych pliku i pomija pola techniczne.
    for key, value in sorted(file_data.items()):
        if key in IGNORED_DUPLICATE_FIELDS:
            continue

        if not has_duplicate_value(value):
            continue

        signature.append((key, normalize_duplicate_value(value)))

    return tuple(signature)


# Funkcja dla znalezienia indeksow plikow, ktore sa duplikatami.
def find_duplicate_indexes(files):
    signatures = {}

    # Loops grupuje pliki wedlug podpisu metadanych.
    for index, file_data in enumerate(files):
        signature = build_duplicate_signature(file_data)

        if not signature:
            continue

        signatures.setdefault(signature, []).append(index)

    duplicate_indexes = set()

    # Loops wybiera tylko grupy, gdzie jest wiecej niz jeden plik.
    for indexes in signatures.values():
        if len(indexes) > 1:
            duplicate_indexes.update(indexes)

    return duplicate_indexes
