from pathlib import Path

from tika import parser


VIDEO_METADATA_FIELDS = {
    "content_type": ["Content-Type", "dc:format", "format"],
    "resource_name": ["resourceName", "resource_name", "filename", "fileName"],
    "duration": ["xmpDM:duration", "duration"],
    "width": ["tiff:ImageWidth", "Image Width", "width"],
    "height": ["tiff:ImageLength", "Image Height", "height"],
    "video_compressor": [
        "xmpDM:videoCompressor",
        "videoCompressor",
        "compressor",
        "codec",
    ],
    "audio_sample_rate": [
        "xmpDM:audioSampleRate",
        "audioSampleRate",
        "sample_rate",
    ],
    "audio_channel_type": [
        "xmpDM:audioChannelType",
        "audioChannelType",
        "channels",
    ],
    "audio_compressor": ["xmpDM:audioCompressor", "audioCompressor"],
    "created": ["dcterms:created", "created", "Creation-Date"],
    "modified_tika": ["dcterms:modified", "modified", "Last-Modified"],
    "latitude": ["geo:lat", "latitude", "GPS Latitude"],
    "longitude": ["geo:long", "longitude", "GPS Longitude"],
    "parser_warning": ["X-TIKA:EXCEPTION:warn"],
}


# ---- Funkcja zwraca pusty zestaw metadanych video ----
def empty_video_metadata(error_message=""):
    return {
        "content_type": "",
        "resource_name": "",
        "duration": "",
        "width": "",
        "height": "",
        "resolution": "",
        "video_compressor": "",
        "audio_sample_rate": "",
        "audio_channel_type": "",
        "audio_compressor": "",
        "created": "",
        "modified_tika": "",
        "latitude": "",
        "longitude": "",
        "parser_warning": error_message,
        "tika_metadata": {},
    }


# ---- Funkcja zamienia wartosc metadanych na tekst ----
def stringify_metadata_value(value):
    if value is None:
        return ""

    if isinstance(value, list):
        return ", ".join(str(item) for item in value if item is not None)

    return str(value)


# ---- Funkcja pobiera pierwsza znaleziona wartosc metadanych ----
def get_metadata_value(metadata, possible_keys):
    normalized_metadata = {
        str(key).strip().lower().replace("-", "_").replace(" ", "_"): value
        for key, value in metadata.items()
    }

    for key in possible_keys:
        if key in metadata:
            return stringify_metadata_value(metadata[key])

    for key in possible_keys:
        normalized_key = str(key).strip().lower().replace("-", "_").replace(" ", "_")
        if normalized_key in normalized_metadata:
            return stringify_metadata_value(normalized_metadata[normalized_key])

    return ""


# ---- Funkcja buduje rozdzielczosc z szerokosci i wysokosci ----
def build_resolution(width, height):
    if width and height:
        return f"{width}x{height}"

    return ""


# ---- Funkcja wyciaga metadane video przy pomocy Tika ----
def extract_video_metadata(file_path):
    path = Path(file_path)

    try:
        parsed = parser.from_file(str(path)) or {}
        metadata = parsed.get("metadata") or {}

        # -- if Tika nie zwrocila slownika metadanych --
        if not isinstance(metadata, dict):
            metadata = {}

        video_metadata = empty_video_metadata()
        video_metadata["tika_metadata"] = metadata

        # --- Loops przepisuje pola Tika na nasze nazwy ---
        for field_name, possible_keys in VIDEO_METADATA_FIELDS.items():
            video_metadata[field_name] = get_metadata_value(metadata, possible_keys)

        video_metadata["resolution"] = build_resolution(
            video_metadata["width"], video_metadata["height"]
        )
        return video_metadata
    except Exception as error:
        return empty_video_metadata(str(error))
