from pathlib import Path


WORD_METADATA_FIELDS = {
    "title": ["dc:title", "title"],
    "author": ["Author", "dc:creator", "meta:author", "author"],
    "subject": ["dc:subject", "subject"],
    "keywords": ["meta:keyword", "Keywords", "keywords"],
    "description": ["dc:description", "Comments", "description", "comments"],
    "created": ["dcterms:created", "Creation-Date", "created"],
    "modified_tika": ["dcterms:modified", "Last-Modified", "modified"],
    "last_author": ["Last-Author", "meta:last-author", "last_author"],
    "pages": ["xmpTPg:NPages", "Page-Count", "pages"],
    "word_count": ["Word-Count", "word_count"],
    "character_count": ["Character-Count", "character_count"],
    "paragraph_count": ["Paragraph-Count", "paragraph_count"],
    "table_count": ["Table-Count", "table_count", "tables"],
    "application_name": ["Application-Name", "producer", "application_name"],
    "content_type": ["Content-Type", "dc:format", "format"],
    "resource_name": ["resourceName", "resource_name", "filename", "fileName"],
    "parser_warning": ["X-TIKA:EXCEPTION:warn"],
}


# ---- Funkcja zwraca pusty zestaw metadanych Word ----
def empty_word_metadata(error_message=""):
    return {
        "title": "",
        "author": "",
        "subject": "",
        "keywords": "",
        "description": "",
        "created": "",
        "modified_tika": "",
        "last_author": "",
        "pages": "",
        "word_count": "",
        "character_count": "",
        "paragraph_count": "",
        "table_count": "",
        "application_name": "",
        "content_type": "",
        "resource_name": "",
        "parser_warning": error_message,
        "tika_metadata": {},
    }


# ---- Funkcja zamienia wartosc metadanych na tekst ----
def stringify_metadata_value(value):
    if value is None:
        return ""

    if isinstance(value, bytes):
        return value.decode("utf-8", errors="ignore")

    if isinstance(value, list):
        return ", ".join(str(item) for item in value if item is not None)

    text = str(value)

    # -- if Tika zwraca nazwe pliku jako tekst podobny do bytes --
    if len(text) > 3 and text.startswith("b'") and text.endswith("'"):
        return text[2:-1]

    if len(text) > 3 and text.startswith('b"') and text.endswith('"'):
        return text[2:-1]

    return text


# ---- Funkcja normalizuje nazwe klucza metadanych ----
def normalize_key(key):
    normalized_key = str(key).strip().lower()
    normalized_key = normalized_key.replace("-", "_")
    normalized_key = normalized_key.replace(" ", "_")
    return normalized_key


# ---- Funkcja pobiera pierwsza znaleziona wartosc metadanych ----
def get_metadata_value(metadata, possible_keys):
    normalized_metadata = {
        normalize_key(key): value for key, value in metadata.items()
    }

    # --- Loops najpierw sprawdza oryginalne nazwy kluczy ---
    for key in possible_keys:
        if key in metadata:
            return stringify_metadata_value(metadata[key])

    # --- Loops potem sprawdza uproszczone nazwy kluczy ---
    for key in possible_keys:
        normalized_key = normalize_key(key)

        if normalized_key in normalized_metadata:
            return stringify_metadata_value(normalized_metadata[normalized_key])

    return ""


# ---- Funkcja liczy slowa z tekstu dokumentu ----
def count_words(content):
    if not content:
        return ""

    words = str(content).split()
    return str(len(words))


# ---- Funkcja liczy znaki z tekstu dokumentu ----
def count_characters(content):
    if not content:
        return ""

    return str(len(str(content)))


# ---- Funkcja liczy akapity na podstawie niepustych linii tekstu ----
def count_paragraphs(content):
    if not content:
        return ""

    paragraphs = [line for line in str(content).splitlines() if line.strip()]
    return str(len(paragraphs))


# ---- Funkcja wyciaga metadane Word przy pomocy Tika ----
def extract_word_metadata(file_path):
    path = Path(file_path)

    try:
        from tika import parser

        parsed = parser.from_file(str(path)) or {}
        metadata = parsed.get("metadata") or {}
        content = parsed.get("content") or ""

        # -- if Tika nie zwrocila slownika metadanych --
        if not isinstance(metadata, dict):
            metadata = {}

        word_metadata = empty_word_metadata()
        word_metadata["tika_metadata"] = metadata

        # --- Loops przepisuje pola Tika na nasze nazwy ---
        for field_name, possible_keys in WORD_METADATA_FIELDS.items():
            word_metadata[field_name] = get_metadata_value(metadata, possible_keys)

        # -- if Tika nie podala licznikow, liczy dostepne wartosci z tekstu --
        if not word_metadata["word_count"]:
            word_metadata["word_count"] = count_words(content)

        if not word_metadata["character_count"]:
            word_metadata["character_count"] = count_characters(content)

        if not word_metadata["paragraph_count"]:
            word_metadata["paragraph_count"] = count_paragraphs(content)

        return word_metadata
    except Exception as error:
        return empty_word_metadata(str(error))
