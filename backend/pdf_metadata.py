from pathlib import Path


PDF_METADATA_FIELDS = {
    "content_type": ["Content-Type", "dc:format", "format"],
    "resource_name": ["resourceName", "resource_name", "filename", "fileName"],
    "title": ["dc:title", "title", "pdf:docinfo:title"],
    "author": ["dc:creator", "Author", "author", "pdf:docinfo:creator"],
    "creator": ["xmp:CreatorTool", "pdf:docinfo:creator_tool", "creator"],
    "producer": ["pdf:producer", "pdf:docinfo:producer", "producer"],
    "created": ["dcterms:created", "xmp:CreateDate", "pdf:docinfo:created"],
    "modified_tika": [
        "dcterms:modified",
        "xmp:ModifyDate",
        "xmp:MetadataDate",
        "pdf:docinfo:modified",
    ],
    "pages": ["xmpTPg:NPages", "pdf:docinfo:numpages", "pages"],
    "pdf_version": ["pdf:PDFVersion", "pdf_version"],
    "encrypted": ["pdf:encrypted", "encrypted"],
    "parser_warning": ["X-TIKA:EXCEPTION:warn"],
}


# ---- Funkcja zwraca pusty zestaw metadanych pdf ----
def empty_pdf_metadata(error_message=""):
    return {
        "content_type": "",
        "resource_name": "",
        "title": "",
        "author": "",
        "creator": "",
        "producer": "",
        "created": "",
        "modified_tika": "",
        "pages": "",
        "pdf_version": "",
        "encrypted": "",
        "word_count": "",
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


# ---- Funkcja pobiera pierwsza znaleziona wartosc metadanych ----
def get_metadata_value(metadata, possible_keys):
    normalized_metadata = {}

    # --- Loops tworzy prostsze nazwy kluczy do porownania ---
    for key, value in metadata.items():
        normalized_key = str(key).strip().lower()
        normalized_key = normalized_key.replace("-", "_")
        normalized_key = normalized_key.replace(" ", "_")
        normalized_metadata[normalized_key] = value

    # --- Loops najpierw sprawdza oryginalne nazwy kluczy ---
    for key in possible_keys:
        if key in metadata:
            return stringify_metadata_value(metadata[key])

    # --- Loops potem sprawdza uproszczone nazwy kluczy ---
    for key in possible_keys:
        normalized_key = str(key).strip().lower()
        normalized_key = normalized_key.replace("-", "_")
        normalized_key = normalized_key.replace(" ", "_")

        if normalized_key in normalized_metadata:
            return stringify_metadata_value(normalized_metadata[normalized_key])

    return ""


# ---- Funkcja liczy slowa z tekstu pdf ----
def count_words(content):
    if not content:
        return ""

    words = str(content).split()
    return str(len(words))


# ---- Funkcja wyciaga metadane pdf przy pomocy Tika ----
def extract_pdf_metadata(file_path):
    path = Path(file_path)

    try:
        from tika import parser

        parsed = parser.from_file(str(path)) or {}
        metadata = parsed.get("metadata") or {}
        content = parsed.get("content") or ""

        # -- if Tika nie zwrocila slownika metadanych --
        if not isinstance(metadata, dict):
            metadata = {}

        pdf_metadata = empty_pdf_metadata()
        pdf_metadata["tika_metadata"] = metadata

        # --- Loops przepisuje pola Tika na nasze nazwy ---
        for field_name, possible_keys in PDF_METADATA_FIELDS.items():
            pdf_metadata[field_name] = get_metadata_value(metadata, possible_keys)

        pdf_metadata["word_count"] = count_words(content)
        return pdf_metadata
    except Exception as error:
        return empty_pdf_metadata(str(error))
