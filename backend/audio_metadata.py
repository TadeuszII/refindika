import re
import time
from pathlib import Path


AUDIO_METADATA_FIELDS = {
    "mime_type": ["Content-Type", "dc:format", "format", "mime_type"],
    "resource_name": ["resourceName", "resource_name", "filename", "fileName"],
    "duration": ["xmpDM:duration", "duration", "length"],
    "sample_rate": [
        "xmpDM:audioSampleRate",
        "audioSampleRate",
        "sample_rate",
        "samplerate",
    ],
    "channels": [
        "channels",
        "xmpDM:audioChannelType",
        "audioChannelType",
        "channel_type",
    ],
    "bitrate": ["bitrate", "bit_rate", "xmpDM:audioCompressor"],
    "codec": ["xmpDM:audioCompressor", "audioCompressor", "encoder", "codec"],
    "title": ["dc:title", "title", "Title"],
    "artist": ["xmpDM:artist", "artist", "Author", "creator", "dc:creator"],
    "album": ["xmpDM:album", "album"],
    "genre": ["xmpDM:genre", "genre"],
    "year": ["xmpDM:releaseDate", "releaseDate", "date", "year"],
    "track_number": ["xmpDM:trackNumber", "trackNumber", "track", "track_number"],
    "composer": ["xmpDM:composer", "composer"],
    "copyright": ["dc:rights", "rights", "copyright"],
    "encoder": ["encoder", "xmpDM:audioCompressor", "audioCompressor"],
}


def extract_audio_metadata(file_path: Path, template: dict | None) -> dict:
    path = Path(file_path)
    record = build_base_record(path)

    try:
        metadata = read_tika_metadata(path)
    except Exception as error:
        record["metadata_error"] = str(error)
        metadata = {}

    record["tika_metadata"] = metadata

    for field_name, tika_keys in AUDIO_METADATA_FIELDS.items():
        record[field_name] = first_metadata_value(metadata, tika_keys)

    record["custom_name"] = render_custom_name(template, record)
    return record


def build_base_record(path: Path) -> dict:
    return {
        "name": path.name,
        "category": "Audio",
        "extension": path.suffix.lower() or "none",
        "original_name": path.name,
        "file_type": "audio",
        "modified": format_modified_time(path),
        "size": format_file_size(path.stat().st_size),
        "path": str(path),
        "custom_name": "",
        "metadata_error": "",
        "tika_metadata": {},
    }


def read_tika_metadata(path: Path) -> dict:
    from tika import parser

    parsed = parser.from_file(str(path)) or {}
    metadata = parsed.get("metadata") or {}

    if isinstance(metadata, dict):
        return metadata

    return {}


def first_metadata_value(metadata: dict, keys: list[str]) -> str:
    normalized_metadata = {}

    # --- Loops tworzy prostsze nazwy kluczy do porownania ---
    for key, value in metadata.items():
        normalized_metadata[normalize_key(key)] = value

    # --- Loops najpierw sprawdza oryginalne nazwy kluczy ---
    for key in keys:
        if key in metadata:
            return stringify_metadata_value(metadata[key])

    # --- Loops potem sprawdza uproszczone nazwy kluczy ---
    for key in keys:
        value = normalized_metadata.get(normalize_key(key))
        if value is not None:
            return stringify_metadata_value(value)

    return ""


def normalize_key(key) -> str:
    normalized_key = str(key).strip().lower()
    normalized_key = normalized_key.replace("-", "_")
    normalized_key = normalized_key.replace(" ", "_")
    return normalized_key


def stringify_metadata_value(value) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        return ", ".join(str(item) for item in value if item is not None)

    return str(value)


def render_custom_name(template: dict | None, record: dict) -> str:
    pattern = ""

    if template:
        pattern = template.get("Template", "")

    if not pattern:
        return record.get("original_name", "")

    def replace_placeholder(match):
        metadata_name = match.group(1)
        return str(record.get(metadata_name, ""))

    return re.sub(r"{([^{}]+)}", replace_placeholder, pattern)


def format_file_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    if size < 1024 * 1024:
        return f"{size / 1024:.0f} KB"
    if size < 1024 * 1024 * 1024:
        return f"{size / (1024 * 1024):.0f} MB"
    return f"{size / (1024 * 1024 * 1024):.1f} GB"


def format_modified_time(path: Path) -> str:
    return time.strftime("%d.%m.%Y %H:%M", time.localtime(path.stat().st_mtime))
