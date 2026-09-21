"""
MeetCore — Upload Validation
Runs before anything is forwarded to AssemblyAI. Keeps garbage out.
"""
from app.core.config import get_settings

settings = get_settings()


class ValidationError(Exception):
    pass


def validate_upload(filename: str, file_size_bytes: int) -> None:
    """
    Raises ValidationError with a clear, user-facing message if the file
    fails either check. Does not touch file content — format is checked
    by extension only at this layer; deeper validation (corrupt files,
    actual codec) is left to AssemblyAI's own error response.
    """
    lower_name = filename.lower()
    if not lower_name.endswith(settings.ALLOWED_AUDIO_FORMATS):
        raise ValidationError(
            f"Unsupported file format. MeetCore accepts: "
            f"{', '.join(settings.ALLOWED_AUDIO_FORMATS)}"
        )

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file_size_bytes > max_bytes:
        raise ValidationError(
            f"File too large. Max size is {settings.MAX_UPLOAD_SIZE_MB}MB, "
            f"yours is {file_size_bytes / (1024 * 1024):.1f}MB."
        )

    if file_size_bytes == 0:
        raise ValidationError("File appears to be empty.")
