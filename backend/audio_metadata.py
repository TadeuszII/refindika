import re
import time
import mimetypes
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

    if not metadata:
        fallback_metadata = read_mutagen_metadata(path)
        metadata.update(fallback_metadata)
    else:
        fallback_metadata = read_mutagen_metadata(path)
        for key, value in fallback_metadata.items():
            metadata.setdefault(key, value)

    record["tika_metadata"] = metadata

    for field_name, tika_keys in AUDIO_METADATA_FIELDS.items():
        record[field_name] = first_metadata_value(metadata, tika_keys)

    fill_missing_base_audio_values(path, record)
    record["custom_name"] = render_custom_name(template, record)
    return record


def fill_missing_base_audio_values(path: Path, record: dict) -> None:
    if not record.get("mime_type"):
        record["mime_type"] = mimetypes.guess_type(path.name)[0] or ""

    if not record.get("resource_name"):
        record["resource_name"] = path.name


def read_mutagen_metadata(path: Path) -> dict:
    try:
        from mutagen import File
    except ImportError:
        return {}

    try:
        audio_file = File(path, easy=True)
    except Exception:
        audio_file = None

    if audio_file is None:
        return {}

    metadata = {}
    info = getattr(audio_file, "info", None)

    if info is not None:
        if getattr(info, "length", None):
            metadata["duration"] = format_duration(info.length)
        if getattr(info, "sample_rate", None):
            metadata["sample_rate"] = str(info.sample_rate)
        if getattr(info, "channels", None):
            metadata["channels"] = str(info.channels)
        if getattr(info, "bitrate", None):
            metadata["bitrate"] = str(info.bitrate)
        if getattr(info, "codec", None):
            metadata["codec"] = str(info.codec)

    tag_aliases = {
        "title": ["title"],
        "artist": ["artist", "author", "albumartist", "performer"],
        "album": ["album"],
        "genre": ["genre"],
        "year": ["date", "year", "originaldate"],
        "track_number": ["tracknumber", "track"],
        "composer": ["composer"],
        "copyright": ["copyright"],
        "encoder": ["encodedby", "encoder"],
    }

    for target_key, source_keys in tag_aliases.items():
        metadata[target_key] = first_mutagen_tag(audio_file, source_keys)

    return {key: value for key, value in metadata.items() if value}


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
    normalized_metadata = normalize_metadata_keys(metadata)

    for key in keys:
        if key in metadata:
            return stringify_metadata_value(metadata[key])

    for key in keys:
        value = normalized_metadata.get(normalize_key(key))
        if value is not None:
            return stringify_metadata_value(value)

    for key in keys:
        normalized_key = normalize_key(key)
        suffix = normalized_key.split(":")[-1]

        for metadata_key, value in normalized_metadata.items():
            if metadata_key.endswith(":" + suffix) or metadata_key.endswith(suffix):
                return stringify_metadata_value(value)

    return ""


def normalize_metadata_keys(metadata: dict) -> dict:
    return {normalize_key(key): value for key, value in metadata.items()}


def normalize_key(key) -> str:
    return str(key).strip().lower().replace("-", "_").replace(" ", "_")


def stringify_metadata_value(value) -> str:
    if value is None:
        return ""

    if isinstance(value, list):
        return ", ".join(str(item) for item in value if item is not None)

    return str(value)


def first_mutagen_tag(audio_file, source_keys: list[str]) -> str:
    for key in source_keys:
        try:
            value = audio_file.get(key)
        except Exception:
            value = None

        text = stringify_metadata_value(value)
        if text:
            return text

    return ""


def format_duration(seconds) -> str:
    try:
        total_seconds = int(round(float(seconds)))
    except (TypeError, ValueError):
        return ""

    minutes, rest = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)

    if hours:
        return f"{hours}:{minutes:02d}:{rest:02d}"

    return f"{minutes}:{rest:02d}"


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
