import os

def format_time(seconds: float) -> str:

    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def validate_file_extension(filename: str, allowed_extensions: set) -> bool:

    ext = os.path.splitext(filename)[1].lower()
    return ext in allowed_extensions


def get_file_extension(filename: str) -> str:

    return os.path.splitext(filename)[1].lower()


def format_file_size(size_bytes: int) -> str:

    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"
